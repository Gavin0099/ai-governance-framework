#!/usr/bin/env python3
"""Report-only memory blocking policy disable attestation helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Sequence

from governance_tools.memory_authority_guard import _BLOCKING_POLICY_RELPATH


DISABLE_RECEIPT_RELPATH = "governance/memory_blocking_policy_disable_receipt.json"
DISABLE_RECEIPT_SCHEMA = "memory_blocking_policy_disable_receipt.v1"
POLICY_CHANGED_IN_CURRENT_DIFF = "blocking_policy_changed_in_current_diff"
POLICY_DISABLED_WITHOUT_ATTESTATION = (
    "blocking_policy_disabled_without_attestation"
)
POLICY_DELETED_WITHOUT_ATTESTATION = (
    "blocking_policy_deleted_without_attestation"
)
DISABLE_RECEIPT_INVALID = "blocking_policy_disable_receipt_invalid"
DISABLE_RECEIPT_STALE = "blocking_policy_disable_receipt_stale"


def normalize_repo_path(path_text: str) -> str:
    return path_text.strip().replace("\\", "/").lstrip("./")


def _run_git(repo: Path, args: Sequence[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _is_git_worktree(repo: Path) -> bool:
    code, stdout, _stderr = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and stdout.strip().lower() == "true"


def _git_commit_exists(repo: Path, commit_hash: str) -> bool:
    if not _is_git_worktree(repo):
        return True
    code, _stdout, _stderr = _run_git(
        repo,
        ["cat-file", "-e", f"{commit_hash}^{{commit}}"],
    )
    return code == 0


def _load_json_file(path: Path) -> tuple[dict | None, bool]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, False
    return (payload, True) if isinstance(payload, dict) else (None, False)


def _policy_file_is_disabled(repo_root: Path) -> bool:
    payload, ok = _load_json_file(repo_root / _BLOCKING_POLICY_RELPATH)
    return ok and payload is not None and payload.get("enabled") is False


def _policy_file_is_enabled(repo_root: Path) -> bool:
    payload, ok = _load_json_file(repo_root / _BLOCKING_POLICY_RELPATH)
    return ok and payload is not None and payload.get("enabled") is True


def _disable_receipt_is_valid(repo_root: Path) -> tuple[bool, bool]:
    path = repo_root / DISABLE_RECEIPT_RELPATH
    if not path.is_file():
        return False, False
    payload, ok = _load_json_file(path)
    if not ok or payload is None:
        return False, True
    if payload.get("receipt_schema") != DISABLE_RECEIPT_SCHEMA:
        return False, True
    for field_name in ("reason", "attested_by", "linked_commit"):
        if (
            not isinstance(payload.get(field_name), str)
            or not payload[field_name].strip()
        ):
            return False, True
    cannot_claim = payload.get("cannot_claim")
    if (
        not isinstance(cannot_claim, list)
        or not cannot_claim
        or not all(isinstance(item, str) and item.strip() for item in cannot_claim)
    ):
        return False, True
    if not _git_commit_exists(repo_root, payload["linked_commit"].strip()):
        return False, True
    return True, False


def policy_disable_attestation_warnings(
    repo_root: Path,
    changed_files: Sequence[str],
) -> list[str]:
    changed = {normalize_repo_path(item) for item in changed_files}
    warnings: list[str] = []

    policy_path = repo_root / _BLOCKING_POLICY_RELPATH
    if _BLOCKING_POLICY_RELPATH in changed:
        warnings.append(POLICY_CHANGED_IN_CURRENT_DIFF)
        if not policy_path.is_file():
            warnings.append(POLICY_DELETED_WITHOUT_ATTESTATION)
            return warnings

    receipt_path = repo_root / DISABLE_RECEIPT_RELPATH
    if not _policy_file_is_disabled(repo_root):
        if _policy_file_is_enabled(repo_root) and receipt_path.is_file():
            warnings.append(DISABLE_RECEIPT_STALE)
        return warnings

    receipt_valid, receipt_invalid = _disable_receipt_is_valid(repo_root)
    if receipt_invalid:
        warnings.append(DISABLE_RECEIPT_INVALID)
    if not receipt_valid:
        warnings.append(POLICY_DISABLED_WITHOUT_ATTESTATION)
    return warnings
