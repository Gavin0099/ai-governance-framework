"""Frozen, single-use Rekor v2 public-write qualification executor.

Importing this module has no side effects.  Network access is possible only
through ``main`` after exact commit authority and frozen-byte validation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from tuf.api.exceptions import DownloadHTTPError
from tuf.ngclient import Updater, UpdaterConfig
from tuf.ngclient.fetcher import FetcherInterface


FREEZE_DIR = Path(__file__).resolve().parent
FRAMEWORK_ROOT = Path(__file__).resolve().parents[5]
FREEZE_RELATIVE_DIR = Path(
    "artifacts/experiments/prepush-bugfix-20260724/"
    "gate1-external-pin/rekor-v2-response-contract-amendment-20260825"
)
MANIFEST_PATH = FREEZE_DIR / "write-probe-manifest.json"
POLICY_PATH = FREEZE_DIR / "write-probe-output-policy.json"
TERMINAL_SCHEMA = "ai-governance.rekor-write-probe-terminal/2"
MANIFEST_SCHEMA = "ai-governance.rekor-v2-write-probe-freeze/3"
TERMINAL_FILENAME = "rekor-v2-write-probe-terminal.json"
_BOOTSTRAP_TERMINAL_POLICY = {
    "allowed_terminals": ["WRITE_PROBE_PRECONDITION_FAILED"],
    "forbidden_fields": [
        "authorization",
        "canonicalizedBody",
        "cookie",
        "privateKey",
        "publicKey",
        "rawProviderOutput",
        "requestBody",
        "signature",
        "signedArtifactBase64",
    ],
}
EXPECTED_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "ai-governance-framework-rekor-write-probe/1",
}
EXPECTED_RESPONSE_AUTHORITY = {
    "repository": "sigstore/rekor-tiles",
    "commit": "69e7f80810e3468a3a656094c5308560d1fd224f",
    "authoritative_surfaces": {
        "server": {
            "path": "internal/server/service.go",
            "blob_oid": "86975f1f6dbc83e4bade3a6d2db8b38397eedd14",
            "bytes": 6208,
            "success_status": 201,
            "role": "provider response authority",
        },
        "official_client": {
            "path": "pkg/client/write/write.go",
            "blob_oid": "bcb67dc20b96d761e5f8dd769d195b6e4a76b475",
            "bytes": 3748,
            "success_status": 201,
            "role": "provider response authority",
        },
    },
    "conflicting_generated_surface": {
        "path": "docs/openapi/rekor/v2/rekor_service.swagger.json",
        "blob_oid": "52f314e070057ef1201d6dcc8aa2329804f126e8",
        "bytes": 27163,
        "declared_success_status": 200,
        "role": "conflicting generated surface; not authoritative for this provider/version",
    },
    "upstream_change": {
        "pull_request": 112,
        "url": "https://github.com/sigstore/rekor-tiles/pull/112",
        "title": "Fix upload success status code",
        "merged": True,
        "merge_commit": "60937e829197c97b7ef813a386bea37ce18d51c5",
        "implementation_commit": "8ce17a17b7b93890b60d4a9643060113969a4fea",
        "decision": "successful entry creation returns HTTP 201 Created",
    },
}
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))


class WriteProbeError(RuntimeError):
    """A fail-closed write-probe boundary error."""


class Transport(Protocol):
    def get(self, url: str, *, timeout_seconds: int) -> bytes: ...

    def post_json(
        self,
        url: str,
        *,
        body: bytes,
        headers: Mapping[str, str],
        timeout_seconds: int,
    ) -> tuple[int, bytes]: ...


class UrllibTransport:
    """Credential-free HTTPS transport with bounded response reads."""

    _MAX_RESPONSE_BYTES = 1_048_576

    def __init__(self) -> None:
        # Do not inherit proxy credentials or routing from the environment.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @staticmethod
    def _read_bounded(response: Any) -> bytes:
        payload = response.read(UrllibTransport._MAX_RESPONSE_BYTES + 1)
        if len(payload) > UrllibTransport._MAX_RESPONSE_BYTES:
            raise WriteProbeError("provider response exceeds the frozen byte ceiling")
        return payload

    def get(self, url: str, *, timeout_seconds: int) -> bytes:
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with self._opener.open(request, timeout=timeout_seconds) as response:
            return self._read_bounded(response)

    def post_json(
        self,
        url: str,
        *,
        body: bytes,
        headers: Mapping[str, str],
        timeout_seconds: int,
    ) -> tuple[int, bytes]:
        request = urllib.request.Request(url, data=body, method="POST", headers=dict(headers))
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                return int(response.status), self._read_bounded(response)
        except urllib.error.HTTPError as exc:
            return int(exc.code), self._read_bounded(exc)


class _TransportFetcher(FetcherInterface):
    """Adapt the frozen transport to python-tuf's verified download API."""

    def __init__(self, transport: Transport, timeout_seconds: int) -> None:
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def _fetch(self, url: str):
        try:
            yield self._transport.get(url, timeout_seconds=self._timeout_seconds)
        except urllib.error.HTTPError as exc:
            raise DownloadHTTPError("TUF endpoint returned an HTTP error", exc.code) from exc


class _PortableUpdater(Updater):
    """Keep python-tuf semantics while avoiding privileged symlinks on Windows."""

    def _update_root_symlink(self) -> None:
        if os.name != "nt":
            super()._update_root_symlink()
            return
        version = self._trusted_set.root.version
        source = Path(self._dir) / "root_history" / f"{version}.root.json"
        destination = Path(self._dir) / "root.json"
        temporary = Path(self._dir) / "root.json.tmp"
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)


@dataclass(frozen=True)
class Terminal:
    schema: str
    status: str
    freeze_commit: str
    public_append_attempted: bool
    public_append_may_have_occurred: bool
    post_attempt_count: int
    provider_profile_sha256: str | None
    request_sha256: str | None
    subject_sha256: str | None
    http_status_code: int | None
    response_bytes: int | None
    response_sha256: str | None
    locator_parse_status: str
    locator_verification_status: str
    log_key_id_sha256: str | None
    external_record_id: str | None
    log_index: int | None
    tree_size: int | None
    canonicalized_body_sha256: str | None
    checkpoint_signed_text_sha256: str | None
    inclusion_hash_count: int | None
    diagnostic: str
    claim_ceiling: str


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WriteProbeError(f"invalid frozen JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise WriteProbeError(f"frozen JSON must be an object: {path.name}")
    return value


def _json_bytes(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WriteProbeError(f"committed JSON is invalid: {name}") from exc
    if not isinstance(value, dict):
        raise WriteProbeError(f"committed JSON must be an object: {name}")
    return value


def _current_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _git_object(root: Path, commit: str, path: str) -> tuple[str, bytes]:
    """Read exact committed bytes and object identity, never worktree bytes."""

    oid_result = subprocess.run(
        ["git", "rev-parse", f"{commit}:{path}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    blob_result = subprocess.run(
        ["git", "cat-file", "blob", oid_result.stdout.strip()],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return oid_result.stdout.strip(), blob_result.stdout


def _load_committed_provider(
    framework_root: Path,
    freeze_commit: str,
    manifest: Mapping[str, Any],
) -> tuple[Any, bytes]:
    from governance_tools.rekor_provider import RekorProviderProfile

    binding = manifest["provider_binding"]
    profile_oid, profile_raw = _git_object(
        framework_root,
        freeze_commit,
        "governance/rekor-v2-provider-profile.json",
    )
    if profile_oid != binding["profile_blob_oid"]:
        raise WriteProbeError("committed provider profile object differs from the freeze")
    if len(profile_raw) != binding["profile_bytes"] or _sha256(profile_raw) != binding["profile_sha256"]:
        raise WriteProbeError("committed provider profile bytes differ from the freeze")
    bootstrap_oid, bootstrap_container = _git_object(
        framework_root,
        freeze_commit,
        "governance/rekor-tuf-bootstrap-root-v15.json.b64",
    )
    if bootstrap_oid != binding["bootstrap_blob_oid"]:
        raise WriteProbeError("committed bootstrap object differs from the freeze")
    try:
        bootstrap = base64.b64decode(bootstrap_container.strip(), validate=True)
    except ValueError as exc:
        raise WriteProbeError("committed bootstrap container is invalid") from exc
    profile = RekorProviderProfile.from_bytes(profile_raw)
    if len(bootstrap) != profile.bootstrap_root_bytes or _sha256(bootstrap) != profile.bootstrap_root_sha256:
        raise WriteProbeError("committed bootstrap bytes differ from the profile")
    return profile, bootstrap


def _load_committed_freeze(
    framework_root: Path,
    freeze_commit: str,
    executing_file: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the authority-bearing manifest and all frozen bytes from Git."""

    prefix = FREEZE_RELATIVE_DIR.as_posix()
    _, manifest_raw = _git_object(
        framework_root,
        freeze_commit,
        f"{prefix}/write-probe-manifest.json",
    )
    manifest = _json_bytes(manifest_raw, "write-probe-manifest.json")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise WriteProbeError("committed write-probe manifest schema mismatch")
    files = manifest.get("frozen_files")
    if not isinstance(files, dict) or "rekor_write_probe.py" not in files:
        raise WriteProbeError("committed executor is not frozen")
    committed_payloads: dict[str, bytes] = {}
    for name, expected in files.items():
        if not isinstance(name, str) or "/" in name or "\\" in name or not isinstance(expected, dict):
            raise WriteProbeError("invalid committed frozen file entry")
        _, raw = _git_object(framework_root, freeze_commit, f"{prefix}/{name}")
        if len(raw) != expected.get("bytes") or _sha256(raw) != expected.get("sha256"):
            raise WriteProbeError(f"committed frozen file binding mismatch: {name}")
        committed_payloads[name] = raw
    try:
        executing_raw = executing_file.read_bytes()
    except OSError as exc:
        raise WriteProbeError("executing write-probe bytes are unreadable") from exc
    expected_executor = files["rekor_write_probe.py"]
    if len(executing_raw) != expected_executor.get("bytes") or _sha256(executing_raw) != expected_executor.get("sha256"):
        raise WriteProbeError("executing write-probe bytes differ from the authorized commit")
    policy = _json_bytes(
        committed_payloads["write-probe-output-policy.json"],
        "write-probe-output-policy.json",
    )
    return manifest, policy


def verify_frozen_files(manifest: Mapping[str, Any], freeze_dir: Path) -> None:
    files = manifest.get("frozen_files")
    if not isinstance(files, dict) or not files:
        raise WriteProbeError("manifest frozen_files is missing")
    if "rekor_write_probe.py" not in files:
        raise WriteProbeError("executor is not frozen")
    for name, expected in files.items():
        if not isinstance(name, str) or "/" in name or "\\" in name or not isinstance(expected, dict):
            raise WriteProbeError("invalid frozen file entry")
        path = freeze_dir / name
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise WriteProbeError(f"frozen file is unreadable: {name}") from exc
        if len(raw) != expected.get("bytes") or _sha256(raw) != expected.get("sha256"):
            raise WriteProbeError(f"frozen file binding mismatch: {name}")


def _validate_headers(headers: Mapping[str, str], expected: Mapping[str, Any]) -> None:
    if dict(headers) != dict(expected):
        raise WriteProbeError("HTTP headers differ from the frozen allowlist")
    forbidden = {"authorization", "cookie", "proxy-authorization"}
    if forbidden.intersection(key.lower() for key in headers):
        raise WriteProbeError("credential-bearing HTTP header is forbidden")


def _validate_response_authority(manifest: Mapping[str, Any]) -> None:
    if manifest.get("response_contract_authority") != EXPECTED_RESPONSE_AUTHORITY:
        raise WriteProbeError("response-contract authority differs from the freeze")


def _validate_retention_policy(policy: Mapping[str, Any]) -> None:
    expected_false = (
        "retain_raw_provider_output",
        "retain_request_body",
        "retain_normalized_proof_receipt",
        "retain_signature",
        "retain_public_key",
        "retain_canonicalized_body",
        "retain_checkpoint_envelope",
        "retain_proof_hash_array",
        "retain_bulk_path_listing",
    )
    if any(policy.get(field) is not False for field in expected_false):
        raise WriteProbeError("retention policy permits forbidden response material")
    if policy.get("maximum_response_bytes") != 1_048_576:
        raise WriteProbeError("response retention ceiling differs from the freeze")


def _validate_execution_contract(manifest: Mapping[str, Any], profile: Any) -> None:
    http = manifest.get("http")
    request = manifest.get("request")
    side_effect = manifest.get("public_side_effect")
    if not isinstance(http, dict) or not isinstance(request, dict) or not isinstance(side_effect, dict):
        raise WriteProbeError("write execution contract is incomplete")
    if http.get("method") != "POST":
        raise WriteProbeError("only POST is allowed")
    if http.get("url") != f"{profile.base_url}/api/v2/log/entries":
        raise WriteProbeError("write URL differs from the selected TUF provider")
    if http.get("timeout_seconds") != 60 or http.get("candidate_success_statuses") != [200, 201]:
        raise WriteProbeError("HTTP timeout or candidate success statuses differ from the freeze")
    if http.get("maximum_attempts") != 1 or http.get("retries_allowed") is not False:
        raise WriteProbeError("exactly one POST attempt is required")
    if http.get("credentials_allowed") is not False:
        raise WriteProbeError("credentials must remain forbidden")
    _validate_headers(http.get("headers", {}), EXPECTED_HEADERS)
    if request.get("kind") != profile.entry_kind or request.get("version") != profile.entry_version:
        raise WriteProbeError("request kind or version differs from the provider profile")
    if request.get("field") != "hashedRekordRequestV002":
        raise WriteProbeError("request field differs from the official v2 contract")
    if side_effect.get("performed") is not False or side_effect.get("non_counted") is not True:
        raise WriteProbeError("committed freeze must remain unexecuted and non-counted")
    if side_effect.get("retry_forbidden_after_dispatch") is not True:
        raise WriteProbeError("retry must remain forbidden after dispatch")
    response = manifest.get("response")
    if not isinstance(response, dict) or response.get("maximum_bytes") != 1_048_576:
        raise WriteProbeError("bounded response contract differs from the freeze")
    if response.get("parse_before_status_decision") is not True:
        raise WriteProbeError("response must be parsed before status selection")
    required = (
        response.get("checkpoint_signature_required"),
        response.get("inclusion_proof_required"),
        response.get("request_body_binding_required"),
    )
    if required != (True, True, True):
        raise WriteProbeError("complete proof verification is required")


def _fetch_tuf_inputs(
    transport: Transport,
    manifest: Mapping[str, Any],
    bootstrap_root: bytes,
) -> dict[str, bytes]:
    """Refresh and download required targets through python-tuf only.

    ``Updater.download_target`` owns consistent-snapshot URL construction and
    verifies target length and hashes before this function returns bytes.
    """

    tuf = manifest["tuf_refresh"]
    timeout = int(tuf["timeout_seconds"])
    client = tuf.get("client")
    if client != {
        "implementation": "tuf.ngclient.Updater",
        "package": "tuf",
        "version": "7.0.0",
        "prefix_targets_with_hash": True,
        "windows_root_alias": "atomic-copy",
    }:
        raise WriteProbeError("formal TUF client contract differs from the freeze")
    required_targets = tuple(manifest["provider_binding"]["required_target_names"])
    with tempfile.TemporaryDirectory(prefix="rekor-tuf-client-") as scratch:
        scratch_root = Path(scratch)
        metadata_dir = scratch_root / "metadata"
        target_dir = scratch_root / "targets"
        metadata_dir.mkdir()
        target_dir.mkdir()
        updater = _PortableUpdater(
            str(metadata_dir),
            str(tuf["metadata_base_url"]),
            str(target_dir),
            str(tuf["targets_base_url"]),
            fetcher=_TransportFetcher(transport, timeout),
            config=UpdaterConfig(
                max_root_rotations=256,
                max_delegations=32,
                root_max_length=512_000,
                timestamp_max_length=16_384,
                snapshot_max_length=2_000_000,
                targets_max_length=5_000_000,
                prefix_targets_with_hash=True,
                app_user_agent=None,
            ),
            bootstrap=bootstrap_root,
        )
        updater.refresh()
        payloads: dict[str, bytes] = {}
        for name in required_targets:
            target = updater.get_targetinfo(name)
            if target is None:
                raise WriteProbeError(f"required TUF target is unavailable: {name}")
            downloaded = Path(updater.download_target(target))
            payloads[name] = downloaded.read_bytes()
        return {
            "timestamp": (metadata_dir / "timestamp.json").read_bytes(),
            "snapshot": (metadata_dir / "snapshot.json").read_bytes(),
            "targets": (metadata_dir / "targets.json").read_bytes(),
            **payloads,
        }


def _build_request(subject: bytes) -> tuple[bytes, str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    signature = private_key.sign(subject, ec.ECDSA(hashes.SHA256()))
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(subject).digest()
    request = {
        "hashedRekordRequestV002": {
            "digest": base64.b64encode(digest).decode("ascii"),
            "signature": {
                "content": base64.b64encode(signature).decode("ascii"),
                "verifier": {
                    "keyDetails": "PKIX_ECDSA_P256_SHA_256",
                    "publicKey": {"rawBytes": base64.b64encode(public_der).decode("ascii")},
                },
            },
        }
    }
    return _canonical_json(request), digest.hex()


def _receipt_input(profile_sha256: str, subject: bytes, response: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "logIndex",
        "logId",
        "kindVersion",
        "integratedTime",
        "inclusionPromise",
        "inclusionProof",
        "canonicalizedBody",
    }
    if set(response) != required:
        raise WriteProbeError("provider response field set mismatch")
    canonicalized = response["canonicalizedBody"]
    if not isinstance(canonicalized, str):
        raise WriteProbeError("provider canonicalized body is not base64 text")
    return {
        "schema": "ai-governance.rekor-proof-bearing-receipt/1",
        "providerProfileSha256": profile_sha256,
        "subjectSha256": _sha256(subject),
        "signedArtifactBase64": base64.b64encode(subject).decode("ascii"),
        "canonicalizedBodyBase64": canonicalized,
        "logEntry": {key: response[key] for key in required if key != "canonicalizedBody"},
    }


def _parse_bounded_response(raw: bytes, maximum_bytes: int) -> dict[str, Any]:
    """Parse a bounded provider response in memory without retaining raw bytes."""

    if len(raw) > maximum_bytes:
        raise WriteProbeError("provider response exceeds the frozen byte ceiling")
    try:
        response = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WriteProbeError("provider response is not valid UTF-8 JSON") from exc
    if not isinstance(response, dict):
        raise WriteProbeError("provider response must be an object")
    return response


def _candidate_locator(response: Mapping[str, Any]) -> tuple[int | None, str | None]:
    """Return only allowlisted locator summaries from an exact response shape."""

    required = {
        "logIndex",
        "logId",
        "kindVersion",
        "integratedTime",
        "inclusionPromise",
        "inclusionProof",
        "canonicalizedBody",
    }
    if set(response) != required:
        raise WriteProbeError("provider response field set mismatch")
    log_index = response.get("logIndex")
    if isinstance(log_index, str) and log_index.isdigit():
        parsed_index: int | None = int(log_index)
    elif isinstance(log_index, int) and not isinstance(log_index, bool) and log_index >= 0:
        parsed_index = log_index
    else:
        parsed_index = None
    log_id = response.get("logId")
    key_id = log_id.get("keyId") if isinstance(log_id, dict) else None
    key_digest = _sha256(key_id.encode("utf-8")) if isinstance(key_id, str) else None
    return parsed_index, key_digest


def _sanitize_diagnostic(value: str, maximum: int) -> str:
    compact = " ".join(value.split())
    forbidden = ("authorization", "cookie", "private", "signature", "publickey", "canonicalizedbody")
    if any(token in compact.lower() for token in forbidden):
        return "diagnostic redacted by output policy"
    return compact[:maximum]


def _assert_repo_external_output(framework_root: Path, output_dir: Path) -> None:
    root = framework_root.resolve()
    destination = output_dir.resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return
    raise WriteProbeError("terminal output directory must be outside the framework repository")


def _validate_terminal(terminal: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    if terminal.get("status") not in policy["allowed_terminals"]:
        raise WriteProbeError("terminal status is not allowed")
    serialized = json.dumps(terminal, ensure_ascii=False, sort_keys=True)
    lowered = serialized.lower()
    for field in policy["forbidden_fields"]:
        if f'"{str(field).lower()}"' in lowered:
            raise WriteProbeError(f"terminal contains forbidden field: {field}")


def _write_terminal_once(path: Path, terminal: Terminal, policy: Mapping[str, Any]) -> None:
    document = asdict(terminal)
    _validate_terminal(document, policy)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def _preflight_output_directory(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sentinel = output_dir / ".rekor-write-probe-preflight"
    try:
        with sentinel.open("x", encoding="ascii", newline="\n") as handle:
            handle.write("preflight\n")
        sentinel.unlink()
    except OSError as exc:
        raise WriteProbeError("repo-external terminal surface is not writable and cleanable") from exc


def _execute_probe_with_documents(
    *,
    framework_root: Path,
    freeze_dir: Path,
    output_dir: Path,
    owner_authorized_commit: str,
    transport: Transport,
    head_reader: Callable[[Path], str] = _current_head,
    receipt_verifier: Callable[[Any, Mapping[str, Any]], Any] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    manifest: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Terminal:
    """Internal orchestration core used by the committed entrypoint and tests."""

    _assert_repo_external_output(framework_root, output_dir)
    _preflight_output_directory(output_dir)
    terminal_path = output_dir / str(policy["terminal_filename"])
    if terminal_path.exists():
        raise WriteProbeError("terminal already exists; retry is forbidden")

    status = "WRITE_PROBE_PRECONDITION_FAILED"
    dispatched = False
    post_count = 0
    profile_sha: str | None = None
    request_sha: str | None = None
    subject_sha: str | None = None
    http_status_code: int | None = None
    response_bytes: int | None = None
    response_sha: str | None = None
    locator_parse_status = "NOT_ATTEMPTED"
    locator_verification_status = "NOT_VERIFIED"
    log_key_id_sha: str | None = None
    candidate_log_index: int | None = None
    verified: Any = None
    diagnostic = "precondition failed"
    freeze_commit = head_reader(framework_root)

    try:
        if owner_authorized_commit != freeze_commit:
            status = "WRITE_PROBE_AUTHORITY_MISMATCH"
            raise WriteProbeError("owner authority does not match the executing freeze commit")
        if manifest.get("execution_authority", {}).get("authorized") is not False:
            raise WriteProbeError("committed manifest must remain unauthorized")
        verify_frozen_files(manifest, freeze_dir)
        _validate_response_authority(manifest)
        _validate_retention_policy(policy)

        from governance_tools.rekor_provider import (
            verify_proof_bearing_receipt,
            verify_tuf_snapshot,
        )

        profile, bootstrap = _load_committed_provider(
            framework_root,
            freeze_commit,
            manifest,
        )
        profile_sha = profile.source_sha256
        if profile_sha != manifest["provider_binding"]["profile_sha256"]:
            raise WriteProbeError("provider profile digest differs from the freeze")
        _validate_execution_contract(manifest, profile)
        tuf_inputs = _fetch_tuf_inputs(transport, manifest, bootstrap)
        verify_tuf_snapshot(
            profile,
            bootstrap_root=bootstrap,
            timestamp=tuf_inputs["timestamp"],
            snapshot=tuf_inputs["snapshot"],
            targets=tuf_inputs["targets"],
            target_payloads={
                "trusted_root.json": tuf_inputs["trusted_root.json"],
                "signing_config_rekor_v2.v0.2.json": tuf_inputs["signing_config_rekor_v2.v0.2.json"],
            },
            reference_time=now(),
        )

        subject = base64.b64decode(manifest["synthetic_subject"]["base64"], validate=True)
        if _sha256(subject) != manifest["synthetic_subject"]["sha256"]:
            raise WriteProbeError("synthetic subject binding mismatch")
        subject_sha = _sha256(subject)
        request_body, request_digest = _build_request(subject)
        request_sha = _sha256(request_body)
        if request_digest != subject_sha:
            raise WriteProbeError("request digest does not bind the subject")

        http = manifest["http"]
        headers = http["headers"]
        dispatched = True
        post_count = 1
        code, raw_response = transport.post_json(
            http["url"],
            body=request_body,
            headers=headers,
            timeout_seconds=int(http["timeout_seconds"]),
        )
        http_status_code = code
        response_bytes = len(raw_response)
        response_sha = _sha256(raw_response)
        try:
            response = _parse_bounded_response(raw_response, int(manifest["response"]["maximum_bytes"]))
            locator_parse_status = "JSON_OBJECT_PARSED"
            candidate_log_index, log_key_id_sha = _candidate_locator(response)
            locator_parse_status = "STRICT_SHAPE_PARSED"
        except WriteProbeError:
            status = "WRITE_PROBE_RESPONSE_INVALID"
            raise
        verifier = receipt_verifier or verify_proof_bearing_receipt
        receipt_document = _receipt_input(profile.source_sha256, subject, response)
        verified = verifier(profile, receipt_document)
        locator_verification_status = "VERIFIED_PROOF_BOUND"
        if code in set(http["candidate_success_statuses"]):
            status = "WRITE_PROBE_PASSED"
            diagnostic = "proof-bearing public write verified; qualification decision remains separate"
        else:
            status = "WRITE_PROBE_UNEXPECTED_STATUS_WITH_VERIFIED_LOCATOR"
            diagnostic = f"provider returned unexpected HTTP {code}; verified locator retained fail closed"
    except WriteProbeError as exc:
        diagnostic = str(exc)
    except Exception as exc:  # fail closed without retaining provider detail
        if dispatched:
            status = "WRITE_PROBE_RESPONSE_INVALID"
        diagnostic = f"{type(exc).__name__} during frozen write probe"

    terminal = Terminal(
        schema=TERMINAL_SCHEMA,
        status=status,
        freeze_commit=freeze_commit,
        public_append_attempted=dispatched,
        public_append_may_have_occurred=dispatched,
        post_attempt_count=post_count,
        provider_profile_sha256=profile_sha,
        request_sha256=request_sha,
        subject_sha256=subject_sha,
        http_status_code=http_status_code,
        response_bytes=response_bytes,
        response_sha256=response_sha,
        locator_parse_status=locator_parse_status,
        locator_verification_status=locator_verification_status,
        log_key_id_sha256=log_key_id_sha,
        external_record_id=getattr(verified, "external_record_id", None),
        log_index=getattr(verified, "log_index", candidate_log_index),
        tree_size=getattr(verified, "tree_size", None),
        canonicalized_body_sha256=getattr(verified, "canonicalized_body_sha256", None),
        checkpoint_signed_text_sha256=getattr(verified, "checkpoint_signed_text_sha256", None),
        inclusion_hash_count=getattr(verified, "inclusion_hash_count", None),
        diagnostic=_sanitize_diagnostic(diagnostic, int(policy["maximum_diagnostic_characters"])),
        claim_ceiling="non-counted Rekor v2 write-path qualification only; not Gate 1 evidence",
    )
    try:
        _write_terminal_once(terminal_path, terminal, policy)
    except (OSError, WriteProbeError) as exc:
        raise WriteProbeError("terminal retention failed after the frozen attempt") from exc
    return terminal


def execute_probe(
    *,
    framework_root: Path,
    freeze_dir: Path,
    output_dir: Path,
    owner_authorized_commit: str,
    transport: Transport,
    head_reader: Callable[[Path], str] = _current_head,
    receipt_verifier: Callable[[Any, Mapping[str, Any]], Any] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> Terminal:
    """Run the exact committed freeze, never mutable worktree configuration."""

    freeze_commit = head_reader(framework_root)
    try:
        manifest, policy = _load_committed_freeze(
            framework_root,
            freeze_commit,
            Path(__file__).resolve(),
        )
    except WriteProbeError as exc:
        _assert_repo_external_output(framework_root, output_dir)
        _preflight_output_directory(output_dir)
        terminal = Terminal(
            schema=TERMINAL_SCHEMA,
            status="WRITE_PROBE_PRECONDITION_FAILED",
            freeze_commit=freeze_commit,
            public_append_attempted=False,
            public_append_may_have_occurred=False,
            post_attempt_count=0,
            provider_profile_sha256=None,
            request_sha256=None,
            subject_sha256=None,
            http_status_code=None,
            response_bytes=None,
            response_sha256=None,
            locator_parse_status="NOT_ATTEMPTED",
            locator_verification_status="NOT_VERIFIED",
            log_key_id_sha256=None,
            external_record_id=None,
            log_index=None,
            tree_size=None,
            canonicalized_body_sha256=None,
            checkpoint_signed_text_sha256=None,
            inclusion_hash_count=None,
            diagnostic=_sanitize_diagnostic(str(exc), 240),
            claim_ceiling="non-counted Rekor v2 write-path qualification only; not Gate 1 evidence",
        )
        try:
            _write_terminal_once(
                output_dir / TERMINAL_FILENAME,
                terminal,
                _BOOTSTRAP_TERMINAL_POLICY,
            )
        except (OSError, WriteProbeError) as retention_exc:
            raise WriteProbeError("terminal retention failed after committed freeze load failure") from retention_exc
        return terminal
    return _execute_probe_with_documents(
        framework_root=framework_root,
        freeze_dir=freeze_dir,
        output_dir=output_dir,
        owner_authorized_commit=owner_authorized_commit,
        transport=transport,
        head_reader=lambda _: freeze_commit,
        receipt_verifier=receipt_verifier,
        now=now,
        manifest=manifest,
        policy=policy,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    terminal = execute_probe(
        framework_root=FRAMEWORK_ROOT,
        freeze_dir=FREEZE_DIR,
        output_dir=args.output_dir,
        owner_authorized_commit=args.owner_authorized_freeze_commit,
        transport=UrllibTransport(),
    )
    print(json.dumps({"status": terminal.status, "terminal": str(args.output_dir / "rekor-v2-write-probe-terminal.json")}))
    return 0 if terminal.status == "WRITE_PROBE_PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
