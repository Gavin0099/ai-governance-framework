from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "codeburn"
    / "phase2"
    / "examples"
    / "codex_smoke_fixture.jsonl"
)
SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = tmp_path / "codex_smoke.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return db_path


def test_p54_smoke_runs_and_returns_fixed_output_keys(tmp_db):
    from codeburn.phase2.codeburn_codex_smoke import run_smoke

    exit_code, summary = run_smoke(
        artifact_path=FIXTURE_PATH,
        db_path=tmp_db,
        session_id="codex-smoke-test-001",
    )

    assert exit_code == 0
    assert set(summary.keys()) == {
        "processed_records",
        "skipped_records",
        "quarantined_records",
        "provenance_rows_written",
        "incomplete_token_records",
        "sqlite_surface_rejected",
        "authority_flags_all_false",
    }


def test_p54_smoke_counts_match_fixture(tmp_db):
    from codeburn.phase2.codeburn_codex_smoke import run_smoke

    exit_code, summary = run_smoke(
        artifact_path=FIXTURE_PATH,
        db_path=tmp_db,
        session_id="codex-smoke-test-002",
    )
    assert exit_code == 0
    assert summary["processed_records"] == 2
    assert summary["skipped_records"] == 3
    assert summary["quarantined_records"] == 1
    assert summary["provenance_rows_written"] == 2
    assert summary["incomplete_token_records"] == 0


def test_p54_smoke_rejects_sqlite_surface_and_preserves_authority_flags(tmp_db):
    from codeburn.phase2.codeburn_codex_smoke import run_smoke

    exit_code, summary = run_smoke(
        artifact_path=FIXTURE_PATH,
        db_path=tmp_db,
        session_id="codex-smoke-test-003",
    )
    assert exit_code == 0
    assert summary["sqlite_surface_rejected"] is True
    assert summary["authority_flags_all_false"] is True


def test_p54_smoke_boundary_assertions_not_violated(tmp_db):
    from codeburn.phase2.codeburn_codex_smoke import run_smoke

    exit_code, _summary = run_smoke(
        artifact_path=FIXTURE_PATH,
        db_path=tmp_db,
        session_id="codex-smoke-test-004",
    )
    assert exit_code == 0

    conn = sqlite3.connect(str(tmp_db))
    rows = conn.execute(
        """
        SELECT prompt_tokens, completion_tokens, total_tokens
        FROM steps
        WHERE session_id = 'codex-smoke-test-004' AND provider = 'codex'
        ORDER BY started_at, rowid
        """
    ).fetchall()
    conn.close()

    assert len(rows) == 2
    # reasoning_output_tokens not folded into output_tokens (80 expected, not 120)
    assert rows[0][1] == 80
    # total_token_usage not consumed as turn-scoped evidence (1200 expected, not 2200)
    assert rows[1][0] == 1200
    # total_tokens always NULL per IAF-3
    assert rows[0][2] is None and rows[1][2] is None


def test_p54_smoke_is_deterministic_for_same_fixture(tmp_db):
    from codeburn.phase2.codeburn_codex_smoke import run_smoke

    code1, summary1 = run_smoke(FIXTURE_PATH, tmp_db, "codex-smoke-test-005-a")
    code2, summary2 = run_smoke(FIXTURE_PATH, tmp_db, "codex-smoke-test-005-b")

    assert code1 == 0 and code2 == 0
    assert summary1 == summary2
