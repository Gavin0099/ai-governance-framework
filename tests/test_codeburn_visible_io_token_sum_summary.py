from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from codeburn.phase2.visible_io_token_sum_summary import (
    build_same_provider_visible_io_token_sum_summary,
)


ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "codeburn" / "phase1" / "schema.sql"


def _make_db(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "visible_io.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def _insert_session(conn: sqlite3.Connection, session_id: str = "s1") -> None:
    conn.execute(
        """
        INSERT INTO sessions(session_id, task, created_at, data_quality)
        VALUES(?, 'visible-io-test', '2026-06-05T00:00:00Z', 'partial')
        """,
        (session_id,),
    )


def _insert_step(
    conn: sqlite3.Connection,
    *,
    step_id: str,
    provider: str,
    session_id: str = "s1",
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> None:
    conn.execute(
        """
        INSERT INTO steps(
            step_id, session_id, step_kind, command, started_at, provider,
            prompt_tokens, completion_tokens, total_tokens, token_source
        ) VALUES(?, ?, 'other', 'seed', ?, ?, ?, ?, NULL, 'estimated')
        """,
        (
            step_id,
            session_id,
            f"2026-06-05T00:00:0{step_id[-1]}Z",
            provider,
            prompt_tokens,
            completion_tokens,
        ),
    )


def test_summary_computes_visible_io_sum_for_codex_same_provider_rows(tmp_path):
    conn = _make_db(tmp_path)
    _insert_session(conn)
    _insert_step(conn, step_id="c1", provider="codex", prompt_tokens=100, completion_tokens=20)
    _insert_step(conn, step_id="c2", provider="codex", prompt_tokens=50, completion_tokens=5)
    _insert_step(conn, step_id="x1", provider="claude-code", prompt_tokens=999, completion_tokens=999)

    summary = build_same_provider_visible_io_token_sum_summary(conn, provider="codex")

    assert summary["provider"] == "codex"
    assert summary["visible_io_token_sum"] == 175
    assert summary["prompt_tokens_observed"] == 150
    assert summary["completion_tokens_observed"] == 25
    assert summary["row_count"] == 2
    assert summary["cross_provider_comparable"] is False
    assert "total_tokens" not in summary


def test_summary_computes_visible_io_sum_for_claude_code_same_provider_rows(tmp_path):
    conn = _make_db(tmp_path)
    _insert_session(conn)
    _insert_step(conn, step_id="h1", provider="claude-code", prompt_tokens=300, completion_tokens=60)

    summary = build_same_provider_visible_io_token_sum_summary(conn, provider="claude-code")

    assert summary["visible_io_token_sum"] == 360
    assert summary["evidence_class"] == "Class C"
    assert summary["billing_truth"] is False
    assert summary["decision_usage_allowed"] is False
    assert summary["analysis_safe_for_decision"] is False
    assert summary["efficiency_inference_allowed"] is False


def test_summary_keeps_visible_sum_null_when_prompt_or_completion_missing(tmp_path):
    conn = _make_db(tmp_path)
    _insert_session(conn)
    _insert_step(conn, step_id="c1", provider="codex", prompt_tokens=None, completion_tokens=42)

    summary = build_same_provider_visible_io_token_sum_summary(conn, provider="codex")

    assert summary["visible_io_token_sum"] is None
    assert summary["prompt_tokens_observed"] is None
    assert summary["completion_tokens_observed"] is None
    assert summary["missing_field_policy"] == "null_not_zero"
    assert summary["missing_field_reason"] == "prompt_tokens_missing"


def test_summary_supports_optional_session_scope_without_cross_provider_rollup(tmp_path):
    conn = _make_db(tmp_path)
    _insert_session(conn, "s1")
    _insert_session(conn, "s2")
    _insert_step(conn, step_id="c1", session_id="s1", provider="codex", prompt_tokens=10, completion_tokens=1)
    _insert_step(conn, step_id="c2", session_id="s2", provider="codex", prompt_tokens=100, completion_tokens=10)

    summary = build_same_provider_visible_io_token_sum_summary(
        conn,
        provider="codex",
        session_id="s1",
    )

    assert summary["session_id"] == "s1"
    assert summary["visible_io_token_sum"] == 11
    assert summary["row_count"] == 1


def test_summary_rejects_unsupported_provider_scope(tmp_path):
    conn = _make_db(tmp_path)

    with pytest.raises(ValueError, match="provider must be one of"):
        build_same_provider_visible_io_token_sum_summary(conn, provider="all")

