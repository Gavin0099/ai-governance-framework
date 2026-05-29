"""
Tests for codeburn/phase2/claude_code_jsonl_ingestor.py

Covers:
  - ingest_claude_code_session: type=assistant rows admitted
  - ingest_claude_code_session: non-assistant rows skipped
  - ingest_claude_code_session: malformed JSON quarantined
  - ingest_claude_code_session: total_tokens always NULL (invariant)
  - ingest_claude_code_session: Class C provenance recorded
  - ingest_claude_code_session: missing usage fields → NULL (not 0)
  - find_claude_session_jsonl: returns None when ~/.claude/projects missing
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from codeburn.phase1.claude_log_ingestor import _ensure_schema
from codeburn.phase2.claude_code_jsonl_ingestor import (
    ClaudeCodeIngestResult,
    find_claude_session_jsonl,
    ingest_claude_code_session,
)

_SESSION_ID = "session-20260529T000000-test01"


def _make_db(tmp_path: Path) -> tuple[Path, sqlite3.Connection]:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    _ensure_schema(conn)
    conn.commit()
    return db_path, conn


def _write_jsonl(path: Path, lines: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(ln) for ln in lines) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# ingest_claude_code_session
# ---------------------------------------------------------------------------

class TestIngestBasic:
    def test_type_assistant_rows_admitted(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "timestamp": "2026-05-29T00:00:00Z",
             "message": {"usage": {"input_tokens": 100, "output_tokens": 20}}},
            {"type": "assistant", "uuid": "u2", "timestamp": "2026-05-29T00:01:00Z",
             "message": {"usage": {"input_tokens": 200, "output_tokens": 40}}},
        ])
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        assert result.records_admitted == 2
        assert result.records_skipped == 0
        assert result.records_quarantined == 0
        assert len(result.step_ids) == 2

    def test_non_assistant_rows_skipped(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "human", "text": "hello"},
            {"type": "tool_result", "content": "ok"},
            {"type": "system", "content": "prompt"},
            {"type": "assistant", "uuid": "u1", "message": {"usage": {"input_tokens": 50, "output_tokens": 10}}},
        ])
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        assert result.records_admitted == 1
        assert result.records_skipped == 3

    def test_malformed_json_quarantined(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = tmp_path / "t.jsonl"
        jl.write_text(
            '{"type":"assistant","uuid":"u1","message":{"usage":{"input_tokens":100,"output_tokens":20}}}\n'
            'NOT VALID JSON\n',
            encoding="utf-8",
        )
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        assert result.records_admitted == 1
        assert result.records_quarantined == 1
        rows = conn.execute("SELECT reason FROM quarantined_records").fetchall()
        assert any("json_parse_error" in r[0] for r in rows)

    def test_missing_message_quarantined(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1"},  # no message key
        ])
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        assert result.records_quarantined == 1
        assert result.records_admitted == 0


class TestInvariantTotalTokensNull:
    def test_total_tokens_always_null(self, tmp_path):
        """Invariant: total_tokens must always be NULL regardless of source data."""
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "message": {
                "usage": {"input_tokens": 100, "output_tokens": 20}
            }},
        ])
        ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        rows = conn.execute("SELECT total_tokens FROM steps WHERE session_id = ?", (_SESSION_ID,)).fetchall()
        assert len(rows) == 1
        assert rows[0][0] is None, "total_tokens must be NULL — billing computation forbidden"


class TestTokenValues:
    def test_prompt_and_completion_tokens_stored(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "message": {
                "usage": {"input_tokens": 300, "output_tokens": 60}
            }},
        ])
        ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        row = conn.execute(
            "SELECT prompt_tokens, completion_tokens FROM steps WHERE session_id = ?",
            (_SESSION_ID,),
        ).fetchone()
        assert row[0] == 300
        assert row[1] == 60

    def test_missing_usage_tokens_stored_as_null(self, tmp_path):
        """Missing token fields → NULL, never 0 (invariant I2)."""
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "message": {"usage": {}}},
        ])
        ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        row = conn.execute(
            "SELECT prompt_tokens, completion_tokens FROM steps WHERE session_id = ?",
            (_SESSION_ID,),
        ).fetchone()
        assert row[0] is None, "missing input_tokens must be NULL"
        assert row[1] is None, "missing output_tokens must be NULL"

    def test_no_usage_field_tokens_stored_as_null(self, tmp_path):
        """No usage dict → NULL tokens."""
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "message": {}},
        ])
        ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        row = conn.execute(
            "SELECT prompt_tokens, completion_tokens FROM steps WHERE session_id = ?",
            (_SESSION_ID,),
        ).fetchone()
        assert row[0] is None
        assert row[1] is None


class TestProvenance:
    def test_class_c_provenance_written(self, tmp_path):
        """Class C provenance row must be written for each admitted step."""
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "message": {
                "usage": {"input_tokens": 50, "output_tokens": 10}
            }},
        ])
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        assert len(result.step_ids) == 1
        prov = conn.execute(
            "SELECT epistemic_class, real_time_observed, analysis_safe_for_decision, "
            "provider_truthfulness_assumed FROM step_ingestion_provenance "
            "WHERE step_id = ?",
            (result.step_ids[0],),
        ).fetchone()
        assert prov is not None
        assert prov[0] == "Class C"
        assert prov[1] == 0
        assert prov[2] == 0
        assert prov[3] == 0

    def test_provider_is_claude_code(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = _write_jsonl(tmp_path / "t.jsonl", [
            {"type": "assistant", "uuid": "u1", "message": {
                "usage": {"input_tokens": 50, "output_tokens": 10}
            }},
        ])
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        row = conn.execute(
            "SELECT provider FROM steps WHERE step_id = ?",
            (result.step_ids[0],),
        ).fetchone()
        assert row[0] == "claude-code"


class TestValidation:
    def test_empty_session_id_raises(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = tmp_path / "t.jsonl"
        jl.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="session_id"):
            ingest_claude_code_session(str(jl), "", conn)

    def test_non_jsonl_extension_raises(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = tmp_path / "t.json"
        jl.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match=".jsonl"):
            ingest_claude_code_session(str(jl), _SESSION_ID, conn)

    def test_missing_file_raises(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        with pytest.raises(FileNotFoundError):
            ingest_claude_code_session(str(tmp_path / "missing.jsonl"), _SESSION_ID, conn)


class TestEmptyFile:
    def test_empty_file_succeeds_with_zero_counts(self, tmp_path):
        db_path, conn = _make_db(tmp_path)
        jl = tmp_path / "empty.jsonl"
        jl.write_text("", encoding="utf-8")
        result = ingest_claude_code_session(str(jl), _SESSION_ID, conn)
        assert isinstance(result, ClaudeCodeIngestResult)
        assert result.records_scanned == 0
        assert result.records_admitted == 0


# ---------------------------------------------------------------------------
# find_claude_session_jsonl
# ---------------------------------------------------------------------------

class TestFindClaudeSessionJsonl:
    def test_returns_none_when_projects_dir_missing(self, tmp_path):
        nonexistent = tmp_path / "no_such_dir"
        with mock.patch("codeburn.phase2.claude_code_jsonl_ingestor.Path") as mock_path_cls:
            # Make Path.home() / ".claude" / "projects" point to nonexistent
            mock_home = mock.MagicMock()
            mock_path_cls.home.return_value = mock_home
            mock_home.__truediv__.return_value = mock_home
            mock_home.is_dir.return_value = False
            result = find_claude_session_jsonl()
        assert result is None

    def test_returns_none_when_no_jsonl_files(self, tmp_path):
        projects_dir = tmp_path / ".claude" / "projects"
        projects_dir.mkdir(parents=True)
        # No .jsonl files in the dir
        with mock.patch(
            "codeburn.phase2.claude_code_jsonl_ingestor.Path.home",
            return_value=tmp_path,
        ):
            result = find_claude_session_jsonl()
        assert result is None

    def test_finds_by_session_id_stem(self, tmp_path):
        projects_dir = tmp_path / ".claude" / "projects" / "myproject"
        projects_dir.mkdir(parents=True)
        session_uuid = "abc-123-uuid"
        jl = projects_dir / f"{session_uuid}.jsonl"
        jl.write_text('{"type":"assistant"}\n', encoding="utf-8")
        with mock.patch(
            "codeburn.phase2.claude_code_jsonl_ingestor.Path.home",
            return_value=tmp_path,
        ):
            result = find_claude_session_jsonl(claude_session_id=session_uuid)
        assert result == jl

    def test_falls_back_to_most_recent_jsonl(self, tmp_path):
        import time
        projects_dir = tmp_path / ".claude" / "projects" / "myproject"
        projects_dir.mkdir(parents=True)
        old_jl = projects_dir / "old-session.jsonl"
        old_jl.write_text('{"type":"assistant"}\n', encoding="utf-8")
        time.sleep(0.05)  # ensure mtime difference
        new_jl = projects_dir / "new-session.jsonl"
        new_jl.write_text('{"type":"assistant"}\n', encoding="utf-8")
        with mock.patch(
            "codeburn.phase2.claude_code_jsonl_ingestor.Path.home",
            return_value=tmp_path,
        ):
            result = find_claude_session_jsonl()
        assert result == new_jl
