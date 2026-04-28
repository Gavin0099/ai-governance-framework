from __future__ import annotations

from pathlib import Path

from validators.governance_hardening_guard import (
    detect_forbidden_inference,
    validate_authority_reference,
    validate_governance_closeout_payload,
)


def test_blocks_pull_command_inference_before_authority_source():
    result = detect_forbidden_inference(
        "What is the governance pull command?",
        authority_source_identified=False,
    )
    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["manual_authority_verification_required"] is True
    assert any(v["code"] == "pull_command_before_authority_source" for v in result["violations"])


def test_blocks_tests_passed_to_governance_complete_shortcut():
    result = detect_forbidden_inference(
        "Tests passed, governance complete.",
        authority_source_identified=True,
    )
    assert result["ok"] is False
    assert any(v["code"] == "tests_only_completion_claim" for v in result["violations"])


def test_allows_neutral_text_when_no_forbidden_inference():
    result = detect_forbidden_inference(
        "Authority source verified and reviewer trace recorded.",
        authority_source_identified=True,
    )
    assert result["ok"] is True
    assert result["violations"] == []


def test_closeout_payload_requires_all_boolean_keys():
    result = validate_governance_closeout_payload(
        {
            "authority_source_verified": True,
            "runtime_path_executed": True,
        }
    )
    assert result["ok"] is False
    assert "missing_required_keys" in result["violations"]


def test_closeout_payload_rejects_governance_complete_without_prerequisites():
    payload = {
        "authority_source_verified": True,
        "runtime_path_executed": True,
        "pre_task_gate_observed": False,
        "post_task_advisory_visible": True,
        "reviewer_surface_present": True,
        "closeout_artifact_generated": True,
        "validation_dataset_updated": True,
        "governance_complete": True,
    }
    result = validate_governance_closeout_payload(payload)
    assert result["ok"] is False
    assert "governance_complete_without_full_prerequisites" in result["violations"]


def test_authority_reference_accepts_canonical_file():
    result = validate_authority_reference(
        project_root=Path(".").resolve(),
        claimed_authority_file="GOVERNANCE_ENTRY.md",
        claimed_overrides_from="runtime_governance_outputs",
    )
    assert result["ok"] is True
    assert result["blocked"] is False


def test_authority_reference_blocks_non_canonical_and_low_precedence_override():
    result = validate_authority_reference(
        project_root=Path(".").resolve(),
        claimed_authority_file="README.md",
        claimed_overrides_from="tests_passed_statements",
    )
    assert result["ok"] is False
    assert "non_canonical_authority_reference" in result["violations"]
    assert "invalid_low_precedence_override" in result["violations"]
