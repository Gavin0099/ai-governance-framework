"""Governed AI Governance update receipt writer.

The receipt is reviewer evidence for updater/F-7 apply paths. It is not proof
that governance adoption, hook enforcement, or framework correctness is complete.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECEIPT_RELATIVE_PATH = "governance/.update-receipt.json"
RECEIPT_VERSION = "0.1"
RECEIPT_TYPE = "ai_governance_update"
CLAIM_BOUNDARY = [
    "receipt is review evidence, not proof",
    "no fetch truth is implied unless explicitly recorded",
    "consumer repo adoption is not proven complete",
]
NOT_CLAIMED = [
    "full governance adoption",
    "hook/CI enforcement",
    "memory completeness",
    "domain correctness",
    "release readiness",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_lock_adopted_commit(repo_root: Path) -> str | None:
    lock_path = repo_root / "governance" / "framework.lock.json"
    if not lock_path.is_file():
        return None
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    raw_adopted = payload.get("adopted_commit", "")
    if raw_adopted is None:
        return None
    adopted = str(raw_adopted).strip()
    return adopted or None


def build_update_receipt(
    *,
    tool: str,
    repo_root: Path,
    framework_root: Path,
    framework_before: str | None,
    framework_after: str | None,
    update_status: str,
    remote_evidence: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    framework_root = framework_root.resolve()
    lock_adopted_commit = _read_lock_adopted_commit(repo_root)
    lock_matches_checkout = bool(
        lock_adopted_commit and framework_after and lock_adopted_commit == framework_after
    )
    receipt: dict[str, Any] = {
        "receipt_version": RECEIPT_VERSION,
        "receipt_type": RECEIPT_TYPE,
        "tool": tool,
        "tool_mode": "apply",
        "repo_root": str(repo_root),
        "framework_root": str(framework_root),
        "framework_before": framework_before,
        "framework_after": framework_after,
        "lock_adopted_commit": lock_adopted_commit,
        "lock_matches_checkout": lock_matches_checkout,
        "update_status": update_status,
        "generated_at_utc": _utc_now(),
        "claim_boundary": list(CLAIM_BOUNDARY),
        "not_claimed": list(NOT_CLAIMED),
    }
    if remote_evidence is not None:
        receipt["remote_evidence"] = remote_evidence
    if warnings:
        receipt["warnings"] = list(warnings)
    return receipt


def write_update_receipt(
    *,
    tool: str,
    repo_root: Path,
    framework_root: Path,
    framework_before: str | None,
    framework_after: str | None,
    update_status: str,
    remote_evidence: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    receipt = build_update_receipt(
        tool=tool,
        repo_root=repo_root,
        framework_root=framework_root,
        framework_before=framework_before,
        framework_after=framework_after,
        update_status=update_status,
        remote_evidence=remote_evidence,
        warnings=warnings,
    )
    repo_root = repo_root.resolve()
    path = repo_root / RECEIPT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "written",
        "path": RECEIPT_RELATIVE_PATH,
        "staged": False,
        "claim_boundary": list(CLAIM_BOUNDARY),
        "not_claimed": list(NOT_CLAIMED),
        "receipt": receipt,
    }


def skipped_update_receipt(reason: str) -> dict[str, Any]:
    return {
        "status": "not_written",
        "path": RECEIPT_RELATIVE_PATH,
        "staged": False,
        "reason": reason,
        "claim_boundary": list(CLAIM_BOUNDARY),
        "not_claimed": list(NOT_CLAIMED),
    }
