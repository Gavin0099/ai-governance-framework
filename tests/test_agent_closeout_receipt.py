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
