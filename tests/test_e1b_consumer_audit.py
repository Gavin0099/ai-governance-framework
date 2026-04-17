"""
tests/test_e1b_consumer_audit.py
===================================
Consumer Violation Injection suite for E1b classification.

Purpose
-------
These tests simulate adversarial consumer inputs — the kind of summaries,
formulas, or narratives that would violate the semantic limits defined in:

  docs/e1b-classification-semantic-limits.md
  docs/e1b-consumer-audit-checklist.md

They verify that scan_consumer_text() CAN DETECT violations.

"Can detect" means: the problem surfaces and can be acted on by a human
or CI check.  These tests do NOT verify that violations are blocked at
runtime — the scanner is a detection tool, not an enforcer.

Three injection scenarios (釘住 — 2026-04-17):
  Scenario 1  Misleading Summary Injection
              transitioning_active + improvement narrative + promotion language
              → must detect P1 (improvement) and P4 (promotion)

  Scenario 2  Aggregation Misuse
              transitioning_count in numeric risk formula
              → must detect P2 (aggregation)

  Scenario 3  Temporal Misinterpretation
              temporal observation duration → reliability claim
              → must detect P3 (temporal)

Negative tests verify that clean / correctly-bounded text is NOT flagged.

NOT tested here
---------------
- Whether violations are blocked at runtime (out of scope — scanner only)
- Exhaustive coverage of every possible forbidden phrasing (smoke tests only)
- Violations in non-text artifacts (binary, JSON schema fields, etc.)
"""
from __future__ import annotations

import pytest

from governance_tools.e1b_consumer_audit import (
    scan_consumer_text,
    violation_pattern_ids,
)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1 — Misleading Summary Injection
# ══════════════════════════════════════════════════════════════════════════════

class TestMisleadingSummaryInjection:
    """
    Simulate a summary that:
      - uses transitioning_active to imply improvement (P1 violation)
      - uses "likely ready for promotion" as a conclusion (P4 violation)

    The scanner must surface BOTH violations so a reviewer can catch them.
    """

    _VIOLATING_SUMMARY = (
        "Repo is transitioning_active and showing improvement trend. "
        "System is likely ready for promotion."
    )

    def test_detects_improvement_narrative(self):
        """P1: 'transitioning_active' + 'improvement' → must be flagged."""
        pids = violation_pattern_ids(self._VIOLATING_SUMMARY)
        assert "P1" in pids, (
            "Expected P1 violation: transitioning_active implies improvement. "
            f"Got pattern IDs: {pids}"
        )

    def test_detects_promotion_narrative(self):
        """P4: 'likely ready for promotion' → must be flagged."""
        pids = violation_pattern_ids(self._VIOLATING_SUMMARY)
        assert "P4" in pids, (
            "Expected P4 violation: 'likely ready for promotion' implies "
            "gate verdict = promotion authorization. "
            f"Got pattern IDs: {pids}"
        )

    def test_violation_includes_excerpt(self):
        """Each violation must include a non-empty excerpt for traceability."""
        violations = scan_consumer_text(self._VIOLATING_SUMMARY)
        for v in violations:
            assert v["excerpt"], f"Violation {v['pattern_id']} has empty excerpt"
            assert len(v["excerpt"]) <= 120

    def test_clean_neutral_description_not_flagged(self):
        """
        Correctly-bounded language must NOT be flagged.
        'transitioning_active' as a neutral state description is permitted.
        """
        clean = (
            "Repo lifecycle_class: transitioning_active "
            "(genuine state variety, n=20). "
            "Monitoring continues. No promote decision at this time."
        )
        pids = violation_pattern_ids(clean)
        assert "P1" not in pids, (
            f"False positive: neutral transitioning_active description flagged as P1. "
            f"Got: {pids}"
        )
        assert "P4" not in pids


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 2 — Aggregation Misuse
# ══════════════════════════════════════════════════════════════════════════════

class TestAggregationMisuse:
    """
    Simulate a risk formula that uses transitioning_count as a numeric weight.

    transitioning_active is semantically neutral — adding it to a risk score
    incorrectly assigns it negative weight, converting a neutral observation
    into an adverse signal.

    The scanner must detect this as a P2 violation.
    """

    _VIOLATING_FORMULA = (
        "risk_score = len(advisory_signals) + transitioning_count"
    )

    def test_detects_aggregation_violation(self):
        """P2: transitioning_count in risk formula → must be flagged."""
        pids = violation_pattern_ids(self._VIOLATING_FORMULA)
        assert "P2" in pids, (
            "Expected P2 violation: transitioning_count used in arithmetic "
            "risk aggregation. "
            f"Got pattern IDs: {pids}"
        )

    def test_clean_count_reference_not_flagged(self):
        """
        Reading the count without arithmetic context is permitted.
        'transitioning count = 2' (assignment, not formula) must not fire P2.
        """
        clean = "transitioning_active count: 2 (informational, no gate impact)"
        pids = violation_pattern_ids(clean)
        assert "P2" not in pids, (
            f"False positive: plain count reference flagged as P2. Got: {pids}"
        )

    def test_risk_score_without_transitioning_not_flagged(self):
        """risk_score formula that does not reference transitioning → no P2."""
        clean = "risk_score = len(advisory_signals) + gate_blocked_count"
        pids = violation_pattern_ids(clean)
        assert "P2" not in pids, (
            f"False positive: risk_score without transitioning flagged as P2. "
            f"Got: {pids}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 3 — Temporal Misinterpretation
# ══════════════════════════════════════════════════════════════════════════════

class TestTemporalMisinterpretation:
    """
    Simulate a narrative that claims longer observation duration improves
    classification reliability.

    The system has no temporal reasoning — timestamps are not in the
    classification path.  Observation duration increases reviewer confidence
    and policy defensibility, NOT model precision.

    The scanner must detect this as a P3 violation.
    """

    _VIOLATING_NARRATIVE = (
        "Observed over multiple days → classification is more reliable."
    )

    def test_detects_temporal_reliability_claim(self):
        """P3: 'observed over multiple days' + 'more reliable' → must be flagged."""
        pids = violation_pattern_ids(self._VIOLATING_NARRATIVE)
        assert "P3" in pids, (
            "Expected P3 violation: temporal observation duration implied to "
            "improve classification reliability. "
            f"Got pattern IDs: {pids}"
        )

    def test_variant_classification_is_more_reliable(self):
        """P3: 'classification is more reliable' (direct phrase) → must be flagged."""
        text = "After extended observation, classification is more reliable."
        pids = violation_pattern_ids(text)
        assert "P3" in pids, (
            f"Expected P3 for direct phrase 'classification is more reliable'. "
            f"Got: {pids}"
        )

    def test_clean_temporal_reference_not_flagged(self):
        """
        Temporal reference WITHOUT a reliability/precision claim is permitted.
        Noting that observations span different contexts is correct.
        """
        clean = (
            "Sessions observed across multiple days provide policy-defensible "
            "confidence that patterns are not burst artifacts. "
            "Classification accuracy is unchanged."
        )
        pids = violation_pattern_ids(clean)
        assert "P3" not in pids, (
            f"False positive: correct temporal framing flagged as P3. Got: {pids}"
        )

    def test_clean_confidence_not_precision_not_flagged(self):
        """
        'reviewer confidence' is the correct framing — must NOT be flagged.
        The forbidden claim is about accuracy/reliability, not confidence.
        """
        clean = (
            "Extended observation increases reviewer confidence "
            "and policy defensibility."
        )
        pids = violation_pattern_ids(clean)
        assert "P3" not in pids, (
            f"False positive: correct 'reviewer confidence' framing flagged as P3. "
            f"Got: {pids}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Cross-scenario: clean summaries produce no violations
# ══════════════════════════════════════════════════════════════════════════════

class TestCleanSummaries:
    """
    Verify that correctly-bounded summaries — the kind Phase C documentation
    should use — produce no violations.

    These texts are the positive examples from the semantic limits doc.
    """

    def test_correct_phase_b_observation_summary(self):
        """A correctly-framed Phase B observation produces no violations."""
        text = (
            "Phase B observation: 3 lifecycle_capable repos. "
            "ai-governance-framework: lifecycle_class=transitioning_active "
            "(genuine state variety, n=45). "
            "recent_lifecycle_class=transitioning_active (last 20 sessions mixed). "
            "Gate: NOT_READY (legacy nondegenerate_ratio fails; v2 lifecycle_active_ratio passes). "
            "Phase 2 blocked by metric promotion decision, not repository readiness. "
            "Observation continues to accumulate policy-defensible session diversity."
        )
        violations = scan_consumer_text(text)
        assert violations == [], (
            f"Unexpected violations in clean Phase B summary: "
            f"{[v['pattern_id'] for v in violations]}"
        )

    def test_correct_ready_framing(self):
        """
        A correctly-framed READY verdict does not trigger P4.
        READY + 'quantitative conditions met' is permitted.
        """
        text = (
            "Gate verdict: READY. "
            "Quantitative conditions met (policy proxy). "
            "This reflects that threshold conditions are satisfied — "
            "it does not validate that the proxy set is universally correct."
        )
        pids = violation_pattern_ids(text)
        assert "P4" not in pids, (
            f"False positive: correct READY framing flagged as P4. Got: {pids}"
        )
