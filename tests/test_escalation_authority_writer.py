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


def test_assess_directory_reports_missing_as_available_false_not_failure():
    project_root = _tmp_dir("missing_dir")
    result = assess_authority_directory(project_root)

    assert result["available"] is False
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
