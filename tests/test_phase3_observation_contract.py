from __future__ import annotations

import json

from scripts.analyze_e1b_distribution import (
    _PHASE3_OBSERVATION_ALLOWED_FIELDS,
    _PHASE3_OBSERVATION_ALLOWLIST_BY_CLASS,
    build_phase3_observation_payload,
    compute_repo_stats,
    enforce_phase3_observation_contract,
    validate_phase3_observation_payload,
)
import scripts.analyze_e1b_distribution as phase3_dist
import pytest


def _entry(repo: str, ts: int, state: str) -> dict:
    return {
        "timestamp": f"2026-04-19T00:00:{ts:02d}+00:00",
        "session_id": f"{repo}-{ts}",
        "repo_name": repo,
        "artifact_state": state,
        "signals": [],
        "gate_blocked": False,
        "policy_provenance": {"skip_type": None},
    }


def test_identical_sessions_emit_raw_only_no_positive_trend_hint():
    # 100 identical stable_ok-like sessions (all ok, no variation).
    entries = [_entry("repo-a", i, "ok") for i in range(50)] + [
        _entry("repo-b", i, "ok") for i in range(50)
    ]
    stats = compute_repo_stats(entries)
    payload = build_phase3_observation_payload(entries, stats)
    check = validate_phase3_observation_payload(payload)

    assert check["valid"] is True
    assert check["violations"] == []
    assert "trend_direction" not in payload
    assert "stability_score" not in payload
    assert "health_hint" not in payload


def test_low_diversity_trivial_diversity_stays_observation_only():
    # Mostly ok with tiny absent noise -> low information variety.
    entries = (
        [_entry("repo-a", i, "ok") for i in range(20)]
        + [_entry("repo-a", 20, "absent")]
        + [_entry("repo-b", i, "ok") for i in range(20)]
        + [_entry("repo-b", 20, "absent")]
    )
    stats = compute_repo_stats(entries)
    payload = build_phase3_observation_payload(entries, stats)
    check = validate_phase3_observation_payload(payload)

    assert check["valid"] is True
    assert "quality_signal" not in payload
    assert "improving" not in payload
    assert "degrading" not in payload


def test_misleading_correlation_case_has_no_quality_inference_field():
    # Two repos move in lockstep due to shared operation; output must remain raw.
    entries = []
    for i in range(15):
        entries.append(_entry("repo-a", i * 2, "absent" if i < 7 else "ok"))
        entries.append(_entry("repo-b", i * 2 + 1, "absent" if i < 7 else "ok"))

    stats = compute_repo_stats(entries)
    payload = build_phase3_observation_payload(entries, stats)
    check = validate_phase3_observation_payload(payload)

    assert check["valid"] is True
    assert "cross_repo_correlation" not in payload
    assert "baseline_alignment" not in payload
    assert "distribution_health" not in payload


def test_alias_based_interpretation_smuggling_is_rejected():
    entries = [_entry("repo-a", i, "ok") for i in range(5)]
    stats = compute_repo_stats(entries)
    payload = build_phase3_observation_payload(entries, stats)

    smuggled = dict(payload)
    smuggled["health_hint"] = "good"
    smuggled["stability_score"] = 0.95
    smuggled["promotion_context"] = "candidate_ready"

    check = validate_phase3_observation_payload(smuggled)
    reasons = {(v["key"], v["reason"]) for v in check["violations"]}

    assert check["valid"] is False
    assert ("health_hint", "interpretive_class_forbidden") in reasons
    assert ("stability_score", "interpretive_class_forbidden") in reasons
    assert ("promotion_context", "interpretive_class_forbidden") in reasons


def test_allowlist_is_strict_raw_observation_classes_only():
    expected_classes = {
        "raw_counts",
        "raw_ratios",
        "raw_distributions",
        "raw_transition_data",
        "raw_repo_partition_data",
    }
    assert set(_PHASE3_OBSERVATION_ALLOWLIST_BY_CLASS) == expected_classes

    expected_allowed = {
        "total_sessions",
        "repo_count",
        "repo_session_counts",
        "repo_session_ratios",
        "artifact_state_counts",
        "artifact_state_ratios",
        "repo_state_breakdown",
        "state_transition_matrix",
    }
    assert set(_PHASE3_OBSERVATION_ALLOWED_FIELDS) == expected_allowed


def test_interpretive_key_is_rejected_even_if_whitelisted(monkeypatch):
    # Contract hardening: interpretive-class keys can never be legalized by
    # broadening allowlist constants alone.
    entries = [_entry("repo-a", i, "ok") for i in range(5)]
    stats = compute_repo_stats(entries)
    payload = build_phase3_observation_payload(entries, stats)

    monkeypatch.setattr(
        phase3_dist,
        "_PHASE3_OBSERVATION_ALLOWED_FIELDS",
        frozenset(set(phase3_dist._PHASE3_OBSERVATION_ALLOWED_FIELDS) | {"readiness_signal"}),
    )
    payload["readiness_signal"] = "looks_ready"

    check = validate_phase3_observation_payload(payload)
    reasons = {(v["key"], v["reason"]) for v in check["violations"]}
    assert check["valid"] is False
    assert ("readiness_signal", "interpretive_class_forbidden") in reasons


def test_enforcement_hard_fails_on_contract_violation():
    payload = {
        "total_sessions": 1,
        "repo_count": 1,
        "repo_session_counts": {"repo-a": 1},
        "artifact_state_counts": {"ok": 1},
        "repo_state_breakdown": {"repo-a": {"ok": 1}},
        "state_transition_matrix": {},
        "trend_direction": "improving",
    }
    check = validate_phase3_observation_payload(payload)
    assert check["valid"] is False
    with pytest.raises(ValueError, match="phase3 observation contract violation"):
        enforce_phase3_observation_contract(check)


def test_main_returns_nonzero_when_phase3_contract_invalid(monkeypatch):
    entries = [_entry("repo-a", 0, "ok")]

    def _bad_payload(_entries, _stats):
        return {"total_sessions": 1, "readiness_signal": "x"}

    monkeypatch.setattr(phase3_dist, "_load_entries", lambda _paths: entries)
    monkeypatch.setattr(phase3_dist, "build_phase3_observation_payload", _bad_payload)
    monkeypatch.setattr(phase3_dist.sys, "argv", ["analyze_e1b_distribution.py", "--json"])

    assert phase3_dist.main() == 1


def test_main_json_emits_downstream_reuse_contract(monkeypatch, capsys):
    entries = [_entry("repo-a", 0, "ok"), _entry("repo-b", 1, "absent")]
    monkeypatch.setattr(phase3_dist, "_load_entries", lambda _paths: entries)
    monkeypatch.setattr(phase3_dist.sys, "argv", ["analyze_e1b_distribution.py", "--json"])

    assert phase3_dist.main() == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    contract = payload["phase3_observation_contract"]["downstream_reuse_contract"]

    assert contract["allowed_use"] == [
        "raw_observation_review",
        "coverage_audit",
        "schema_migration_monitoring",
        "phase2_observation_baseline_tracking",
    ]
    assert contract["forbidden_use"] == [
        "readiness_inference",
        "promotion_decision_support",
        "trend_quality_verdict",
        "stability_health_summary",
        "policy_threshold_calibration_input",
    ]
    assert contract["interpretation_requires_separate_phase_contract"] is True
    assert contract["required_phase_contract"] == "phase3_interpretation_contract"
    reviewer = payload["phase3_observation_contract"]["reviewer_interpretation_boundary"]
    assert reviewer["human_authored_commentary_non_authoritative"] is True
    assert reviewer["allowed_summary_scope"] == [
        "raw_observation_restatement",
        "coverage_gap_note",
        "schema_migration_context",
        "evidence_scope_caveat",
    ]
    assert reviewer["forbidden_summary_claims"] == [
        "readiness_declared",
        "promotion_recommended",
        "stability_conclusion_declared",
        "interpretation_authority_substitution",
    ]
    assert reviewer["interpretation_requires_explicit_phase_transition"] is True


def test_cumulative_illusion_does_not_create_interpretation_fields():
    # 20 sessions with gradually improving raw states; output must remain raw.
    entries = []
    for i in range(20):
        state = "absent" if i < 8 else ("stale" if i < 12 else "ok")
        entries.append(_entry("repo-a", i, state))
        entries.append(_entry("repo-b", i + 20, state))

    stats = compute_repo_stats(entries)
    payload = build_phase3_observation_payload(entries, stats)
    check = validate_phase3_observation_payload(payload)

    assert check["valid"] is True
    assert set(payload) == set(_PHASE3_OBSERVATION_ALLOWED_FIELDS)
    assert "trend_direction" not in payload
    assert "improving" not in payload
    assert "health_summary" not in payload
    assert "readiness_signal" not in payload
