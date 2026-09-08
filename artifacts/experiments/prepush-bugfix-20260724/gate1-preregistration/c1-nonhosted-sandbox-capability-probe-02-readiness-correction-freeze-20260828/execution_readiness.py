from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Mapping


RECEIPT_SCHEMA = "c1-probe02-parent-readiness-receipt.v1"
REVIEW_SCHEMA = "c1-probe02-parent-readiness-review.v1"
ATTEMPT_ID = "C1-nonhosted-sandbox-capability-probe-02"
SENTINEL_BYTES = b"C1_PROBE02_PARENT_WRITE_SENTINEL_V1\n"
WHOAMI = Path("C:/Windows/System32/whoami.exe")
OWNER_SID_SHA256 = "dea14b735f9ee0b9f76ed9a612e88cfc5e620f872a5527d24d9db738a4842072"
SANDBOX_SID_SHA256 = "f0499f65a3828dfd191d0f3179ee47528dd723df2c1753e0f4131f83cd5017ce"
REPARSE_POINT = 0x400


class ReadinessError(RuntimeError):
    pass


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def safe_repo_path(raw: str, label: str) -> PurePosixPath:
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
        raise ReadinessError(f"unsafe repo path: {label}")
    return posix


def contained(repo: Path, raw: str, label: str) -> Path:
    anchor = repo.resolve()
    candidate = anchor.joinpath(*safe_repo_path(raw, label).parts).resolve()
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise ReadinessError(f"path escapes repository: {label}") from exc
    return candidate


def is_reparse_or_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & REPARSE_POINT)


def identity_projection(
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> Mapping[str, object]:
    completed = runner(
        [str(WHOAMI), "/user", "/fo", "csv", "/nh"],
        input=b"",
        capture_output=True,
        check=False,
        timeout=10.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise ReadinessError("bounded execution identity unavailable")
    matches = re.findall(rb"S-\d+(?:-\d+)+", completed.stdout)
    if len(matches) != 1:
        raise ReadinessError("bounded execution identity invalid")
    sid_digest = sha256(matches[0])
    account_class = {
        OWNER_SID_SHA256: "owner_candidate",
        SANDBOX_SID_SHA256: "offline_sandbox",
    }.get(sid_digest, "other")
    return {"sid_sha256": sid_digest, "account_class": account_class}


def _parent_contract(manifest: Mapping[str, object]) -> Mapping[str, object]:
    contracts = manifest.get("required_parent_roots")
    if not isinstance(contracts, list) or len(contracts) != 1:
        raise ReadinessError("required parent contract unavailable")
    contract = contracts[0]
    if not isinstance(contract, dict):
        raise ReadinessError("required parent contract invalid")
    required = {
        "repo_relative_path",
        "required_type",
        "anchor_repo_relative_path",
        "anchor_git_blob_oid",
        "anchor_bytes",
        "anchor_sha256",
        "expected_child_names",
        "resolved_containment_required",
        "reparse_or_symlink_forbidden",
        "write_capability_evidence_required",
    }
    if set(contract) != required:
        raise ReadinessError("required parent contract field drift")
    if (
        contract["required_type"] != "directory"
        or contract["resolved_containment_required"] is not True
        or contract["reparse_or_symlink_forbidden"] is not True
        or contract["write_capability_evidence_required"] is not True
    ):
        raise ReadinessError("required parent contract weakened")
    return contract


def verify_anchor_git_binding(
    repo: Path, commit: str, manifest: Mapping[str, object],
    git_runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    contract = _parent_contract(manifest)
    anchor_rel = str(contract["anchor_repo_relative_path"])
    completed = git_runner(
        [
            "git", "--no-replace-objects", "-c", f"safe.directory={repo.resolve()}",
            "-C", str(repo.resolve()), "rev-parse", f"{commit}:{anchor_rel}",
        ],
        input=b"",
        capture_output=True,
        check=False,
        timeout=15.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise ReadinessError("parent anchor Git binding unavailable")
    oid = completed.stdout.decode("ascii", errors="strict").strip()
    if oid != contract["anchor_git_blob_oid"]:
        raise ReadinessError("parent anchor Git OID mismatch")


def inspect_parent(
    repo: Path, manifest: Mapping[str, object]
) -> Mapping[str, object]:
    contract = _parent_contract(manifest)
    parent_rel = str(contract["repo_relative_path"])
    anchor_rel = str(contract["anchor_repo_relative_path"])
    parent = contained(repo, parent_rel, "required_parent")
    anchor = contained(repo, anchor_rel, "parent_anchor")
    if anchor.parent != parent:
        raise ReadinessError("parent anchor is not a direct child")
    if not parent.is_dir() or is_reparse_or_symlink(parent):
        raise ReadinessError("required parent is unavailable or indirect")
    if not anchor.is_file() or is_reparse_or_symlink(anchor):
        raise ReadinessError("required parent anchor is unavailable or indirect")
    if (
        anchor.stat().st_size != contract["anchor_bytes"]
        or sha256_file(anchor) != contract["anchor_sha256"]
    ):
        raise ReadinessError("required parent anchor binding mismatch")
    expected = contract["expected_child_names"]
    if not isinstance(expected, list) or any(not isinstance(item, str) for item in expected):
        raise ReadinessError("expected child allowlist invalid")
    children = sorted(item.name for item in parent.iterdir())
    if children != sorted(expected):
        raise ReadinessError("required parent contains unexpected children")
    projection = {
        "repo_relative_path": parent_rel,
        "anchor_repo_relative_path": anchor_rel,
        "anchor_sha256": str(contract["anchor_sha256"]),
        "children": children,
        "required_type": "directory",
        "resolved_containment": True,
        "reparse_or_symlink": False,
    }
    return {
        "parent": parent,
        "projection": projection,
        "projection_sha256": sha256(canonical_json(projection)),
    }


def run_readiness_probe(
    *, repo: Path, commit: str, manifest: Mapping[str, object],
    identity: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    before = inspect_parent(repo, manifest)
    parent = before["parent"]
    assert isinstance(parent, Path)
    sentinel = parent / ".c1-probe02-parent-readiness-sentinel"
    if sentinel.exists():
        raise ReadinessError("readiness sentinel already exists")
    cleanup_complete = False
    try:
        with sentinel.open("xb") as handle:
            handle.write(SENTINEL_BYTES)
            handle.flush()
            os.fsync(handle.fileno())
        if sentinel.read_bytes() != SENTINEL_BYTES:
            raise ReadinessError("readiness sentinel readback mismatch")
    finally:
        if sentinel.exists():
            sentinel.unlink()
        cleanup_complete = not sentinel.exists()
    if not cleanup_complete:
        raise ReadinessError("readiness sentinel cleanup failed")
    after = inspect_parent(repo, manifest)
    if before["projection_sha256"] != after["projection_sha256"]:
        raise ReadinessError("parent state drifted during readiness probe")
    value = {
        "schema": RECEIPT_SCHEMA,
        "status": "PARENT_READINESS_PASSED",
        "attempt_id": ATTEMPT_ID,
        "execution_commit": commit,
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "identity": dict(identity or identity_projection()),
        "parent_projection": before["projection"],
        "parent_projection_sha256": before["projection_sha256"],
        "sentinel_bytes": len(SENTINEL_BYTES),
        "sentinel_sha256": sha256(SENTINEL_BYTES),
        "sentinel_create_exclusive": True,
        "sentinel_fsync_completed": True,
        "sentinel_readback_exact": True,
        "cleanup_complete": True,
        "formal_attempt_claim_created": False,
        "hosted_requests": 0,
        "auth_payloads": 0,
        "qualification_attempts_consumed": 0,
    }
    return value


def validate_reviewed_readiness(
    *, repo: Path, commit: str, manifest: Mapping[str, object],
    owner_authorized_review_sha256: str,
    identity: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    binding = manifest.get("readiness_evidence")
    if not isinstance(binding, dict):
        raise ReadinessError("readiness evidence binding unavailable")
    expected_sentinel_bytes = binding.get("sentinel_bytes")
    expected_sentinel_sha256 = binding.get("sentinel_sha256")
    if (
        expected_sentinel_bytes != len(SENTINEL_BYTES)
        or expected_sentinel_sha256 != sha256(SENTINEL_BYTES)
    ):
        raise ReadinessError("readiness sentinel binding mismatch")
    receipt_path = Path(str(binding.get("receipt_path")))
    review_path = Path(str(binding.get("review_packet_path")))
    if not receipt_path.is_absolute() or not review_path.is_absolute():
        raise ReadinessError("readiness evidence path is not absolute")
    if not receipt_path.is_file() or not review_path.is_file():
        raise ReadinessError("reviewed readiness evidence unavailable")
    if (
        receipt_path.stat().st_size > int(binding.get("receipt_max_bytes", 0))
        or review_path.stat().st_size > int(binding.get("review_packet_max_bytes", 0))
    ):
        raise ReadinessError("reviewed readiness evidence exceeds bounded size")
    if len(owner_authorized_review_sha256) != 64:
        raise ReadinessError("owner readiness review digest invalid")
    review_payload = review_path.read_bytes()
    if sha256(review_payload) != owner_authorized_review_sha256:
        raise ReadinessError("owner readiness review digest mismatch")
    try:
        review = json.loads(review_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("readiness review packet invalid") from exc
    if not isinstance(review, dict) or review.get("schema") != REVIEW_SCHEMA:
        raise ReadinessError("readiness review schema mismatch")
    if review.get("review_verdict") != "APPROVED" or not review.get("review_session"):
        raise ReadinessError("readiness review was not independently approved")
    receipt_payload = receipt_path.read_bytes()
    if sha256(receipt_payload) != review.get("reviewed_receipt_sha256"):
        raise ReadinessError("reviewed readiness receipt digest mismatch")
    try:
        receipt = json.loads(receipt_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("readiness receipt invalid") from exc
    current_identity = dict(identity or identity_projection())
    live = inspect_parent(repo, manifest)
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("status") != "PARENT_READINESS_PASSED"
        or receipt.get("attempt_id") != ATTEMPT_ID
        or receipt.get("execution_commit") != commit
        or receipt.get("identity") != current_identity
        or receipt.get("parent_projection_sha256") != live["projection_sha256"]
        or receipt.get("sentinel_bytes") != expected_sentinel_bytes
        or receipt.get("sentinel_sha256") != expected_sentinel_sha256
        or receipt.get("sentinel_create_exclusive") is not True
        or receipt.get("sentinel_fsync_completed") is not True
        or receipt.get("sentinel_readback_exact") is not True
        or receipt.get("cleanup_complete") is not True
        or receipt.get("formal_attempt_claim_created") is not False
        or receipt.get("hosted_requests") != 0
        or receipt.get("auth_payloads") != 0
        or receipt.get("qualification_attempts_consumed") != 0
    ):
        raise ReadinessError("reviewed readiness receipt does not match live execution")
    return receipt


def evaluate_convergence(
    policy: Mapping[str, object], member: str, evidence: Mapping[str, object]
) -> str:
    members = policy.get("window_members")
    categories = policy.get("modeled_infrastructure_categories")
    if not isinstance(members, list) or member not in members or not isinstance(categories, list):
        raise ReadinessError("convergence policy unavailable")
    category = evidence.get("infrastructure_failure_category")
    if category is not None and category not in categories:
        return "STOP_BEFORE_FURTHER_FORMAL_ATTEMPT"
    requirements_key = (
        "probe_02_intended_surface_requires"
        if member == ATTEMPT_ID
        else "qualification_03_intended_surface_requires"
    )
    required = policy.get(requirements_key)
    if not isinstance(required, list):
        raise ReadinessError("intended surface contract unavailable")
    if all(evidence.get(field) is True for field in required):
        return "REACHED_INTENDED_SURFACE"
    if category in categories:
        return "MODELED_INFRASTRUCTURE_FAILURE"
    return "STOP_BEFORE_FURTHER_FORMAL_ATTEMPT"
