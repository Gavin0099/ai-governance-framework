from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.enumd_ingestion_contract import (
    reinterpret_policy_decision,
    apply_ingestion_contract,
    run_ingestion_contract_probe,
    run_targeted_residual_probe,
    _mask_field,
)
from governance_tools.enumd_semantic_isolation import (
    analyze_candidate,
    _classify_batch_conclusion,
)


# ── shared fixtures ───────────────────────────────────────────────────────────

def _stateless_candidate(session_id: str = "test-session") -> dict:
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
                "missing_fields": ["TASK_INTENT"],
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


# ── A: contract reinterpretation tests ───────────────────────────────────────

class TestReinterpretPolicyDecision:
    def test_do_not_promote_is_recognized(self):
        r = reinterpret_policy_decision("DO_NOT_PROMOTE")
        assert r["reinterpretation_status"] == "applied"

    def test_do_not_promote_actual_scope_is_session_memory(self):
        r = reinterpret_policy_decision("DO_NOT_PROMOTE")
        assert r["actual_scope"] == "session_memory_promotion"

    def test_do_not_promote_consumer_safe_label(self):
        r = reinterpret_policy_decision("DO_NOT_PROMOTE")
        assert r["consumer_safe_label"] == "memory_promotion_disallowed"

    def test_do_not_promote_non_equivalence_present(self):
        r = reinterpret_policy_decision("DO_NOT_PROMOTE")
        assert "not_repo_governance_promotion" in r["non_equivalence"]
        assert "not_integration_readiness_verdict" in r["non_equivalence"]

    def test_do_not_promote_collision_mitigated(self):
        r = reinterpret_policy_decision("DO_NOT_PROMOTE")
        assert r["semantic_collision_mitigated"] is True

    def test_raw_value_preserved(self):
        r = reinterpret_policy_decision("DO_NOT_PROMOTE")
        assert r["raw_value"] == "DO_NOT_PROMOTE"

    def test_unknown_value_not_mitigated(self):
        r = reinterpret_policy_decision("TOTALLY_UNKNOWN")
        assert r["reinterpretation_status"] == "unknown_value"
        assert r["semantic_collision_mitigated"] is False
        assert r["actual_scope"] is None
        assert r["consumer_safe_label"] is None

    def test_unknown_value_raw_preserved(self):
        r = reinterpret_policy_decision("TOTALLY_UNKNOWN")
        assert r["raw_value"] == "TOTALLY_UNKNOWN"

    def test_promote_is_recognized(self):
        r = reinterpret_policy_decision("PROMOTE")
        assert r["reinterpretation_status"] == "applied"
        assert r["consumer_safe_label"] == "memory_promotion_allowed"
        assert r["semantic_collision_mitigated"] is True


class TestApplyIngestionContract:
    def test_policy_decision_reinterpreted_key_added(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        assert "policy_decision_reinterpreted" in result

    def test_raw_policy_demoted_to_provenance(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        assert "_raw_provenance" in result["policy"]
        assert "decision" not in result["policy"]

    def test_provenance_contains_original_decision(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        raw = result["policy"]["_raw_provenance"]
        assert raw["decision"] == "DO_NOT_PROMOTE"

    def test_consumer_safe_label_is_primary(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        r = result["policy_decision_reinterpreted"]
        assert r["consumer_safe_label"] == "memory_promotion_disallowed"

    def test_actual_scope_present_and_non_null(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        r = result["policy_decision_reinterpreted"]
        assert r["actual_scope"] is not None
        assert r["actual_scope"] == "session_memory_promotion"

    def test_non_equivalence_in_artifact_not_just_docs(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        r = result["policy_decision_reinterpreted"]
        assert isinstance(r["non_equivalence"], list)
        assert len(r["non_equivalence"]) >= 2

    def test_semantic_collision_mitigated_true(self):
        result, _ = apply_ingestion_contract(_stateless_candidate())
        assert result["policy_decision_reinterpreted"]["semantic_collision_mitigated"] is True

    def test_ingestion_contract_metadata_block_present(self):
        result, meta = apply_ingestion_contract(_stateless_candidate())
        assert "ingestion_contract" in result
        assert result["ingestion_contract"]["collision_mitigation_complete"] is True

    def test_contract_metadata_records_field_reinterpreted(self):
        _, meta = apply_ingestion_contract(_stateless_candidate())
        assert "policy.decision" in meta["reinterpretations_applied"]

    def test_no_policy_decision_leaves_candidate_unchanged(self):
        candidate = {"session_id": "x", "policy": None, "checks": {}, "errors": []}
        result, meta = apply_ingestion_contract(candidate)
        assert "policy_decision_reinterpreted" not in result
        assert meta["collision_mitigation_complete"] is False
        assert meta["reinterpretations_applied"] == []

    def test_unknown_decision_value_recorded_as_failure(self):
        candidate = _stateless_candidate()
        candidate["policy"]["decision"] = "MADE_UP_VALUE"
        result, meta = apply_ingestion_contract(candidate)
        assert meta["reinterpretation_failures"]
        failure = meta["reinterpretation_failures"][0]
        assert failure["field"] == "policy.decision"
        assert failure["status"] == "unknown_value"
        # raw_value is still preserved in provenance
        assert result["policy"]["_raw_provenance"]["decision"] == "MADE_UP_VALUE"


# ── B: collision downgrade tests ─────────────────────────────────────────────

class TestCollisionDowngrade:
    """
    Verify that applying the ingestion contract downgrades batch_conclusion
    from observe_only_with_semantic_collision without pretending the risk
    is fully gone (raw value is in provenance, not hidden).
    """

    def test_before_contract_batch_is_semantic_collision(self):
        samples = [
            analyze_candidate(_stateless_candidate(f"s{i}"), f"/fake/s{i}.json")
            for i in range(5)
        ]
        assert _classify_batch_conclusion(samples) == "observe_only_with_semantic_collision"

    def test_after_contract_batch_is_downgraded(self):
        samples = []
        for i in range(5):
            reinterpreted, _ = apply_ingestion_contract(_stateless_candidate(f"s{i}"))
            samples.append(analyze_candidate(reinterpreted, f"/fake/s{i}.json"))
        conclusion = _classify_batch_conclusion(samples)
        assert conclusion != "observe_only_with_semantic_collision"

    def test_after_contract_raw_value_still_accessible_in_provenance(self):
        reinterpreted, _ = apply_ingestion_contract(_stateless_candidate())
        raw = reinterpreted["policy"]["_raw_provenance"]["decision"]
        assert raw == "DO_NOT_PROMOTE"

    def test_after_contract_policy_decision_not_at_primary_path(self):
        """policy.decision must NOT be accessible at the top-level dot-path after contract."""
        from governance_tools.enumd_semantic_isolation import _get_nested
        reinterpreted, _ = apply_ingestion_contract(_stateless_candidate())
        exists, _ = _get_nested(reinterpreted, "policy.decision")
        assert not exists

    def test_downgrade_does_not_mark_as_integration_ready(self):
        """After contract, conclusion must NOT be 'integration_ready' — risk is contained, not erased."""
        samples = []
        for i in range(5):
            reinterpreted, _ = apply_ingestion_contract(_stateless_candidate(f"s{i}"))
            samples.append(analyze_candidate(reinterpreted, f"/fake/s{i}.json"))
        conclusion = _classify_batch_conclusion(samples)
        assert conclusion != "integration_ready"

    def test_consumer_safe_label_present_in_reinterpreted_artifact(self):
        reinterpreted, _ = apply_ingestion_contract(_stateless_candidate())
        label = reinterpreted["policy_decision_reinterpreted"]["consumer_safe_label"]
        assert label is not None
        assert "DO_NOT_PROMOTE" not in label

    def test_policy_decision_reinterpreted_actual_scope_not_null(self):
        reinterpreted, _ = apply_ingestion_contract(_stateless_candidate())
        assert reinterpreted["policy_decision_reinterpreted"]["actual_scope"] is not None


# ── run_ingestion_contract_probe ─────────────────────────────────────────────

class TestRunIngestionContractProbe:
    def _write(self, path: Path, name: str, data: dict) -> None:
        (path / name).write_text(json.dumps(data), encoding="utf-8")

    def test_downgrade_achieved_for_stateless_batch(self, tmp_path):
        for i in range(5):
            self._write(tmp_path, f"s{i:02d}.json", _stateless_candidate(f"s{i}"))
        report = run_ingestion_contract_probe(tmp_path)
        assert report["downgrade_achieved"] is True
        assert report["batch_conclusion_before"] == "observe_only_with_semantic_collision"
        assert report["batch_conclusion_after"] != "observe_only_with_semantic_collision"

    def test_mitigation_complete_count_equals_n(self, tmp_path):
        for i in range(3):
            self._write(tmp_path, f"s{i:02d}.json", _stateless_candidate(f"s{i}"))
        report = run_ingestion_contract_probe(tmp_path)
        assert report["mitigation_complete_count"] == 3

    def test_unknown_decision_increments_failure_count(self, tmp_path):
        candidate = _stateless_candidate()
        candidate["policy"]["decision"] = "UNKNOWN_VALUE"
        self._write(tmp_path, "s.json", candidate)
        report = run_ingestion_contract_probe(tmp_path)
        assert report["reinterpretation_failure_count"] == 1

    def test_safety_check_risk_contained_on_downgrade(self, tmp_path):
        for i in range(3):
            self._write(tmp_path, f"s{i:02d}.json", _stateless_candidate(f"s{i}"))
        report = run_ingestion_contract_probe(tmp_path)
        assert report["safety_check"] == "risk_contained"

    def test_report_schema_keys(self, tmp_path):
        self._write(tmp_path, "s.json", _stateless_candidate())
        report = run_ingestion_contract_probe(tmp_path)
        for key in (
            "schema_version", "artifact_type", "generated_at", "n",
            "batch_conclusion_before", "batch_conclusion_after",
            "downgrade_achieved", "mitigation_complete_count",
            "reinterpretation_failure_count", "safety_check", "samples",
        ):
            assert key in report

    def test_output_dir_writes_reinterpreted_files(self, tmp_path):
        candidates_dir = tmp_path / "candidates"
        output_dir = tmp_path / "reinterpreted"
        candidates_dir.mkdir()
        self._write(candidates_dir, "s0.json", _stateless_candidate("s0"))
        run_ingestion_contract_probe(candidates_dir, output_dir)
        assert (output_dir / "s0.json").exists()
        data = json.loads((output_dir / "s0.json").read_text())
        assert "policy_decision_reinterpreted" in data

    def test_empty_dir_not_downgraded_but_safe(self, tmp_path):
        report = run_ingestion_contract_probe(tmp_path)
        assert report["downgrade_achieved"] is False
        assert report["n"] == 0


# ── _mask_field ───────────────────────────────────────────────────────────────

class TestMaskField:
    def test_top_level_field_set_to_none(self):
        d = {"a": 1, "b": 2}
        result = _mask_field(d, "a")
        assert result["a"] is None
        assert result["b"] == 2

    def test_nested_field_set_to_none(self):
        d = {"checks": {"repo_readiness_level": 3, "other": "x"}}
        result = _mask_field(d, "checks.repo_readiness_level")
        assert result["checks"]["repo_readiness_level"] is None
        assert result["checks"]["other"] == "x"

    def test_original_not_mutated(self):
        d = {"checks": {"repo_readiness_level": 3}}
        _mask_field(d, "checks.repo_readiness_level")
        assert d["checks"]["repo_readiness_level"] == 3

    def test_missing_field_leaves_dict_unchanged(self):
        d = {"checks": {"other": "x"}}
        result = _mask_field(d, "checks.nonexistent")
        assert result == {"checks": {"other": "x", "nonexistent": None}}


# ── run_targeted_residual_probe ───────────────────────────────────────────────

class TestRunTargetedResidualProbe:
    def _write(self, path: Path, name: str, data: dict) -> None:
        (path / name).write_text(json.dumps(data), encoding="utf-8")

    def _make_batch(self, tmp_path: Path, n: int = 5) -> None:
        for i in range(n):
            self._write(tmp_path, f"s{i:02d}.json", _stateless_candidate(f"s{i}"))

    def test_report_schema_keys(self, tmp_path):
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        for key in (
            "schema_version", "artifact_type", "n",
            "baseline", "probe_a_mask_repo_readiness_level",
            "probe_b_mask_closeout_schema_validity",
            "mask_both_medium", "mask_all_medium_low",
            "finding", "interpretation",
        ):
            assert key in report

    def test_baseline_conclusion_is_inducement_risk_after_contract(self, tmp_path):
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        assert report["baseline"]["batch_conclusion"] == "observe_only_with_inducement_risk"

    def test_probe_a_conclusion_unchanged(self, tmp_path):
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        assert report["probe_a_mask_repo_readiness_level"]["conclusion_changed"] is False

    def test_probe_b_conclusion_unchanged(self, tmp_path):
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        assert report["probe_b_mask_closeout_schema_validity"]["conclusion_changed"] is False

    def test_both_medium_masked_conclusion_unchanged(self, tmp_path):
        # Even masking both medium fields, low-collision fields remain → still inducement_risk
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        assert report["mask_both_medium"]["conclusion_changed"] is False

    def test_mask_all_achieves_safe(self, tmp_path):
        # Only by masking ALL registered medium/low fields does conclusion reach safe
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        assert report["mask_all_medium_low"]["batch_conclusion"] == "observe_only_safe"
        assert report["mask_all_medium_low"]["conclusion_changed"] is True

    def test_finding_is_residual_downstream_effect(self, tmp_path):
        # Because A and B individually don't change conclusion
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        assert report["finding"] == "residual_downstream_effect"

    def test_avg_authority_fields_decreases_as_more_masked(self, tmp_path):
        self._make_batch(tmp_path)
        report = run_targeted_residual_probe(tmp_path)
        # Masking more fields should reduce avg authority fields
        assert (
            report["mask_both_medium"]["avg_authority_fields_per_sample"]
            < report["baseline"]["avg_authority_fields_per_sample"]
        )
        assert (
            report["mask_all_medium_low"]["avg_authority_fields_per_sample"]
            == 0.0
        )

    def test_empty_dir(self, tmp_path):
        report = run_targeted_residual_probe(tmp_path)
        assert report["n"] == 0
        assert report["finding"] == "residual_downstream_effect"
