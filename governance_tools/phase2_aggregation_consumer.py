#!/usr/bin/env python3
"""
Phase 2 aggregation consumer (minimal deterministic implementation).

Purpose:
- Normalize legacy alias: none_observed -> not_observed_in_window
- Apply canonical aggregation precedence deterministically
- Emit a single canonical current_state
- Provide a strict promote guardrail
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MISUSE_EVIDENCE_STATUSES = frozenset({
    "observed",
    "not_observed_in_window",
    "not_tested",
})

LEGACY_STATUS_ALIASES = {
    "none_observed": "not_observed_in_window",
}

CANONICAL_CURRENT_STATES = frozenset({
    "insufficient_observation",
    "risk_observed",
    "risk_persists",
    "risk_not_reobserved_yet",
    "insufficient_closure_evidence",
    "closure_verified",
})

APPROVED_CLOSURE_REVIEWER_ROLES = frozenset({
    "human_reviewer",
    "risk_owner",
})


@dataclass(frozen=True)
class WindowSpec:
    runs: int
    sessions: int
    min_runs: int = 3
    min_sessions: int = 2

    @property
    def adequate(self) -> bool:
        return self.runs >= self.min_runs and self.sessions >= self.min_sessions


def normalize_misuse_evidence_status(raw_status: str) -> str:
    """Normalize legacy alias to canonical status and validate value."""
    status = LEGACY_STATUS_ALIASES.get(raw_status, raw_status)
    if status not in MISUSE_EVIDENCE_STATUSES:
        raise ValueError(f"invalid misuse_evidence_status: {raw_status!r}")
    return status


def _validate_closure_approval(
    closure_approval: dict[str, Any] | None,
    *,
    historical_observed: bool,
    closure_review_approved: bool,
) -> dict[str, Any]:
    """
    Validate closure approval trust boundary.

    Rules:
    - approval is only meaningful on closure path (historical_observed=True)
    - approved=True requires reviewer metadata + evidence refs
    - legacy bool-only approval is rejected when True (must provide metadata)
    """
    if closure_approval is None:
        if closure_review_approved:
            raise ValueError(
                "closure_review_approved=True requires closure_approval metadata "
                "(reviewer_id/reviewer_role/review_note/evidence_refs)"
            )
        return {"approved": False}

    if not isinstance(closure_approval, dict):
        raise ValueError("closure_approval must be a dict when provided")

    approved = closure_approval.get("approved")
    if not isinstance(approved, bool):
        raise ValueError("closure_approval.approved must be bool")

    if approved and not historical_observed:
        raise ValueError(
            "closure approval is only valid on closure path (historical_observed=True)"
        )

    if not approved:
        return {"approved": False}

    reviewer_id = closure_approval.get("reviewer_id")
    reviewer_role = closure_approval.get("reviewer_role")
    review_note = closure_approval.get("review_note")
    evidence_refs = closure_approval.get("evidence_refs")

    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise ValueError("closure_approval.reviewer_id is required when approved=true")
    if reviewer_role not in APPROVED_CLOSURE_REVIEWER_ROLES:
        raise ValueError(
            "closure_approval.reviewer_role must be one of "
            f"{sorted(APPROVED_CLOSURE_REVIEWER_ROLES)} when approved=true"
        )
    if not isinstance(review_note, str) or not review_note.strip():
        raise ValueError("closure_approval.review_note is required when approved=true")
    if not isinstance(evidence_refs, list) or not evidence_refs or not all(
        isinstance(x, str) and x.strip() for x in evidence_refs
    ):
        raise ValueError(
            "closure_approval.evidence_refs must be a non-empty list[str] when approved=true"
        )

    return {
        "approved": True,
        "reviewer_id": reviewer_id.strip(),
        "reviewer_role": reviewer_role,
        "review_note": review_note.strip(),
        "evidence_refs": [x.strip() for x in evidence_refs],
    }


def aggregate_phase2_state(
    *,
    sample_statuses: list[str],
    window: WindowSpec,
    historical_observed: bool,
    remediation_introduced: bool = False,
    covers_original_misuse_path: bool = False,
    closure_review_approved: bool = False,
    closure_approval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Deterministic aggregation based on canonical precedence.

    Returns:
      {
        "current_state": <canonical enum>,
        "historical_observed": bool,
        "closure_condition_met": bool,
        "normalized_statuses": [...],
        "promote_eligible": bool,
      }
    """
    if not sample_statuses:
        sample_statuses = ["not_tested"]

    normalized_closure_approval = _validate_closure_approval(
        closure_approval,
        historical_observed=historical_observed,
        closure_review_approved=closure_review_approved,
    )
    closure_approved = normalized_closure_approval["approved"]

    normalized = [normalize_misuse_evidence_status(s) for s in sample_statuses]

    has_observed_in_window = any(s == "observed" for s in normalized)
    has_tested_evidence = any(s != "not_tested" for s in normalized)
    all_not_tested = all(s == "not_tested" for s in normalized)

    closure_condition_met = (
        historical_observed
        and remediation_introduced
        and covers_original_misuse_path
        and window.adequate
        and (not has_observed_in_window)
        and has_tested_evidence
        and closure_approved
    )

    if has_observed_in_window:
        current_state = "risk_observed"
    elif all_not_tested:
        current_state = "insufficient_observation"
    elif historical_observed:
        if not remediation_introduced:
            current_state = "risk_persists"
        elif closure_condition_met:
            current_state = "closure_verified"
        elif (not window.adequate) or (not covers_original_misuse_path) or (not has_tested_evidence):
            current_state = "insufficient_closure_evidence"
        else:
            current_state = "risk_not_reobserved_yet"
    else:
        # Conservative default: no historical observed does not auto-promote.
        current_state = "insufficient_observation"

    if current_state not in CANONICAL_CURRENT_STATES:
        raise ValueError(f"internal error: non-canonical current_state {current_state!r}")

    return {
        "current_state": current_state,
        "historical_observed": historical_observed,
        "closure_condition_met": closure_condition_met,
        "closure_approval": normalized_closure_approval,
        "normalized_statuses": normalized,
        "promote_eligible": current_state == "closure_verified",
    }
