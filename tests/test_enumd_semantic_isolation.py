from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.enumd_semantic_isolation import (
    analyze_candidate,
    run_probe,
    _classify_batch_conclusion,
    SampleProbeResult,
    AuthorityLikeField,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _stateless_candidate(session_id: str = "test-session") -> dict:
    """Minimal Enumd candidate with DO_NOT_PROMOTE / stateless pattern."""
    return {
        "session_id": session_id,
        "runtime_contract": {"memory_mode": "stateless"},
        "checks": {
            "closeout_status": "closeout_missing",
            "closeout_schema_validity": "invalid",
            "closeout_content_sufficiency": "insufficient",
            "repo_readiness_level": 3,
            "repo_closeout_activation_state": "observed",
            "closeout_per_layer_results": {
                "missing_fields": ["TASK_INTENT", "WORK_COMPLETED"],
                "content_issues": [],
                "inconsistencies": [],
                "cross_reference_results": [],
            },
        },
        "policy": {
            "decision": "DO_NOT_PROMOTE",
            "reasons": ["Session is stateless; durable memory is not allowed."],
        },
        "errors": [],
        "warnings": [],
    }


def _clean_candidate(session_id: str = "clean-session") -> dict:
    """Candidate with no authority-like fields present."""
    return {
        "session_id": session_id,
        "runtime_contract": {"memory_mode": "candidate"},
        "checks": {
            "closeout_per_layer_results": {
                "missing_fields": [],
                "content_issues": [],
                "inconsistencies": [],
                "cross_reference_results": [],
            },
        },
        "policy": None,
        "errors": [],
        "warnings": [],
    }


# ── analyze_candidate ─────────────────────────────────────────────────────────

class TestAnalyzeCandidate:
    def test_detects_all_authority_like_fields_in_stateless_candidate(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        fields = {f.field for f in result.authority_like_fields}
        assert "policy.decision" in fields
        assert "checks.repo_readiness_level" in fields
        assert "checks.closeout_schema_validity" in fields
        assert "checks.closeout_content_sufficiency" in fields
        assert "checks.repo_closeout_activation_state" in fields

    def test_policy_decision_has_correct_scope_annotation(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        pd = next(f for f in result.authority_like_fields if f.field == "policy.decision")
        assert pd.actual_scope == "session_memory_promotion"
        assert pd.misread_scope == "repo_integration_decision"
        assert pd.collision_risk == "high"
        assert pd.reinterpretation_required is True

    def test_observed_value_preserved(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        pd = next(f for f in result.authority_like_fields if f.field == "policy.decision")
        assert pd.observed_value == "DO_NOT_PROMOTE"

    def test_inducement_risk_high_when_high_collision_field_present(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        assert result.inducement_risk == "high"
        assert result.misread_risk == "high"

    def test_semantic_isolation_applied_when_fields_detected(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        assert result.semantic_isolation_applied is True

    def test_boundary_status_pass_for_normal_candidate(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        assert result.boundary_status == "pass"

    def test_ingestion_valid_false_when_missing_fields(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        assert result.ingestion_valid is False

    def test_clean_candidate_no_authority_fields(self):
        result = analyze_candidate(_clean_candidate(), "/fake/path/clean-session.json")
        assert result.authority_like_fields == []
        assert result.semantic_isolation_applied is False
        assert result.inducement_risk == "low"

    def test_clean_candidate_ingestion_valid(self):
        result = analyze_candidate(_clean_candidate(), "/fake/path/clean-session.json")
        assert result.ingestion_valid is True

    def test_boundary_fail_on_explicit_error(self):
        candidate = _stateless_candidate()
        candidate["errors"] = ["boundary_fail_do_not_progress"]
        result = analyze_candidate(candidate, "/fake/path/fail-session.json")
        assert result.boundary_status == "fail"

    def test_to_dict_contains_required_keys(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        d = result.to_dict()
        for key in ("sample_id", "ingestion_valid", "boundary_status", "inducement_risk",
                    "misread_risk", "authority_like_fields", "semantic_isolation_applied"):
            assert key in d

    def test_authority_like_field_to_dict_structure(self):
        result = analyze_candidate(_stateless_candidate(), "/fake/path/test-session.json")
        pd_dict = next(
            f for f in result.to_dict()["authority_like_fields"] if f["field"] == "policy.decision"
        )
        assert "family" in pd_dict
        assert "actual_scope" in pd_dict
        assert "misread_scope" in pd_dict
        assert "reinterpretation_required" in pd_dict
        assert "observed_value" in pd_dict
        assert "non_equivalence" in pd_dict


# ── batch conclusion ──────────────────────────────────────────────────────────

class TestBatchConclusion:
    def _make_sample(self, fields: list[AuthorityLikeField]) -> SampleProbeResult:
        return SampleProbeResult(
            sample_id="x",
            source_path="/x",
            ingestion_valid=False,
            boundary_status="pass",
            runtime_eligible_result="observe_only",
            inducement_risk="high",
            misread_risk="high",
            authority_like_fields=fields,
        )

    def _high_collision_field(self) -> AuthorityLikeField:
        return AuthorityLikeField(
            field="policy.decision",
            family="promotion_like",
            actual_scope="session_memory_promotion",
            misread_scope="repo_integration_decision",
            reinterpretation_required=True,
            collision_risk="high",
            observed_value="DO_NOT_PROMOTE",
            non_equivalence="policy.decision != framework verdict.decision",
        )

    def _low_collision_field(self) -> AuthorityLikeField:
        return AuthorityLikeField(
            field="checks.closeout_content_sufficiency",
            family="binary_verdict",
            actual_scope="artifact_file_content_completeness",
            misread_scope="governance_content_sufficiency",
            reinterpretation_required=True,
            collision_risk="low",
            observed_value="insufficient",
            non_equivalence="closeout_content_sufficiency != governance_content_sufficiency",
        )

    def test_semantic_collision_when_high_collision_field_in_all_samples(self):
        samples = [self._make_sample([self._high_collision_field()]) for _ in range(10)]
        assert _classify_batch_conclusion(samples) == "observe_only_with_semantic_collision"

    def test_semantic_collision_when_high_collision_field_in_majority(self):
        samples = (
            [self._make_sample([self._high_collision_field()]) for _ in range(6)]
            + [self._make_sample([]) for _ in range(4)]
        )
        assert _classify_batch_conclusion(samples) == "observe_only_with_semantic_collision"

    def test_inducement_risk_when_only_low_collision_fields(self):
        samples = [self._make_sample([self._low_collision_field()]) for _ in range(10)]
        assert _classify_batch_conclusion(samples) == "observe_only_with_inducement_risk"

    def test_safe_when_no_authority_fields(self):
        samples = [self._make_sample([]) for _ in range(5)]
        assert _classify_batch_conclusion(samples) == "observe_only_safe"

    def test_empty_samples_returns_safe(self):
        assert _classify_batch_conclusion([]) == "observe_only_safe"

    def test_minority_high_collision_not_enough_for_semantic_collision(self):
        samples = (
            [self._make_sample([self._high_collision_field()]) for _ in range(4)]
            + [self._make_sample([]) for _ in range(6)]
        )
        assert _classify_batch_conclusion(samples) == "observe_only_with_inducement_risk"


# ── run_probe (integration) ───────────────────────────────────────────────────

class TestRunProbe:
    def _write_candidate(self, tmp_path: Path, name: str, candidate: dict) -> None:
        (tmp_path / name).write_text(json.dumps(candidate), encoding="utf-8")

    def test_probe_on_all_stateless_batch(self, tmp_path):
        for i in range(5):
            self._write_candidate(tmp_path, f"session-{i:03d}.json", _stateless_candidate(f"s{i}"))
        report = run_probe(tmp_path)
        assert report["n"] == 5
        assert report["batch_conclusion"] == "observe_only_with_semantic_collision"
        assert report["boundary_fail_count"] == 0
        assert "policy.decision" in report["systematic_collision_fields"]

    def test_probe_on_clean_batch(self, tmp_path):
        for i in range(3):
            self._write_candidate(tmp_path, f"clean-{i:03d}.json", _clean_candidate(f"c{i}"))
        report = run_probe(tmp_path)
        assert report["batch_conclusion"] == "observe_only_safe"
        assert report["systematic_collision_fields"] == []

    def test_probe_report_schema_keys(self, tmp_path):
        self._write_candidate(tmp_path, "x.json", _stateless_candidate())
        report = run_probe(tmp_path)
        for key in ("schema_version", "artifact_type", "generated_at", "source_dir",
                    "n", "batch_conclusion", "systematic_collision_fields",
                    "boundary_fail_count", "ingestion_valid_count",
                    "semantic_isolation_applied_count", "samples"):
            assert key in report

    def test_probe_handles_parse_error_gracefully(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
        report = run_probe(tmp_path)
        assert report["n"] == 1
        assert report["samples"][0]["boundary_status"] == "error"

    def test_probe_empty_dir(self, tmp_path):
        report = run_probe(tmp_path)
        assert report["n"] == 0
        assert report["batch_conclusion"] == "observe_only_safe"
