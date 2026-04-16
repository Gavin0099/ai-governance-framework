"""
tests/test_enumd_e2e_phase3.py

End-to-end integration test: Enumd raw input cannot influence Phase 3 promotion gate.

Purpose
-------
This test suite walks the full pipeline:

    Enumd raw report
        -> integrations/enumd/enumd_adapter.adapt_enumd_report()
        -> canonical advisory envelope (ingest_status, observation, decision_constraints)
        -> governance_tools/phase2_aggregation_consumer.aggregate_phase2_state()
        -> governance_tools/phase3_promotion_gate.evaluate_phase3_promotion_entry()

and asserts that:

E1  No Enumd raw field (including forbidden authority fields like verdict,
    current_state, promote_eligible, phase3_entry_allowed) can cause
    phase3_entry_allowed=True in the gate output.

E2  An Enumd "all pass" report (suppressed=0, flagged=0, no advisories)
    does NOT satisfy Phase 3 promotion conditions.

E3  An Enumd report that injects promote_eligible=True and
    current_state="closure_verified" is stripped before reaching the gate.
    The gate still produces phase3_entry_allowed=False because the canonical
    aggregation (based on not_tested samples, no human closure approval) does
    not produce closure_verified.

E4  Even a maximally assertive Enumd payload (all forbidden fields set to the
    most permissive values) produces phase3_entry_allowed=False.

E5  The only way to reach phase3_entry_allowed=True is through the canonical
    aggregation path with legitimate inputs — an Enumd observation alone is
    insufficient.

Test structure
--------------
Each test exercises a distinct adversarial or boundary scenario to ensure that
the read-only pilot trust boundary is structurally enforced, not just documented.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.enumd.enumd_adapter import adapt_enumd_report
from governance_tools.phase2_aggregation_consumer import aggregate_phase2_state, WindowSpec
from governance_tools.phase3_promotion_gate import evaluate_phase3_promotion_entry

# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "enumd"


def _load(name: str) -> dict:
    p = FIXTURES_DIR / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _enumd_to_aggregation_input(env: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate what a downstream consumer might naively do: extract the
    misuse_evidence_status from the Enumd advisory envelope and feed it
    into the Phase 2 aggregation as a single-sample window.

    This represents the most direct (and adversarial) path: attempt to
    use Enumd observation as a direct Phase 2 sample.
    """
    status = env["observation"]["misuse_evidence_status"]
    return {
        "sample_statuses": [status],
        "window": WindowSpec(runs=1, sessions=1, min_runs=1, min_sessions=1),
        "historical_observed": False,
        "remediation_introduced": False,
        "covers_original_misuse_path": False,
        "closure_review_approved": False,
        "closure_approval": None,
    }


def _run_full_pipeline(report: dict[str, Any]) -> dict[str, Any]:
    """
    Run the complete Enumd -> adapter -> aggregation -> gate pipeline.

    Returns the Phase 3 gate output dict.
    """
    # Step 1: Enumd adapter
    envelope = adapt_enumd_report(report)

    # Step 2: Feed envelope observation as phase 2 sample
    agg_kwargs = _enumd_to_aggregation_input(envelope)
    agg_result = aggregate_phase2_state(**agg_kwargs)

    # Step 3: Phase 3 gate
    gate_input = {"aggregation_result": agg_result}
    gate_output = evaluate_phase3_promotion_entry(gate_input)

    return {
        "envelope": envelope,
        "aggregation_result": agg_result,
        "gate_output": gate_output,
    }


# ─────────────────────────────────────────────────────────────────────────────
# E1 — normal Enumd report cannot satisfy Phase 3 promotion
# ─────────────────────────────────────────────────────────────────────────────

def test_e1_normal_enumd_cannot_promote() -> None:
    """
    A normal well-formed Enumd report fed through the full pipeline must
    produce phase3_entry_allowed=False.

    Reason: Enumd produces misuse_evidence_status=not_tested, which leads to
    aggregate current_state=insufficient_observation.  Phase 3 requires
    closure_verified, so promotion is denied.
    """
    report = _load("valid_wave5")
    result = _run_full_pipeline(report)

    gate = result["gate_output"]
    assert gate["phase3_entry_allowed"] is False, (
        f"Enumd normal report must not satisfy Phase 3 promotion; "
        f"got phase3_entry_allowed={gate['phase3_entry_allowed']}, "
        f"decision_basis={gate['decision_basis']}"
    )
    # Confirm the denial basis is lack of closure_verified
    assert result["aggregation_result"]["current_state"] != "closure_verified"


# ─────────────────────────────────────────────────────────────────────────────
# E2 — all-pass Enumd report cannot satisfy Phase 3 promotion
# ─────────────────────────────────────────────────────────────────────────────

def test_e2_all_pass_enumd_cannot_promote() -> None:
    """
    An Enumd report where suppressed=0, flagged=0, no advisories must still
    produce phase3_entry_allowed=False.

    Enumd "all pass" is a synthesis quality signal, not a framework risk
    clearance.  It does not grant closure_verified status.
    """
    report = _load("looks_safe_not_tested")
    result = _run_full_pipeline(report)

    gate = result["gate_output"]
    assert gate["phase3_entry_allowed"] is False, (
        "Enumd all-pass must not grant Phase 3 promotion. "
        f"Got: {gate}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# E3 — forbidden authority field injection cannot satisfy Phase 3 promotion
# ─────────────────────────────────────────────────────────────────────────────

def test_e3_forbidden_authority_injection_cannot_promote() -> None:
    """
    An Enumd report that directly injects:
      verdict = "APPROVED"
      current_state = "closure_verified"
      promote_eligible = True
      phase3_entry_allowed = True
      closure_review_approved = True

    must still produce phase3_entry_allowed=False in the Phase 3 gate.

    The authority fields must be stripped by the adapter layer before reaching
    the aggregation or gate.
    """
    report = _load("forbidden_authority_fields")
    result = _run_full_pipeline(report)

    envelope = result["envelope"]
    gate = result["gate_output"]

    # Adapter must have degraded the envelope
    assert envelope["ingest_status"] == "degraded", (
        "Forbidden authority fields must cause degraded ingest_status"
    )

    # The injected promote_eligible=True and current_state=closure_verified
    # must NOT have propagated to the gate
    assert gate["phase3_entry_allowed"] is False, (
        "Forbidden authority field injection must not grant Phase 3 promotion. "
        f"Got gate_output={gate}"
    )

    # Confirm the aggregation reached not_tested (not closure_verified)
    agg = result["aggregation_result"]
    assert agg["current_state"] != "closure_verified", (
        "Injected current_state=closure_verified must not reach aggregation"
    )
    assert agg["promote_eligible"] is False, (
        "Injected promote_eligible=True must not propagate to aggregation output"
    )


# ─────────────────────────────────────────────────────────────────────────────
# E4 — maximally assertive Enumd payload cannot satisfy Phase 3 promotion
# ─────────────────────────────────────────────────────────────────────────────

def test_e4_maximally_assertive_enumd_cannot_promote() -> None:
    """
    A hand-crafted Enumd-like payload with every possible forbidden authority
    field set to the most permissive value must not produce
    phase3_entry_allowed=True.

    This is the most adversarial scenario: an external system attempting to
    claim maximum authority.
    """
    adversarial_report = {
        "producer": "enumd",
        "artifact_type": "governance_report",
        "schema_version": "1.0",
        "observation_class": "external_analysis_artifact",
        "observation_type": "synthesis_governance_report",
        "run_id": "adversarial-probe",
        "semantic_boundary": {
            "represents_agent_behavior": False,
            "derivation": "synthesis_pipeline",
        },
        "calibration_profile": {
            "name": "adversarial_v1",
            "overlap_thresholds": {"low_overlap": 0.0, "handoff": 0.0, "any_node": 0.0},
        },
        "observed": {"total_nodes": 1, "total_claims": 1},
        "policy_applied": {
            "policy_id": "bypass-all",
            "calibration_profile": "adversarial_v1",
            "outcomes": {"suppressed": 0, "flagged": 0, "passed": 1},
        },
        "advisories": [],
        # All forbidden authority fields set to most permissive values
        "verdict": "APPROVED",
        "gate_verdict": "pass",
        "current_state": "closure_verified",
        "closure_verified": True,
        "promote_eligible": True,
        "phase3_entry_allowed": True,
        "closure_review_approved": True,
    }

    result = _run_full_pipeline(adversarial_report)
    gate = result["gate_output"]

    assert gate["phase3_entry_allowed"] is False, (
        "Maximally assertive Enumd payload must not grant Phase 3 promotion. "
        f"Got: {gate}"
    )
    assert result["envelope"]["ingest_status"] == "degraded"
    assert result["envelope"]["decision_constraints"]["promotion_authority"] is False


# ─────────────────────────────────────────────────────────────────────────────
# E5 — canonical path DOES produce phase3_entry_allowed=True (control case)
# ─────────────────────────────────────────────────────────────────────────────

def test_e5_canonical_path_can_promote() -> None:
    """
    Control case: the canonical aggregation path with closure_verified state
    and human closure approval DOES produce phase3_entry_allowed=True.

    This proves that the gate works correctly and that E1-E4 denials are due
    to Enumd's advisory-only status, not a broken gate.
    """
    # Build a canonical aggregation result directly (bypassing Enumd entirely)
    # with all conditions for Phase 3 promotion met.
    #
    # closure_verified requires: historical_observed=True, remediation_introduced=True,
    # covers_original_misuse_path=True, window.adequate, NOT has_observed_in_window,
    # has_tested_evidence, closure_approved=True.
    #
    # The sample window must contain only not_observed_in_window entries (no "observed")
    # because closure means the risk was remediated and is no longer seen in the window.
    agg_result = aggregate_phase2_state(
        sample_statuses=["not_observed_in_window", "not_observed_in_window", "not_observed_in_window"],
        window=WindowSpec(runs=5, sessions=3),
        historical_observed=True,
        remediation_introduced=True,
        covers_original_misuse_path=True,
        closure_review_approved=True,
        closure_approval={
            "approved": True,
            "reviewer_id": "reviewer-001",
            "reviewer_role": "human_reviewer",
            "review_note": "Risk addressed and verified in production.",
            "evidence_refs": ["pr-4521", "test-run-7890"],
        },
    )

    gate_input = {"aggregation_result": agg_result}
    gate_output = evaluate_phase3_promotion_entry(gate_input)

    assert gate_output["phase3_entry_allowed"] is True, (
        "Canonical path with proper closure approval must produce "
        f"phase3_entry_allowed=True; got {gate_output}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# E6 — Enumd observation fields never appear in gate decision_basis
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture_name", [
    "valid_wave5",
    "forbidden_authority_fields",
    "looks_safe_not_tested",
    "ambiguous_status",
])
def test_e6_enumd_fields_absent_from_gate_decision_basis(fixture_name: str) -> None:
    """
    The Phase 3 gate decision_basis must only contain current_state and
    promote_eligible from the canonical aggregation — no raw Enumd fields.

    This confirms that Enumd data is fully absorbed by the adapter/aggregation
    layers and does not reach the gate's decision surface.
    """
    report = _load(fixture_name)
    result = _run_full_pipeline(report)

    decision_basis = result["gate_output"]["decision_basis"]

    # Gate decision basis must only have canonical keys
    expected_keys = {"current_state", "promote_eligible"}
    actual_keys = set(decision_basis.keys())
    assert actual_keys == expected_keys, (
        f"[{fixture_name}] Gate decision_basis has unexpected keys: "
        f"{actual_keys - expected_keys}"
    )

    # No Enumd-specific field names should appear in decision basis
    enumd_field_names = {
        "enumd", "run_id", "calibration_profile", "semantic_boundary",
        "synthesis", "advisory", "signal", "verdict", "suppressed", "flagged",
        "overlap_score", "domain_misalignment_risk", "thin_synthesis",
    }
    for key in decision_basis:
        assert key not in enumd_field_names, (
            f"[{fixture_name}] Enumd field {key!r} appeared in gate decision_basis"
        )
