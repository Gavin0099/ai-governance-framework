from __future__ import annotations

import json
import subprocess
from pathlib import Path

from governance_tools.manage_agent_closeout import _manual_closeout_cmd, op_status
from governance_tools.session_closeout_entry import (
    CLOSEOUT_RECEIPT_SCHEMA_VERSION,
    _apply_stale_duplicate_guard,
    _latest_receipt_checksum,
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
        session_id="session-20260528T000000-abc123",
    )

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == CLOSEOUT_RECEIPT_SCHEMA_VERSION
    assert payload["session_id"] == "session-20260528T000000-abc123"
    assert payload["agent_id"] == "chatgpt-web"
    assert payload["trigger_mode"] == "manual_fallback"
    assert payload["entrypoint"] == "governance_tools.session_closeout_entry"
    assert payload["exit_code"] == 0
    assert "linked_head_commit" in payload
    assert isinstance(payload["linked_head_commit"], str)
    assert payload["closeout_artifact_path"].endswith("sample.json")
    assert isinstance(payload["checksum_of_cleaned_path"], str)
    assert len(payload["checksum_of_cleaned_path"]) == 64
    assert payload["memory_eligibility_evaluated"] is True
    assert payload["memory_write_required"] is True
    assert payload["memory_write_performed"] is False
    assert payload["memory_eligibility_reason"] == "repo_state_or_session_closeout_present"


def test_closeout_receipt_includes_linked_head_commit_when_repo_has_head(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True, text=True)
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True, text=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    artifact = tmp_path / "artifacts" / "session-closeout.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("TASK_INTENT: test\n", encoding="utf-8")

    receipt_path = _write_closeout_receipt(
        tmp_path,
        agent_id="chatgpt-web",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["linked_head_commit"] == head


def test_matrix_negative_receipt_without_linked_head_commit_not_verified() -> None:
    def matrix_verified(*, candidate: bool, dirty_explainable: bool, evidence_exists: bool, linked_head_commit: str, repo_head: str, timestamp_in_window: bool) -> bool:
        head_match = bool(linked_head_commit) and bool(repo_head) and linked_head_commit == repo_head
        return candidate and dirty_explainable and evidence_exists and head_match and timestamp_in_window

    assert matrix_verified(
        candidate=True,
        dirty_explainable=True,
        evidence_exists=True,
        linked_head_commit="",
        repo_head="abc123",
        timestamp_in_window=True,
    ) is False
    assert matrix_verified(
        candidate=True,
        dirty_explainable=True,
        evidence_exists=True,
        linked_head_commit="abc123",
        repo_head="abc123",
        timestamp_in_window=True,
    ) is True


def test_matrix_positive_repo_with_hooks_valid_root_and_fresh_closeout_is_verified() -> None:
    def matrix_verified(
        *,
        hooks_ready: bool,
        framework_root_valid: bool,
        candidate: bool,
        dirty_explainable: bool,
        evidence_exists: bool,
        linked_head_commit: str,
        repo_head: str,
        timestamp_in_window: bool,
    ) -> bool:
        head_match = bool(linked_head_commit) and bool(repo_head) and linked_head_commit == repo_head
        return (
            hooks_ready
            and framework_root_valid
            and candidate
            and dirty_explainable
            and evidence_exists
            and head_match
            and timestamp_in_window
        )

    assert matrix_verified(
        hooks_ready=True,
        framework_root_valid=True,
        candidate=True,
        dirty_explainable=True,
        evidence_exists=True,
        linked_head_commit="abc123",
        repo_head="abc123",
        timestamp_in_window=True,
    ) is True


def test_latest_receipt_checksum_returns_empty_when_no_receipts(tmp_path: Path) -> None:
    assert _latest_receipt_checksum(tmp_path) == ""


def test_latest_receipt_checksum_returns_most_recent_checksum(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "session-closeout.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("TASK_INTENT: test\n", encoding="utf-8")

    # Write two receipts — second one should be returned.
    _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
    )
    import time; time.sleep(0.01)  # ensure distinct filenames
    receipt2 = _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
    )
    expected = json.loads(receipt2.read_text(encoding="utf-8"))["checksum_of_cleaned_path"]
    assert _latest_receipt_checksum(tmp_path) == expected
    assert len(expected) == 64  # SHA256 hex


def test_latest_receipt_checksum_detects_content_change(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "session-closeout.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("TASK_INTENT: session A\n", encoding="utf-8")

    _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
    )
    previous_checksum = _latest_receipt_checksum(tmp_path)

    # Simulate agent updating the closeout file for a new session.
    artifact.write_text("TASK_INTENT: session B\n", encoding="utf-8")

    import hashlib
    h = hashlib.sha256()
    h.update(artifact.read_bytes())
    new_checksum = h.hexdigest()

    assert new_checksum != previous_checksum, "New content must produce a different checksum"


def test_stale_duplicate_guard_suppresses_memory_write_required(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "session-closeout.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("TASK_INTENT: same\n", encoding="utf-8")

    _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=True,
        memory_write_performed=False,
        memory_eligibility_reason="memory_candidate_signals_detected",
    )

    required, reason, stale = _apply_stale_duplicate_guard(
        project_root=tmp_path,
        closeout_artifact_path=str(artifact),
        memory_write_required=True,
        memory_eligibility_reason="memory_candidate_signals_detected",
    )
    assert stale is True
    assert required is False
    assert "stale_duplicate_detected" in reason


def test_stale_duplicate_guard_keeps_required_when_content_changed(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "session-closeout.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("TASK_INTENT: before\n", encoding="utf-8")
    _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=str(artifact),
        memory_eligibility_evaluated=True,
        memory_write_required=True,
        memory_write_performed=False,
        memory_eligibility_reason="memory_candidate_signals_detected",
    )
    artifact.write_text("TASK_INTENT: after\n", encoding="utf-8")

    required, reason, stale = _apply_stale_duplicate_guard(
        project_root=tmp_path,
        closeout_artifact_path=str(artifact),
        memory_write_required=True,
        memory_eligibility_reason="memory_candidate_signals_detected",
    )
    assert stale is False
    assert required is True
    assert reason == "memory_candidate_signals_detected"


def test_stale_duplicate_guard_keeps_required_without_previous_receipt(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "session-closeout.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("TASK_INTENT: first\n", encoding="utf-8")

    required, reason, stale = _apply_stale_duplicate_guard(
        project_root=tmp_path,
        closeout_artifact_path=str(artifact),
        memory_write_required=True,
        memory_eligibility_reason="memory_candidate_signals_detected",
    )
    assert stale is False
    assert required is True
    assert reason == "memory_candidate_signals_detected"


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
    # memory gate strictness: required + not performed => NON_COMPLIANT
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
    # non-zero process exit must fail even if receipt exists
    assert compliant(
        process_exit_code=1,
        evidence_recorded=True,
        receipt_recorded=True,
        receipt_exit_code_ok=True,
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
    ) is False
    # runtime-error receipt semantics: receipt present with exit_code!=0 must fail
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
        receipt_artifact_exists=True,
        memory_eligibility_evaluated=True,
        memory_write_required=True,
        memory_write_performed=True,
    ) is True


def test_receipt_persists_session_id_as_given(tmp_path: Path) -> None:
    """Receipt session_id field must equal the session_id passed to _write_closeout_receipt."""
    receipt_path = _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=None,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
        session_id="session-20260528T120000-deadbe",
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["session_id"] == "session-20260528T120000-deadbe"


def test_receipt_session_id_defaults_to_empty_string_when_omitted(tmp_path: Path) -> None:
    """Backward-compatible: omitting session_id yields '' in the receipt, not a missing key."""
    receipt_path = _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="manual_fallback",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=None,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "session_id" in payload
    assert payload["session_id"] == ""


def test_human_output_and_receipt_session_id_match(tmp_path: Path) -> None:
    """Human output session_id line and receipt session_id field must be identical."""
    from governance_tools.session_end_hook import format_human_result, run_session_end_hook

    result = run_session_end_hook(tmp_path)
    session_id = result["session_id"]
    assert session_id, "run_session_end_hook must produce a non-empty session_id"

    receipt_path = _write_closeout_receipt(
        tmp_path,
        agent_id="test",
        trigger_mode="native_hook",
        entrypoint="governance_tools.session_closeout_entry",
        exit_code=0,
        closeout_artifact_path=None,
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="no_eligibility_trigger",
        session_id=session_id,
    )

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    human_output = format_human_result(result)

    # human output must contain the session_id line
    assert f"session_id={session_id}" in human_output
    # receipt must persist the same value
    assert payload["session_id"] == session_id
    # explicit equality proof: both ends of the authority chain carry the same id
    assert payload["session_id"] == result["session_id"]
