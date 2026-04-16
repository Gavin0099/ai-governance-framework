from __future__ import annotations

import pytest

from governance_tools.phase2_aggregation_consumer import (
    CANONICAL_CURRENT_STATES,
    WindowSpec,
    aggregate_phase2_state,
    normalize_misuse_evidence_status,
)


def test_alias_normalization_none_observed_to_not_observed_in_window():
    assert normalize_misuse_evidence_status("none_observed") == "not_observed_in_window"


def test_invalid_status_raises_value_error():
    with pytest.raises(ValueError):
        normalize_misuse_evidence_status("safe")


def test_case_a_all_not_tested_is_insufficient_observation():
    result = aggregate_phase2_state(
        sample_statuses=["not_tested", "not_tested", "not_tested"],
        window=WindowSpec(runs=3, sessions=2),
        historical_observed=False,
    )
    assert result["current_state"] == "insufficient_observation"
    assert result["promote_eligible"] is False


def test_case_b_historical_observed_then_not_reobserved_is_not_auto_closed():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=3, sessions=2),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
    )
    assert result["current_state"] == "risk_not_reobserved_yet"
    assert result["promote_eligible"] is False


def test_case_c_small_window_stays_insufficient_observation():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=1, sessions=1),
        historical_observed=False,
    )
    assert result["current_state"] == "insufficient_observation"
    assert result["promote_eligible"] is False


def test_case_d_closure_conditions_met_is_closure_verified():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=3, sessions=2),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        closure_review_approved=True,
    )
    assert result["current_state"] == "closure_verified"
    assert result["closure_condition_met"] is True
    assert result["promote_eligible"] is True


def test_closure_review_not_approved_cannot_be_closure_verified():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=3, sessions=2),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        closure_review_approved=False,
    )
    assert result["current_state"] == "risk_not_reobserved_yet"
    assert result["closure_condition_met"] is False
    assert result["promote_eligible"] is False


def test_closure_review_missing_defaults_to_not_approved():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=3, sessions=2),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        # closure_review_approved intentionally omitted (default False)
    )
    assert result["current_state"] == "risk_not_reobserved_yet"
    assert result["closure_condition_met"] is False
    assert result["promote_eligible"] is False


def test_historical_observed_with_insufficient_window_is_insufficient_closure_evidence():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=1, sessions=1),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        closure_review_approved=True,
    )
    assert result["current_state"] == "insufficient_closure_evidence"
    assert result["promote_eligible"] is False


def test_approved_cannot_override_insufficient_window():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=1, sessions=1),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        closure_review_approved=True,
    )
    assert result["current_state"] == "insufficient_closure_evidence"
    assert result["closure_condition_met"] is False
    assert result["promote_eligible"] is False


def test_observed_in_window_has_precedence_over_all_other_signals():
    result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "observed", "not_tested"],
        window=WindowSpec(runs=10, sessions=5),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        closure_review_approved=True,
    )
    assert result["current_state"] == "risk_observed"
    assert result["promote_eligible"] is False


def test_current_state_is_always_single_canonical_enum_value():
    result = aggregate_phase2_state(
        sample_statuses=["none_observed", "not_tested"],
        window=WindowSpec(runs=3, sessions=2),
        historical_observed=False,
    )
    assert result["current_state"] in CANONICAL_CURRENT_STATES
    assert isinstance(result["current_state"], str)
