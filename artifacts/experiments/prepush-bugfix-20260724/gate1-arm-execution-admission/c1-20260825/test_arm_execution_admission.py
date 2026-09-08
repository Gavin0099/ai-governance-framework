from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MANIFEST = HERE / "arm-execution-admission-manifest.json"
FACTS = HERE / "local-runtime-facts.json"
POLICY = (
    ROOT
    / "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration"
    / "c1-20260825/arm-d-feedback-policy.json"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


admission = load_module("arm_execution_admission", HERE / "arm_execution_admission.py")
adapter = load_module("arm_d_feedback_adapter", HERE / "arm_d_feedback_adapter.py")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(tmp_path: Path, *, manifest: dict | None = None, facts: dict | None = None):
    return admission.evaluate_admission(
        repo_root=ROOT,
        manifest=manifest or load_json(MANIFEST),
        runtime_facts=facts or load_json(FACTS),
        randomization_path=tmp_path / "randomization.json",
    )


def test_exact_bindings_pass_without_randomization(tmp_path: Path) -> None:
    result = evaluate(tmp_path)
    assert result["status"] == admission.PASSED
    assert result["randomization_created"] is False
    assert result["reasons"] == []
    assert all(result["checks"].values())
    assert not (tmp_path / "randomization.json").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cli_version", "codex-cli 0.148.0-alpha.10"),
        ("cli_executable_sha256", "0" * 64),
        ("runner_sha256", "0" * 64),
        ("command_contract_sha256", "0" * 64),
        ("model_requested_id", "another-model"),
    ],
)
def test_any_client_identity_drift_stops(
    tmp_path: Path, field: str, value: object
) -> None:
    facts = load_json(FACTS)
    facts[field] = value
    result = evaluate(tmp_path, facts=facts)
    assert result["status"] == admission.STOPPED
    assert result["reasons"] == ["CLIENT_IDENTITY_INVALID:ClientIdentityError"]


def test_provider_observation_lookalike_stops(tmp_path: Path) -> None:
    facts = load_json(FACTS)
    facts["model_observed_id"] = "gpt-5.6-sol"
    result = evaluate(tmp_path, facts=facts)
    assert result["status"] == admission.STOPPED
    assert result["reasons"] == ["CLIENT_IDENTITY_INVALID:ValueError"]


def test_missing_binding_stops(tmp_path: Path) -> None:
    manifest = load_json(MANIFEST)
    manifest["bindings"][0]["sha256"] = "0" * 64
    result = evaluate(tmp_path, manifest=manifest)
    assert result["status"] == admission.STOPPED
    assert any(reason.startswith("BINDING_MISMATCH:") for reason in result["reasons"])


def test_provider_contract_mismatch_stops(tmp_path: Path) -> None:
    manifest = load_json(MANIFEST)
    manifest["external_pin_provider"]["provider_profile_sha256"] = "0" * 64
    result = evaluate(tmp_path, manifest=manifest)
    assert result["status"] == admission.STOPPED
    assert result["reasons"] == ["EXTERNAL_PIN_PROVIDER_INVALID:ValueError"]


def test_d5_drift_stops(tmp_path: Path) -> None:
    manifest = load_json(MANIFEST)
    manifest["d5_countability"] = "silently_resolved"
    result = evaluate(tmp_path, manifest=manifest)
    assert result["status"] == admission.STOPPED
    assert "D5_DECISION_DRIFT" in result["reasons"]


def test_existing_randomization_is_never_accepted(tmp_path: Path) -> None:
    randomization = tmp_path / "randomization.json"
    randomization.write_bytes(b"{}\n")
    result = admission.evaluate_admission(
        repo_root=ROOT,
        manifest=load_json(MANIFEST),
        runtime_facts=load_json(FACTS),
        randomization_path=randomization,
    )
    assert result["status"] == admission.STOPPED
    assert "RANDOMIZATION_ALREADY_EXISTS" in result["reasons"]
    assert randomization.read_bytes() == b"{}\n"


def test_arm_d_feedback_is_transient_and_retained_evidence_is_aggregate() -> None:
    policy = load_json(POLICY)
    adapter.validate_transient_feedback(
        [
            {
                "bounded_description": "conditional survived",
                "column": 4,
                "line": 12,
                "mutant_id": "m-1",
                "mutator": "ConditionalExpression",
                "relative_path": "src/example.ts",
            }
        ],
        policy,
        arm="D",
    )
    adapter.validate_retained_evidence(
        {
            "cleanup_confirmed": True,
            "duration_ms": 10,
            "mutant_count": 1,
            "operator_counts": {"ConditionalExpression": 1},
            "phase_status": "completed",
            "raw_report_sha256": "a" * 64,
            "status_counts": {"Survived": 1},
            "surviving_mutant_count": 1,
            "target_rule_sha256": "b" * 64,
        },
        policy,
    )


def test_arm_d_forbidden_detail_and_other_arm_fail_closed() -> None:
    policy = load_json(POLICY)
    with pytest.raises(adapter.ArmDFeedbackError, match="Arm D only"):
        adapter.validate_transient_feedback([], policy, arm="C")
    with pytest.raises(adapter.ArmDFeedbackError, match="non-aggregate"):
        adapter.validate_retained_evidence(
            {
                "cleanup_confirmed": True,
                "files": ["private/path.ts"],
                "raw_report_sha256": "a" * 64,
                "target_rule_sha256": "b" * 64,
            },
            policy,
        )


def test_cli_precondition_failure_writes_one_fail_closed_terminal(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]\n", encoding="utf-8")
    out = tmp_path / "terminal.json"
    exit_code = admission.main(
        [
            "--repo-root",
            str(ROOT),
            "--manifest",
            str(invalid),
            "--runtime-facts",
            str(FACTS),
            "--randomization-path",
            str(tmp_path / "never-created.json"),
            "--out",
            str(out),
        ]
    )
    terminal = load_json(out)
    assert exit_code == 3
    assert terminal["status"] == admission.STOPPED
    assert terminal["randomization_created"] is False
    assert terminal["reasons"] == ["ADMISSION_PRECONDITION_FAILED:ValueError"]
    assert len(list(tmp_path.glob("terminal.json"))) == 1
