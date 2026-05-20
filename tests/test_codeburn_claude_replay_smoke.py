"""
CodeBurn Claude Replay Smoke Tests (P4.5)

Tests for the replay smoke command:
  1. Exits 0 on the built-in fixture (REPLAY_SMOKE_OK)
  2. Exits 1 on missing file (system error)
  3. Reports invariant stability
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "codeburn" / "phase1" / "examples" / "claude_smoke_fixture.jsonl"
)
SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = tmp_path / "replay_smoke_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("""
        INSERT INTO sessions(
            session_id, task, created_at, data_quality,
            comparability_token, comparability_duration, comparability_change
        ) VALUES('replay-smoke-test-001','replay-smoke','2026-05-20','complete',0,1,1)
    """)
    conn.commit()
    conn.close()
    return db_path


class TestReplaySmokeOperability:
    def test_replay_smoke_exits_0_on_fixture(self, tmp_db):
        from codeburn.phase1.codeburn_claude_replay_smoke import run_replay_smoke
        exit_code = run_replay_smoke(
            artifact_path=FIXTURE_PATH,
            db_path=tmp_db,
            session_id="replay-smoke-test-001",
            verbose=False,
        )
        assert exit_code == 0, f"replay smoke returned {exit_code}, expected 0 (REPLAY_SMOKE_OK)"

    def test_replay_smoke_exits_1_on_missing_file(self, tmp_db):
        from codeburn.phase1.codeburn_claude_replay_smoke import run_replay_smoke
        exit_code = run_replay_smoke(
            artifact_path=Path("/nonexistent/path/session.jsonl"),
            db_path=tmp_db,
            session_id="replay-smoke-test-001",
            verbose=False,
        )
        assert exit_code == 1, f"missing file should return 1, got {exit_code}"

    def test_replay_smoke_verbose_exits_0(self, tmp_db):
        from codeburn.phase1.codeburn_claude_replay_smoke import run_replay_smoke
        exit_code = run_replay_smoke(
            artifact_path=FIXTURE_PATH,
            db_path=tmp_db,
            session_id="replay-smoke-test-001",
            verbose=True,
        )
        assert exit_code == 0
