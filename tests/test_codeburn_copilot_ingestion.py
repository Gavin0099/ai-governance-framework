from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from codeburn.phase2.copilot_billing_ingestor import ingest_copilot_csv

FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "codeburn"
    / "phase2"
    / "examples"
    / "copilot_smoke_fixture.csv"
)
SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"


@pytest.fixture()
def conn(tmp_path):
    db = tmp_path / "copilot_ingestion.db"
    c = sqlite3.connect(str(db))
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c.commit()
    try:
        yield c
    finally:
        c.close()


def test_cp1_pricing_rate_forbidden(conn):
    with pytest.raises(ValueError, match="CP-1 violation"):
        ingest_copilot_csv(str(FIXTURE_PATH), conn, model_pricing_rate=0.002)


def test_cp2_no_session_level_provenance_written(conn):
    ingest_copilot_csv(str(FIXTURE_PATH), conn, mark_final=False)

    sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    steps = conn.execute("SELECT COUNT(*) FROM steps").fetchone()[0]
    prov = conn.execute("SELECT COUNT(*) FROM step_ingestion_provenance").fetchone()[0]

    assert sessions == 0
    assert steps == 0
    assert prov == 0


def test_cp3_preview_and_mark_final_behavior(conn):
    # First pass: preview
    result1 = ingest_copilot_csv(str(FIXTURE_PATH), conn, mark_final=False)
    assert result1.rows_scanned == 5
    assert result1.rows_admitted == 2
    assert result1.rows_skipped_duplicate == 1
    assert result1.rows_quarantined == 2

    preview = conn.execute(
        "SELECT COUNT(*) FROM copilot_billing_events WHERE is_preview = 1"
    ).fetchone()[0]
    final = conn.execute(
        "SELECT COUNT(*) FROM copilot_billing_events WHERE is_preview = 0"
    ).fetchone()[0]
    assert preview == 2
    assert final == 0

    # Second pass: mark-final on same file flips existing rows to final.
    result2 = ingest_copilot_csv(str(FIXTURE_PATH), conn, mark_final=True)
    assert result2.rows_admitted == 0
    assert result2.mark_final_updated == 2

    preview2 = conn.execute(
        "SELECT COUNT(*) FROM copilot_billing_events WHERE is_preview = 1"
    ).fetchone()[0]
    final2 = conn.execute(
        "SELECT COUNT(*) FROM copilot_billing_events WHERE is_preview = 0"
    ).fetchone()[0]
    assert preview2 == 0
    assert final2 == 2


def test_malformed_rows_quarantined_and_duplicates_skipped(conn):
    result = ingest_copilot_csv(str(FIXTURE_PATH), conn, mark_final=False)

    assert result.rows_quarantined == 2
    assert result.rows_skipped_duplicate == 1

    qr = conn.execute(
        """
        SELECT COUNT(*)
        FROM quarantined_records
        WHERE provider = 'copilot_billing' AND source_artifact_path = ?
        """,
        (str(FIXTURE_PATH),),
    ).fetchone()[0]
    assert qr == 2

    inserted = conn.execute("SELECT COUNT(*) FROM copilot_billing_events").fetchone()[0]
    assert inserted == 2
