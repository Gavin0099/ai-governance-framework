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
    default_authority_dir,
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

def _resolved_confirmed_payload(escalation_id: str = "esc-20260417-001") -> dict:
    payload = _valid_payload()
    payload["escalation_id"] = escalation_id
    payload["authority_lifecycle_state"] = "resolved_confirmed"
    payload["release_claims_resolved"] = True
    payload["lifecycle_transition"] = {
        "from_state": "resolved_provisional",
        "actor": "reviewer_confirmed",
        "auto": False,
        "reviewer_confirmation": {
            "reviewer_id": "reviewer-001",
            "confirmed_at": "2026-04-27T09:00:00+00:00",
        },
    }
    return payload


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


def test_resolved_confirmed_write_requires_lifecycle_transition_guard():
    project_root = _tmp_dir("resolved_confirmed_missing_transition")
    payload = _valid_payload()
    payload["authority_lifecycle_state"] = "resolved_confirmed"
    payload["release_claims_resolved"] = True

    write_result = write_authority_artifact(project_root, payload)

    assert write_result["ok"] is False
    assert any(
        "lifecycle_transition is required for resolved_* lifecycle states" in err
        for err in (write_result.get("authority_errors") or [])
    )


def test_resolved_confirmed_write_fails_closed_for_author_provisional_actor():
    project_root = _tmp_dir("resolved_confirmed_author_provisional_forbidden")
    payload = _valid_payload()
    payload["authority_lifecycle_state"] = "resolved_confirmed"
    payload["release_claims_resolved"] = True
    payload["lifecycle_transition"] = {
        "from_state": "resolved_provisional",
        "actor": "author_provisional",
        "auto": False,
        "reviewer_confirmation": {
            "reviewer_id": "reviewer-001",
            "confirmed_at": "2026-04-27T08:00:00+00:00",
        },
    }

    write_result = write_authority_artifact(project_root, payload)

    assert write_result["ok"] is False
    assert any(
        "lifecycle_transition_guard_failed" in err
        for err in (write_result.get("authority_errors") or [])
    )


def test_resolved_confirmed_write_requires_reviewer_confirmation():
    project_root = _tmp_dir("resolved_confirmed_missing_reviewer_confirmation")
    payload = _resolved_confirmed_payload()
    del payload["lifecycle_transition"]["reviewer_confirmation"]

    write_result = write_authority_artifact(project_root, payload)

    assert write_result["ok"] is False
    assert any(
        "resolved_confirmed requires lifecycle_transition.reviewer_confirmation" in err
        for err in (write_result.get("authority_errors") or [])
    )


def test_assess_resolved_confirmed_fails_closed_without_reviewer_confirmation():
    project_root = _tmp_dir("assess_resolved_confirmed_missing_reviewer_confirmation")
    payload = _resolved_confirmed_payload()
    del payload["lifecycle_transition"]["reviewer_confirmation"]
    artifact = build_authority_artifact(payload)
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["ok"] is False
    assert assessed["release_blocked"] is True
    assert "untrusted_escalation_provenance" in assessed["release_block_reasons"]
    assert "payload_prewrite_validation_failed" in assessed["release_block_reasons"]


def test_assess_resolved_confirmed_fails_closed_for_untrusted_writer_identity():
    project_root = _tmp_dir("assess_resolved_confirmed_untrusted_writer")
    payload = _resolved_confirmed_payload()
    artifact = build_authority_artifact(payload)
    artifact["authority_provenance"]["writer_id"] = "manual.json.writer"
    out_file = default_authority_artifact_path(project_root, payload["escalation_id"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assessed = assess_authority_artifact(out_file)

    assert assessed["ok"] is False
    assert assessed["release_blocked"] is True
    assert "untrusted_escalation_provenance" in assessed["release_block_reasons"]
    assert "untrusted_writer_identity" in assessed["release_block_reasons"]


# ---------------------------------------------------------------------------
# assess_authority_directory: companion register cross-verification
# ---------------------------------------------------------------------------


def test_assess_directory_fails_closed_when_register_active_and_no_log():
    """Register says active IDs exist, no log → escalation_expected_missing → fail-closed."""
    from governance_tools.escalation_log_writer import write_escalation_register

    project_root = _tmp_dir("dir_register_active_no_log")
    authority_dir = default_authority_dir(project_root)
    authority_dir.parent.mkdir(parents=True, exist_ok=True)
    register_path = authority_dir.parent / "phase-b-escalation-register.json"
    write_escalation_register(register_path, ["esc-001"])
    # No log file, no authority/ dir

    result = assess_authority_directory(project_root)

    assert result["ok"] is False
    assert result["release_blocked"] is True
    assert result["source"] == "escalation_expected_missing"
    assert "escalation_active_but_no_authority_artifacts" in result["release_block_reasons"]


def test_assess_directory_fails_closed_when_register_untrusted():
    """Register exists but writer_id is untrusted → register_integrity_failed → fail-closed."""
    from governance_tools.escalation_log_writer import REGISTER_SCHEMA, REGISTER_WRITER_VERSION

    project_root = _tmp_dir("dir_register_untrusted")
    authority_dir = default_authority_dir(project_root)
    authority_dir.parent.mkdir(parents=True, exist_ok=True)
    register_path = authority_dir.parent / "phase-b-escalation-register.json"
    register_path.write_text(
        json.dumps(
            {
                "register_schema": REGISTER_SCHEMA,
                "writer_id": "evil.writer",
                "writer_version": REGISTER_WRITER_VERSION,
                "written_at": "2026-04-27T00:00:00+00:00",
                "active_escalation_ids": [],
                "active_case_count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_authority_directory(project_root)

    assert result["ok"] is False
    assert result["release_blocked"] is True
    assert result["source"] == "register_integrity_failed"
    assert "register_writer_untrusted" in result["release_block_reasons"]


def test_assess_directory_precedence_active_state_blocks_even_when_resolved_confirmed_exists():
    project_root = _tmp_dir("dir_precedence_active_blocks")

    resolved_payload = _resolved_confirmed_payload("esc-resolved")
    write_result_resolved = write_authority_artifact(project_root, resolved_payload)
    assert write_result_resolved["ok"] is True

    active_payload = _valid_payload()
    active_payload["escalation_id"] = "esc-active"
    active_payload["mitigation_validation_state"] = "validated"
    active_payload["governance_track_state"] = "closure_eligible"
    active_payload["authority_lifecycle_state"] = "active"
    active_payload["release_claims_resolved"] = False
    write_result_active = write_authority_artifact(project_root, active_payload)
    assert write_result_active["ok"] is True

    result = assess_authority_directory(project_root)

    assert result["ok"] is False
    assert result["release_blocked"] is True
    assert "authority_precedence_active_blocks_release" in result["release_block_reasons"]
    assert result["lifecycle_effective_by_escalation"]["esc-active"] == "active"
    assert result["lifecycle_effective_by_escalation"]["esc-resolved"] == "resolved_confirmed"


def test_assess_directory_register_active_overrides_resolved_confirmed_for_same_escalation():
    from governance_tools.escalation_log_writer import write_escalation_register

    project_root = _tmp_dir("dir_precedence_register_active_override")

    payload = _resolved_confirmed_payload("esc-001")
    write_result = write_authority_artifact(project_root, payload)
    assert write_result["ok"] is True

    authority_dir = default_authority_dir(project_root)
    register_path = authority_dir.parent / "phase-b-escalation-register.json"
    write_escalation_register(register_path, ["esc-001"])

    result = assess_authority_directory(project_root)

    assert result["ok"] is False
    assert result["release_blocked"] is True
    assert (
        "authority_precedence_active_register_overrides_resolved_confirmed:esc-001"
        in result["release_block_reasons"]
    )
