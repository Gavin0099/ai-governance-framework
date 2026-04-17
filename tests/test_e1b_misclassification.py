"""
tests/test_e1b_misclassification.py
=====================================
Anti-drift verification suite for E1b Phase 2 classification and gate.

Purpose
-------
These tests verify CORRECTNESS and STABILITY of the classification system —
not just that features "work", but that the system does NOT misclassify in
ways that would lead to incorrect promotion decisions.

Three verifications (釘住 — 2026-04-17):

  1. False Transition
     transitioning_active is semantically NEUTRAL: it is applied to both
     "genuinely improving" and "persistently oscillating" repos.
     The system does not claim directional certainty it does not have.
     Mitigation: recent_lifecycle_class IS directional (rolling window).
     Test pins: both trajectories → transitioning_active (full-history);
     only improving → stable_ok (recent window).

  2. Observation Window Bias
     n >= 3 is necessary but NOT sufficient for temporal diversity.
     Three sessions from the same burst context yield the same lifecycle_class
     as three sessions spread across weeks.  Timestamps are not part of the
     lifecycle_class computation.
     Test pins: n<3 → insufficient_evidence; n>=3 from burst → classified
     (no temporal_diversity signal exposed).

  3. Gate Promotion Resistance
     High-volume transitioning_active fleets do NOT auto-promote through the
     Phase 2 gate.  The legacy nondegenerate_ratio check acts as a conservative
     barrier when session counts grow large enough to decay legacy entropy.
     Test pins:
       - 20-session transitioning fleet → gate NOT_READY (legacy blocks)
       - 7-session high-variety transitioning fleet → gate CAN be READY
       - lifecycle_active_ratio passes with ONLY transitioning_active repos
       - lifecycle_active_ratio requires NOT stuck_absent, not stable_ok
"""
from __future__ import annotations

import pytest

from scripts.analyze_e1b_distribution import (
    compute_repo_stats,
    evaluate_phase2_gate,
    _PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO,
    _PHASE2_MIN_NONDEGENERATE_RATIO,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _entry(
    repo: str,
    state: str,
    ts: str = "2026-04-17T00:00:00+00:00",
) -> dict:
    """Build a minimal audit log entry with a unique session_id."""
    return {
        "timestamp": ts,
        "session_id": f"sid-{repo}-{state}-{id({})}",
        "repo_name": repo,
        "artifact_state": state,
        "signals": [],
        "gate_blocked": False,
        "policy_provenance": {},
    }


def _n(
    repo: str,
    state: str,
    n: int,
    ts: str = "2026-04-17T00:00:00+00:00",
) -> list[dict]:
    return [
        {
            "timestamp": ts,
            "session_id": f"sid-{repo}-{state}-{i}",
            "repo_name": repo,
            "artifact_state": state,
            "signals": [],
            "gate_blocked": False,
            "policy_provenance": {},
        }
        for i in range(n)
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 1. FALSE TRANSITION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFalseTransition:
    """
    Pin: transitioning_active is semantically neutral.

    It is applied identically to:
      - A repo in the middle of genuine adoption (improving trajectory)
      - A repo that persistently oscillates with no directional trend

    The system does NOT claim directional certainty it does not have.
    Callers must NOT interpret transitioning_active as "confirmed improving".

    Mitigation: recent_lifecycle_class (rolling window) IS directional.
    A truly improving repo will show stable_ok in the recent window once
    the recent sessions converge; an oscillating repo will not.
    """

    def test_persistently_oscillating_gets_transitioning_active(self):
        """
        Equal absent/ok split (no directional trend) → transitioning_active.
        This is CORRECT: the system stays agnostic when evidence is ambiguous.
        Callers must not treat this as "confirmed improving".
        """
        entries = _n("osc", "absent", 10) + _n("osc", "ok", 10)
        stats = compute_repo_stats(entries)
        s = stats["osc"]
        assert s["lifecycle_class"] == "transitioning_active"
        # Not a quality failure — genuinely active, just not converged
        assert s["is_degenerate_v2"] is False

    def test_genuinely_improving_also_gets_transitioning_active(self):
        """
        Early absent phase + growing ok entries → transitioning_active (full-history).
        ok share = 13/21 = 62% < 90% threshold → cannot confirm stable yet.
        This is CORRECT: full-history view does not have enough evidence.
        """
        old_absent = _n("improve", "absent", 8)
        recent_ok = _n("improve", "ok", 13)
        entries = old_absent + recent_ok
        stats = compute_repo_stats(entries)
        s = stats["improve"]
        assert s["lifecycle_class"] == "transitioning_active"
        assert s["is_degenerate_v2"] is False

    def test_recent_window_distinguishes_improving_from_oscillating(self):
        """
        DESIGN BOUNDARY: transitioning_active is ambiguous in full-history,
        but recent_lifecycle_class CAN distinguish the two trajectories.

          improving  (10 old absent + 20 recent ok):
            full-history → transitioning_active
            recent window (last 20) → all ok → stable_ok

          oscillating (persistent absent/ok mix):
            full-history → transitioning_active
            recent window → still mixed → transitioning_active

        recent_lifecycle_class is the correct signal for promotion decisions.
        lifecycle_class (full-history) is audit context only.
        """
        # Improving: 10 old absent + 20 recent ok
        improving_entries = _n("imp", "absent", 10) + _n("imp", "ok", 20)

        # Oscillating: 15 absent + 15 ok interspersed, recent window still mixed
        oscillating_entries: list[dict] = []
        for i in range(15):
            oscillating_entries.append({
                "timestamp": "2026-04-17T00:00:00+00:00",
                "session_id": f"sid-osc2-ab-{i}",
                "repo_name": "osc2",
                "artifact_state": "absent",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            })
            oscillating_entries.append({
                "timestamp": "2026-04-17T00:00:00+00:00",
                "session_id": f"sid-osc2-ok-{i}",
                "repo_name": "osc2",
                "artifact_state": "ok",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            })

        imp_stats = compute_repo_stats(improving_entries)
        osc_stats = compute_repo_stats(oscillating_entries)

        imp = imp_stats["imp"]
        osc = osc_stats["osc2"]

        # Full-history: both transitioning_active
        assert imp["lifecycle_class"] == "transitioning_active", (
            "improving repo (ok<90%) must be transitioning_active in full-history"
        )
        assert osc["lifecycle_class"] == "transitioning_active", (
            "oscillating repo must be transitioning_active"
        )

        # Recent window: improving → stable_ok; oscillating → still transitioning
        assert imp["recent_lifecycle_class"] == "stable_ok", (
            "improving repo's recent 20 sessions are all ok → stable_ok"
        )
        assert osc["recent_lifecycle_class"] == "transitioning_active", (
            "oscillating repo's recent window still mixed → transitioning_active"
        )

    def test_transitioning_active_with_high_session_count_stays_neutral(self):
        """
        100 sessions with genuine variety → still transitioning_active.
        High session count does NOT upgrade semantic certainty of the label.
        """
        entries = (
            _n("heavy", "absent", 40)
            + _n("heavy", "ok", 40)
            + _n("heavy", "stale", 20)
        )
        stats = compute_repo_stats(entries)
        s = stats["heavy"]
        assert s["session_count"] == 100
        assert s["lifecycle_class"] == "transitioning_active"
        # v2 still non-degenerate despite high session count decaying legacy entropy
        assert s["is_degenerate_v2"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 2. OBSERVATION WINDOW BIAS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestObservationWindowBias:
    """
    Pin: n >= 3 is necessary but NOT sufficient for temporal diversity.

    The lifecycle_class computation does NOT use timestamps.  Three sessions
    from the same burst context (same minute) yield the same classification as
    three sessions spread across months.

    This is a documented design boundary, not a bug.  Tests pin the current
    behavior so that future changes do not accidentally introduce timestamp
    assumptions without explicit architectural review.
    """

    def test_three_same_timestamp_not_insufficient_evidence(self):
        """
        3 entries with identical timestamps (same-burst context) → classified
        normally, NOT marked insufficient_evidence.
        The n=3 threshold is count-based, not time-diversity-based.
        """
        ts = "2026-04-17T10:00:00+00:00"
        entries = [
            {
                "timestamp": ts,
                "session_id": f"sid-burst-absent-{i}",
                "repo_name": "burst",
                "artifact_state": "absent",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            }
            for i in range(3)
        ]
        stats = compute_repo_stats(entries)
        assert stats["burst"]["lifecycle_class"] != "insufficient_evidence"

    def test_three_spread_timestamps_same_classification_as_burst(self):
        """
        3 entries weeks apart → same lifecycle_class as 3 same-timestamp entries
        with identical states.  Temporal diversity is NOT captured.
        """
        burst_entries = [
            {
                "timestamp": "2026-04-17T10:00:00+00:00",
                "session_id": f"sid-b2-absent-{i}",
                "repo_name": "burst2",
                "artifact_state": "absent",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            }
            for i in range(3)
        ]
        spread_entries = [
            {
                "timestamp": "2026-01-01T10:00:00+00:00",
                "session_id": "sid-s2-absent-0",
                "repo_name": "spread2",
                "artifact_state": "absent",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            },
            {
                "timestamp": "2026-02-15T10:00:00+00:00",
                "session_id": "sid-s2-absent-1",
                "repo_name": "spread2",
                "artifact_state": "absent",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            },
            {
                "timestamp": "2026-04-01T10:00:00+00:00",
                "session_id": "sid-s2-absent-2",
                "repo_name": "spread2",
                "artifact_state": "absent",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            },
        ]
        burst_stats = compute_repo_stats(burst_entries)
        spread_stats = compute_repo_stats(spread_entries)

        # Identical state pattern → identical classification regardless of timestamp spread
        assert burst_stats["burst2"]["lifecycle_class"] == spread_stats["spread2"]["lifecycle_class"]

    def test_two_sessions_insufficient_regardless_of_time_spread(self):
        """
        2 entries months apart → still insufficient_evidence.
        The threshold is session COUNT, not calendar span.
        """
        entries = [
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "session_id": "sid-two-ok-0",
                "repo_name": "two-spread",
                "artifact_state": "ok",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            },
            {
                "timestamp": "2026-04-01T00:00:00+00:00",
                "session_id": "sid-two-ok-1",
                "repo_name": "two-spread",
                "artifact_state": "ok",
                "signals": [],
                "gate_blocked": False,
                "policy_provenance": {},
            },
        ]
        stats = compute_repo_stats(entries)
        assert stats["two-spread"]["lifecycle_class"] == "insufficient_evidence"

    def test_no_temporal_diversity_field_in_output(self):
        """
        DESIGN BOUNDARY: repo_stats output has no 'temporal_diversity' key.
        Callers that want to reason about observation time-spread must compute
        it themselves from 'first_seen' / 'last_seen'.
        """
        entries = _n("td", "ok", 5)
        stats = compute_repo_stats(entries)
        s = stats["td"]
        assert "temporal_diversity" not in s
        # but first_seen / last_seen ARE available for external calculation
        assert "first_seen" in s
        assert "last_seen" in s


# ══════════════════════════════════════════════════════════════════════════════
# 3. GATE PROMOTION RESISTANCE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGatePromotionResistance:
    """
    Pin: high-volume transitioning_active fleets do NOT auto-promote through
    Phase 2 gate.

    The legacy nondegenerate_ratio check (entropy = distinct_states / n) decays
    as session count grows.  With 20+ sessions and only 2–3 distinct states,
    entropy = 2/20 = 0.1 < 0.3 → is_degenerate = True (legacy).

    Result: the legacy metric provides conservative resistance even when the v2
    lifecycle_active_ratio check passes (all repos are non-stuck-absent).

    This resistance is NOT from a deliberate gate design choice — it is an
    artifact of the legacy entropy formula's decay.  It will disappear once the
    v2 metric is formally promoted in PLAN.md.  Until then, it acts as a safety
    brake for high-session-count fleets.

    Tests document both the resistance scenario AND the valid low-volume path
    where a transitioning_active fleet can legitimately pass the gate.
    """

    def test_high_volume_transitioning_fleet_gate_not_ready(self):
        """
        3 repos × 20 sessions each (alternating absent/ok) → all transitioning_active.
        v2: lifecycle_active_ratio = 1.0 → PASSES.
        Legacy: entropy = 2/20 = 0.1 < 0.3 → all degenerate → nondegenerate_ratio = 0.0 → FAILS.
        Gate verdict = NOT_READY.

        Documents: legacy entropy decay provides conservative gate resistance
        for high-volume fleets until v2 is promoted.
        """
        entries = (
            _n("r-a", "absent", 10) + _n("r-a", "ok", 10)
            + _n("r-b", "absent", 10) + _n("r-b", "ok", 10)
            + _n("r-c", "absent", 10) + _n("r-c", "ok", 10)
        )
        stats = compute_repo_stats(entries)

        # All repos: transitioning_active, not stuck, not stable
        for repo in ("r-a", "r-b", "r-c"):
            s = stats[repo]
            assert s["lifecycle_class"] == "transitioning_active"
            assert s["is_degenerate_v2"] is False
            # Legacy entropy fires (2/20 = 0.1 < 0.3)
            assert s["is_degenerate"] is True, (
                f"{repo}: expected legacy degenerate for high-volume 2-state repo"
            )

        gate = evaluate_phase2_gate(
            entries, stats,
            min_sessions=20,
            min_repos=3,
            min_nondegenerate_ratio=_PHASE2_MIN_NONDEGENERATE_RATIO,
            max_dominance=0.6,
            min_lifecycle_active_ratio=_PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO,
        )

        # v2 lifecycle_active_ratio: all non-stuck → PASSES
        assert gate["checks"]["lifecycle_active_ratio"]["pass"] is True
        assert gate["non_stuck_absent_ratio_v2"] == pytest.approx(1.0)

        # Legacy nondegenerate_ratio: all degenerate → FAILS
        assert gate["checks"]["min_nondegenerate_ratio"]["pass"] is False
        assert gate["nondegenerate_ratio"] == pytest.approx(0.0)

        # Overall gate: NOT_READY despite v2 positive
        assert gate["verdict"] == "NOT_READY"

    def test_low_volume_high_variety_transitioning_fleet_can_pass(self):
        """
        3 repos × 7 sessions each (3 distinct states) → all transitioning_active.
        Legacy entropy = 3/7 ≈ 0.43 >= 0.3 → NOT degenerate → legacy check passes.
        All 5 gate conditions pass → verdict = READY.

        Documents: Phase 2 READY is achievable with a transitioning_active fleet
        when session counts are small enough that legacy entropy does not decay.
        The gate does NOT require any repo to be stable_ok.
        """
        # 3 absent + 2 ok + 2 stale = 7 sessions, 3 states → entropy = 3/7 ≈ 0.43
        entries = (
            _n("t-a", "absent", 3) + _n("t-a", "ok", 2) + _n("t-a", "stale", 2)
            + _n("t-b", "absent", 3) + _n("t-b", "ok", 2) + _n("t-b", "stale", 2)
            + _n("t-c", "absent", 3) + _n("t-c", "ok", 2) + _n("t-c", "stale", 2)
        )
        stats = compute_repo_stats(entries)

        for repo in ("t-a", "t-b", "t-c"):
            s = stats[repo]
            assert s["lifecycle_class"] == "transitioning_active"
            assert s["is_degenerate"] is False, (
                f"{repo}: expected NOT legacy degenerate (entropy 3/7 >= 0.3)"
            )

        gate = evaluate_phase2_gate(
            entries, stats,
            min_sessions=20,
            min_repos=3,
            min_nondegenerate_ratio=_PHASE2_MIN_NONDEGENERATE_RATIO,
            max_dominance=0.6,
            min_lifecycle_active_ratio=_PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO,
        )

        # All 5 conditions should pass
        assert gate["checks"]["min_sessions"]["pass"] is True       # 21 >= 20
        assert gate["checks"]["min_repos"]["pass"] is True          # 3 >= 3
        assert gate["checks"]["min_nondegenerate_ratio"]["pass"] is True   # 1.0 >= 0.7
        assert gate["checks"]["max_repo_dominance"]["pass"] is True # 7/21 = 0.33 <= 0.6
        assert gate["checks"]["lifecycle_active_ratio"]["pass"] is True    # 1.0 >= 0.5

        assert gate["verdict"] == "READY"

    def test_lifecycle_active_ratio_requires_not_stuck_not_stable_ok(self):
        """
        stable_ok AND transitioning_active both count positively for
        lifecycle_active_ratio.  Only stuck_absent reduces the ratio.

        Documents: lifecycle_active_ratio is a FLOOR guard against adoption
        failure, not a CEILING that requires stable_ok maturity.
        """
        entries = (
            # stable_ok: 20 ok sessions, converged
            _n("stable", "ok", 20)
            # transitioning_active: genuine variety (n=20, 3 states)
            + _n("transit", "absent", 7) + _n("transit", "ok", 7) + _n("transit", "stale", 6)
            # stuck_absent: 20 identical absent sessions, frozen fingerprint
            + _n("stuck", "absent", 20)
        )
        stats = compute_repo_stats(entries)

        assert stats["stable"]["lifecycle_class"] == "stable_ok"
        assert stats["transit"]["lifecycle_class"] == "transitioning_active"
        assert stats["stuck"]["lifecycle_class"] == "stuck_absent"

        gate = evaluate_phase2_gate(
            entries, stats,
            min_sessions=1,
            min_repos=1,
            min_nondegenerate_ratio=0.0,
            max_dominance=1.0,
            min_lifecycle_active_ratio=_PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO,
        )

        # non_stuck = stable + transit = 2; total = 3 → ratio ≈ 0.667 >= 0.5
        assert gate["non_stuck_absent_repos_v2"] == 2
        assert gate["non_stuck_absent_ratio_v2"] == pytest.approx(2 / 3, abs=1e-3)
        assert gate["checks"]["lifecycle_active_ratio"]["pass"] is True

    def test_all_transitioning_no_stable_ok_lifecycle_active_passes(self):
        """
        Fleet with ONLY transitioning_active repos (no stable_ok) →
        lifecycle_active_ratio = 1.0 → lifecycle_active_ratio check PASSES.

        Documents: lifecycle_active_ratio does NOT demand stable_ok maturity.
        A fleet of genuinely-transitioning repos satisfies this condition.
        Conservative resistance comes from the legacy nondegenerate_ratio check
        when session counts grow large enough to decay entropy.
        """
        entries = (
            _n("m-a", "absent", 5) + _n("m-a", "ok", 5) + _n("m-a", "stale", 5)
            + _n("m-b", "absent", 5) + _n("m-b", "ok", 5) + _n("m-b", "stale", 5)
            + _n("m-c", "absent", 5) + _n("m-c", "ok", 5) + _n("m-c", "stale", 5)
        )
        stats = compute_repo_stats(entries)

        for repo in ("m-a", "m-b", "m-c"):
            assert stats[repo]["lifecycle_class"] == "transitioning_active"
            assert stats[repo]["lifecycle_class"] != "stable_ok"

        gate = evaluate_phase2_gate(
            entries, stats,
            min_sessions=1,
            min_repos=1,
            min_nondegenerate_ratio=0.0,
            max_dominance=1.0,
            min_lifecycle_active_ratio=_PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO,
        )

        # No stable_ok → lifecycle_active_ratio still passes (all non-stuck)
        assert gate["non_stuck_absent_ratio_v2"] == pytest.approx(1.0)
        assert gate["checks"]["lifecycle_active_ratio"]["pass"] is True
