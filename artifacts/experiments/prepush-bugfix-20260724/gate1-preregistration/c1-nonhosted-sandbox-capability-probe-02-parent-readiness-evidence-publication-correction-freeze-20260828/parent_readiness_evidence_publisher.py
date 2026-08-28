from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Mapping, Sequence


SCHEMA = "c1-probe02-parent-readiness-evidence-publication-freeze.v1"
FRAMEWORK_BASE = "0872889912ec7bc6f881e59082d726c7fc2db67e"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-parent-readiness-evidence-"
    "publication-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/parent-readiness-evidence-publication-manifest.json"
PUBLISHER_NAME = "parent_readiness_evidence_publisher.py"
EXPECTED_GIT_PATH = Path("C:/Program Files/Git/cmd/git.exe")
EXPECTED_GIT_BYTES = 46480
EXPECTED_GIT_SHA256 = "3cbd024d9d11ef08bd6a0cb5a973613c50825b4952bc6006f3f4222f436091e5"
EXPECTED_PYTHON_PATH = Path("D:/ai-governance-framework/.venv/Scripts/python.exe")
EXPECTED_PYTHON_BYTES = 255320
EXPECTED_PYTHON_SHA256 = "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
EXPECTED_BOOTSTRAP_OID = "595e0111df1b1b8a1927609a12c9e3430a801e08"
EXPECTED_BOOTSTRAP_BYTES = 13188
EXPECTED_BOOTSTRAP_SHA256 = "b00ee7482c8bcdf26273bf2bce70cd17d19295d3536f70918cf06ab0d6e00716"
RECEIPT_SCHEMA = "c1-probe02-parent-readiness-receipt.v1"
ATTEMPT_ID = "C1-nonhosted-sandbox-capability-probe-02"
START_NAME = "start.json"
RECEIPT_NAME = "c1-nonhosted-capability-probe-02-readiness-receipt-20260828-rev1.json"
TERMINAL_NAME = "terminal.json"
REVIEW_NAME = "c1-nonhosted-capability-probe-02-readiness-review-20260828-rev1.json"
RECEIPT_MAX_BYTES = 8192
CHILD_TIMEOUT_SECONDS = 180.0
REPARSE_POINT = 0x400
HEX = frozenset("0123456789abcdef")
EXCEPTION_ALLOWLIST = {
    "EvidencePublicationError",
    "FileExistsError",
    "JSONDecodeError",
    "OSError",
    "PermissionError",
    "TimeoutExpired",
    "UnicodeDecodeError",
}
REQUIRED_SOURCE_LABELS = {
    "trusted_bootstrap",
    "trusted_bootstrap_manifest",
    "readiness_manifest",
}


class EvidencePublicationError(RuntimeError):
    pass


class EvidenceRootAlreadyClaimed(EvidencePublicationError):
    pass


class TerminalPublicationError(EvidencePublicationError):
    pass


@dataclass(frozen=True)
class ChildResult:
    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes


Launcher = Callable[[Sequence[str], bytes, Path, Mapping[str, str], float], ChildResult]
Publisher = Callable[[Path, str, bytes], Mapping[str, object]]
Clock = Callable[[], str]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _json_object(payload: bytes, label: str) -> Mapping[str, object]:
    try:
        text = payload.decode("utf-8", errors="strict")
        decoder = json.JSONDecoder()
        value, end = decoder.raw_decode(text.lstrip())
        leading = len(text) - len(text.lstrip())
        if text[leading + end :].strip():
            raise EvidencePublicationError(f"multiple JSON values: {label}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidencePublicationError(f"invalid JSON: {label}") from exc
    if not isinstance(value, dict):
        raise EvidencePublicationError(f"JSON object required: {label}")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _verify_file(path: Path, expected_bytes: int, expected_sha256: str, label: str) -> None:
    if (
        not path.is_file()
        or path.stat().st_size != expected_bytes
        or _sha256_file(path) != expected_sha256
    ):
        raise EvidencePublicationError(f"{label} binding mismatch")


def _verify_runtime() -> None:
    _verify_file(EXPECTED_GIT_PATH, EXPECTED_GIT_BYTES, EXPECTED_GIT_SHA256, "Git")
    _verify_file(EXPECTED_PYTHON_PATH, EXPECTED_PYTHON_BYTES, EXPECTED_PYTHON_SHA256, "Python")
    if Path(sys.executable).resolve() != EXPECTED_PYTHON_PATH.resolve():
        raise EvidencePublicationError("executing Python identity mismatch")


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        [
            str(EXPECTED_GIT_PATH),
            "--no-replace-objects",
            "-c",
            f"safe.directory={repo}",
            "-C",
            str(repo),
            *args,
        ],
        input=b"",
        capture_output=True,
        check=False,
        timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise EvidencePublicationError("Git binding command failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, "cat-file", "blob", oid, binary=True)
    assert isinstance(payload, bytes)
    return oid, payload


def _safe_repo_path(raw: str) -> None:
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    if (
        not posix.parts
        or posix.is_absolute()
        or windows.drive
        or windows.root
        or "." in posix.parts
        or ".." in posix.parts
        or "." in windows.parts
        or ".." in windows.parts
    ):
        raise EvidencePublicationError("unsafe bound repo path")


def _manifest(repo: Path, commit: str) -> Mapping[str, object]:
    _, payload = _blob(repo, commit, MANIFEST_REPO_PATH)
    value = _json_object(payload, "manifest")
    if value.get("schema") != SCHEMA or value.get("framework_base") != FRAMEWORK_BASE:
        raise EvidencePublicationError("publisher manifest binding mismatch")
    return value


def _verify_inventory(repo: Path, commit: str, manifest: Mapping[str, object]) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise EvidencePublicationError("frozen inventory unavailable")
    actual = set(str(_git(repo, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines())
    expected = {"parent-readiness-evidence-publication-manifest.json"}
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise EvidencePublicationError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe_repo_path(path)
        expected.add(path)
        oid, payload = _blob(repo, commit, f"{FREEZE_REPO_DIR}/{path}")
        if (
            oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise EvidencePublicationError(f"frozen binding mismatch: {path}")
        blobs[path] = payload
    if actual != expected:
        raise EvidencePublicationError("frozen directory inventory drift")
    if _sha256(blobs.get(PUBLISHER_NAME, b"")) != manifest.get("frozen_executor_sha256"):
        raise EvidencePublicationError("publisher authority mismatch")
    return blobs


def _verify_sources(repo: Path, manifest: Mapping[str, object]) -> Mapping[str, bytes]:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise EvidencePublicationError("source bindings unavailable")
    blobs: dict[str, bytes] = {}
    metadata: dict[str, Mapping[str, object]] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise EvidencePublicationError("source binding invalid")
        label = str(item.get("label"))
        commit = str(item.get("commit"))
        path = str(item.get("path"))
        _safe_repo_path(path)
        oid, payload = _blob(repo, commit, path)
        if (
            commit != FRAMEWORK_BASE
            or oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise EvidencePublicationError(f"source binding mismatch: {label}")
        if label in blobs:
            raise EvidencePublicationError("duplicate source binding")
        blobs[label] = payload
        metadata[label] = item
    if set(blobs) != REQUIRED_SOURCE_LABELS:
        raise EvidencePublicationError("source binding label set mismatch")
    if (
        metadata["trusted_bootstrap"].get("git_blob_oid") != EXPECTED_BOOTSTRAP_OID
        or len(blobs["trusted_bootstrap"]) != EXPECTED_BOOTSTRAP_BYTES
        or _sha256(blobs["trusted_bootstrap"]) != EXPECTED_BOOTSTRAP_SHA256
    ):
        raise EvidencePublicationError("trusted bootstrap binding mismatch")
    return blobs


def _evidence_contract(manifest: Mapping[str, object], sources: Mapping[str, bytes]) -> Mapping[str, Path]:
    contract = manifest.get("evidence_contract")
    if not isinstance(contract, dict):
        raise EvidencePublicationError("evidence contract unavailable")
    trusted = _json_object(sources["trusted_bootstrap_manifest"], "trusted_bootstrap_manifest")
    if (
        trusted.get("schema") != "c1-probe02-parent-readiness-trusted-bootstrap-freeze.v1"
        or trusted.get("status") != "FROZEN_NOT_EXECUTED"
        or trusted.get("frozen_executor_sha256") != EXPECTED_BOOTSTRAP_SHA256
    ):
        raise EvidencePublicationError("trusted bootstrap manifest semantic mismatch")
    trusted_authority = trusted.get("execution_authority")
    if not isinstance(trusted_authority, dict) or any(trusted_authority.values()):
        raise EvidencePublicationError("trusted bootstrap authority drift")
    readiness = _json_object(sources["readiness_manifest"], "readiness_manifest")
    binding = readiness.get("readiness_evidence")
    if not isinstance(binding, dict):
        raise EvidencePublicationError("predecessor readiness evidence unavailable")
    receipt = Path(str(binding.get("receipt_path")))
    review = Path(str(binding.get("review_packet_path")))
    root = Path(str(contract.get("evidence_root")))
    base = Path(str(contract.get("evidence_parent")))
    terminal = root / TERMINAL_NAME
    start = root / START_NAME
    if (
        not all(path.is_absolute() for path in (base, root, receipt, review))
        or root.parent != base
        or receipt.parent != root
        or review.parent != root
        or receipt.name != RECEIPT_NAME
        or review.name != REVIEW_NAME
        or int(binding.get("receipt_max_bytes", 0)) != RECEIPT_MAX_BYTES
        or contract.get("start_file") != START_NAME
        or contract.get("terminal_file") != TERMINAL_NAME
    ):
        raise EvidencePublicationError("evidence path contract mismatch")
    return {
        "base": base,
        "root": root,
        "start": start,
        "receipt": receipt,
        "terminal": terminal,
        "review": review,
    }


def _bootstrap_staging(repo: Path) -> Path:
    return (repo.parent / f".{repo.name}.c1-probe02-parent-readiness-bootstrap-staging").resolve()


def _is_reparse_or_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    return bool(getattr(path.lstat(), "st_file_attributes", 0) & REPARSE_POINT)


def _verify_preclaim(paths: Mapping[str, Path], repo: Path) -> None:
    base = paths["base"]
    if not base.is_dir() or _is_reparse_or_symlink(base):
        raise EvidencePublicationError("exact evidence parent unavailable")
    if paths["root"].exists():
        raise EvidenceRootAlreadyClaimed("evidence root already exists")
    if _bootstrap_staging(repo).exists():
        raise EvidencePublicationError("trusted bootstrap staging root already exists")


def _claim_root(root: Path) -> None:
    try:
        root.mkdir()
    except FileExistsError as exc:
        raise EvidenceRootAlreadyClaimed("evidence root already exists") from exc


def _atomic_publish(root: Path, name: str, payload: bytes) -> Mapping[str, object]:
    final = root / name
    staging = root / f".{name}.staging"
    if final.exists() or staging.exists():
        raise EvidencePublicationError(f"evidence file already exists: {name}")
    try:
        with staging.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if staging.read_bytes() != payload:
            raise EvidencePublicationError(f"evidence staging readback mismatch: {name}")
        os.replace(staging, final)
        if final.read_bytes() != payload:
            raise EvidencePublicationError(f"evidence final readback mismatch: {name}")
        return _json_object(payload, name)
    except BaseException:
        if staging.exists():
            try:
                staging.unlink()
            except OSError:
                pass
        raise


def _default_launcher(
    argv: Sequence[str], payload: bytes, cwd: Path, environment: Mapping[str, str], timeout: float
) -> ChildResult:
    try:
        completed = subprocess.run(
            list(argv),
            input=payload,
            cwd=cwd,
            env=dict(environment),
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        return ChildResult(completed.returncode, False, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        return ChildResult(None, True, exc.stdout or b"", exc.stderr or b"")


def _transport(result: ChildResult | None) -> Mapping[str, object] | None:
    if result is None:
        return None
    return {
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "stdout_bytes": len(result.stdout),
        "stderr_bytes": len(result.stderr),
        "stdout_sha256": _sha256(result.stdout),
        "stderr_sha256": _sha256(result.stderr),
    }


def _exception_class(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name in EXCEPTION_ALLOWLIST else "OTHER"


def _validate_receipt(payload: bytes, commit: str) -> Mapping[str, object]:
    if not payload or len(payload) > RECEIPT_MAX_BYTES:
        raise EvidencePublicationError("readiness receipt stdout bounds invalid")
    receipt = _json_object(payload, "readiness_receipt")
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("status") != "PARENT_READINESS_PASSED"
        or receipt.get("attempt_id") != ATTEMPT_ID
        or receipt.get("execution_commit") != commit
        or receipt.get("sentinel_create_exclusive") is not True
        or receipt.get("sentinel_fsync_completed") is not True
        or receipt.get("sentinel_readback_exact") is not True
        or receipt.get("cleanup_complete") is not True
        or receipt.get("formal_attempt_claim_created") is not False
        or receipt.get("hosted_requests") != 0
        or receipt.get("auth_payloads") != 0
        or receipt.get("qualification_attempts_consumed") != 0
    ):
        raise EvidencePublicationError("readiness receipt schema or invariant mismatch")
    return receipt


def _start_payload(commit: str, publisher_sha256: str, bootstrap_sha256: str, observed_at: str) -> bytes:
    return _canonical(
        {
            "schema": "c1-probe02-parent-readiness-publication-start.v1",
            "execution_commit": commit,
            "attempt_id": ATTEMPT_ID,
            "publisher_sha256": publisher_sha256,
            "trusted_bootstrap_sha256": bootstrap_sha256,
            "observed_at_utc": observed_at,
            "readiness_invocation_started": True,
            "probe02_authority_consumed": False,
            "child_launch_attempted": False,
            "hosted_requests": 0,
            "auth_payloads": 0,
            "qualification_attempts_consumed": 0,
            "randomization_created": False,
        }
    )


def _terminal_payload(
    *, commit: str, stage: str, exc: BaseException, result: ChildResult | None,
    receipt_present: bool, bootstrap_staging_present: bool,
) -> bytes:
    return _canonical(
        {
            "schema": "c1-probe02-parent-readiness-publication-terminal.v1",
            "status": "PARENT_READINESS_PUBLICATION_FAILED",
            "execution_commit": commit,
            "attempt_id": ATTEMPT_ID,
            "failure_stage": stage,
            "exception_class": _exception_class(exc),
            "transport": _transport(result),
            "receipt_present": receipt_present,
            "bootstrap_staging_present": bootstrap_staging_present,
            "start_record_present": True,
            "raw_stdout_retained": False,
            "raw_stderr_retained": False,
            "review_packet_created": False,
            "review_approved_claimed": False,
            "probe02_authority_consumed": False,
            "hosted_requests": 0,
            "auth_payloads": 0,
            "qualification_attempts_consumed": 0,
            "randomization_created": False,
        }
    )


def run_publisher(
    *, repo: Path, commit: str, paths: Mapping[str, Path], publisher_sha256: str,
    trusted_bootstrap: bytes, launcher: Launcher = _default_launcher,
    publisher: Publisher = _atomic_publish, clock: Clock = _now,
) -> Mapping[str, object]:
    _verify_preclaim(paths, repo)
    _claim_root(paths["root"])
    start_payload = _start_payload(commit, publisher_sha256, _sha256(trusted_bootstrap), clock())
    try:
        start = publisher(paths["root"], START_NAME, start_payload)
    except BaseException:
        if paths["root"].exists() and not any(paths["root"].iterdir()):
            try:
                paths["root"].rmdir()
            except OSError:
                pass
        raise
    if (
        start.get("readiness_invocation_started") is not True
        or paths["start"].read_bytes() != start_payload
    ):
        raise EvidencePublicationError("readiness start record unavailable")

    result: ChildResult | None = None
    stage = "child_launch"
    try:
        argv = [
            str(EXPECTED_PYTHON_PATH),
            "-I",
            "-",
            "--repo-root",
            str(repo),
            "--owner-authorized-freeze-commit",
            commit,
        ]
        result = launcher(argv, trusted_bootstrap, repo, dict(os.environ), CHILD_TIMEOUT_SECONDS)
        stage = "transport_result"
        if result.timed_out:
            raise EvidencePublicationError("readiness child timed out")
        if result.returncode != 0:
            raise EvidencePublicationError("readiness child returned nonzero")
        if result.stderr:
            raise EvidencePublicationError("readiness child produced stderr")
        stage = "receipt_validation"
        receipt = _validate_receipt(result.stdout, commit)
        if _bootstrap_staging(repo).exists():
            raise EvidencePublicationError("trusted bootstrap staging cleanup incomplete")
        stage = "receipt_publication"
        published = publisher(paths["root"], RECEIPT_NAME, result.stdout)
        if published != receipt or paths["receipt"].read_bytes() != result.stdout:
            raise EvidencePublicationError("published readiness receipt readback mismatch")
        if paths["review"].exists() or paths["terminal"].exists():
            raise EvidencePublicationError("unexpected review or terminal evidence")
        return {
            "status": "PARENT_READINESS_RECEIPT_PUBLISHED_NOT_REVIEWED",
            "execution_commit": commit,
            "receipt_bytes": len(result.stdout),
            "receipt_sha256": _sha256(result.stdout),
            "review_packet_created": False,
            "probe02_authority_consumed": False,
            "hosted_requests": 0,
        }
    except BaseException as exc:
        terminal_payload = _terminal_payload(
            commit=commit,
            stage=stage,
            exc=exc,
            result=result,
            receipt_present=paths["receipt"].is_file(),
            bootstrap_staging_present=_bootstrap_staging(repo).exists(),
        )
        try:
            return publisher(paths["root"], TERMINAL_NAME, terminal_payload)
        except BaseException as terminal_exc:
            if not paths["start"].is_file():
                raise TerminalPublicationError("terminal failed without durable start") from terminal_exc
            raise TerminalPublicationError("terminal publication failed; durable start remains") from terminal_exc


def execute(
    *, repo_root: Path, owner_authorized_freeze_commit: str,
    launcher: Launcher = _default_launcher, publisher: Publisher = _atomic_publish,
    clock: Clock = _now,
) -> Mapping[str, object]:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise EvidencePublicationError("publisher must be streamed from the owner-authorized commit blob")
    commit = owner_authorized_freeze_commit.lower()
    if len(commit) != 40 or any(char not in HEX for char in commit):
        raise EvidencePublicationError("owner-authorized commit invalid")
    repo = repo_root.resolve()
    _verify_runtime()
    if str(_git(repo, "rev-parse", "HEAD")) != commit:
        raise EvidencePublicationError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, commit)
    frozen = _verify_inventory(repo, commit, manifest)
    sources = _verify_sources(repo, manifest)
    paths = _evidence_contract(manifest, sources)
    return run_publisher(
        repo=repo,
        commit=commit,
        paths=paths,
        publisher_sha256=_sha256(frozen[PUBLISHER_NAME]),
        trusted_bootstrap=sources["trusted_bootstrap"],
        launcher=launcher,
        publisher=publisher,
        clock=clock,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = execute(
        repo_root=Path(args.repo_root),
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
