import json
from pathlib import Path


MATRIX_PATH = Path("governance/failure_mode_test_matrix.v0.1.json")
DOC_PATH = Path("docs/failure-mode-test-plan.md")


def test_failure_mode_plan_artifacts_exist():
    assert MATRIX_PATH.exists()
    assert DOC_PATH.exists()


def test_failure_mode_matrix_covers_initial_break_test_categories():
    payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    assert payload["version"] == "0.1"
    assert payload["status"] == "draft"

    scenario_categories = {scenario["category"] for scenario in payload["scenarios"]}
    assert scenario_categories == {
        "missing_required_evidence",
        "invalid_evidence_schema",
        "policy_conflict",
        "runtime_failure",
        "determinism_replay",
    }


def test_failure_mode_matrix_rows_have_required_fields():
    payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    required_fields = {
        "id",
        "category",
        "description",
        "target_layer",
        "fault_injection",
        "expected_detector",
        "expected_verdict_impact",
        "expected_runtime_behavior",
        "expected_artifacts",
        "determinism_assertion",
    }

    for scenario in payload["scenarios"]:
        assert required_fields <= set(scenario)
        assert scenario["expected_artifacts"]


def test_failure_mode_doc_references_machine_readable_matrix():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "governance/failure_mode_test_matrix.v0.1.json" in text
    assert "missing_required_evidence" in text
    assert "determinism must be checked with repeated inputs" in text
