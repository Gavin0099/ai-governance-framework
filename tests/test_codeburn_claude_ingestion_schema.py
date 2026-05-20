"""
CodeBurn Claude Artifact Ingestion — Schema Constraint Tests (P3.1)

These tests verify the DB-level constraints on step_ingestion_provenance and
quarantined_records. They do not depend on the ingestion module — they test
the schema directly via sqlite3.

Hard invariants under test:
  - real_time_observed is always 0 (schema rejects 1)
  - analysis_safe_for_decision is always 0 (schema rejects 1)
  - provider_truthfulness_assumed is always 0 (schema rejects 1)
  - epistemic_class must be one of the five ontology classes
  - source_record_line >= 1 (schema rejects 0 and negative)
  - required columns exist on both new tables
  - quarantined_records does not accept line number < 1
"""
from __future__ import annotations

import sqlite3
import tempfile
import os
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"


@pytest.fixture()
def conn():
    """In-process SQLite connection with the full schema applied."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    c = sqlite3.connect(db_path)
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Seed minimal session + step for FK tests
    c.execute("""
        INSERT INTO sessions(session_id, task, created_at, data_quality,
                             comparability_token, comparability_duration, comparability_change)
        VALUES('sess-001', 'test task', '2026-05-20T00:00:00Z', 'complete', 0, 1, 1)
    """)
    c.execute("""
        INSERT INTO steps(step_id, session_id, step_kind, command, started_at)
        VALUES('step-001', 'sess-001', 'other', 'test', '2026-05-20T00:00:00Z')
    """)
    c.commit()
    yield c
    c.close()
    os.unlink(db_path)


def _valid_provenance_row(step_id: str = "step-001") -> dict:
    return {
        "step_id": step_id,
        "provider": "claude",
        "epistemic_class": "Class C",
        "acquisition_mode": "session_log_ingestion",
        "source_artifact_path": "/home/user/.claude/projects/proj/session.jsonl",
        "source_record_line": 4,
        "source_record_offset": 1024,
        "real_time_observed": 0,
        "analysis_safe_for_decision": 0,
        "provider_truthfulness_assumed": 0,
        "created_at": "2026-05-20T00:00:00Z",
    }


def _insert_provenance(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT INTO step_ingestion_provenance(
            step_id, provider, epistemic_class, acquisition_mode,
            source_artifact_path, source_record_line, source_record_offset,
            real_time_observed, analysis_safe_for_decision,
            provider_truthfulness_assumed, created_at
        ) VALUES(
            :step_id, :provider, :epistemic_class, :acquisition_mode,
            :source_artifact_path, :source_record_line, :source_record_offset,
            :real_time_observed, :analysis_safe_for_decision,
            :provider_truthfulness_assumed, :created_at
        )
    """, row)
    conn.commit()


# ---------------------------------------------------------------------------
# Table existence
# ---------------------------------------------------------------------------

class TestTablesExist:
    def test_step_ingestion_provenance_table_exists(self, conn):
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "step_ingestion_provenance" in tables

    def test_quarantined_records_table_exists(self, conn):
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "quarantined_records" in tables


# ---------------------------------------------------------------------------
# Column existence
# ---------------------------------------------------------------------------

class TestStepIngestionProvenanceColumns:
    REQUIRED_COLUMNS = {
        "id", "step_id", "provider", "epistemic_class", "acquisition_mode",
        "source_artifact_path", "source_record_line", "source_record_offset",
        "real_time_observed", "analysis_safe_for_decision",
        "provider_truthfulness_assumed", "created_at",
    }

    def test_all_required_columns_present(self, conn):
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(step_ingestion_provenance)"
        ).fetchall()}
        missing = self.REQUIRED_COLUMNS - cols
        assert not missing, f"missing columns: {missing}"


class TestQuarantinedRecordsColumns:
    REQUIRED_COLUMNS = {
        "id", "provider", "source_artifact_path", "source_record_line",
        "source_record_offset", "reason", "raw_record", "created_at",
    }

    def test_all_required_columns_present(self, conn):
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(quarantined_records)"
        ).fetchall()}
        missing = self.REQUIRED_COLUMNS - cols
        assert not missing, f"missing columns: {missing}"


# ---------------------------------------------------------------------------
# Hard invariant: real_time_observed must be 0
# ---------------------------------------------------------------------------

class TestRealTimeObservedConstraint:
    def test_real_time_observed_0_accepted(self, conn):
        row = _valid_provenance_row()
        row["real_time_observed"] = 0
        _insert_provenance(conn, row)  # must not raise
        result = conn.execute(
            "SELECT real_time_observed FROM step_ingestion_provenance"
        ).fetchone()
        assert result[0] == 0

    def test_real_time_observed_1_rejected(self, conn):
        row = _valid_provenance_row()
        row["real_time_observed"] = 1
        with pytest.raises(sqlite3.IntegrityError):
            _insert_provenance(conn, row)

    def test_real_time_observed_default_is_0(self, conn):
        conn.execute("""
            INSERT INTO step_ingestion_provenance(
                step_id, provider, epistemic_class, acquisition_mode,
                source_artifact_path, source_record_line,
                analysis_safe_for_decision, provider_truthfulness_assumed, created_at
            ) VALUES('step-001','claude','Class C','session_log_ingestion',
                     '/tmp/x.jsonl', 1, 0, 0, '2026-05-20')
        """)
        conn.commit()
        result = conn.execute(
            "SELECT real_time_observed FROM step_ingestion_provenance"
        ).fetchone()
        assert result[0] == 0, "default value for real_time_observed must be 0"


# ---------------------------------------------------------------------------
# Hard invariant: analysis_safe_for_decision must be 0
# ---------------------------------------------------------------------------

class TestAnalysisSafeForDecisionConstraint:
    def test_analysis_safe_for_decision_0_accepted(self, conn):
        row = _valid_provenance_row()
        row["analysis_safe_for_decision"] = 0
        _insert_provenance(conn, row)

    def test_analysis_safe_for_decision_1_rejected(self, conn):
        """This is the authority upgrade path — schema must prevent it."""
        row = _valid_provenance_row()
        row["analysis_safe_for_decision"] = 1
        with pytest.raises(sqlite3.IntegrityError):
            _insert_provenance(conn, row)

    def test_analysis_safe_for_decision_default_is_0(self, conn):
        conn.execute("""
            INSERT INTO step_ingestion_provenance(
                step_id, provider, epistemic_class, acquisition_mode,
                source_artifact_path, source_record_line,
                real_time_observed, provider_truthfulness_assumed, created_at
            ) VALUES('step-001','claude','Class C','session_log_ingestion',
                     '/tmp/x.jsonl', 1, 0, 0, '2026-05-20')
        """)
        conn.commit()
        result = conn.execute(
            "SELECT analysis_safe_for_decision FROM step_ingestion_provenance"
        ).fetchone()
        assert result[0] == 0, "default value for analysis_safe_for_decision must be 0"


# ---------------------------------------------------------------------------
# Hard invariant: provider_truthfulness_assumed must be 0
# ---------------------------------------------------------------------------

class TestProviderTruthfulnessAssumedConstraint:
    def test_provider_truthfulness_assumed_0_accepted(self, conn):
        row = _valid_provenance_row()
        _insert_provenance(conn, row)

    def test_provider_truthfulness_assumed_1_rejected(self, conn):
        row = _valid_provenance_row()
        row["provider_truthfulness_assumed"] = 1
        with pytest.raises(sqlite3.IntegrityError):
            _insert_provenance(conn, row)


# ---------------------------------------------------------------------------
# epistemic_class: only ontology classes accepted
# ---------------------------------------------------------------------------

class TestEpistemicClassConstraint:
    @pytest.mark.parametrize("cls", ["Class A", "Class B", "Class C", "Class D", "Class E"])
    def test_valid_ontology_classes_accepted(self, conn, cls):
        row = _valid_provenance_row()
        row["epistemic_class"] = cls
        # NB: only Class C should ever appear in practice, but schema allows all
        _insert_provenance(conn, row)
        result = conn.execute(
            "SELECT epistemic_class FROM step_ingestion_provenance"
        ).fetchone()
        assert result[0] == cls

    @pytest.mark.parametrize("bad_cls", ["Class Z", "C", "class c", "UNKNOWN", "", "provider"])
    def test_invalid_classes_rejected(self, conn, bad_cls):
        row = _valid_provenance_row()
        row["epistemic_class"] = bad_cls
        with pytest.raises(sqlite3.IntegrityError):
            _insert_provenance(conn, row)


# ---------------------------------------------------------------------------
# source_record_line: must be >= 1
# ---------------------------------------------------------------------------

class TestSourceRecordLineConstraint:
    def test_line_1_accepted(self, conn):
        row = _valid_provenance_row()
        row["source_record_line"] = 1
        _insert_provenance(conn, row)

    def test_line_0_rejected(self, conn):
        row = _valid_provenance_row()
        row["source_record_line"] = 0
        with pytest.raises(sqlite3.IntegrityError):
            _insert_provenance(conn, row)

    def test_negative_line_rejected(self, conn):
        row = _valid_provenance_row()
        row["source_record_line"] = -1
        with pytest.raises(sqlite3.IntegrityError):
            _insert_provenance(conn, row)


# ---------------------------------------------------------------------------
# quarantined_records constraints
# ---------------------------------------------------------------------------

class TestQuarantinedRecordsConstraints:
    def _insert_quarantine(self, conn: sqlite3.Connection, **overrides):
        row = {
            "provider": "claude",
            "source_artifact_path": "/tmp/session.jsonl",
            "source_record_line": 7,
            "source_record_offset": 512,
            "reason": "json_parse_error",
            "raw_record": "{bad json",
            "created_at": "2026-05-20T00:00:00Z",
        }
        row.update(overrides)
        conn.execute("""
            INSERT INTO quarantined_records(
                provider, source_artifact_path, source_record_line, source_record_offset,
                reason, raw_record, created_at
            ) VALUES(
                :provider, :source_artifact_path, :source_record_line, :source_record_offset,
                :reason, :raw_record, :created_at
            )
        """, row)
        conn.commit()

    def test_valid_quarantine_row_accepted(self, conn):
        self._insert_quarantine(conn)
        rows = conn.execute("SELECT * FROM quarantined_records").fetchall()
        assert len(rows) == 1

    def test_quarantine_line_0_rejected(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_quarantine(conn, source_record_line=0)

    def test_quarantine_negative_line_rejected(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_quarantine(conn, source_record_line=-5)

    def test_quarantine_null_reason_rejected(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_quarantine(conn, reason=None)

    def test_quarantine_null_source_path_rejected(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_quarantine(conn, source_artifact_path=None)
