from __future__ import annotations

import sqlite3
from argparse import Namespace
from pathlib import Path

from codeburn.phase1 import codeburn_session


def _start(db_path: Path, schema_path: Path, repo: Path, task: str, action: str, timeout_min: int = 60) -> int:
    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        operator="test",
        cmd="session-start",
        task=task,
        idle_timeout_minutes=timeout_min,
        open_session_action=action,
    )
    return codeburn_session.session_start(args)


def test_open_session_auto_close_previous(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    repo = Path(".").resolve()
    assert _start(db_path, schema_path, repo, "s1", "auto_close_previous") == 0
    assert _start(db_path, schema_path, repo, "s2", "auto_close_previous") == 0

    conn = sqlite3.connect(db_path)
    sessions = conn.execute("SELECT task, ended_by, data_quality, ended_at FROM sessions ORDER BY created_at").fetchall()
    assert len(sessions) == 2
    assert sessions[0][0] == "s1"
    assert sessions[0][1] == "auto_close_previous"
    assert sessions[0][2] == "recovered"
    assert sessions[0][3] is not None
    events = conn.execute("SELECT action_taken FROM recovery_events").fetchall()
    assert events and events[0][0] == "auto_close_previous"
    conn.close()


def test_open_session_resume_previous(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    repo = Path(".").resolve()
    assert _start(db_path, schema_path, repo, "s1", "auto_close_previous") == 0
    assert _start(db_path, schema_path, repo, "s2", "resume_previous") == 0

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert count == 1
    row = conn.execute("SELECT task, data_quality, ended_at FROM sessions").fetchone()
    assert row[0] == "s1"
    assert row[1] == "recovered"
    assert row[2] is None
    evt = conn.execute("SELECT action_taken, new_session_id FROM recovery_events ORDER BY id DESC LIMIT 1").fetchone()
    assert evt[0] == "resume_previous"
    assert evt[1] is not None
    conn.close()


def test_open_session_abort_start(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    repo = Path(".").resolve()
    assert _start(db_path, schema_path, repo, "s1", "auto_close_previous") == 0
    assert _start(db_path, schema_path, repo, "s2", "abort_start") == 1

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert count == 1
    evt = conn.execute("SELECT action_taken FROM recovery_events ORDER BY id DESC LIMIT 1").fetchone()
    assert evt[0] == "abort_start"
    conn.close()


def test_idle_timeout_exceeded_auto_close_and_event(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    repo = Path(".").resolve()
    assert _start(db_path, schema_path, repo, "s1", "auto_close_previous") == 0
    assert _start(db_path, schema_path, repo, "s2", "auto_close_previous", timeout_min=0) == 0

    conn = sqlite3.connect(db_path)
    first = conn.execute("SELECT ended_by, data_quality FROM sessions ORDER BY created_at LIMIT 1").fetchone()
    assert first[0] == "idle_timeout"
    assert first[1] == "partial"
    evt = conn.execute("SELECT action_taken, reason FROM recovery_events ORDER BY id LIMIT 1").fetchone()
    assert evt[0] == "auto_close_previous"
    assert "idle-timeout" in evt[1]
    conn.close()
