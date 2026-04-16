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


def aggregate_phase2_state(
    *,
    sample_statuses: list[str],
    window: WindowSpec,
    historical_observed: bool,
    remediation_introduced: bool = False,
    covers_original_misuse_path: bool = False,
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
        "normalized_statuses": normalized,
        "promote_eligible": current_state == "closure_verified",
    }

