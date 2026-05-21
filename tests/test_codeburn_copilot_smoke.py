from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "codeburn"
    / "phase2"
    / "examples"
    / "copilot_smoke_fixture.csv"
)


@pytest.fixture()
def tmp_db(tmp_path):
    return tmp_path / "copilot_smoke.db"


def test_smoke_runs_and_returns_fixed_output_keys(tmp_db):
    from codeburn.phase2.codeburn_copilot_smoke import run_smoke

    exit_code, summary = run_smoke(FIXTURE_PATH, tmp_db, mark_final=False)

    assert exit_code == 0
    assert set(summary.keys()) == {
        "processed_rows",
        "inserted_events",
        "skipped_duplicates",
        "quarantined_rows",
        "preview_events",
        "final_events",
        "authority_flags_all_false",
    }


def test_smoke_counts_preview_mode(tmp_db):
    from codeburn.phase2.codeburn_copilot_smoke import run_smoke

    exit_code, summary = run_smoke(FIXTURE_PATH, tmp_db, mark_final=False)

    assert exit_code == 0
    assert summary["processed_rows"] == 5
    assert summary["inserted_events"] == 2
    assert summary["skipped_duplicates"] == 1
    assert summary["quarantined_rows"] == 2
    assert summary["preview_events"] == 2
    assert summary["final_events"] == 0
    assert summary["authority_flags_all_false"] is True


def test_smoke_mark_final_converts_existing_preview_rows(tmp_db):
    from codeburn.phase2.codeburn_copilot_smoke import run_smoke

    code1, summary1 = run_smoke(FIXTURE_PATH, tmp_db, mark_final=False)
    code2, summary2 = run_smoke(FIXTURE_PATH, tmp_db, mark_final=True)

    assert code1 == 0 and code2 == 0
    assert summary1["preview_events"] == 2
    assert summary2["preview_events"] == 0
    assert summary2["final_events"] == 2


def test_smoke_deterministic_for_fresh_db_runs(tmp_path):
    from codeburn.phase2.codeburn_copilot_smoke import run_smoke

    db1 = tmp_path / "a.db"
    db2 = tmp_path / "b.db"

    code1, summary1 = run_smoke(FIXTURE_PATH, db1, mark_final=False)
    code2, summary2 = run_smoke(FIXTURE_PATH, db2, mark_final=False)

    assert code1 == 0 and code2 == 0
    assert summary1 == summary2


def test_smoke_does_not_write_session_or_step_provenance(tmp_db):
    from codeburn.phase2.codeburn_copilot_smoke import run_smoke

    code, _summary = run_smoke(FIXTURE_PATH, tmp_db, mark_final=False)
    assert code == 0

    conn = sqlite3.connect(str(tmp_db))
    sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    steps = conn.execute("SELECT COUNT(*) FROM steps").fetchone()[0]
    provenance = conn.execute("SELECT COUNT(*) FROM step_ingestion_provenance").fetchone()[0]
    conn.close()

    assert sessions == 0
    assert steps == 0
    assert provenance == 0
