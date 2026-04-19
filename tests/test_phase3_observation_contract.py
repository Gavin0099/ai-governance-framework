from __future__ import annotations

from scripts.analyze_e1b_distribution import (
    build_phase3_observation_payload,
    compute_repo_stats,
    validate_phase3_observation_payload,
)


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
