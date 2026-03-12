#!/usr/bin/env python3
"""
Promotion policy for candidate memory.
"""

from __future__ import annotations

from typing import Any


ARCHITECTURE_SENSITIVE_RULES = {"architecture-sensitive", "refactor", "release", "cpp"}


def _extract_errors(check_result: dict[str, Any] | None) -> list[str]:
    if not check_result:
        return []
    errors = check_result.get("errors", [])
    return errors if isinstance(errors, list) else [str(errors)]


def classify_promotion_policy(
    runtime_contract: dict[str, Any],
    check_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rules = runtime_contract.get("rules", []) or []
    risk = str(runtime_contract.get("risk", "medium")).strip().lower()
    oversight = str(runtime_contract.get("oversight", "auto")).strip().lower()
    memory_mode = str(runtime_contract.get("memory_mode", "candidate")).strip().lower()
    errors = _extract_errors(check_result)

    if errors:
        return {
            "decision": "DO_NOT_PROMOTE",
            "reasons": ["Runtime checks reported blocking errors."],
        }

    if memory_mode == "stateless":
        return {
            "decision": "DO_NOT_PROMOTE",
            "reasons": ["Session is stateless; durable memory is not allowed."],
        }

    if risk == "high":
        return {
            "decision": "REVIEW_REQUIRED",
            "reasons": ["High-risk sessions require human review before memory promotion."],
        }

    if oversight in {"review-required", "human-approval"}:
        return {
            "decision": "REVIEW_REQUIRED",
            "reasons": [f"Oversight={oversight} requires explicit review before promotion."],
        }

    if memory_mode == "durable":
        return {
            "decision": "REVIEW_REQUIRED",
            "reasons": ["Durable memory must be confirmed through reviewed promotion flow."],
        }

    if any(rule in ARCHITECTURE_SENSITIVE_RULES for rule in rules):
        return {
            "decision": "REVIEW_REQUIRED",
            "reasons": ["Architecture-sensitive rule packs require reviewed memory promotion."],
        }

    if risk == "low" and oversight == "auto" and memory_mode == "candidate":
        return {
            "decision": "AUTO_PROMOTE",
            "reasons": ["Low-risk candidate memory may be auto-promoted."],
        }

    return {
        "decision": "REVIEW_REQUIRED",
        "reasons": ["Default to reviewed promotion when policy is not explicitly auto-safe."],
    }
