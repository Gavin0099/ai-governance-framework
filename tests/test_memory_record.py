from __future__ import annotations

from pathlib import Path

from governance_tools.memory_record import (
    WRITER_ID,
    append_session_derived_entry,
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
