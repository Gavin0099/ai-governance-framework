"""
tests/test_e1b_distribution_v2.py
===================================
Unit tests for E1b v2 shadow metrics introduced in bea9a03.

Covers:
  _normalized_shannon_entropy()
  compute_repo_stats() — normalized_state_entropy, dominant_state,
                          dominant_state_share, lifecycle_class, is_degenerate_v2
  evaluate_phase2_gate() — non_stuck_absent_ratio_v2, non_stuck_absent_repos_v2
  _auto_discover_logs()

Design boundary tests (釘住 PLAN.md 的語意邊界):
  - stable_ok is NOT degenerate_v2 even with low normalized entropy
  - stuck_absent requires dominant_state in absent/malformed AND frozen fingerprints
  - stable_ok does not let gate be over-optimistic (ratio still counts against
    non_stuck_absent, not AS pass — this only tests classification, not gate verdict)

NOT tested here:
  - Legacy entropy/is_degenerate (covered in test_e1b_observation.py)
  - Phase 2 gate verdict promotion (requires post-schema data; deferred)
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from scripts.analyze_e1b_distribution import (
    _auto_discover_logs,
    _load_entries,
    _normalized_shannon_entropy,
    compute_fleet_coverage,
    compute_repo_stats,
    evaluate_phase2_gate,
    _LC_DOMINANT_SHARE_THRESHOLD,
    _LC_FROZEN_DIVERSITY_THRESHOLD,
    _PHASE2_MIN_NONDEGENERATE_RATIO,
    _PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO,
)

_AUDIT_LOG_RELPATH = Path("artifacts") / "runtime" / "canonical-audit-log.jsonl"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _entry(repo: str, state: str, signals: list[str] | None = None,
           skip_type: str | None = None,
           schema_aware: bool = False) -> dict:
    """Build a fake audit log entry.

    schema_aware=True simulates a new-schema session_end_hook that always
    writes the 'skip_type' key (even when the value is None/null).
    schema_aware=False (default) simulates a pre-schema entry that lacks the
    key entirely.
    """
    prov: dict = {}
    if schema_aware:
        prov["skip_type"] = skip_type  # key always present; value may be null
    elif skip_type is not None:
        prov["skip_type"] = skip_type
    return {
        "timestamp": "2026-04-14T00:00:00+00:00",
        "session_id": f"sid-{repo}-{state}-{id(state)}",
        "repo_name": repo,
        "artifact_state": state,
        "signals": signals or [],
        "gate_blocked": False,
        "policy_provenance": prov,
    }


def _entries_n(repo: str, state: str, n: int) -> list[dict]:
    return [_entry(repo, state) for _ in range(n)]


# ── _normalized_shannon_entropy ───────────────────────────────────────────────

class TestNormalizedShannonEntropy:
    def test_all_same_state_is_zero(self):
        """All entries in one state → H = 0."""
        breakdown = {"absent": 100}
        assert _normalized_shannon_entropy(breakdown, 100) == 0.0

    def test_uniform_four_states_is_one(self):
        """Equal distribution across all 4 artifact states → H_norm ≈ 1.0."""
        breakdown = {"absent": 25, "ok": 25, "stale": 25, "malformed": 25}
        h = _normalized_shannon_entropy(breakdown, 100)
        assert h == pytest.approx(1.0, abs=1e-4)

    def test_stable_ok_heavy_is_low_but_nonzero(self):
        """ok:40, absent:1 → very low but > 0; must not equal all-same."""
        breakdown = {"ok": 40, "absent": 1}
        h = _normalized_shannon_entropy(breakdown, 41)
        assert 0.0 < h < 0.15, f"expected small positive, got {h}"

    def test_stable_with_100_sessions_same_as_10(self):
        """
        Normalized entropy must NOT decay with session count.
        ok:10 and ok:100 both → H_norm = 0 (pure single-state = degenerate by entropy).
        """
        h10 = _normalized_shannon_entropy({"ok": 10}, 10)
        h100 = _normalized_shannon_entropy({"ok": 100}, 100)
        assert h10 == h100 == 0.0

    def test_two_state_split_independent_of_n(self):
        """
        50/50 two-state split should return the same H_norm regardless of total n.
        absent:5/ok:5 == absent:50/ok:50
        """
        h5 = _normalized_shannon_entropy({"absent": 5, "ok": 5}, 10)
        h50 = _normalized_shannon_entropy({"absent": 50, "ok": 50}, 100)
        assert h5 == pytest.approx(h50, abs=1e-4)

    def test_zero_n_returns_zero(self):
        assert _normalized_shannon_entropy({}, 0) == 0.0


# ── lifecycle_class — stuck_absent ────────────────────────────────────────────

class TestLifecycleClassStuckAbsent:
    def test_all_absent_is_stuck_absent(self):
        """272 absent sessions → stuck_absent, is_degenerate_v2=True."""
        entries = _entries_n("repo-x", "absent", 29)
        stats = compute_repo_stats(entries)
        s = stats["repo-x"]
        assert s["lifecycle_class"] == "stuck_absent"
        assert s["is_degenerate_v2"] is True

    def test_dominant_malformed_is_stuck_absent(self):
        """
        All entries in malformed (single state, no diversity) → stuck_absent.
        Using a single state ensures fingerprint_diversity = 0 (all identical).
        NOTE: mixing malformed + absent gives diversity=0.10 which is NOT < threshold,
        so that scenario is correctly classified as mixed_active, not stuck_absent.
        """
        entries = _entries_n("repo-m", "malformed", 20)
        stats = compute_repo_stats(entries)
        s = stats["repo-m"]
        # dominant_state_share = 1.0; fingerprint_diversity = 0.0 (< 0.10) → stuck_absent
        assert s["lifecycle_class"] == "stuck_absent"

    def test_just_over_threshold_is_stuck_absent(self):
        """Exactly at _LC_DOMINANT_SHARE_THRESHOLD (0.90)."""
        n = 10
        absent_count = int(n * _LC_DOMINANT_SHARE_THRESHOLD)  # 9
        ok_count = n - absent_count  # 1
        entries = _entries_n("repo-t", "absent", absent_count) + _entries_n("repo-t", "ok", ok_count)
        stats = compute_repo_stats(entries)
        s = stats["repo-t"]
        # share = 0.90 (absent), fingerprint: 2 distinct (absent-no-sig vs ok-no-sig)
        # fingerprint_diversity = 2/10 = 0.2 >= 0.10 threshold → NOT frozen
        # so lifecycle_class should be mixed_active (not stuck_absent)
        assert s["lifecycle_class"] == "mixed_active"

    def test_below_share_threshold_not_stuck(self):
        """80% absent (< 0.90) → not stuck_absent."""
        entries = _entries_n("repo-b", "absent", 8) + _entries_n("repo-b", "ok", 2)
        stats = compute_repo_stats(entries)
        assert stats["repo-b"]["lifecycle_class"] != "stuck_absent"


# ── lifecycle_class — stable_ok ───────────────────────────────────────────────

class TestLifecycleClassStableOk:
    def test_mostly_ok_is_stable_ok(self):
        """ok:40, absent:1 → stable_ok, NOT is_degenerate_v2."""
        entries = _entries_n("bookstore", "ok", 40) + [_entry("bookstore", "absent")]
        stats = compute_repo_stats(entries)
        s = stats["bookstore"]
        assert s["lifecycle_class"] == "stable_ok"
        assert s["is_degenerate_v2"] is False

    def test_stable_ok_dominant_state_is_ok(self):
        entries = _entries_n("repo-ok", "ok", 30)
        stats = compute_repo_stats(entries)
        s = stats["repo-ok"]
        assert s["dominant_state"] == "ok"
        assert s["dominant_state_share"] == pytest.approx(1.0)

    def test_stable_ok_legacy_still_marks_degenerate(self):
        """
        DESIGN BOUNDARY: stable_ok has is_degenerate=True (legacy) but
        is_degenerate_v2=False.
        This test documents the intentional divergence.
        """
        entries = _entries_n("repo-ok2", "ok", 30)
        stats = compute_repo_stats(entries)
        s = stats["repo-ok2"]
        assert s["is_degenerate"] is True, "legacy metric still fires for stable_ok"
        assert s["is_degenerate_v2"] is False, "v2 must NOT misclassify stable_ok"

    def test_ok_with_few_sessions_is_stable_ok(self):
        """5 sessions all ok → stable_ok (sample size does not affect classification)."""
        entries = _entries_n("repo-small", "ok", 5)
        stats = compute_repo_stats(entries)
        # dominant_state_share = 1.0 >= 0.90; dominant_state = ok → stable_ok
        assert stats["repo-small"]["lifecycle_class"] == "stable_ok"


# ── lifecycle_class — mixed_active ────────────────────────────────────────────

class TestLifecycleClassMixedActive:
    def test_genuine_variety_is_mixed_active(self):
        """absent/ok/stale with reasonable spread → mixed_active."""
        entries = (
            _entries_n("repo-mix", "absent", 5)
            + _entries_n("repo-mix", "ok", 10)
            + _entries_n("repo-mix", "stale", 5)
        )
        stats = compute_repo_stats(entries)
        assert stats["repo-mix"]["lifecycle_class"] == "mixed_active"

    def test_single_session_is_mixed_active(self):
        """1 session → mixed_active (insufficient evidence)."""
        entries = [_entry("repo-1", "absent")]
        stats = compute_repo_stats(entries)
        assert stats["repo-1"]["lifecycle_class"] == "mixed_active"

    def test_mixed_active_not_degenerate_v2(self):
        """mixed_active → is_degenerate_v2=False."""
        entries = _entries_n("repo-m2", "absent", 5) + _entries_n("repo-m2", "ok", 5)
        stats = compute_repo_stats(entries)
        assert stats["repo-m2"]["is_degenerate_v2"] is False


# ── dominant_state + dominant_state_share ────────────────────────────────────

class TestDominantState:
    def test_dominant_state_is_most_frequent(self):
        entries = (
            _entries_n("repo-d", "absent", 3)
            + _entries_n("repo-d", "ok", 10)
            + _entries_n("repo-d", "stale", 2)
        )
        stats = compute_repo_stats(entries)
        s = stats["repo-d"]
        assert s["dominant_state"] == "ok"
        assert s["dominant_state_share"] == pytest.approx(10 / 15, abs=1e-3)

    def test_dominant_state_share_sums_correctly(self):
        entries = _entries_n("repo-s", "malformed", 7) + _entries_n("repo-s", "absent", 3)
        stats = compute_repo_stats(entries)
        s = stats["repo-s"]
        assert s["dominant_state"] == "malformed"
        assert s["dominant_state_share"] == pytest.approx(0.7, abs=1e-3)


# ── evaluate_phase2_gate — v2 shadow fields ───────────────────────────────────

class TestGateV2ShadowFields:
    def _make_fleet_entries(self, repo_configs: list[tuple[str, str, int]]) -> list[dict]:
        """repo_configs: list of (repo_name, dominant_state, count)."""
        entries = []
        for repo, state, n in repo_configs:
            entries.extend(_entries_n(repo, state, n))
        return entries

    def test_non_stuck_absent_ratio_counts_stable_ok(self):
        """
        1 stuck_absent repo + 1 stable_ok repo → non_stuck_absent_ratio_v2 = 0.5
        Both are lifecycle_capable (no skip_type).
        """
        entries = (
            _entries_n("stuck-repo", "absent", 20)
            + _entries_n("healthy-repo", "ok", 20)
        )
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 20, 2, 0.7, 0.6, 0.4)
        assert gate["non_stuck_absent_repos_v2"] == 1
        assert gate["non_stuck_absent_ratio_v2"] == pytest.approx(0.5)

    def test_all_stuck_absent_gives_zero_v2_ratio(self):
        entries = (
            _entries_n("repo-a", "absent", 20)
            + _entries_n("repo-b", "absent", 20)
            + _entries_n("repo-c", "absent", 20)
        )
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 20, 3, 0.7, 0.6, 0.4)
        assert gate["non_stuck_absent_ratio_v2"] == 0.0
        assert gate["non_stuck_absent_repos_v2"] == 0

    def test_all_stable_ok_gives_full_v2_ratio(self):
        entries = (
            _entries_n("repo-a", "ok", 20)
            + _entries_n("repo-b", "ok", 20)
            + _entries_n("repo-c", "ok", 20)
        )
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 20, 3, 0.7, 0.6, 0.4)
        assert gate["non_stuck_absent_ratio_v2"] == pytest.approx(1.0)
        assert gate["non_stuck_absent_repos_v2"] == 3

    def test_v2_shadow_present_in_gate_result(self):
        """Gate result dict must carry both v2 shadow keys."""
        entries = _entries_n("repo-x", "absent", 20)
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 1, 1, 0.7, 0.9, 0.1)
        assert "non_stuck_absent_ratio_v2" in gate
        assert "non_stuck_absent_repos_v2" in gate

    def test_legacy_degenerate_diverges_from_v2_for_stable_ok(self):
        """
        DESIGN BOUNDARY: fleet of stable_ok repos → legacy marks many as degenerate
        but v2 non_stuck_absent_ratio_v2 = 1.0.
        Documents the intentional split.
        """
        entries = (
            _entries_n("repo-a", "ok", 25)
            + _entries_n("repo-b", "ok", 25)
            + _entries_n("repo-c", "ok", 25)
        )
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 20, 3, 0.7, 0.6, 0.4)
        # Legacy: nondegenerate_ratio = 0.0 (all fail entropy < 0.3)
        assert gate["nondegenerate_ratio"] == 0.0, "legacy should see all as degenerate"
        # v2: non_stuck_absent_ratio = 1.0 (stable_ok, not adoption failure)
        assert gate["non_stuck_absent_ratio_v2"] == pytest.approx(1.0)


# ── lifecycle_active_ratio gate condition ─────────────────────────────────────

class TestLifecycleActiveRatioGateCondition:
    """Condition 5 uses non_stuck_absent_ratio_v2 (not unique_pattern_ratio).

    Design: unique_pattern_ratio was non-identifiable in a healthy fleet.
    stable_ok repos converge to (ok,(),False) fingerprint -> low ratio even when
    fleet IS healthy.  Replaced by lifecycle_active_ratio = repos where
    lifecycle_class != stuck_absent / total lifecycle_capable repos.
    """

    def test_lifecycle_active_ratio_appears_in_checks(self):
        """checks dict must have 'lifecycle_active_ratio' key (not unique_pattern_ratio)."""
        entries = _entries_n("repo-a", "ok", 20)
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 1, 1, 0.0, 1.0,
                                    _PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO)
        assert "lifecycle_active_ratio" in gate["checks"]
        assert "unique_pattern_ratio" not in gate["checks"]

    def test_lifecycle_active_ratio_passes_for_all_stable_ok(self):
        """All stable_ok fleet: ratio=1.0 >= 0.5 -> Condition 5 PASS."""
        entries = (
            _entries_n("repo-a", "ok", 20)
            + _entries_n("repo-b", "ok", 20)
            + _entries_n("repo-c", "ok", 20)
        )
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 20, 3, 0.7, 0.6,
                                    _PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO)
        cond5 = gate["checks"]["lifecycle_active_ratio"]
        assert cond5["pass"] is True
        assert cond5["actual"] == pytest.approx(1.0)

    def test_lifecycle_active_ratio_fails_for_all_stuck_absent(self):
        """All stuck_absent fleet: ratio=0.0 < 0.5 -> Condition 5 FAIL."""
        entries = (
            _entries_n("repo-a", "absent", 20)
            + _entries_n("repo-b", "absent", 20)
            + _entries_n("repo-c", "absent", 20)
        )
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 20, 3, 0.7, 0.6,
                                    _PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO)
        cond5 = gate["checks"]["lifecycle_active_ratio"]
        assert cond5["pass"] is False
        assert cond5["actual"] == pytest.approx(0.0)

    def test_unique_pattern_ratio_still_informational(self):
        """unique_pattern_ratio remains in gate result as informational key (non-blocking)."""
        entries = _entries_n("repo-x", "ok", 20)
        stats = compute_repo_stats(entries)
        gate = evaluate_phase2_gate(entries, stats, 1, 1, 0.0, 1.0,
                                    _PHASE2_MIN_LIFECYCLE_ACTIVE_RATIO)
        assert "unique_pattern_ratio" in gate  # informational key present
        assert "unique_patterns" in gate


    def test_discovers_own_log(self, tmp_path):
        """Framework repo log is included in auto-discover results."""
        log = tmp_path / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
        log.parent.mkdir(parents=True)
        log.write_text("")
        found = _auto_discover_logs(tmp_path)
        assert log in found

    def test_discovers_sibling_logs(self, tmp_path):
        """Sibling repos' logs appear in auto-discover results."""
        framework = tmp_path / "ai-governance-framework"
        sibling_a = tmp_path / "repo-a"
        sibling_b = tmp_path / "repo-b"
        for repo in (framework, sibling_a, sibling_b):
            log = repo / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text("")
        found = _auto_discover_logs(framework)
        assert len(found) == 3
        paths_str = [str(p) for p in found]
        assert any("repo-a" in p for p in paths_str)
        assert any("repo-b" in p for p in paths_str)

    def test_sibling_without_log_not_included(self, tmp_path):
        """Sibling with no audit log is silently skipped."""
        framework = tmp_path / "framework"
        empty_sibling = tmp_path / "no-log-repo"
        empty_sibling.mkdir()
        own_log = framework / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
        own_log.parent.mkdir(parents=True)
        own_log.write_text("")
        found = _auto_discover_logs(framework)
        assert len(found) == 1
        assert own_log in found

    def test_fallback_when_nothing_found(self, tmp_path):
        """When no logs exist, returns the default log path (not empty list)."""
        empty_dir = tmp_path / "framework"
        empty_dir.mkdir()
        from scripts.analyze_e1b_distribution import _DEFAULT_LOG_PATH
        found = _auto_discover_logs(empty_dir)
        assert found == [_DEFAULT_LOG_PATH]

    def test_sorted_deterministic(self, tmp_path):
        """Multiple siblings → result order is deterministic (sorted)."""
        framework = tmp_path / "framework"
        for name in ("zzz-repo", "aaa-repo", "mmm-repo"):
            log = tmp_path / name / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text("")
        own_log = framework / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
        own_log.parent.mkdir(parents=True)
        own_log.write_text("")
        found1 = _auto_discover_logs(framework)
        found2 = _auto_discover_logs(framework)
        assert found1 == found2


# ── ERA skip_type coverage — schema-migration detection ──────────────────────

class TestEraSkipTypeCoverage:
    """Tests for skip_type_entry_count / fleet ERA calculation.

    The ERA progression tracks whether audit log entries were written by a
    schema-aware session_end_hook (one that always writes the 'skip_type' key,
    even when the value is null for lifecycle-capable repos).

    Old entries (pre-schema) have NO 'skip_type' key in policy_provenance.
    New lifecycle-capable entries have 'skip_type': null (key present, value null).
    New structural/temporary skip entries have 'skip_type': 'structural'/'temporary'.

    Only key PRESENCE (not non-null value) counts as schema-aware.
    """

    def test_null_skip_type_key_counts_as_schema_aware(self):
        """Entry with 'skip_type': null key IS schema-aware (counts toward ERA)."""
        e = _entry("repo-a", "ok", schema_aware=True, skip_type=None)
        prov = e["policy_provenance"]
        assert "skip_type" in prov, "schema_aware entry must have skip_type key"
        assert prov["skip_type"] is None
        # simulate what compute_repo_stats does
        count = sum(1 for x in [e] if "skip_type" in (x.get("policy_provenance") or {}))
        assert count == 1

    def test_missing_key_does_not_count_toward_era(self):
        """Old entry without 'skip_type' key is NOT schema-aware."""
        e = _entry("repo-a", "ok")  # pre-schema, no key
        prov = e["policy_provenance"]
        assert "skip_type" not in prov
        count = sum(1 for x in [e] if "skip_type" in (x.get("policy_provenance") or {}))
        assert count == 0

    def test_lifecycle_capable_sessions_advance_era(self, tmp_path):
        """New sessions from lifecycle-capable repos advance fleet ERA ratio."""
        log = tmp_path / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
        log.parent.mkdir(parents=True)
        # 1 old entry (no key) + 9 new schema-aware lifecycle entries (key=null)
        old = _entry("repo-a", "ok")
        new_entries = [_entry("repo-a", "ok", schema_aware=True) for _ in range(9)]
        text = "\n".join(json.dumps(e) for e in [old] + new_entries)
        log.write_text(text)

        entries = _load_entries([log])
        stats = compute_repo_stats(entries)
        s = stats["repo-a"]
        # 9 of 10 entries are schema-aware → coverage = 0.9
        assert s["skip_type_entry_count"] == 9
        assert s["skip_type_coverage_ratio"] == 0.9

    def test_fleet_era_current_when_coverage_reaches_threshold(self, tmp_path):
        """Fleet ERA = CURRENT when >= 0.7 of entries carry skip_type key."""
        from scripts.analyze_e1b_distribution import compute_fleet_coverage
        log = tmp_path / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
        log.parent.mkdir(parents=True)
        # 7 schema-aware lifecycle-capable + 3 old entries = 0.7 coverage
        entries = (
            [_entry("repo-a", "ok", schema_aware=True) for _ in range(7)]
            + [_entry("repo-a", "ok") for _ in range(3)]
        )
        log.write_text("\n".join(json.dumps(e) for e in entries))
        loaded = _load_entries([log])
        stats = compute_repo_stats(loaded)
        fleet = compute_fleet_coverage(stats)
        assert fleet["fleet_era_tag"] == "CURRENT", (
            f"expected CURRENT but got {fleet['fleet_era_tag']!r}; "
            f"coverage={fleet['fleet_skip_type_coverage_ratio']}"
        )
