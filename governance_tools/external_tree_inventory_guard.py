#!/usr/bin/env python3
"""Detect bulk Git-tree inventories that identify an external repository.

Path-based CI scans and pre-push Git-object scans share the same identity,
decoding, and classification semantics.  The pre-push mode scans the
newly-reachable object closure described by updated-ref pairs; it does not
claim byte-for-byte equivalence with Git's wire pack.

Exit codes used by the CLI:
  0 — no externally identified bulk tree inventory was found
  1 — an externally identified bulk tree inventory was found
  2 — a JSON input could not be decoded or parsed
  3 — a bulk tree inventory lacks reliable repository identity
"""

from __future__ import annotations

import argparse
import codecs
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, TextIO
from urllib.parse import urlparse


STATUS_PASS = "PASS"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNREADABLE = "UNREADABLE"
STATUS_UNATTRIBUTED_BULK_INVENTORY = "UNATTRIBUTED_BULK_INVENTORY"
DEFAULT_ENTRY_THRESHOLD = 100
IDENTITY_CONFIG_SCHEMA = "external-tree-inventory-guard-identities.v1"
REPOSITORY_ROOT_TOKEN = "@repository-root"
SCANNER_ERROR_EXIT = 4
_OID_PATTERN = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")

_PATH_KEYS = ("path", "repo_path", "relative_path")
_OID_KEYS = ("oid", "blob_oid", "git_oid")
_REPOSITORY_ID_KEYS = {
    "repository",
    "repository_id",
    "repository_name",
    "repo",
    "repo_id",
    "repo_name",
    "source_repository",
    "consumer_repository",
}


@dataclass(frozen=True)
class CollectionEntryCount:
    json_path: str
    distinct_entry_count: int


@dataclass(frozen=True)
class CollectionFinding:
    json_path: str
    distinct_entry_count: int
    source_repository_identities: tuple[str, ...]
    status: str
    reason: str
    collection_entry_counts: tuple[CollectionEntryCount, ...]


@dataclass(frozen=True)
class _CollectionObservation:
    json_path: str
    entries: frozenset[tuple[str, str]]
    source_repository_identities: tuple[str, ...]


@dataclass(frozen=True)
class GuardResult:
    status: str
    threshold: int
    findings: tuple[CollectionFinding, ...]
    reason: str


@dataclass(frozen=True)
class PrePushUpdate:
    local_ref: str
    local_oid: str
    remote_ref: str
    remote_oid: str


@dataclass(frozen=True)
class BlobAssessment:
    oid: str
    path: str
    result: GuardResult


@dataclass(frozen=True)
class PrePushScanResult:
    update_count: int
    json_blob_count: int
    assessments: tuple[BlobAssessment, ...]


class IdentityConfigError(ValueError):
    """The shared repository identity configuration is unusable."""


class PrePushScanError(RuntimeError):
    """The updated-ref object closure could not be scanned safely."""


def _normalize_repository_identity(value: str) -> str:
    """Normalize an explicitly supplied identity without guessing aliases."""

    text = value.strip().replace("\\", "/")
    if not text:
        return ""

    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        text = parsed.path

    text = text.split("?", 1)[0].split("#", 1)[0].strip("/")
    if text.lower().endswith(".git"):
        text = text[:-4]
    return text.casefold()


def decode_json_bytes(raw: bytes) -> Any:
    """Decode supported JSON byte encodings without working-tree mediation."""

    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise ValueError("json_unreadable:UnsupportedEncoding:utf-32")
    if raw.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
    elif raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    else:
        encoding = "utf-8"

    try:
        return json.loads(raw.decode(encoding))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"json_unreadable:{type(exc).__name__}") from exc


def load_repository_identities(config_path: Path, *, repository_root: Path) -> tuple[str, ...]:
    """Load the one shared identity authority used by CI and pre-push."""

    try:
        document = decode_json_bytes(config_path.read_bytes())
    except OSError as exc:
        raise IdentityConfigError(
            f"repository identity config is unreadable: {config_path}: {type(exc).__name__}"
        ) from exc
    except ValueError as exc:
        raise IdentityConfigError(
            f"repository identity config is invalid: {config_path}: {exc}"
        ) from exc

    if not isinstance(document, dict) or document.get("schema") != IDENTITY_CONFIG_SCHEMA:
        raise IdentityConfigError(
            f"repository identity config schema must be {IDENTITY_CONFIG_SCHEMA}: {config_path}"
        )
    configured = document.get("repository_identities")
    if not isinstance(configured, list) or not configured:
        raise IdentityConfigError(
            f"repository identity config has no identities: {config_path}"
        )

    identities: list[str] = []
    for value in configured:
        if not isinstance(value, str) or not value.strip():
            raise IdentityConfigError(
                f"repository identity config contains a non-string or empty identity: {config_path}"
            )
        resolved = str(repository_root.resolve()) if value == REPOSITORY_ROOT_TOKEN else value
        if not _normalize_repository_identity(resolved):
            raise IdentityConfigError(
                f"repository identity config contains an unusable identity: {config_path}"
            )
        identities.append(resolved)
    return tuple(identities)


def _repository_identities(value: Any) -> set[str]:
    """Extract explicit repository identities from a declared identity value."""

    if isinstance(value, str):
        normalized = _normalize_repository_identity(value)
        return {normalized} if normalized else set()

    if not isinstance(value, dict):
        return set()

    identities: set[str] = set()
    for key in ("full_name", "slug", "url", "html_url", "path", "root"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            normalized = _normalize_repository_identity(candidate)
            if normalized:
                identities.add(normalized)

    owner = value.get("owner")
    name = value.get("name")
    if isinstance(owner, str) and isinstance(name, str):
        normalized = _normalize_repository_identity(f"{owner}/{name}")
        if normalized:
            identities.add(normalized)
    elif isinstance(name, str):
        normalized = _normalize_repository_identity(name)
        if normalized:
            identities.add(normalized)

    return identities


def _direct_repository_identities(node: dict[str, Any]) -> set[str]:
    identities: set[str] = set()
    for key, value in node.items():
        if key.casefold() in _REPOSITORY_ID_KEYS:
            identities.update(_repository_identities(value))
    return identities


def _string_field(item: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _bulk_entries(node: list[Any]) -> frozenset[tuple[str, str]]:
    distinct_entries: set[tuple[str, str]] = set()
    for item in node:
        if not isinstance(item, dict):
            continue
        path = _string_field(item, _PATH_KEYS)
        oid = _string_field(item, _OID_KEYS)
        if path is not None and oid is not None:
            distinct_entries.add((path, oid))
    return frozenset(distinct_entries)


def _json_path(parent: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}" if parent != "$" else f"$.{key}"


def _collect_observations(
    node: Any,
    *,
    inherited_identities: set[str],
    path: str,
) -> list[_CollectionObservation]:
    observations: list[_CollectionObservation] = []

    if isinstance(node, dict):
        current_identities = inherited_identities | _direct_repository_identities(node)
        for key, value in node.items():
            observations.extend(
                _collect_observations(
                    value,
                    inherited_identities=current_identities,
                    path=_json_path(path, key),
                )
            )
        return observations

    if not isinstance(node, list):
        return observations

    entries = _bulk_entries(node)
    if entries:
        observations.append(
            _CollectionObservation(
                json_path=path,
                entries=entries,
                source_repository_identities=tuple(sorted(inherited_identities)),
            )
        )

    for index, value in enumerate(node):
        observations.extend(
            _collect_observations(
                value,
                inherited_identities=inherited_identities,
                path=_json_path(path, index),
            )
        )
    return observations


def _aggregate_findings(
    observations: Sequence[_CollectionObservation],
    *,
    expected_identities: set[str],
    threshold: int,
) -> tuple[CollectionFinding, ...]:
    grouped: dict[tuple[str, ...], list[_CollectionObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.source_repository_identities, []).append(observation)

    findings: list[CollectionFinding] = []
    for identities, group in sorted(grouped.items()):
        document_entries = set().union(*(observation.entries for observation in group))
        if len(document_entries) < threshold:
            continue

        identity_set = set(identities)
        external = sorted(identity_set - expected_identities)
        if external:
            status = STATUS_BLOCKED
            reason = "bulk_tree_inventory_explicitly_identifies_external_repository"
        elif not identity_set:
            status = STATUS_UNATTRIBUTED_BULK_INVENTORY
            reason = "bulk_tree_inventory_has_no_reliable_repository_identity"
        else:
            status = STATUS_PASS
            reason = "bulk_tree_inventory_identifies_expected_repository"

        collection_counts = tuple(
            CollectionEntryCount(
                json_path=observation.json_path,
                distinct_entry_count=len(observation.entries),
            )
            for observation in group
        )
        findings.append(
            CollectionFinding(
                json_path=(collection_counts[0].json_path if len(collection_counts) == 1 else "$"),
                distinct_entry_count=len(document_entries),
                source_repository_identities=identities,
                status=status,
                reason=reason,
                collection_entry_counts=collection_counts,
            )
        )
    return tuple(findings)


def assess_document(
    document: Any,
    *,
    expected_repository_identities: Sequence[str],
    entry_threshold: int = DEFAULT_ENTRY_THRESHOLD,
) -> GuardResult:
    """Classify one decoded JSON document.

    ``UNATTRIBUTED_BULK_INVENTORY`` is deliberately distinct from ``PASS``.
    A bulk path/OID collection without reliable repository identity cannot
    support a safety claim.  Decoding and parsing failures are classified by
    :func:`assess_path` as ``UNREADABLE`` instead of being conflated with this
    document-level result.
    """

    if entry_threshold < 1:
        raise ValueError("entry_threshold must be at least 1")

    expected = {
        normalized
        for value in expected_repository_identities
        if (normalized := _normalize_repository_identity(value))
    }
    if not expected:
        raise ValueError("at least one non-empty expected repository identity is required")

    observations = _collect_observations(
        document,
        inherited_identities=set(),
        path="$",
    )
    findings = _aggregate_findings(
        observations,
        expected_identities=expected,
        threshold=entry_threshold,
    )

    if any(item.status == STATUS_BLOCKED for item in findings):
        return GuardResult(
            status=STATUS_BLOCKED,
            threshold=entry_threshold,
            findings=findings,
            reason="external_bulk_tree_inventory_detected",
        )
    if any(item.status == STATUS_UNATTRIBUTED_BULK_INVENTORY for item in findings):
        return GuardResult(
            status=STATUS_UNATTRIBUTED_BULK_INVENTORY,
            threshold=entry_threshold,
            findings=findings,
            reason="unattributed_bulk_tree_inventory_detected",
        )
    return GuardResult(
        status=STATUS_PASS,
        threshold=entry_threshold,
        findings=findings,
        reason=("only_expected_repository_bulk_inventories_detected" if findings else "no_bulk_tree_inventory_detected"),
    )


def assess_path(
    path: Path,
    *,
    expected_repository_identities: Sequence[str],
    entry_threshold: int = DEFAULT_ENTRY_THRESHOLD,
) -> GuardResult:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return GuardResult(
            status=STATUS_UNREADABLE,
            threshold=entry_threshold,
            findings=(),
            reason=f"json_unreadable:{type(exc).__name__}",
        )
    return assess_bytes(
        raw,
        expected_repository_identities=expected_repository_identities,
        entry_threshold=entry_threshold,
    )


def assess_bytes(
    raw: bytes,
    *,
    expected_repository_identities: Sequence[str],
    entry_threshold: int = DEFAULT_ENTRY_THRESHOLD,
) -> GuardResult:
    """Classify raw JSON bytes using the same encoding contract as path scans."""

    try:
        document = decode_json_bytes(raw)
    except ValueError as exc:
        return GuardResult(
            status=STATUS_UNREADABLE,
            threshold=entry_threshold,
            findings=(),
            reason=str(exc),
        )
    return assess_document(
        document,
        expected_repository_identities=expected_repository_identities,
        entry_threshold=entry_threshold,
    )


def _is_zero_oid(value: str) -> bool:
    return bool(value) and set(value) == {"0"} and len(value) in (40, 64)


def parse_pre_push_updates(stream: TextIO) -> tuple[PrePushUpdate, ...]:
    updates: list[PrePushUpdate] = []
    for line_number, raw_line in enumerate(stream, start=1):
        line = raw_line.rstrip("\r\n")
        if not line:
            continue
        fields = line.split()
        if len(fields) != 4:
            raise PrePushScanError(
                f"malformed pre-push update at line {line_number}: expected four fields"
            )
        local_ref, local_oid, remote_ref, remote_oid = fields
        if not _OID_PATTERN.fullmatch(local_oid) or not _OID_PATTERN.fullmatch(remote_oid):
            raise PrePushScanError(
                f"malformed pre-push update at line {line_number}: invalid object ID"
            )
        if len(local_oid) != len(remote_oid):
            raise PrePushScanError(
                f"malformed pre-push update at line {line_number}: object ID lengths differ"
            )
        updates.append(PrePushUpdate(local_ref, local_oid.lower(), remote_ref, remote_oid.lower()))
    if not updates:
        raise PrePushScanError("pre-push update stream is empty")
    return tuple(updates)


def _git_object_exists(repository_root: Path, oid: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), "cat-file", "-e", f"{oid}^{{object}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode == 0


def _enumerate_json_blob_candidates(
    repository_root: Path,
    updates: Sequence[PrePushUpdate],
) -> dict[str, set[str]]:
    candidates: dict[str, set[str]] = {}
    for update in updates:
        if _is_zero_oid(update.local_oid):
            continue
        if not _git_object_exists(repository_root, update.local_oid):
            raise PrePushScanError(
                f"local object is unavailable: {update.local_oid} ({update.local_ref})"
            )

        command = [
            "git",
            "-C",
            str(repository_root),
            "rev-list",
            "--objects",
            "-z",
            update.local_oid,
        ]
        if not _is_zero_oid(update.remote_oid):
            if not _git_object_exists(repository_root, update.remote_oid):
                raise PrePushScanError(
                    "remote old object is unavailable locally: "
                    f"{update.remote_oid} ({update.remote_ref}); run git fetch before pushing"
                )
            command.append(f"^{update.remote_oid}")

        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise PrePushScanError(
                f"git rev-list failed for {update.remote_ref}: {detail or 'no diagnostic'}"
            )

        current_oid: str | None = None
        for record in completed.stdout.split(b"\0"):
            if not record:
                continue
            if record.startswith(b"path="):
                if current_oid is None:
                    raise PrePushScanError("git rev-list emitted a path without an object ID")
                path = record[5:].decode("utf-8", errors="surrogateescape")
                if path.casefold().endswith(".json"):
                    candidates.setdefault(current_oid, set()).add(path)
                current_oid = None
                continue

            try:
                token = record.decode("ascii", errors="strict")
            except UnicodeDecodeError as exc:
                raise PrePushScanError(
                    "git rev-list emitted a non-ASCII object ID record"
                ) from exc
            if not _OID_PATTERN.fullmatch(token):
                raise PrePushScanError("git rev-list emitted an invalid object ID record")
            current_oid = token.lower()
    return candidates


def _read_blob_batch(repository_root: Path, oids: Sequence[str]) -> dict[str, bytes]:
    if not oids:
        return {}
    process = subprocess.Popen(
        ["git", "-C", str(repository_root), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    query = b"".join(oid.encode("ascii") + b"\n" for oid in oids)
    stdout, stderr = process.communicate(query)
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise PrePushScanError(f"git cat-file --batch failed: {detail or 'no diagnostic'}")

    blobs: dict[str, bytes] = {}
    offset = 0
    for requested_oid in oids:
        header_end = stdout.find(b"\n", offset)
        if header_end < 0:
            raise PrePushScanError("git cat-file --batch returned a truncated header")
        header = stdout[offset:header_end].decode("ascii", errors="replace")
        offset = header_end + 1
        parts = header.split()
        if len(parts) == 2 and parts[1] == "missing":
            raise PrePushScanError(f"git cat-file reports missing object: {requested_oid}")
        if len(parts) != 3:
            raise PrePushScanError(f"git cat-file returned an invalid header: {header}")
        returned_oid, object_type, size_text = parts
        if returned_oid.lower() != requested_oid.lower():
            raise PrePushScanError(
                f"git cat-file returned unexpected object {returned_oid} for {requested_oid}"
            )
        if object_type != "blob":
            raise PrePushScanError(
                f"JSON path resolves to unsupported Git object type {object_type}: {requested_oid}"
            )
        try:
            size = int(size_text)
        except ValueError as exc:
            raise PrePushScanError(f"git cat-file returned an invalid size: {header}") from exc
        end = offset + size
        if end >= len(stdout) or stdout[end : end + 1] != b"\n":
            raise PrePushScanError(f"git cat-file returned truncated blob bytes: {requested_oid}")
        blobs[requested_oid] = stdout[offset:end]
        offset = end + 1
    if offset != len(stdout):
        raise PrePushScanError("git cat-file --batch returned unexpected trailing bytes")
    return blobs


def scan_pre_push_updates(
    repository_root: Path,
    updates: Sequence[PrePushUpdate],
    *,
    expected_repository_identities: Sequence[str],
    entry_threshold: int = DEFAULT_ENTRY_THRESHOLD,
) -> PrePushScanResult:
    """Assess JSON blobs in the per-ref newly-reachable object union."""

    candidates = _enumerate_json_blob_candidates(repository_root, updates)
    ordered_oids = sorted(candidates)
    blobs = _read_blob_batch(repository_root, ordered_oids)
    assessments = tuple(
        BlobAssessment(
            oid=oid,
            path=sorted(candidates[oid])[0],
            result=assess_bytes(
                blobs[oid],
                expected_repository_identities=expected_repository_identities,
                entry_threshold=entry_threshold,
            ),
        )
        for oid in ordered_oids
    )
    return PrePushScanResult(
        update_count=len(updates),
        json_blob_count=len(ordered_oids),
        assessments=assessments,
    )


def _format_human(path: Path, result: GuardResult) -> str:
    lines = [
        f"file: {path}",
        f"status: {result.status}",
        f"reason: {result.reason}",
        f"entry_threshold: {result.threshold}",
    ]
    for finding in result.findings:
        identities = ",".join(finding.source_repository_identities) or "<unknown>"
        lines.append(
            "finding: "
            f"path={finding.json_path} entries={finding.distinct_entry_count} "
            f"repositories={identities} status={finding.status} reason={finding.reason}"
        )
        for collection in finding.collection_entry_counts:
            lines.append(
                "collection: "
                f"path={collection.json_path} entries={collection.distinct_entry_count}"
            )
    return "\n".join(lines)


def _result_exit_code(results: Iterable[GuardResult]) -> int:
    statuses = {result.status for result in results}
    if STATUS_BLOCKED in statuses:
        return 1
    if STATUS_UNATTRIBUTED_BULK_INVENTORY in statuses:
        return 3
    if STATUS_UNREADABLE in statuses:
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify JSON files for externally identified bulk Git-tree inventories."
    )
    parser.add_argument("files", nargs="*", type=Path)
    identity_group = parser.add_mutually_exclusive_group(required=True)
    identity_group.add_argument(
        "--repository-id",
        action="append",
        dest="repository_ids",
        help="Expected repository identity; repeat for exact aliases such as owner/name and URL.",
    )
    identity_group.add_argument(
        "--identity-config",
        type=Path,
        help="Shared repository identity configuration used by CI and pre-push.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--pre-push-updates",
        action="store_true",
        help="Read pre-push updated-ref pairs from stdin and scan raw Git object bytes.",
    )
    parser.add_argument("--entry-threshold", type=int, default=DEFAULT_ENTRY_THRESHOLD)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    try:
        repository_ids = (
            load_repository_identities(args.identity_config, repository_root=args.repo_root)
            if args.identity_config is not None
            else tuple(args.repository_ids)
        )
    except IdentityConfigError as exc:
        print(f"status: ERROR\nreason: {exc}", file=sys.stderr)
        return SCANNER_ERROR_EXIT

    if args.pre_push_updates:
        if args.files:
            parser.error("file paths cannot be combined with --pre-push-updates")
        try:
            updates = parse_pre_push_updates(sys.stdin)
            scan = scan_pre_push_updates(
                args.repo_root,
                updates,
                expected_repository_identities=repository_ids,
                entry_threshold=args.entry_threshold,
            )
        except PrePushScanError as exc:
            print(f"status: ERROR\nreason: {exc}", file=sys.stderr)
            return SCANNER_ERROR_EXIT

        exit_code = _result_exit_code(item.result for item in scan.assessments)
        if exit_code == 0:
            print(
                "pre-push external tree inventory guard passed: "
                f"updates={scan.update_count} json_blobs={scan.json_blob_count}"
            )
            return 0
        if args.format == "json":
            print(
                json.dumps(
                    [asdict(item) for item in scan.assessments if item.result.status != STATUS_PASS],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(
                "\n\n".join(
                    f"blob: {item.oid}\n" + _format_human(Path(item.path), item.result)
                    for item in scan.assessments
                    if item.result.status != STATUS_PASS
                )
            )
        return exit_code

    if not args.files:
        parser.error("at least one JSON file is required unless --pre-push-updates is used")

    results = [
        (
            path,
            assess_path(
                path,
                expected_repository_identities=repository_ids,
                entry_threshold=args.entry_threshold,
            ),
        )
        for path in args.files
    ]

    if args.format == "json":
        print(
            json.dumps(
                [{"file": str(path), **asdict(result)} for path, result in results],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("\n\n".join(_format_human(path, result) for path, result in results))

    return _result_exit_code(result for _, result in results)


if __name__ == "__main__":
    raise SystemExit(main())
