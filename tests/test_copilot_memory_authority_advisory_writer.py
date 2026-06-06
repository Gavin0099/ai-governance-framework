from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.copilot_memory_authority_advisory_writer import (
    SCHEMA,
    WRITER_ID,
    write_advisory,
)


def _base_kwargs(output_dir: Path) -> dict:
    return {
        "output_dir": output_dir,
        "session_id": "test-session-001",
        "date": "2026-06-06",
        "agent": "copilot",
        "repo": "gl_electron_tool",
        "active_non_canonical_writer_count": 1,
        "canonical_writer_used": "no",
        "manual_write_detected": "unknown",
        "evidence_source": "pasted_response",
        "confidence": "medium",
        "disposition": "advisory_warning",
    }


def test_write_advisory_creates_file(tmp_path: Path) -> None:
    ok, path, errors = write_advisory(**_base_kwargs(tmp_path))

    assert ok is True
    assert errors == []
    assert path is not None
    assert path.exists()
    assert path.name.startswith("copilot-memory-authority-advisory-")
    assert path.suffix == ".json"


def test_artifact_fields_are_correct(tmp_path: Path) -> None:
    ok, path, _ = write_advisory(**_base_kwargs(tmp_path))

    assert ok is True
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["schema"] == SCHEMA
    assert artifact["writer"] == WRITER_ID
    assert artifact["session_id"] == "test-session-001"
    assert artifact["agent"] == "copilot"
    assert artifact["repo"] == "gl_electron_tool"
    assert artifact["active_non_canonical_writer"]["count"] == 1
    assert artifact["canonical_writer_used"] == "no"
    assert artifact["manual_write_detected"] == "unknown"
    assert artifact["evidence_source"] == "pasted_response"
    assert artifact["confidence"] == "medium"
    assert artifact["disposition"] == "advisory_warning"
    assert artifact["blocking_gate_enabled"] is False


def test_blocking_gate_is_always_false(tmp_path: Path) -> None:
    for disposition in ("advisory_warning", "observe_only", "escalate"):
        kwargs = _base_kwargs(tmp_path)
        kwargs["session_id"] = f"s-{disposition}"
        kwargs["disposition"] = disposition
        ok, path, _ = write_advisory(**kwargs)
        assert ok is True
        artifact = json.loads(path.read_text(encoding="utf-8"))
        assert artifact["blocking_gate_enabled"] is False


def test_rejects_empty_session_id(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    kwargs["session_id"] = "  "
    ok, path, errors = write_advisory(**kwargs)
    assert ok is False
    assert any("session_id" in e for e in errors)


def test_rejects_invalid_date(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    kwargs["date"] = "not-a-date"
    ok, path, errors = write_advisory(**kwargs)
    assert ok is False
    assert any("date" in e for e in errors)


def test_rejects_negative_count(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    kwargs["active_non_canonical_writer_count"] = -1
    ok, path, errors = write_advisory(**kwargs)
    assert ok is False
    assert any("count" in e for e in errors)


def test_rejects_invalid_disposition(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    kwargs["disposition"] = "block_immediately"
    ok, path, errors = write_advisory(**kwargs)
    assert ok is False
    assert any("disposition" in e for e in errors)


def test_zero_count_observe_only_is_valid(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    kwargs["active_non_canonical_writer_count"] = 0
    kwargs["disposition"] = "observe_only"
    kwargs["canonical_writer_used"] = "yes"
    ok, path, errors = write_advisory(**kwargs)
    assert ok is True
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["active_non_canonical_writer"]["count"] == 0


def test_notes_optional(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    ok, path, _ = write_advisory(**kwargs)
    assert ok is True
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["notes"] == ""

    kwargs2 = _base_kwargs(tmp_path)
    kwargs2["session_id"] = "test-session-002"
    kwargs2["notes"] = "manual review confirms canonical writer absent"
    ok2, path2, _ = write_advisory(**kwargs2)
    assert ok2 is True
    artifact2 = json.loads(path2.read_text(encoding="utf-8"))
    assert "canonical writer absent" in artifact2["notes"]
