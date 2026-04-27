from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.escalation_authority_writer import (
    ARTIFACT_SCHEMA,
    WRITER_ID,
    assess_authority_artifact,
    assess_authority_directory,
    build_authority_artifact,
    default_authority_artifact_path,
    validate_prewrite_payload,
    write_authority_artifact,
)


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_escalation_authority_writer" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _valid_payload() -> dict:
    return {
        "escalation_id": "esc-20260417-001",
        "mitigation_validation_state": "author_provisional",
        "governance_track_state": "pending_independent_validation",
        "forced_owner": "framework_maintainer",
        "forced_escalation_target": "tier1_reviewer_pool",
        "forced_route_due_date": "2026-05-05",
        "forced_route_status": "assigned",
        "protected_claim_used": True,
        "coverage_era": "CURRENT",
        "coverage_caveat": None,
        "contamination_status": "resolved",
        "release_claims_resolved": False,
        "escalation_closed": False,
    }


def test_validate_prewrite_rejects_missing_forced_owner_on_author_provisional():
    payload = _valid_payload()
    payload["forced_owner"] = ""
    ok, errors, _ = validate_prewrite_payload(payload)

    assert ok is False
    assert any("forced_owner is required" in error for error in errors)


def test_write_and_assess_roundtrip_is_authority_valid():
    project_root = _tmp_dir("roundtrip")
    payload = _valid_payload()

    write_result = write_authority_artifact(project_root, payload)
    assessed = assess_authority_artifact(Path(write_result["artifact_file"]))

    assert write_result["ok"] is True
    assert assessed["ok"] is True
    assert assessed["authority_valid"] is True
    assert assessed["trusted_writer"] is True
    assert assessed["fingerprint_valid"] is True
    assert assessed["release_blocked"] is False


def test_write_rejects_non_canonical_authority_output_path():
    project_root = _tmp_dir("non_canonical_write_path")
    payload = _valid_payload()
    non_canonical = project_root / "manual" / "authority.json"

    write_result = write_authority_artifact(project_root, payload, out_file=non_canonical)

    assert write_result["ok"] is False
    assert write_result["error"] == "authority_write_path_violation"
    assert write_result["release_blocked"] is True
    assert "authority_write_path_violation" in write_result["release_block_reasons"]
    assert non_canonical.exists() is False


def test_write_rejects_silent_overwrite_of_existing_untrusted_artifact():
    project_root = _tmp_dir("reject_silent_overwrite_untrusted")
    payload = _valid_payload()
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps({"artifact_type": "e1b_phase_b_escalation_authority", "payload": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    write_result = write_authority_artifact(project_root, payload)

    assert write_result["ok"] is False
    assert write_result["error"] == "authority_write_existing_untrusted_artifact"
    assert "existing_untrusted_authority_artifact" in write_result["release_block_reasons"]


def test_assess_fails_closed_for_untrusted_writer():
    project_root = _tmp_dir("untrusted_writer")
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)
    artifact["authority_provenance"]["writer_id"] = "fake.writer"
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["ok"] is False
    assert assessed["authority_valid"] is False
    assert assessed["release_blocked"] is True
    assert "untrusted_escalation_provenance" in assessed["release_block_reasons"]
    assert "untrusted_writer_identity" in assessed["release_block_reasons"]


def test_assess_fails_closed_when_provenance_linkage_is_missing():
    project_root = _tmp_dir("missing_linkage")
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)
    del artifact["authority_provenance"]["normalized_payload_hash"]
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["ok"] is False
    assert assessed["authority_valid"] is False
    assert assessed["linkage_fields_ok"] is False
    assert assessed["release_blocked"] is True


def test_assess_fails_closed_for_fingerprint_mismatch():
    project_root = _tmp_dir("fingerprint_mismatch")
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)
    artifact["payload"]["forced_owner"] = "tampered_owner"
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["ok"] is False
    assert assessed["fingerprint_valid"] is False
    assert assessed["release_blocked"] is True
    assert "payload_fingerprint_mismatch" in assessed["release_block_reasons"]
    assert "normalized_payload_hash_mismatch" in assessed["release_block_reasons"]


def test_overdue_route_is_release_blocked_even_when_authority_valid():
    project_root = _tmp_dir("overdue")
    payload = _valid_payload()
    payload["forced_route_status"] = "overdue"
    payload["release_claims_resolved"] = False

    write_result = write_authority_artifact(project_root, payload)
    assessed = assess_authority_artifact(Path(write_result["artifact_file"]))

    assert assessed["ok"] is True
    assert assessed["release_blocked"] is True
    assert "forced_route_overdue" in assessed["release_block_reasons"]


def test_assess_directory_no_escalation_expected_when_no_log():
    """No authority dir AND no escalation log → no_escalation_expected → ok=True."""
    project_root = _tmp_dir("missing_dir_no_log")
    result = assess_authority_directory(project_root)

    assert result["available"] is False
    assert result["ok"] is True
    assert result["release_blocked"] is False
    assert result["source"] == "no_escalation_expected"


def test_assess_directory_escalation_expected_missing_fails_closed_when_log_active():
    """Authority dir absent BUT escalation log present with content → fail-closed."""
    project_root = _tmp_dir("missing_dir_with_log")
    # Create the escalation log sibling (parent of authority/ dir)
    from governance_tools.escalation_authority_writer import default_authority_dir
    authority_dir = default_authority_dir(project_root)
    authority_dir.parent.mkdir(parents=True, exist_ok=True)
    escalation_log = authority_dir.parent / "phase-b-escalation-log.jsonl"
    escalation_log.write_text('{"escalation_id": "esc-001"}\n', encoding="utf-8")
    # authority_dir itself does NOT exist

    result = assess_authority_directory(project_root)

    assert result["available"] is False
    assert result["ok"] is False
    assert result["release_blocked"] is True
    assert "escalation_active_but_no_authority_artifacts" in result["release_block_reasons"]
    assert result["source"] == "escalation_expected_missing"


def test_assess_directory_no_escalation_expected_when_log_empty():
    """Escalation log exists but is empty (zero bytes) → treated as no active cases → ok=True."""
    project_root = _tmp_dir("missing_dir_empty_log")
    from governance_tools.escalation_authority_writer import default_authority_dir
    authority_dir = default_authority_dir(project_root)
    authority_dir.parent.mkdir(parents=True, exist_ok=True)
    escalation_log = authority_dir.parent / "phase-b-escalation-log.jsonl"
    escalation_log.write_text("", encoding="utf-8")

    result = assess_authority_directory(project_root)

    assert result["ok"] is True
    assert result["release_blocked"] is False


def test_written_artifact_declares_expected_schema_and_writer_id():
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)

    assert artifact["artifact_schema"] == ARTIFACT_SCHEMA
    assert artifact["authority_provenance"]["writer_id"] == WRITER_ID
    assert artifact["authority_provenance"]["provenance_linkage_version"] == "v1"
    assert "source_inputs_hash" in artifact["authority_provenance"]
    assert "normalized_payload_hash" in artifact["authority_provenance"]


def test_tamper_replay_blocks_schema_valid_but_non_authority_writer_artifact():
    project_root = _tmp_dir("tamper_schema_valid_untrusted_writer")
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)
    artifact["authority_provenance"]["writer_id"] = "manual.json.writer"
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["release_blocked"] is True
    assert "untrusted_escalation_provenance" in assessed["release_block_reasons"]
    assert "untrusted_writer_identity" in assessed["release_block_reasons"]
    assert assessed["trusted_writer"] is False


def test_tamper_replay_blocks_forced_owner_and_status_mutation_of_copied_artifact():
    project_root = _tmp_dir("tamper_forced_owner_status")
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)
    artifact["payload"]["forced_owner"] = "tampered_owner"
    artifact["payload"]["forced_route_status"] = "completed"
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["release_blocked"] is True
    assert "untrusted_escalation_provenance" in assessed["release_block_reasons"]
    assert "payload_fingerprint_mismatch" in assessed["release_block_reasons"]
    assert "normalized_payload_hash_mismatch" in assessed["release_block_reasons"]
    assert assessed["fingerprint_valid"] is False
    assert assessed["normalized_hash_valid"] is False


def test_tamper_replay_blocks_coverage_and_protected_claim_linkage_mutation():
    project_root = _tmp_dir("tamper_coverage_linkage")
    payload = _valid_payload()
    artifact = build_authority_artifact(payload)
    artifact["payload"]["coverage_era"] = "TRANSITION"
    artifact["payload"]["coverage_caveat"] = None
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["release_blocked"] is True
    assert "untrusted_escalation_provenance" in assessed["release_block_reasons"]
    assert "payload_prewrite_validation_failed" in assessed["release_block_reasons"]
    assert "normalized_payload_hash_mismatch" in assessed["release_block_reasons"]
    assert assessed["authority_valid"] is False
