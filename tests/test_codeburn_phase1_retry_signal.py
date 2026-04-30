from __future__ import annotations

import sqlite3
from argparse import Namespace
from pathlib import Path

from codeburn.phase1 import codeburn_run


def _seed_db(db_path: Path, schema_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO sessions(session_id, task, repo_path, git_branch, created_at, data_quality)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        ("s1", "retry", ".", "main", "2026-04-30T00:00:00+00:00", "complete"),
    )
    conn.commit()
    conn.close()


def _insert_step(conn: sqlite3.Connection, step_id: str, step_kind: str, retry_of: str | None, started_at: str) -> None:
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, retry_of, git_status_before, git_status_after
        ) VALUES(?, 's1', ?, 'cmd', 'local', ?, ?, 10, 1, 0, 1, 'unknown', ?, '', '')
        """,
        (step_id, step_kind, started_at, started_at, retry_of),
    )


def test_retry_signal_medium_without_changed_files(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _seed_db(db_path, schema_path)

    conn = sqlite3.connect(db_path)
    _insert_step(conn, "st1", "retry", None, "2026-04-30T00:00:01+00:00")
    _insert_step(conn, "st2", "retry", None, "2026-04-30T00:00:02+00:00")
    _insert_step(conn, "st3", "retry", None, "2026-04-30T00:00:03+00:00")
    conn.commit()
    codeburn_run._maybe_emit_retry_signal(conn, "s1", "st3")
    row = conn.execute(
        "SELECT signal, advisory_only, can_block, confidence FROM signals WHERE step_id='st3'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "retry_pattern_detected"
    assert row[1] == 1
    assert row[2] == 0
    assert row[3] == "medium"


def test_retry_signal_low_with_changed_files(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _seed_db(db_path, schema_path)

    conn = sqlite3.connect(db_path)
    _insert_step(conn, "st1", "retry", None, "2026-04-30T00:00:01+00:00")
    _insert_step(conn, "st2", "retry", None, "2026-04-30T00:00:02+00:00")
    _insert_step(conn, "st3", "retry", None, "2026-04-30T00:00:03+00:00")
    conn.execute(
        "INSERT INTO changed_files(step_id, file_path, change_kind, source) VALUES('st2', 'a.txt', 'modified', 'git_diff_name_only')"
    )
    conn.commit()
    codeburn_run._maybe_emit_retry_signal(conn, "s1", "st3")
    row = conn.execute("SELECT confidence FROM signals WHERE step_id='st3'").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "low"


def test_retry_signal_supports_retry_of_sequence(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _seed_db(db_path, schema_path)
    conn = sqlite3.connect(db_path)
    _insert_step(conn, "st1", "execution", "x1", "2026-04-30T00:00:01+00:00")
    _insert_step(conn, "st2", "execution", "x2", "2026-04-30T00:00:02+00:00")
    _insert_step(conn, "st3", "execution", "x3", "2026-04-30T00:00:03+00:00")
    conn.commit()
    codeburn_run._maybe_emit_retry_signal(conn, "s1", "st3")
    row = conn.execute("SELECT COUNT(*) FROM signals").fetchone()
    conn.close()
    assert row[0] == 1


def test_retry_fallback_inferred_for_implicit_execution_retries(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _seed_db(db_path, schema_path)
    conn = sqlite3.connect(db_path)
    _insert_step(conn, "st1", "execution", None, "2026-04-30T00:00:01+00:00")
    _insert_step(conn, "st2", "execution", None, "2026-04-30T00:00:02+00:00")
    _insert_step(conn, "st3", "execution", None, "2026-04-30T00:00:03+00:00")
    conn.execute("UPDATE steps SET command='pytest -q', exit_code=1 WHERE step_id IN ('st1','st2','st3')")
    conn.commit()
    codeburn_run._maybe_emit_retry_fallback_signal(conn, "s1", "st3")
    row = conn.execute(
        "SELECT signal, advisory_only, can_block, confidence, source FROM signals WHERE step_id='st3'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "retry_pattern_inferred"
    assert row[1] == 1
    assert row[2] == 0
    assert row[3] == "low"
    assert row[4] == "phase1_fallback"
