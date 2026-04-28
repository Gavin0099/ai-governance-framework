from __future__ import annotations

import pytest

from governance_tools.phase3_promotion_gate import evaluate_phase3_promotion_entry


def test_phase3_entry_allowed_only_on_closure_verified_and_promote_true():
    result = evaluate_phase3_promotion_entry(
        {
            "aggregation_result": {
                "current_state": "closure_verified",
                "promote_eligible": True,
            }
        }
    )
    assert result["phase3_entry_allowed"] is True


def test_phase3_entry_denied_when_promote_false_even_if_closure_verified():
    result = evaluate_phase3_promotion_entry(
        {
            "aggregation_result": {
                "current_state": "closure_verified",
                "promote_eligible": False,
            }
        }
    )
    assert result["phase3_entry_allowed"] is False


def test_phase3_entry_denied_for_non_closure_state_even_with_promote_true():
    result = evaluate_phase3_promotion_entry(
        {
            "aggregation_result": {
                "current_state": "risk_not_reobserved_yet",
                "promote_eligible": True,
            }
        }
    )
    assert result["phase3_entry_allowed"] is False


def test_raw_fields_cannot_bypass_gate_decision():
    """
    Integration proof:
    Even if raw fields imply an optimistic interpretation, the gate must deny
    when canonical aggregation_result is non-promotable.
    """
    payload = {
        "sample_level": {
            "misuse_evidence_status": "not_observed_in_window",
            "confidence_level": "high",
            "reviewer_note": "looks good to me",
        },
        "aggregation_result": {
            "current_state": "insufficient_closure_evidence",
            "promote_eligible": False,
        },
    }
    result = evaluate_phase3_promotion_entry(payload)
    assert result["phase3_entry_allowed"] is False
    assert result["decision_basis"]["current_state"] == "insufficient_closure_evidence"


def test_missing_aggregation_result_is_rejected():
    with pytest.raises(ValueError):
        evaluate_phase3_promotion_entry({})


def test_invalid_current_state_is_rejected():
    with pytest.raises(ValueError):
        evaluate_phase3_promotion_entry(
            {
                "aggregation_result": {
                    "current_state": "safe_now",
                    "promote_eligible": True,
                }
            }
        )


def test_non_bool_promote_eligible_is_rejected():
    with pytest.raises(ValueError):
        evaluate_phase3_promotion_entry(
            {
                "aggregation_result": {
                    "current_state": "closure_verified",
                    "promote_eligible": "true",
                }
            }
        )

