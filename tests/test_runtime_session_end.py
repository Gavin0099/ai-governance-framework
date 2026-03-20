import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.session_end import format_human_result, run_session_end


@pytest.fixture
def local_project_root():
    path = Path("tests") / "_tmp_session_end"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _contract(**overrides):
    contract = {
        "task": "Runtime governance closeout",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "candidate",
    }
    contract.update(overrides)
    return contract


def test_session_end_auto_promotes_low_risk_candidate(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-01",
        runtime_contract=_contract(),
        checks={"ok": True, "errors": []},
        event_log=[{"event_type": "post_task"}],
        response_text="runtime output",
        summary="Low-risk session",
    )

    assert result["ok"] is True
    assert result["decision"] == "AUTO_PROMOTE"
    assert result["snapshot"] is not None
    assert result["curated"] is not None
    assert result["promotion"] is not None

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["promoted"] is True
    verdict_payload = json.loads(Path(result["verdict_artifact"]).read_text(encoding="utf-8"))
    assert verdict_payload["artifact_type"] == "runtime-verdict"
    assert verdict_payload["verdict"]["decision"] == "AUTO_PROMOTE"
    trace_payload = json.loads(Path(result["trace_artifact"]).read_text(encoding="utf-8"))
    assert trace_payload["artifact_type"] == "runtime-trace"
    assert trace_payload["result"]["decision"] == "AUTO_PROMOTE"
    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert curated_payload["curation_status"] == "CURATED"


def test_session_end_requires_review_for_high_risk(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-02",
        runtime_contract=_contract(risk="high", oversight="review-required"),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
        summary="High-risk session",
    )

    assert result["ok"] is True
    assert result["decision"] == "REVIEW_REQUIRED"
    assert result["snapshot"] is not None
    assert result["curated"] is not None
    assert result["promotion"] is None


def test_session_end_does_not_promote_stateless_session(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-03",
        runtime_contract=_contract(memory_mode="stateless"),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
    )

    assert result["ok"] is True
    assert result["decision"] == "DO_NOT_PROMOTE"
    assert result["snapshot"] is None


def test_session_end_blocks_missing_contract_fields(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-04",
        runtime_contract={"task": "Broken session", "rules": []},
        checks={"ok": True, "errors": []},
        response_text="runtime output",
    )

    assert result["ok"] is False
    assert any("runtime_contract missing required fields" in error for error in result["errors"])


def test_session_end_records_public_api_diff_in_summary_and_curated_artifact(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-05",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={
            "ok": True,
            "errors": [],
            "public_api_diff": {
                "ok": True,
                "removed": [],
                "added": ["public int Ping() => 0;"],
                "warnings": ["Public API surface added or changed."],
                "errors": [],
            },
        },
        response_text="runtime output",
        summary="Refactor session with API additions",
    )

    assert result["ok"] is True
    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["public_api_diff_present"] is True
    assert summary_payload["public_api_added_count"] == 1
    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "public_api_diff.added" for item in curated_payload["items"])


def test_session_end_curates_removed_public_api_as_followup(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-06",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={
            "ok": False,
            "errors": ["public-api-diff: Public API surface removed or changed."],
            "public_api_diff": {
                "ok": False,
                "removed": ["public int Run(int value) => value;"],
                "added": [],
                "warnings": [],
                "errors": ["Public API surface removed or changed."],
            },
        },
        response_text="runtime output",
        summary="Refactor session with API removal",
    )

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(
        item["source"] == "public_api_diff.removed" and item["type"] == "followup"
        for item in curated_payload["items"]
    )


def test_session_end_records_architecture_impact_preview(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-07",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={"ok": True, "errors": []},
        architecture_impact_preview={
            "concerns": ["cross-layer-change-risk", "public-api-expansion-risk"],
            "required_evidence": ["architecture-review", "public-api-review"],
            "recommended_risk": "high",
            "recommended_oversight": "human-approval",
            "boundary_risk": "high",
        },
        response_text="runtime output",
        summary="Proposal-time impact preview captured",
    )

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["architecture_impact_present"] is True
    assert summary_payload["architecture_impact_concern_count"] == 2
    assert summary_payload["architecture_impact_recommended_risk"] == "high"

    candidate_payload = json.loads(Path(result["candidate_artifact"]).read_text(encoding="utf-8"))
    assert candidate_payload["architecture_impact_preview"]["boundary_risk"] == "high"

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "architecture_impact_preview.concerns" for item in curated_payload["items"])


def test_session_end_records_proposal_summary_in_audit_chain(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-08",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={"ok": True, "errors": []},
        proposal_summary={
            "requested_rules": ["common", "refactor"],
            "recommended_risk": "high",
            "recommended_oversight": "human-approval",
            "required_evidence": ["architecture-review", "public-api-review"],
            "expected_validators": ["architecture_drift_checker", "public_api_diff_checker"],
            "concerns": ["cross-layer-change-risk"],
        },
        response_text="runtime output",
        summary="Proposal summary captured in session audit",
    )

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["proposal_summary_present"] is True
    assert summary_payload["proposal_summary_recommended_risk"] == "high"
    assert summary_payload["proposal_summary_expected_validator_count"] == 2

    candidate_payload = json.loads(Path(result["candidate_artifact"]).read_text(encoding="utf-8"))
    assert candidate_payload["proposal_summary"]["recommended_oversight"] == "human-approval"

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "proposal_summary.concerns" for item in curated_payload["items"])
    assert any(item["source"] == "proposal_summary.required_evidence" for item in curated_payload["items"])


def test_session_end_preserves_contract_context_in_summary_and_curated_artifact(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-09",
        runtime_contract=_contract(rules=["common", "cpp", "kernel-driver"]),
        checks={"ok": True, "errors": []},
        contract_resolution={
            "source": "discovery",
            "path": "D:/Kernel-Driver-Contract/contract.yaml",
        },
        domain_contract={
            "name": "kernel-driver-contract",
            "raw": {
                "domain": "kernel-driver",
                "plugin_version": "1.0.0",
            },
        },
        response_text="runtime output",
        summary="Kernel-driver session with external contract",
    )

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["contract_resolution_present"] is True
    assert summary_payload["contract_source"] == "discovery"
    assert summary_payload["contract_name"] == "kernel-driver-contract"
    assert summary_payload["contract_domain"] == "kernel-driver"
    assert summary_payload["contract_plugin_version"] == "1.0.0"
    assert summary_payload["contract_risk_tier"] == "high"

    candidate_payload = json.loads(Path(result["candidate_artifact"]).read_text(encoding="utf-8"))
    assert candidate_payload["contract_resolution"]["source"] == "discovery"
    assert candidate_payload["domain_contract"]["name"] == "kernel-driver-contract"
    verdict_payload = json.loads(Path(result["verdict_artifact"]).read_text(encoding="utf-8"))
    assert verdict_payload["contract_identity"]["name"] == "kernel-driver-contract"
    assert verdict_payload["contract_identity"]["domain"] == "kernel-driver"
    assert verdict_payload["contract_identity"]["risk_tier"] == "high"
    trace_payload = json.loads(Path(result["trace_artifact"]).read_text(encoding="utf-8"))
    assert trace_payload["contract_identity"]["plugin_version"] == "1.0.0"

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "contract_resolution" for item in curated_payload["items"])


def test_session_end_human_output_includes_contract_context(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-10",
        runtime_contract=_contract(rules=["common", "cpp", "kernel-driver"]),
        checks={"ok": True, "errors": []},
        contract_resolution={
            "source": "explicit",
            "path": "D:/Kernel-Driver-Contract/contract.yaml",
        },
        domain_contract={
            "name": "kernel-driver-contract",
            "raw": {
                "domain": "kernel-driver",
                "plugin_version": "1.0.0",
            },
        },
        response_text="runtime output",
        summary="Kernel-driver session human output",
    )

    output = format_human_result(result)

    assert "contract_source=explicit" in output
    assert "contract_path=D:/Kernel-Driver-Contract/contract.yaml" in output
    assert "contract_name=kernel-driver-contract" in output
    assert "contract_domain=kernel-driver" in output
    assert "contract_plugin_version=1.0.0" in output
    assert "contract_risk_tier=high" in output
    assert "verdict_artifact=" in output
    assert "trace_artifact=" in output



def test_session_end_fails_closed_on_forced_runtime_failure(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-11",
        runtime_contract=_contract(),
        checks={
            "ok": True,
            "errors": [],
            "force_runtime_failure_stage": "artifact_emission",
        },
        response_text="runtime output",
        summary="Forced runtime failure session",
    )

    assert result["ok"] is False
    assert result["decision"] == "RUNTIME_FAILURE"
    assert result["policy"]["decision"] == "STOP"
    assert any("runtime_failure: forced runtime failure at stage: artifact_emission" in error for error in result["errors"])
    assert Path(result["trace_artifact"]).exists()
    trace_payload = json.loads(Path(result["trace_artifact"]).read_text(encoding="utf-8"))
    assert trace_payload["artifact_type"] == "runtime-failure-trace"
    assert trace_payload["runtime_failure"]["violation_type"] == "runtime_failure"
    assert trace_payload["runtime_failure"]["verdict_impact"] == "stop"
    assert trace_payload["runtime_failure"]["stage"] == "artifact_emission"



def test_session_end_replay_preserves_verdict_for_same_input(local_project_root):
    session_id = "2026-03-12-12"
    runtime_contract = _contract(memory_mode="stateless", rules=["common", "refactor"])
    checks = {
        "ok": False,
        "errors": ["public-api-diff: Public API surface removed or changed."],
        "public_api_diff": {
            "ok": False,
            "removed": ["public int Run(int value) => value;"],
            "added": [],
            "compatibility_risk": "high",
            "breaking_changes": ["public int Run(int value) => value;"],
            "non_breaking_changes": [],
            "warnings": [],
            "errors": ["Public API surface removed or changed."],
        },
    }

    result_a = run_session_end(
        project_root=local_project_root,
        session_id=session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        response_text="",
        summary="Determinism replay session",
    )
    verdict_a = json.loads(Path(result_a["verdict_artifact"]).read_text(encoding="utf-8"))
    trace_a = json.loads(Path(result_a["trace_artifact"]).read_text(encoding="utf-8"))

    result_b = run_session_end(
        project_root=local_project_root,
        session_id=session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        response_text="",
        summary="Determinism replay session",
    )
    verdict_b = json.loads(Path(result_b["verdict_artifact"]).read_text(encoding="utf-8"))
    trace_b = json.loads(Path(result_b["trace_artifact"]).read_text(encoding="utf-8"))

    assert result_a["decision"] == result_b["decision"]
    assert result_a["policy"] == result_b["policy"]
    assert result_a["errors"] == result_b["errors"]
    assert verdict_a["policy_ref"]["governance_runtime_decision_model"] == "2.6"
    assert trace_a["policy_ref"]["governance_runtime_decision_model"] == "2.6"
    assert verdict_a["policy_ref"]["runtime_version"] == "v2.6-draft-runtime"
    assert trace_a["policy_ref"]["runtime_version"] == "v2.6-draft-runtime"
    assert verdict_a["verdict"] == verdict_b["verdict"]
    assert verdict_a["contract_identity"] == verdict_b["contract_identity"]
    assert verdict_a["evidence_summary"] == verdict_b["evidence_summary"]
    assert trace_a["result"] == trace_b["result"]
    assert trace_a["decision_path"] == trace_b["decision_path"]
