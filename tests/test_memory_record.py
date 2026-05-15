from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from governance_tools.memory_record import (
    WRITER_ID,
    append_session_derived_entry,
    build_memory_record_suggestion,
    build_session_derived_record,
)


def test_build_session_derived_record_includes_canonical_fields() -> None:
    record = build_session_derived_record(
        what_changed="changed",
        commit="abc1234",
        session_id="session-1",
        memory_binding="bound",
        test_evidence="ok",
        next_step="next",
    )
    assert record["memory_type"] == "session-derived"
    assert record["record_format_version"] == "1.0"
    assert record["writer"] == WRITER_ID
    assert record["commit_hash"] == "abc1234"


def test_append_session_derived_entry_writes_expected_lines(tmp_path: Path) -> None:
    record = build_session_derived_record(
        what_changed="changed",
        commit="abc1234",
        session_id="session-1",
        memory_binding="bound",
        test_evidence="ok",
        next_step="next",
    )
    output = append_session_derived_entry(project_root=tmp_path, record=record)
    text = output.read_text(encoding="utf-8")
    assert "- memory_type: session-derived" in text
    assert "record_format_version: 1.0" in text
    assert f"writer: {WRITER_ID}" in text
    assert "commit_hash: abc1234" in text


def test_cli_writes_canonical_entry(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_record.py",
            "--what-changed", "cli test change",
            "--next-step", "verify cli output",
            "--commit", "abc1234",
            "--session-id", "test-session-cli",
            "--test-evidence", "subprocess invocation ok",
            "--project-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "[memory_record] Written:" in result.stdout
    daily_files = list(tmp_path.glob("memory/*.md"))
    assert len(daily_files) == 1
    text = daily_files[0].read_text(encoding="utf-8")
    assert "- memory_type: session-derived" in text
    assert f"writer: {WRITER_ID}" in text
    assert "cli test change" in text
    assert "test-session-cli" in text
    assert "memory_binding: bound" in text


def test_build_memory_record_suggestion_returns_cli_command() -> None:
    cmd = build_memory_record_suggestion(
        what_changed="test change",
        commit="abc1234",
        session_id="session-1",
        next_step="verify",
    )
    assert cmd.startswith("python governance_tools/memory_record.py")
    assert "--what-changed" in cmd
    assert "--commit abc1234" in cmd
    assert "--session-id session-1" in cmd


def test_append_session_derived_entry_deduplicates_equivalent_content(tmp_path: Path) -> None:
    record_a = build_session_derived_record(
        what_changed="changed (session=session-a)",
        commit="abc1234",
        session_id="session-a",
        memory_binding="bound",
        test_evidence="same evidence",
        next_step="same next step",
    )
    record_b = build_session_derived_record(
        what_changed="changed (session=session-b)",
        commit="abc1234",
        session_id="session-b",
        memory_binding="bound",
        test_evidence="same evidence",
        next_step="same next step",
    )
    output = append_session_derived_entry(project_root=tmp_path, record=record_a)
    append_session_derived_entry(project_root=tmp_path, record=record_b)
    text = output.read_text(encoding="utf-8")
    assert text.count("- memory_type: session-derived") == 1
