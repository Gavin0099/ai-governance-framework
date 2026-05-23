import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.change_control_summary import build_change_control_summary, format_human_result


def test_change_control_summary_merges_proposal_and_runtime():
    result = build_change_control_summary(
        session_start={
            "task_text": "Refactor service boundary",
            "runtime_contract": {"rules": ["common"], "risk": "medium", "oversight": "review-required"},
            "contract_resolution": {
                "source": "discovery",
                "path": "D:/USB-Hub-Firmware-Architecture-Contract/contract.yaml",
            },
            "domain_contract": {
                "name": "usb-hub-firmware-contract",
                "raw": {
                    "domain": "firmware",
                    "plugin_version": "1.0.0",
                },
            },
            "suggested_rules_preview": ["common", "csharp", "avalonia", "refactor"],
            "suggested_skills": ["code-style", "governance-runtime"],
            "suggested_agent": "advanced-agent",
            "proposal_summary": {
                "requested_rules": ["common", "refactor"],
                "recommended_risk": "high",
                "recommended_oversight": "human-approval",
                "expected_validators": ["architecture_drift_checker", "public_api_diff_checker"],
                "required_evidence": ["architecture-review", "public-api-review"],
                "concerns": ["cross-layer-change-risk"],
            },
        },
        session_end={
            "task": "Refactor service boundary",
            "decision": "REVIEW_REQUIRED",
            "risk": "medium",
            "oversight": "review-required",
            "rules": ["common"],
            "public_api_diff_present": True,
            "public_api_added_count": 1,
            "public_api_removed_count": 0,
            "warning_count": 1,
            "error_count": 0,
            "promoted": False,
        },
    )

    assert result["task"] == "Refactor service boundary"
    assert result["requested_rules"] == ["common", "refactor"]
    assert result["active_rules"] == ["common"]
    assert result["contract_resolution"]["source"] == "discovery"
    assert result["contract_resolution"]["domain"] == "firmware"
    assert result["proposal"]["recommended_risk"] == "high"
    assert result["runtime"]["decision"] == "REVIEW_REQUIRED"


def test_change_control_summary_human_output_is_reviewable():
    output = format_human_result(
        build_change_control_summary(
            session_start={
                "task_text": "Improve CLI output",
                "runtime_contract": {"rules": ["common"], "risk": "medium", "oversight": "review-required"},
                "contract_resolution": {
                    "source": "env",
                    "path": "D:/Kernel-Driver-Contract/contract.yaml",
                },
                "domain_contract": {
                    "name": "kernel-driver-contract",
                    "raw": {
                        "domain": "kernel-driver",
                        "plugin_version": "1.0.0",
                    },
                },
                "proposal_summary": {
                    "requested_rules": ["common"],
                    "recommended_risk": "medium",
                    "recommended_oversight": "review-required",
                    "expected_validators": ["failure_completeness_validator"],
                    "required_evidence": ["cli-review"],
                    "concerns": ["human-output-change"],
                },
            },
            session_end={
                "decision": "AUTO_PROMOTE",
                "risk": "medium",
                "oversight": "review-required",
                "public_api_diff_present": False,
                "warning_count": 0,
                "error_count": 0,
                "promoted": True,
            },
        )
    )

    assert "[change_control_summary]" in output
    assert "summary=task=Improve CLI output | proposal_risk=medium | runtime_decision=AUTO_PROMOTE | promoted=True | contract=kernel-driver/high" in output
    assert "[contract_resolution]" in output
    assert "contract_source=env" in output
    assert "contract_risk_tier=high" in output
    assert "promoted=True" in output
    assert "suggested_skills=" not in output
    assert "suggested_agent=" not in output
    assert "[signal_profile]" in output
    assert "runtime.decision: class=enforcement effect=routing promotion_allowed=True" in output
    assert "[promotion_gate]" in output
    assert "contract_version=0.1" in output
    assert "allowed=True" in output
    assert "gate_inputs_digest=" in output


def test_change_control_summary_builds_signal_profile():
    result = build_change_control_summary(
        session_start={
            "task_text": "Refactor service boundary",
            "runtime_contract": {"rules": ["common"], "risk": "medium", "oversight": "review-required"},
            "proposal_summary": {
                "requested_rules": ["common"],
                "recommended_risk": "medium",
                "recommended_oversight": "review-required",
            },
        },
        session_end={
            "decision": "REVIEW_REQUIRED",
            "public_api_diff_present": True,
            "promoted": False,
        },
    )

    profile = result["signal_profile"]
    assert profile["task"]["signal_class"] == "descriptive"
    assert profile["proposal.recommended_risk"]["signal_class"] == "advisory"
    assert profile["runtime.decision"]["signal_class"] == "enforcement"
    assert profile["runtime.public_api_diff_present"]["decision_effect"] == "approval_required"


def test_change_control_summary_blocks_promotion_on_placeholder_task_provenance():
    result = build_change_control_summary(
        session_start={
            "task_text": "Refactor service boundary",
            "task_provenance": {"status": "placeholder_suppressed", "source_key": "prompt"},
            "proposal_summary": {
                "recommended_risk": "medium",
                "recommended_oversight": "review-required",
            },
        },
        session_end={
            "decision": "AUTO_PROMOTE",
            "promoted": True,
        },
    )

    assert result["promotion_gate"]["allowed"] is False
    assert "task_provenance_placeholder_suppressed_blocks_promotion" in result["promotion_gate"]["reasons"]
    assert result["promotion_gate"]["blocking_reasons"] == result["promotion_gate"]["reasons"]
    assert result["runtime"]["promoted"] is False


def test_change_control_summary_blocks_unknown_signal_class():
    result = build_change_control_summary(
        session_start={
            "task_text": "Refactor service boundary",
            "proposal_summary": {
                "recommended_risk": "medium",
                "recommended_oversight": "review-required",
            },
        },
        session_end={
            "decision": "AUTO_PROMOTE",
            "promoted": True,
        },
    )
    result["signal_profile"]["runtime.decision"]["signal_class"] = "mystery"
    # Rebuild gate consumption behavior with unknown class scenario.
    from governance_tools.change_control_summary import _evaluate_promotion_gate

    gate = _evaluate_promotion_gate(
        signal_profile=result["signal_profile"],
        task_provenance=result["task_provenance"],
        runtime=result["runtime"],
        requested_promoted=True,
    )
    assert gate["allowed"] is False
    assert any(reason.startswith("unknown_signal_class_blocks_promotion:") for reason in gate["reasons"])


def test_change_control_summary_blocks_advisory_only_promotion():
    result = build_change_control_summary(
        session_start={
            "task_text": "Refactor service boundary",
            "proposal_summary": {
                "recommended_risk": "medium",
                "recommended_oversight": "review-required",
            },
        },
        session_end={
            "promoted": True,
        },
    )
    assert result["promotion_gate"]["allowed"] is False
    assert "missing_enforcement_or_admissibility_signal" in result["promotion_gate"]["reasons"]
    assert result["runtime"]["promoted"] is False


def test_change_control_summary_promotion_gate_receipt_digest_is_stable_for_same_inputs():
    session_start = {
        "task_text": "Refactor service boundary",
        "task_provenance": {"status": "accepted", "source_key": "prompt"},
        "proposal_summary": {
            "recommended_risk": "medium",
            "recommended_oversight": "review-required",
        },
    }
    session_end = {
        "decision": "AUTO_PROMOTE",
        "promoted": True,
        "public_api_diff_present": False,
    }
    result_a = build_change_control_summary(session_start=session_start, session_end=session_end)
    result_b = build_change_control_summary(session_start=session_start, session_end=session_end)
    gate_a = result_a["promotion_gate"]
    gate_b = result_b["promotion_gate"]
    assert gate_a["promotion_gate_contract_version"] == "0.1"
    assert gate_a["gate_input_fields"] == gate_b["gate_input_fields"]
    assert gate_a["gate_inputs_digest"] == gate_b["gate_inputs_digest"]


def test_change_control_summary_promotion_gate_receipt_digest_changes_on_relevant_input_change():
    base_start = {
        "task_text": "Refactor service boundary",
        "task_provenance": {"status": "accepted", "source_key": "prompt"},
        "proposal_summary": {
            "recommended_risk": "medium",
            "recommended_oversight": "review-required",
        },
    }
    session_end = {
        "decision": "AUTO_PROMOTE",
        "promoted": True,
        "public_api_diff_present": False,
    }
    result_a = build_change_control_summary(session_start=base_start, session_end=session_end)
    changed_start = dict(base_start)
    changed_start["task_provenance"] = {"status": "placeholder_suppressed", "source_key": "prompt"}
    result_b = build_change_control_summary(session_start=changed_start, session_end=session_end)
    assert (
        result_a["promotion_gate"]["gate_inputs_digest"]
        != result_b["promotion_gate"]["gate_inputs_digest"]
    )


def test_change_control_summary_accepts_smoke_envelope_shape():
    result = build_change_control_summary(
        session_start={
                "event_type": "session_start",
                "payload_file": "runtime_hooks/examples/shared/session_start.shared.json",
                "result": {
                    "task_text": "Refactor service boundary",
                "runtime_contract": {"rules": ["common"], "risk": "medium", "oversight": "review-required"},
                "contract_resolution": {
                    "source": "explicit",
                    "path": "D:/USB-Hub-Firmware-Architecture-Contract/contract.yaml",
                },
                "domain_contract": {
                    "name": "usb-hub-firmware-contract",
                    "raw": {
                        "domain": "firmware",
                        "plugin_version": "1.0.0",
                    },
                },
                "suggested_rules_preview": ["common", "csharp", "avalonia", "refactor"],
                "suggested_skills": ["code-style", "governance-runtime"],
                "suggested_agent": "advanced-agent",
                "proposal_summary": {
                    "requested_rules": ["common", "refactor"],
                    "recommended_risk": "high",
                    "recommended_oversight": "human-approval",
                    "expected_validators": ["architecture_drift_checker"],
                    "required_evidence": ["architecture-review"],
                    "concerns": ["cross-layer-change-risk"],
                },
            },
        }
    )

    assert result["task"] == "Refactor service boundary"
    assert result["requested_rules"] == ["common", "refactor"]
    assert result["suggested_agent"] == "advanced-agent"
    assert result["contract_resolution"]["source"] == "explicit"


def test_change_control_summary_cli_runs_as_direct_script(tmp_path):
    session_start_file = tmp_path / "session_start.json"
    session_start_file.write_text(
        json.dumps(
            {
                "event_type": "session_start",
                "result": {
                    "task_text": "Verify direct script execution",
                    "runtime_contract": {
                        "rules": ["common"],
                        "risk": "medium",
                        "oversight": "review-required",
                    },
                    "contract_resolution": {
                        "source": "explicit",
                        "path": "D:/Kernel-Driver-Contract/contract.yaml",
                    },
                    "domain_contract": {
                        "name": "kernel-driver-contract",
                        "raw": {
                            "domain": "kernel-driver",
                            "plugin_version": "1.0.0",
                        },
                    },
                    "proposal_summary": {
                        "requested_rules": ["common"],
                        "recommended_risk": "medium",
                        "recommended_oversight": "review-required",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "governance_tools/change_control_summary.py",
            "--session-start-file",
            str(session_start_file),
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "[change_control_summary]" in completed.stdout
    assert "contract_risk_tier=high" in completed.stdout
