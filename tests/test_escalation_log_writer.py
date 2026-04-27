"""
Tests for governance_tools/escalation_log_writer.py.

Slice 1 — Log writer identity:
  append_escalation_log_entry, assess_log_writer_integrity

Slice 2 — Companion escalation register:
  write_escalation_register, assess_escalation_register
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from governance_tools.escalation_log_writer import (
    LOG_WRITER_ID,
    LOG_WRITER_VERSION,
    REGISTER_SCHEMA,
    REGISTER_WRITER_ID,
    REGISTER_WRITER_VERSION,
    append_escalation_log_entry,
    assess_escalation_register,
    assess_log_writer_integrity,
    write_escalation_register,
)


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_escalation_log_writer" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


# ---------------------------------------------------------------------------
# Slice 1: append_escalation_log_entry
# ---------------------------------------------------------------------------


def test_append_injects_writer_identity():
    d = _tmp_dir("append_injects_identity")
    log_path = d / "test.jsonl"
    entry = {"escalation_id": "esc-001", "status": "triaged"}

    result = append_escalation_log_entry(log_path, entry)

    assert result["_writer_id"] == LOG_WRITER_ID
    assert result["_writer_version"] == LOG_WRITER_VERSION
    assert "_written_at" in result
    assert result["escalation_id"] == "esc-001"


def test_append_writes_valid_jsonl_line():
    d = _tmp_dir("append_writes_jsonl")
    log_path = d / "test.jsonl"
    entry = {"escalation_id": "esc-001"}

    append_escalation_log_entry(log_path, entry)

    lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["escalation_id"] == "esc-001"
    assert parsed["_writer_id"] == LOG_WRITER_ID


def test_append_rejects_caller_set_writer_id():
    d = _tmp_dir("append_rejects_caller_writer_id")
    log_path = d / "test.jsonl"
    entry = {"escalation_id": "esc-001", "_writer_id": "someone.else"}

    with pytest.raises(ValueError, match="_writer_id"):
        append_escalation_log_entry(log_path, entry)


def test_append_rejects_caller_set_writer_version():
    d = _tmp_dir("append_rejects_caller_writer_version")
    log_path = d / "test.jsonl"
    entry = {"escalation_id": "esc-001", "_writer_version": "99.9"}

    with pytest.raises(ValueError, match="_writer_version"):
        append_escalation_log_entry(log_path, entry)


def test_append_creates_parent_directories():
    d = _tmp_dir("append_creates_parents")
    log_path = d / "sub" / "deep" / "test.jsonl"
    entry = {"escalation_id": "esc-001"}

    append_escalation_log_entry(log_path, entry)

    assert log_path.is_file()


def test_append_multiple_entries_accumulate():
    d = _tmp_dir("append_multiple")
    log_path = d / "test.jsonl"

    append_escalation_log_entry(log_path, {"escalation_id": "esc-001"})
    append_escalation_log_entry(log_path, {"escalation_id": "esc-002"})

    lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# Slice 1: assess_log_writer_integrity
# ---------------------------------------------------------------------------


def test_integrity_absent_log_returns_log_absent():
    d = _tmp_dir("integrity_absent")
    log_path = d / "nonexistent.jsonl"

    result = assess_log_writer_integrity(log_path)

    assert result["exists"] is False
    assert result["ok"] is False
    assert result["writer_integrity"] == "log_absent"
    assert result["release_blocked"] is False  # absence handled by assess_authority_directory


def test_integrity_all_trusted_entries():
    d = _tmp_dir("integrity_trusted")
    log_path = d / "test.jsonl"
    append_escalation_log_entry(log_path, {"escalation_id": "esc-001"})
    append_escalation_log_entry(log_path, {"escalation_id": "esc-002"})

    result = assess_log_writer_integrity(log_path)

    assert result["ok"] is True
    assert result["writer_integrity"] == "trusted"
    assert result["trusted_entry_count"] == 2
    assert result["legacy_entry_count"] == 0
    assert result["untrusted_entry_count"] == 0
    assert result["release_blocked"] is False


def test_integrity_legacy_entries_not_fail_closed():
    """Entries without _writer_id are pre-hardening legacy — ok=True, not fail-closed."""
    d = _tmp_dir("integrity_legacy")
    log_path = d / "test.jsonl"
    log_path.write_text(
        json.dumps({"escalation_id": "esc-001"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = assess_log_writer_integrity(log_path)

    assert result["ok"] is True
    assert result["writer_integrity"] == "legacy_only"
    assert result["legacy_entry_count"] == 1
    assert result["trusted_entry_count"] == 0
    assert result["release_blocked"] is False


def test_integrity_untrusted_writer_id_is_fail_closed():
    """Entries with a non-trusted _writer_id → untrusted_present → ok=False."""
    d = _tmp_dir("integrity_untrusted")
    log_path = d / "test.jsonl"
    log_path.write_text(
        json.dumps({"escalation_id": "esc-001", "_writer_id": "evil.writer"}) + "\n",
        encoding="utf-8",
    )

    result = assess_log_writer_integrity(log_path)

    assert result["ok"] is False
    assert result["writer_integrity"] == "untrusted_present"
    assert result["untrusted_entry_count"] == 1
    assert result["release_blocked"] is True
    assert "log_entries_with_untrusted_writer_id" in result["release_block_reasons"]


def test_integrity_mixed_trusted_and_legacy():
    """Trusted + legacy entries → legacy_only (any legacy prevents 'trusted' label)."""
    d = _tmp_dir("integrity_mixed_trusted_legacy")
    log_path = d / "test.jsonl"
    # Write a legacy entry (no _writer_id)
    log_path.write_text(
        json.dumps({"escalation_id": "esc-001"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # Append a canonical trusted entry
    append_escalation_log_entry(log_path, {"escalation_id": "esc-002"})

    result = assess_log_writer_integrity(log_path)

    assert result["ok"] is True
    assert result["writer_integrity"] == "legacy_only"  # legacy present → not "trusted"
    assert result["trusted_entry_count"] == 1
    assert result["legacy_entry_count"] == 1
    assert result["release_blocked"] is False


def test_integrity_entry_count_matches_total():
    d = _tmp_dir("integrity_entry_count")
    log_path = d / "test.jsonl"
    append_escalation_log_entry(log_path, {"escalation_id": "esc-001"})
    append_escalation_log_entry(log_path, {"escalation_id": "esc-002"})
    append_escalation_log_entry(log_path, {"escalation_id": "esc-003"})

    result = assess_log_writer_integrity(log_path)

    assert result["entry_count"] == 3


# ---------------------------------------------------------------------------
# Slice 2: write_escalation_register
# ---------------------------------------------------------------------------


def test_write_register_creates_valid_json():
    d = _tmp_dir("write_register")
    register_path = d / "register.json"
    ids = ["esc-001", "esc-002"]

    result = write_escalation_register(register_path, ids)

    assert register_path.is_file()
    on_disk = json.loads(register_path.read_text(encoding="utf-8"))
    assert on_disk["register_schema"] == REGISTER_SCHEMA
    assert on_disk["writer_id"] == REGISTER_WRITER_ID
    assert on_disk["writer_version"] == REGISTER_WRITER_VERSION
    assert on_disk["active_escalation_ids"] == ids
    assert on_disk["active_case_count"] == 2
    assert result == on_disk


def test_write_register_deduplicates_ids():
    d = _tmp_dir("write_register_dedup")
    register_path = d / "register.json"

    write_escalation_register(register_path, ["esc-001", "esc-002", "esc-001"])
    on_disk = json.loads(register_path.read_text(encoding="utf-8"))

    assert on_disk["active_escalation_ids"] == ["esc-001", "esc-002"]
    assert on_disk["active_case_count"] == 2


def test_write_register_empty_list_is_valid():
    d = _tmp_dir("write_register_empty")
    register_path = d / "register.json"

    write_escalation_register(register_path, [])
    on_disk = json.loads(register_path.read_text(encoding="utf-8"))

    assert on_disk["active_escalation_ids"] == []
    assert on_disk["active_case_count"] == 0


def test_write_register_rejects_non_list():
    d = _tmp_dir("write_register_non_list")
    register_path = d / "register.json"

    with pytest.raises(ValueError, match="list"):
        write_escalation_register(register_path, "esc-001")  # type: ignore[arg-type]


def test_write_register_creates_parent_directories():
    d = _tmp_dir("write_register_parents")
    register_path = d / "sub" / "deep" / "register.json"

    write_escalation_register(register_path, ["esc-001"])

    assert register_path.is_file()


# ---------------------------------------------------------------------------
# Slice 2: assess_escalation_register
# ---------------------------------------------------------------------------


def test_assess_register_absent_returns_not_available_ok_true():
    d = _tmp_dir("assess_register_absent")
    register_path = d / "nonexistent.json"

    result = assess_escalation_register(register_path)

    assert result["available"] is False
    assert result["ok"] is True
    assert result["escalation_active"] is False
    assert result["release_blocked"] is False


def test_assess_register_trusted_with_active_ids():
    d = _tmp_dir("assess_register_active")
    register_path = d / "register.json"
    write_escalation_register(register_path, ["esc-001"])

    result = assess_escalation_register(register_path)

    assert result["available"] is True
    assert result["ok"] is True
    assert result["trusted_writer"] is True
    assert result["active_escalation_ids"] == ["esc-001"]
    assert result["active_case_count"] == 1
    assert result["escalation_active"] is True
    assert result["release_blocked"] is False


def test_assess_register_trusted_with_empty_ids():
    d = _tmp_dir("assess_register_empty_ids")
    register_path = d / "register.json"
    write_escalation_register(register_path, [])

    result = assess_escalation_register(register_path)

    assert result["available"] is True
    assert result["ok"] is True
    assert result["escalation_active"] is False
    assert result["release_blocked"] is False


def test_assess_register_untrusted_writer_fails_closed():
    d = _tmp_dir("assess_register_untrusted")
    register_path = d / "register.json"
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

    result = assess_escalation_register(register_path)

    assert result["available"] is True
    assert result["ok"] is False
    assert result["trusted_writer"] is False
    assert result["release_blocked"] is True
    assert "register_writer_untrusted" in result["release_block_reasons"]


def test_assess_register_invalid_json_fails_closed():
    d = _tmp_dir("assess_register_invalid_json")
    register_path = d / "register.json"
    register_path.write_text("not valid json", encoding="utf-8")

    result = assess_escalation_register(register_path)

    assert result["available"] is True
    assert result["ok"] is False
    assert result["release_blocked"] is True


def test_assess_register_wrong_schema_fails_closed():
    d = _tmp_dir("assess_register_wrong_schema")
    register_path = d / "register.json"
    register_path.write_text(
        json.dumps(
            {
                "register_schema": "some.other.schema.v99",
                "writer_id": REGISTER_WRITER_ID,
                "writer_version": REGISTER_WRITER_VERSION,
                "written_at": "2026-04-27T00:00:00+00:00",
                "active_escalation_ids": ["esc-001"],
                "active_case_count": 1,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_escalation_register(register_path)

    assert result["ok"] is False
    assert result["trusted_writer"] is False
    assert result["release_blocked"] is True
