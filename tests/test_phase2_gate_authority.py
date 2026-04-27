"""
Tests for build_phase2_gate() — the authority-aware Phase 2 gate layer.

Design contract:
- Promotion gate never reads authority_assessment directly.
- build_phase2_gate() is the ONLY place where misuse evidence eligibility
  and escalation authority are combined.
- Fail-closed: missing or empty authority_assessment denies promotion.
"""
from __future__ import annotations

import pytest

from governance_tools.phase2_aggregation_consumer import build_phase2_gate
from governance_tools.phase3_promotion_gate import evaluate_phase3_promotion_entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _closure_verified_aggregation() -> dict:
    return {
        "current_state": "closure_verified",
        "promote_eligible": True,
    }


def _non_eligible_aggregation(state: str = "risk_not_reobserved_yet") -> dict:
    return {
        "current_state": state,
        "promote_eligible": False,
    }


def _authority_ok() -> dict:
    return {
        "ok": True,
        "release_blocked": False,
        "source": "authority-writer-monopoly",
        "release_block_reasons": [],
    }


def _authority_escalation_missing() -> dict:
    return {
        "ok": False,
        "release_blocked": True,
        "source": "escalation_expected_missing",
        "release_block_reasons": ["escalation_active_but_no_authority_artifacts"],
    }


def _authority_untrusted() -> dict:
    return {
        "ok": False,
        "release_blocked": True,
        "source": "authority-writer-monopoly",
        "release_block_reasons": [
            "untrusted_escalation_provenance",
            "untrusted_writer_identity",
        ],
    }


# ---------------------------------------------------------------------------
# build_phase2_gate: allow path
# ---------------------------------------------------------------------------

def test_gate_allows_when_aggregation_and_authority_both_ok():
    gate = build_phase2_gate(_closure_verified_aggregation(), _authority_ok())

    assert gate["gate_promote_eligible"] is True
    assert gate["aggregation_result"]["promote_eligible"] is True
    assert gate["authority_assessment_summary"]["ok"] is True
    assert gate["gate_block_reasons"] == []
    assert gate["gate_version"] == "phase2_gate.v1"


# ---------------------------------------------------------------------------
# build_phase2_gate: authority blocks promotion even when aggregation is eligible
# ---------------------------------------------------------------------------

def test_gate_denies_when_authority_missing_escalation():
    gate = build_phase2_gate(_closure_verified_aggregation(), _authority_escalation_missing())

    assert gate["gate_promote_eligible"] is False
    assert gate["aggregation_result"]["promote_eligible"] is False
    assert gate["authority_assessment_summary"]["ok"] is False
    assert "escalation_active_but_no_authority_artifacts" in gate["gate_block_reasons"]


def test_gate_denies_when_authority_untrusted():
    gate = build_phase2_gate(_closure_verified_aggregation(), _authority_untrusted())

    assert gate["gate_promote_eligible"] is False
    assert "untrusted_escalation_provenance" in gate["gate_block_reasons"]
    assert "untrusted_writer_identity" in gate["gate_block_reasons"]


def test_gate_denies_when_authority_release_blocked_even_if_ok_true():
    """release_blocked=True is sufficient to deny even when ok=True."""
    authority = {
        "ok": True,
        "release_blocked": True,
        "source": "authority-writer-monopoly",
        "release_block_reasons": ["forced_route_overdue"],
    }
    gate = build_phase2_gate(_closure_verified_aggregation(), authority)

    assert gate["gate_promote_eligible"] is False
    assert "forced_route_overdue" in gate["gate_block_reasons"]


# ---------------------------------------------------------------------------
# build_phase2_gate: fail-closed defaults
# ---------------------------------------------------------------------------

def test_gate_denies_on_empty_authority_assessment():
    """Empty dict → fail-closed defaults: ok=False, release_blocked=True."""
    gate = build_phase2_gate(_closure_verified_aggregation(), {})

    assert gate["gate_promote_eligible"] is False
    assert gate["authority_assessment_summary"]["ok"] is False
    assert gate["authority_assessment_summary"]["release_blocked"] is True


def test_gate_denies_when_aggregation_not_eligible_even_if_authority_ok():
    gate = build_phase2_gate(_non_eligible_aggregation(), _authority_ok())

    assert gate["gate_promote_eligible"] is False
    assert any(
        "aggregation_not_promote_eligible" in r for r in gate["gate_block_reasons"]
    )


def test_gate_accumulates_block_reasons_from_both_sides():
    gate = build_phase2_gate(_non_eligible_aggregation("risk_observed"), _authority_untrusted())

    reasons = gate["gate_block_reasons"]
    assert any("aggregation_not_promote_eligible" in r for r in reasons)
    assert "untrusted_escalation_provenance" in reasons


# ---------------------------------------------------------------------------
# build_phase2_gate: payload structure
# ---------------------------------------------------------------------------

def test_gate_payload_carries_authority_assessment_summary():
    gate = build_phase2_gate(_closure_verified_aggregation(), _authority_ok())

    summary = gate["authority_assessment_summary"]
    assert "ok" in summary
    assert "release_blocked" in summary
    assert "source" in summary
    assert "release_block_reasons" in summary


def test_gate_payload_aggregation_result_current_state_is_preserved():
    gate = build_phase2_gate(
        _non_eligible_aggregation("insufficient_closure_evidence"),
        _authority_ok(),
    )
    assert gate["aggregation_result"]["current_state"] == "insufficient_closure_evidence"


# ---------------------------------------------------------------------------
# Integration: build_phase2_gate → evaluate_phase3_promotion_entry
# ---------------------------------------------------------------------------

def test_promotion_gate_allows_via_gate_payload():
    gate = build_phase2_gate(_closure_verified_aggregation(), _authority_ok())
    result = evaluate_phase3_promotion_entry(gate)

    assert result["phase3_entry_allowed"] is True
    assert result["decision_basis"]["authority_ok"] is True
    assert result["decision_basis"].get("gate_block_reasons", []) == []


def test_promotion_gate_denies_via_gate_payload_when_authority_missing():
    gate = build_phase2_gate(_closure_verified_aggregation(), _authority_escalation_missing())
    result = evaluate_phase3_promotion_entry(gate)

    assert result["phase3_entry_allowed"] is False
    assert result["decision_basis"]["authority_ok"] is False
    assert "escalation_active_but_no_authority_artifacts" in result["decision_basis"]["gate_block_reasons"]


def test_promotion_gate_denies_via_gate_payload_when_aggregation_not_eligible():
    gate = build_phase2_gate(_non_eligible_aggregation(), _authority_ok())
    result = evaluate_phase3_promotion_entry(gate)

    assert result["phase3_entry_allowed"] is False
    assert result["decision_basis"]["promote_eligible"] is False


def test_promotion_gate_denies_via_gate_payload_when_both_fail():
    gate = build_phase2_gate(_non_eligible_aggregation(), _authority_escalation_missing())
    result = evaluate_phase3_promotion_entry(gate)

    assert result["phase3_entry_allowed"] is False
    assert result["decision_basis"]["authority_ok"] is False


def test_promotion_gate_existing_interface_still_works_without_authority():
    """Existing callers not using build_phase2_gate() must not regress."""
    result = evaluate_phase3_promotion_entry(
        {
            "aggregation_result": {
                "current_state": "closure_verified",
                "promote_eligible": True,
            }
        }
    )
    assert result["phase3_entry_allowed"] is True
    assert "gate_block_reasons" not in result["decision_basis"]
    assert "authority_ok" not in result["decision_basis"]
