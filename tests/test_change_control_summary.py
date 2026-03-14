import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.change_control_summary import build_change_control_summary, format_human_result


def test_change_control_summary_merges_proposal_and_runtime():
    result = build_change_control_summary(
        session_start={
            "task_text": "Refactor Avalonia boundary",
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
            "task": "Refactor Avalonia boundary",
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

    assert result["task"] == "Refactor Avalonia boundary"
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
    assert "contract_domain=kernel-driver" in output
    assert "plugin_version=1.0.0" in output
    assert "contract_risk_tier=high" in output
    assert "expected_validators=failure_completeness_validator" in output
    assert "promoted=True" in output


def test_change_control_summary_accepts_smoke_envelope_shape():
    result = build_change_control_summary(
        session_start={
            "event_type": "session_start",
            "payload_file": "runtime_hooks/examples/shared/session_start.shared.json",
            "result": {
                "task_text": "Refactor Avalonia boundary",
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

    assert result["task"] == "Refactor Avalonia boundary"
    assert result["requested_rules"] == ["common", "refactor"]
    assert result["suggested_agent"] == "advanced-agent"
    assert result["contract_resolution"]["source"] == "explicit"
