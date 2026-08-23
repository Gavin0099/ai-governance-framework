#!/usr/bin/env python3
"""Detect bulk Git-tree inventories that identify an external repository.

This module is intentionally standalone in its first slice.  It does not wire
itself into hooks, CI, runtime governance, or evidence admission.  Callers must
provide one or more identities for the repository being checked.

Exit codes used by the CLI:
  0 — no externally identified bulk tree inventory was found
  1 — an externally identified bulk tree inventory was found
  2 — the result is unknown (for example, bulk entries lack source identity)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse


STATUS_PASS = "PASS"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNKNOWN = "UNKNOWN"
DEFAULT_ENTRY_THRESHOLD = 100

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
class CollectionFinding:
    json_path: str
    distinct_entry_count: int
    source_repository_identities: tuple[str, ...]
    status: str
    reason: str


@dataclass(frozen=True)
class GuardResult:
    status: str
    threshold: int
    findings: tuple[CollectionFinding, ...]
    reason: str


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


def _bulk_entry_count(node: list[Any]) -> int:
    distinct_entries: set[tuple[str, str]] = set()
    for item in node:
        if not isinstance(item, dict):
            continue
        path = _string_field(item, _PATH_KEYS)
        oid = _string_field(item, _OID_KEYS)
        if path is not None and oid is not None:
            distinct_entries.add((path, oid))
    return len(distinct_entries)


def _json_path(parent: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}" if parent != "$" else f"$.{key}"


def _walk_collections(
    node: Any,
    *,
    expected_identities: set[str],
    threshold: int,
    inherited_identities: set[str],
    path: str,
) -> list[CollectionFinding]:
    findings: list[CollectionFinding] = []

    if isinstance(node, dict):
        current_identities = inherited_identities | _direct_repository_identities(node)
        for key, value in node.items():
            findings.extend(
                _walk_collections(
                    value,
                    expected_identities=expected_identities,
                    threshold=threshold,
                    inherited_identities=current_identities,
                    path=_json_path(path, key),
                )
            )
        return findings

    if not isinstance(node, list):
        return findings

    distinct_count = _bulk_entry_count(node)
    if distinct_count >= threshold:
        identities = tuple(sorted(inherited_identities))
        external = sorted(inherited_identities - expected_identities)
        if external:
            status = STATUS_BLOCKED
            reason = "bulk_tree_inventory_explicitly_identifies_external_repository"
        elif not inherited_identities:
            status = STATUS_UNKNOWN
            reason = "bulk_tree_inventory_has_no_reliable_repository_identity"
        else:
            status = STATUS_PASS
            reason = "bulk_tree_inventory_identifies_expected_repository"
        findings.append(
            CollectionFinding(
                json_path=path,
                distinct_entry_count=distinct_count,
                source_repository_identities=identities,
                status=status,
                reason=reason,
            )
        )

    for index, value in enumerate(node):
        findings.extend(
            _walk_collections(
                value,
                expected_identities=expected_identities,
                threshold=threshold,
                inherited_identities=inherited_identities,
                path=_json_path(path, index),
            )
        )
    return findings


def assess_document(
    document: Any,
    *,
    expected_repository_identities: Sequence[str],
    entry_threshold: int = DEFAULT_ENTRY_THRESHOLD,
) -> GuardResult:
    """Classify one decoded JSON document.

    ``UNKNOWN`` is deliberately distinct from ``PASS``.  A bulk path/OID
    collection without reliable repository identity cannot support a safety
    claim, but this first slice does not decide how a future hook or CI job
    should enforce that state.
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

    findings = tuple(
        _walk_collections(
            document,
            expected_identities=expected,
            threshold=entry_threshold,
            inherited_identities=set(),
            path="$",
        )
    )

    if any(item.status == STATUS_BLOCKED for item in findings):
        return GuardResult(
            status=STATUS_BLOCKED,
            threshold=entry_threshold,
            findings=findings,
            reason="external_bulk_tree_inventory_detected",
        )
    if any(item.status == STATUS_UNKNOWN for item in findings):
        return GuardResult(
            status=STATUS_UNKNOWN,
            threshold=entry_threshold,
            findings=findings,
            reason="bulk_tree_inventory_source_identity_unknown",
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
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return GuardResult(
            status=STATUS_UNKNOWN,
            threshold=entry_threshold,
            findings=(),
            reason=f"json_unreadable:{type(exc).__name__}",
        )
    return assess_document(
        document,
        expected_repository_identities=expected_repository_identities,
        entry_threshold=entry_threshold,
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
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify JSON files for externally identified bulk Git-tree inventories."
    )
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--repository-id",
        action="append",
        required=True,
        dest="repository_ids",
        help="Expected repository identity; repeat for exact aliases such as owner/name and URL.",
    )
    parser.add_argument("--entry-threshold", type=int, default=DEFAULT_ENTRY_THRESHOLD)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    results = [
        (
            path,
            assess_path(
                path,
                expected_repository_identities=args.repository_ids,
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

    if any(result.status == STATUS_BLOCKED for _, result in results):
        return 1
    if any(result.status == STATUS_UNKNOWN for _, result in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
