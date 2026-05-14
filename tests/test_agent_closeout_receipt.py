from __future__ import annotations

import json
from pathlib import Path

from governance_tools.manage_agent_closeout import _manual_closeout_cmd, op_status
from governance_tools.session_closeout_entry import (
    CLOSEOUT_RECEIPT_SCHEMA_VERSION,
    _write_closeout_receipt,
)


def test_closeout_receipt_contains_required_fields_and_checksum(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "runtime" / "closeouts" / "sample.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"ok": true}\n', encoding="utf-8")

    receipt_path = _write_closeout_receipt(
        tmp_path,
        agent_id="chatgpt-web",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=True,
        memory_write_performed=False,
        memory_eligibility_reason="repo_state_or_session_closeout_present",
    )

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == CLOSEOUT_RECEIPT_SCHEMA_VERSION
    assert payload["agent_id"] == "chatgpt-web"
    assert payload["trigger_mode"] == "manual_fallback"
    assert payload["entrypoint"] == "governance_tools.session_closeout_entry"
    assert payload["exit_code"] == 0
    assert payload["closeout_artifact_path"].endswith("sample.json")
    assert isinstance(payload["checksum_of_cleaned_path"], str)
    assert len(payload["checksum_of_cleaned_path"]) == 64
    assert payload["memory_eligibility_evaluated"] is True
    assert payload["memory_write_required"] is True
    assert payload["memory_write_performed"] is False
    assert payload["memory_eligibility_reason"] == "repo_state_or_session_closeout_present"


def test_manual_closeout_command_includes_agent_and_trigger_mode(tmp_path: Path) -> None:
    cmd = _manual_closeout_cmd(tmp_path, "codex", "manual_fallback")
    assert "--agent-id codex" in cmd
    assert "--trigger-mode manual_fallback" in cmd


def test_status_json_contains_machine_readable_fields(tmp_path: Path) -> None:
    rows = op_status(tmp_path, tmp_path)
    chatgpt = next(r for r in rows if r["agent"] == "chatgpt-web")
    assert set(
        ["agent", "tier", "hook_surface", "installed", "auto_trigger_capable", "fallback_required"]
    ).issubset(chatgpt.keys())
    assert chatgpt["enforcement_level"] == "MANUAL_FALLBACK"
    assert chatgpt["compliance_status"] == "PENDING_MANUAL_ACTION"


def test_synthetic_smoke_compliance_matrix_logic(tmp_path: Path) -> None:
    # local mirror of expected compliance rule used by smoke output
    def compliant(
        *,
        process_exit_code: int,
        evidence_recorded: bool,
        receipt_recorded: bool,
        receipt_exit_code_ok: bool,
        receipt_artifact_exists: bool,
        memory_eligibility_evaluated: bool,
        memory_write_required: bool,
        memory_write_performed: bool,
    ) -> bool:
        return (
            process_exit_code == 0
            and evidence_recorded
            and receipt_recorded
            and receipt_exit_code_ok
            and receipt_artifact_exists
            and memory_eligibility_evaluated
            and (not memory_write_required or memory_write_performed)
        )

    assert compliant(
        process_exit_code=0,
        evidence_recorded=False,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
    ) is False
    assert compliant(
        process_exit_code=0,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
    ) is True
    assert compliant(
        process_exit_code=0,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=False,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
    ) is False
    assert compliant(
        process_exit_code=0,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=False,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
    ) is False
    assert compliant(
        process_exit_code=0,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=False,
        memory_write_required=False,
        memory_write_performed=False,
    ) is False
    assert compliant(
        process_exit_code=0,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=True,
        memory_write_performed=False,
    ) is False
    assert compliant(
        process_exit_code=0,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=True,
        memory_write_performed=True,
    ) is True
