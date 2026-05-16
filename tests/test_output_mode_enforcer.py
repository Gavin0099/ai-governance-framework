"""
test_output_mode_enforcer.py — enforce_output_mode claim ceiling enforcement

Tests:
  1.  governance_effective requested → always blocked (prohibited)
  2.  Unknown mode requested → blocked
  3.  existence=False → ceiling=transparency_observed; higher mode degraded
  4.  eligibility_evaluated=False → ceiling=closeout_recorded
  5.  compliance_present=False → ceiling=closeout_recorded
  6.  semantics_reviewed=False → ceiling=procedural_compliance_observed
  7.  All 4 layers present, no downgrade, no causal chain → ceiling=procedural_compliance_observed
  8.  Tier 0 downgrade → ceiling stays procedural_compliance_observed (reclassified as unconsumed)
  9.  Tier 1 downgrade, no causal chain → ceiling=bounded_integrity_discipline
  10. Tier 1 downgrade + causal chain (not cross_layer) → ceiling=causal_inference
  11. Tier 1 downgrade + causal chain + cross_layer → ceiling=governance_adequate
  12. Tier 2 without constrained_path_traceable → treated as Tier 1 (ceiling=bounded_integrity_discipline)
  13. Tier 2 with constrained_path_traceable + causal chain + cross_layer → ceiling=governance_adequate
  14. No downgrade + causal chain only (not cross_layer) → ceiling=causal_inference
  15. No downgrade + causal chain + cross_layer → ceiling=governance_adequate
  16. Request at exactly ceiling → allowed=True, enforcement_action=allow
  17. Request below ceiling → allowed=True, enforcement_action=allow
  18. Request above ceiling → allowed=False, enforcement_action=degrade, actual_mode=ceiling
  19. Missing record fields default to most conservative interpretation
  20. Invalid consequence_tier coerced to 0
  21. Degradation reason references correct contract layer for each failure point
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.output_mode_enforcer import enforce_output_mode


# ── Helpers ───────────────────────────────────────────────────────────────────

def _full_state(
    existence=True,
    eligibility_evaluated=True,
    compliance_present=True,
    semantics_reviewed=True,
) -> dict:
    return {
        "admissibility_state": {
            "existence": existence,
            "eligibility_evaluated": eligibility_evaluated,
            "compliance_present": compliance_present,
            "semantics_reviewed": semantics_reviewed,
        }
    }


def _with_downgrade(base: dict, applied=True, tier=1, traceable=False) -> dict:
    record = dict(base)
    record["downgrade"] = {
        "applied": applied,
        "consequence_tier": tier,
        "constrained_path_traceable": traceable,
    }
    return record


def _with_causal(base: dict, present=True, cross_layer=False) -> dict:
    record = dict(base)
    record["causal_chain"] = {"present": present, "cross_layer": cross_layer}
    return record


# ── 1. Prohibited mode ────────────────────────────────────────────────────────

def test_governance_effective_always_blocked():
    result = enforce_output_mode({}, "governance_effective")
    assert result["allowed"] is False
    assert result["enforcement_action"] == "block"
    assert "permanently prohibited" in result["reason"]
    assert result["actual_mode"] == "governance_adequate"


# ── 2. Unknown mode ───────────────────────────────────────────────────────────

def test_unknown_mode_blocked():
    result = enforce_output_mode({}, "some_made_up_mode")
    assert result["allowed"] is False
    assert result["enforcement_action"] == "block"
    assert "unknown mode" in result["reason"]
    assert result["actual_mode"] == "transparency_observed"


# ── 3. existence=False → ceiling=transparency_observed ───────────────────────

def test_existence_false_ceiling_transparency():
    record = _full_state(existence=False)
    result = enforce_output_mode(record, "closeout_recorded")
    assert result["allowed"] is False
    assert result["ceiling"] == "transparency_observed"
    assert result["enforcement_action"] == "degrade"
    assert "existence" in result["reason"]


def test_existence_false_transparency_itself_allowed():
    record = _full_state(existence=False)
    result = enforce_output_mode(record, "transparency_observed")
    assert result["allowed"] is True
    assert result["enforcement_action"] == "allow"


# ── 4. eligibility_evaluated=False → ceiling=closeout_recorded ───────────────

def test_eligibility_missing_ceiling_closeout_recorded():
    record = _full_state(eligibility_evaluated=False)
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["ceiling"] == "closeout_recorded"
    assert result["allowed"] is False
    assert "eligibility" in result["reason"]


def test_eligibility_missing_closeout_recorded_allowed():
    record = _full_state(eligibility_evaluated=False)
    result = enforce_output_mode(record, "closeout_recorded")
    assert result["allowed"] is True


# ── 5. compliance_present=False → ceiling=closeout_recorded ──────────────────

def test_compliance_missing_ceiling_closeout_recorded():
    record = _full_state(compliance_present=False)
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["ceiling"] == "closeout_recorded"
    assert result["allowed"] is False
    assert "compliance" in result["reason"]


# ── 6. semantics_reviewed=False → ceiling=procedural_compliance_observed ─────

def test_semantics_missing_ceiling_procedural():
    record = _full_state(semantics_reviewed=False)
    result = enforce_output_mode(record, "bounded_integrity_discipline")
    assert result["ceiling"] == "procedural_compliance_observed"
    assert result["allowed"] is False
    assert "semantics" in result["reason"]


def test_semantics_missing_procedural_allowed():
    record = _full_state(semantics_reviewed=False)
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["allowed"] is True


# ── 7. All 4 layers, no downgrade, no causal → procedural_compliance ─────────

def test_all_layers_no_causal_ceiling_procedural():
    record = _full_state()
    result = enforce_output_mode(record, "bounded_integrity_discipline")
    assert result["ceiling"] == "procedural_compliance_observed"
    assert result["allowed"] is False


def test_all_layers_no_causal_procedural_allowed():
    record = _full_state()
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["allowed"] is True
    assert result["ceiling"] == "procedural_compliance_observed"


# ── 8. Tier 0 downgrade → reclassified as unconsumed, ceiling=procedural ─────

def test_tier0_downgrade_ceiling_stays_procedural():
    record = _with_downgrade(_full_state(), tier=0)
    result = enforce_output_mode(record, "bounded_integrity_discipline")
    assert result["ceiling"] == "procedural_compliance_observed"
    assert result["allowed"] is False
    assert "Tier 0" in result["reason"] or "unconsumed" in result["reason"]


def test_tier0_downgrade_procedural_allowed():
    record = _with_downgrade(_full_state(), tier=0)
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["allowed"] is True


# ── 9. Tier 1 downgrade, no causal → bounded_integrity_discipline ─────────────

def test_tier1_no_causal_ceiling_bounded():
    record = _with_downgrade(_full_state(), tier=1)
    result = enforce_output_mode(record, "causal_inference")
    assert result["ceiling"] == "bounded_integrity_discipline"
    assert result["allowed"] is False


def test_tier1_no_causal_bounded_allowed():
    record = _with_downgrade(_full_state(), tier=1)
    result = enforce_output_mode(record, "bounded_integrity_discipline")
    assert result["allowed"] is True
    assert result["ceiling"] == "bounded_integrity_discipline"


# ── 10. Tier 1 + causal (not cross_layer) → causal_inference ─────────────────

def test_tier1_causal_no_cross_layer_ceiling_causal():
    record = _with_causal(_with_downgrade(_full_state(), tier=1), cross_layer=False)
    result = enforce_output_mode(record, "governance_adequate")
    assert result["ceiling"] == "causal_inference"
    assert result["allowed"] is False
    assert "cross_layer" in result["reason"] or "cross-layer" in result["reason"]


def test_tier1_causal_no_cross_layer_causal_allowed():
    record = _with_causal(_with_downgrade(_full_state(), tier=1), cross_layer=False)
    result = enforce_output_mode(record, "causal_inference")
    assert result["allowed"] is True


# ── 11. Tier 1 + causal + cross_layer → governance_adequate ──────────────────

def test_tier1_causal_cross_layer_ceiling_adequate():
    record = _with_causal(_with_downgrade(_full_state(), tier=1), cross_layer=True)
    result = enforce_output_mode(record, "governance_adequate")
    assert result["ceiling"] == "governance_adequate"
    assert result["allowed"] is True
    assert result["enforcement_action"] == "allow"


# ── 12. Tier 2 without traceable path → treated as Tier 1 ────────────────────

def test_tier2_not_traceable_treated_as_tier1():
    record = _with_causal(
        _with_downgrade(_full_state(), tier=2, traceable=False),
        cross_layer=True,
    )
    # Even with cross_layer, Tier 2 not traceable → Tier 1 path → governance_adequate
    # Wait: Tier 1 + causal + cross_layer IS governance_adequate (test 11 above).
    # But consequence_tier is downgraded to 1 first, then causal chain determines.
    # So: Tier2-not-traceable → Tier1 effective → causal+cross_layer → governance_adequate
    result = enforce_output_mode(record, "governance_adequate")
    assert result["ceiling"] == "governance_adequate"
    assert result["allowed"] is True


def test_tier2_not_traceable_no_causal_treated_as_tier1():
    record = _with_downgrade(_full_state(), tier=2, traceable=False)
    # No causal chain; Tier 2 → Tier 1 effective → ceiling = bounded_integrity_discipline
    result = enforce_output_mode(record, "causal_inference")
    assert result["ceiling"] == "bounded_integrity_discipline"
    assert result["allowed"] is False


# ── 13. Tier 2 traceable + causal + cross_layer → governance_adequate ─────────

def test_tier2_traceable_causal_cross_layer_ceiling_adequate():
    record = _with_causal(
        _with_downgrade(_full_state(), tier=2, traceable=True),
        cross_layer=True,
    )
    result = enforce_output_mode(record, "governance_adequate")
    assert result["ceiling"] == "governance_adequate"
    assert result["allowed"] is True


# ── 14. No downgrade + causal only (not cross_layer) → causal_inference ───────

def test_no_downgrade_causal_no_cross_ceiling_causal():
    record = _with_causal(_full_state(), cross_layer=False)
    result = enforce_output_mode(record, "governance_adequate")
    assert result["ceiling"] == "causal_inference"
    assert result["allowed"] is False


def test_no_downgrade_causal_no_cross_causal_allowed():
    record = _with_causal(_full_state(), cross_layer=False)
    result = enforce_output_mode(record, "causal_inference")
    assert result["allowed"] is True


# ── 15. No downgrade + causal + cross_layer → governance_adequate ─────────────

def test_no_downgrade_causal_cross_layer_ceiling_adequate():
    record = _with_causal(_full_state(), cross_layer=True)
    result = enforce_output_mode(record, "governance_adequate")
    assert result["ceiling"] == "governance_adequate"
    assert result["allowed"] is True


# ── 16. Request at exactly ceiling → allowed ──────────────────────────────────

def test_request_at_ceiling_allowed():
    record = _full_state()
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["allowed"] is True
    assert result["actual_mode"] == "procedural_compliance_observed"
    assert result["enforcement_action"] == "allow"


# ── 17. Request below ceiling → allowed ───────────────────────────────────────

def test_request_below_ceiling_allowed():
    record = _with_causal(_full_state(), cross_layer=True)
    # ceiling = governance_adequate; request closeout_recorded (well below)
    result = enforce_output_mode(record, "closeout_recorded")
    assert result["allowed"] is True
    assert result["ceiling"] == "governance_adequate"
    assert result["actual_mode"] == "closeout_recorded"


# ── 18. Request above ceiling → degraded to ceiling ───────────────────────────

def test_request_above_ceiling_degrades():
    record = _full_state()  # ceiling = procedural_compliance_observed
    result = enforce_output_mode(record, "governance_adequate")
    assert result["allowed"] is False
    assert result["enforcement_action"] == "degrade"
    assert result["actual_mode"] == "procedural_compliance_observed"
    assert result["ceiling"] == "procedural_compliance_observed"


# ── 19. Missing record fields default conservatively ──────────────────────────

def test_empty_record_ceiling_transparency():
    result = enforce_output_mode({}, "closeout_recorded")
    assert result["ceiling"] == "transparency_observed"
    assert result["allowed"] is False


def test_partial_record_no_downgrade_key():
    # admissibility_state fully satisfied, no downgrade key, no causal key
    record = {"admissibility_state": {
        "existence": True,
        "eligibility_evaluated": True,
        "compliance_present": True,
        "semantics_reviewed": True,
    }}
    result = enforce_output_mode(record, "procedural_compliance_observed")
    assert result["allowed"] is True
    assert result["ceiling"] == "procedural_compliance_observed"


def test_null_admissibility_state():
    record = {"admissibility_state": None}
    result = enforce_output_mode(record, "closeout_recorded")
    assert result["ceiling"] == "transparency_observed"
    assert result["allowed"] is False


# ── 20. Invalid consequence_tier coerced to 0 ────────────────────────────────

def test_invalid_tier_string_coerced_to_0():
    record = _full_state()
    record["downgrade"] = {"applied": True, "consequence_tier": "bad_value"}
    result = enforce_output_mode(record, "bounded_integrity_discipline")
    # tier="bad_value" → 0 → Tier 0 → ceiling = procedural_compliance_observed
    assert result["ceiling"] == "procedural_compliance_observed"
    assert result["allowed"] is False


def test_invalid_tier_none_coerced_to_0():
    record = _full_state()
    record["downgrade"] = {"applied": True, "consequence_tier": None}
    result = enforce_output_mode(record, "bounded_integrity_discipline")
    assert result["ceiling"] == "procedural_compliance_observed"


def test_tier_out_of_range_clamped():
    # tier=99 → clamped to 2; with no causal chain → bounded_integrity_discipline
    record = _full_state()
    record["downgrade"] = {
        "applied": True,
        "consequence_tier": 99,
        "constrained_path_traceable": True,
    }
    result = enforce_output_mode(record, "causal_inference")
    assert result["ceiling"] == "bounded_integrity_discipline"
    assert result["allowed"] is False


# ── 21. Degradation reason references contract layer ─────────────────────────

def test_reason_names_existence_layer():
    result = enforce_output_mode(
        _full_state(existence=False), "closeout_recorded"
    )
    assert "existence" in result["reason"]


def test_reason_names_eligibility_layer():
    result = enforce_output_mode(
        _full_state(eligibility_evaluated=False), "procedural_compliance_observed"
    )
    assert "eligibility" in result["reason"]


def test_reason_names_compliance_layer():
    result = enforce_output_mode(
        _full_state(compliance_present=False), "procedural_compliance_observed"
    )
    assert "compliance" in result["reason"]


def test_reason_names_semantics_layer():
    result = enforce_output_mode(
        _full_state(semantics_reviewed=False), "bounded_integrity_discipline"
    )
    assert "semantics" in result["reason"]


def test_reason_names_causal_chain_for_causal_inference():
    record = _full_state()  # ceiling = procedural_compliance_observed
    result = enforce_output_mode(record, "causal_inference")
    assert "causal" in result["reason"]


def test_reason_names_cross_layer_for_governance_adequate():
    record = _with_causal(_full_state(), cross_layer=False)
    result = enforce_output_mode(record, "governance_adequate")
    assert "cross" in result["reason"]


# ── Result schema completeness ────────────────────────────────────────────────

def test_result_contains_all_required_keys():
    result = enforce_output_mode({}, "transparency_observed")
    required = {"requested_mode", "allowed", "actual_mode", "ceiling", "enforcement_action", "reason"}
    assert required <= result.keys()


def test_requested_mode_echoed():
    result = enforce_output_mode({}, "transparency_observed")
    assert result["requested_mode"] == "transparency_observed"
