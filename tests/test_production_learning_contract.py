from __future__ import annotations

from pathlib import Path

from governance_tools.production_learning_contract import (
    build_production_learning_contract,
    write_contract_artifact,
)


def _valid_closeout_payload() -> dict[str, bool]:
    return {
        "authority_source_verified": True,
        "runtime_path_executed": True,
        "pre_task_gate_observed": True,
        "post_task_advisory_visible": True,
        "reviewer_surface_present": True,
        "closeout_artifact_generated": True,
        "validation_dataset_updated": True,
        "governance_complete": False,
    }


def test_contract_is_advisory_only_and_blocks_completion_claim_from_itself():
    contract = build_production_learning_contract(
        project_root=Path(".").resolve(),
        spec_text="The system shall return code 200 within 2 seconds. Acceptance criteria: pass if request_id exists.",
        analysis_text="Authority source verified.",
        authority_source_identified=True,
        claimed_authority_file="GOVERNANCE_ENTRY.md",
        closeout_payload=_valid_closeout_payload(),
    )
    assert contract["advisory_only"] is True
    assert contract["governance_complete_claim_allowed"] is False


def test_contract_flags_forbidden_inference_and_invalid_authority_reference():
    contract = build_production_learning_contract(
        project_root=Path(".").resolve(),
        spec_text="Implement behavior as needed. TBD.",
        analysis_text="Tests passed, governance complete.",
        authority_source_identified=True,
        claimed_authority_file="README.md",
        closeout_payload=_valid_closeout_payload(),
    )
    assert contract["reviewer_action_required"] is True
    assert "forbidden_inference_detected" in contract["advisory_findings"]
    assert "authority_reference_invalid" in contract["advisory_findings"]


def test_contract_artifact_written():
    contract = build_production_learning_contract(
        project_root=Path(".").resolve(),
        spec_text="",
        analysis_text="What is the governance pull command?",
        authority_source_identified=False,
        claimed_authority_file="GOVERNANCE_ENTRY.md",
        closeout_payload=_valid_closeout_payload(),
    )
    out = Path("artifacts/runtime/test-production-learning/latest-test.json")
    written = write_contract_artifact(contract, out)
    assert written.exists()
