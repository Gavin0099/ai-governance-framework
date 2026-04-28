import json
from pathlib import Path


MODEL_PATH = Path("governance/governance_decision_model.v2.6.json")
DOC_PATH = Path("docs/governance-runtime-v2.6.md")


def test_v26_decision_model_artifacts_exist():
    assert MODEL_PATH.exists()
    assert DOC_PATH.exists()


def test_v26_decision_model_has_required_sections():
    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))

    assert payload["version"] == "2.6"
    assert payload["enforcement_model"]["machine_checkable_contract"] is True
    assert payload["enforcement_model"]["runtime_role"] == "single decision computation source"

    matrices = payload["matrices"]
    assert set(matrices) == {
        "decision_ownership",
        "policy_precedence",
        "evidence_classification",
        "violation_handling",
    }


def test_v26_matrix_rows_have_required_fields():
    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    matrices = payload["matrices"]

    expected_fields = {
        "decision_ownership": {
            "concern",
            "owner",
            "can_override",
            "override_path",
            "trace_required",
            "violation_effect",
        },
        "policy_precedence": {
            "policy_type",
            "scope",
            "override_target",
            "allowed",
            "conflict_resolution",
            "violation_effect",
        },
        "evidence_classification": {
            "evidence_kind",
            "required",
            "producer",
            "schema",
            "validation_rule",
            "trust_level",
            "missing_effect",
        },
        "violation_handling": {
            "violation_type",
            "detected_by",
            "severity",
            "default_verdict_impact",
            "override_allowed",
            "trace_required",
        },
    }

    for matrix_name, fields in expected_fields.items():
        assert matrices[matrix_name]
        for row in matrices[matrix_name]:
            assert fields <= set(row)


def test_v26_determinism_contract_is_explicit():
    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    contract = payload["determinism_contract"]

    assert contract["same_policy_and_evidence_requires_same_verdict"] is True
    assert contract["evidence_snapshot_required"] is True
    assert contract["policy_snapshot_required"] is True
    assert contract["runtime_version_trace_required"] is True
    assert "evidence snapshot changes" in contract["reevaluation"]["may_change_result_only_when"]


def test_v26_doc_references_constraint_layer_and_machine_readable_model():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Governance Constraint Layer" in text
    assert "Violation Handling Matrix" in text
    assert "Determinism Contract" in text
    assert "governance/governance_decision_model.v2.6.json" in text
