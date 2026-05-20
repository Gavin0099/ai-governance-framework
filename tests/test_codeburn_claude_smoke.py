"""
CodeBurn Claude Log Ingestion Smoke -- P3.5 operability tests

Tests that the smoke command:
  1. Runs without system error on the built-in fixture
  2. Reports SMOKE_OK (exit code 0)
  3. Produces correct counts for the fixture (3 processed, 1 quarantined)
  4. Authority ceiling flags are all False in the result

These are operability tests, not correctness tests.
Quarantined records are expected, not failures.
"""
from __future__ import annotations

import sqlite3
import tempfile
import os
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "codeburn" / "phase1" / "examples" / "claude_smoke_fixture.jsonl"
)
SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = tmp_path / "smoke_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("""
        INSERT INTO sessions(
            session_id, task, created_at, data_quality,
            comparability_token, comparability_duration, comparability_change
        ) VALUES('smoke-test-001','smoke','2026-05-20','complete',0,1,1)
    """)
    conn.commit()
    conn.close()
    return db_path


class TestSmokeRunsWithoutSystemError:
    def test_smoke_exits_0_on_fixture(self, tmp_db):
        from codeburn.phase1.codeburn_claude_smoke import run_smoke
        exit_code = run_smoke(
            artifact_path=FIXTURE_PATH,
            db_path=tmp_db,
            session_id="smoke-test-001",
            verbose=False,
        )
        assert exit_code == 0, f"smoke returned exit code {exit_code}, expected 0"

    def test_smoke_exits_1_on_missing_file(self, tmp_db):
        from codeburn.phase1.codeburn_claude_smoke import run_smoke
        exit_code = run_smoke(
            artifact_path=Path("/nonexistent/path/session.jsonl"),
            db_path=tmp_db,
            session_id="smoke-test-001",
            verbose=False,
        )
        assert exit_code == 1, "missing file should return exit code 1 (system error)"


class TestSmokeFixtureCounts:
    """Fixture has: 3 assistant records, 1 malformed, 6 non-assistant."""

    def test_smoke_processes_3_assistant_records(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        result = ingest(
            artifact_path=FIXTURE_PATH,
            session_id="smoke-test-001",
            db_path=tmp_db,
        )
        assert result["processed"] == 3, (
            f"expected 3 processed (3 assistant records), got {result['processed']}"
        )

    def test_smoke_quarantines_1_malformed_record(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        result = ingest(
            artifact_path=FIXTURE_PATH,
            session_id="smoke-test-001",
            db_path=tmp_db,
        )
        assert result["quarantined"] == 1, (
            f"expected 1 quarantined (1 malformed line), got {result['quarantined']}"
        )

    def test_smoke_skips_non_assistant_records(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        result = ingest(
            artifact_path=FIXTURE_PATH,
            session_id="smoke-test-001",
            db_path=tmp_db,
        )
        assert result["skipped"] >= 5, (
            f"expected at least 5 skipped (non-assistant records), got {result['skipped']}"
        )


class TestSmokeAuthorityCeiling:
    """Authority ceiling must be intact after ingestion."""

    def test_all_provenance_rows_are_class_c(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        ingest(artifact_path=FIXTURE_PATH, session_id="smoke-test-001", db_path=tmp_db)
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT DISTINCT epistemic_class FROM step_ingestion_provenance"
        ).fetchall()
        conn.close()
        assert rows, "no provenance rows found"
        classes = {r[0] for r in rows}
        assert classes == {"Class C"}, f"expected only Class C, got {classes}"

    def test_real_time_observed_is_0_for_all(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        ingest(artifact_path=FIXTURE_PATH, session_id="smoke-test-001", db_path=tmp_db)
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT COUNT(*) FROM step_ingestion_provenance WHERE real_time_observed != 0"
        ).fetchone()
        conn.close()
        assert rows[0] == 0, "real_time_observed must be 0 for all rows"

    def test_analysis_safe_for_decision_is_0_for_all(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        ingest(artifact_path=FIXTURE_PATH, session_id="smoke-test-001", db_path=tmp_db)
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT COUNT(*) FROM step_ingestion_provenance WHERE analysis_safe_for_decision != 0"
        ).fetchone()
        conn.close()
        assert rows[0] == 0, "analysis_safe_for_decision must be 0 for all rows"

    def test_result_dict_reports_epistemic_position(self, tmp_db):
        from codeburn.phase1.claude_log_ingestor import ingest
        result = ingest(artifact_path=FIXTURE_PATH, session_id="smoke-test-001", db_path=tmp_db)
        assert result["epistemic_class"] == "Class C"
        assert result["real_time_observed"] is False
        assert result["analysis_safe_for_decision"] is False
        assert result["provider_truthfulness_assumed"] is False
