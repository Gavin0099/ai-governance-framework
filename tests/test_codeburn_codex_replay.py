"""
CodeBurn Codex Replay / Provenance Verification Tests (P5 follow-up aligned to P4 semantics)

Scope: replay/provenance stability only. No new authority or correctness claims.

Semantic guardrails explicitly preserved:
  - replay stable != provider truthful
  - duplicate ingest allowed != duplicate semantic consumption allowed

Test groups:
  1) valid token_count replay identity stable
  2) malformed/inadmissible quarantine identity stable
  3) duplicate ingest creates duplicate rows, but same provenance identity
"""
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
SESSION_ID = "codex-replay-test-001"


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = tmp_path / "codex_replay_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO sessions(
            session_id, task, created_at, data_quality,
            comparability_token, comparability_duration, comparability_change
        ) VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (SESSION_ID, "codex-replay", "2026-05-21", "partial", 0, 1, 1),
    )
    conn.commit()
    conn.close()
    return db_path


def _ingest(db_path):
    from codeburn.phase2.codex_log_ingestor import ingest_codex_session

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    result = ingest_codex_session(str(FIXTURE_PATH), SESSION_ID, conn)
    conn.close()
    return result


def _get_provenance_pairs(db_path):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT p.source_record_line, p.source_record_offset
        FROM step_ingestion_provenance p
        INNER JOIN steps s ON p.step_id = s.step_id
        WHERE p.source_artifact_path = ? AND s.provider = 'codex'
        ORDER BY p.source_record_line, p.source_record_offset
        """,
        (str(FIXTURE_PATH.resolve()),),
    ).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _get_quarantine_pairs(db_path):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT source_record_line, source_record_offset
        FROM quarantined_records
        WHERE source_artifact_path = ? AND provider = 'codex'
        ORDER BY source_record_line, source_record_offset
        """,
        (str(FIXTURE_PATH.resolve()),),
    ).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


class TestValidTokenCountReplayIdentityStable:
    """Group 1: same JSONL -> same source_record_line/source_record_offset for admitted rows."""

    def test_valid_replay_identity_set_stable(self, tmp_db):
        _ingest(tmp_db)
        first = set(_get_provenance_pairs(tmp_db))
        assert len(first) == 2

        _ingest(tmp_db)
        second = set(_get_provenance_pairs(tmp_db))
        assert second == first

    def test_valid_replay_doubles_rows_but_not_identity_set(self, tmp_db):
        _ingest(tmp_db)
        pairs1 = _get_provenance_pairs(tmp_db)

        _ingest(tmp_db)
        pairs2 = _get_provenance_pairs(tmp_db)
        assert len(pairs2) == 2 * len(pairs1)
        assert set(pairs2) == set(pairs1)


class TestMalformedQuarantineIdentityStable:
    """Group 2: malformed/inadmissible record quarantine identity remains stable across replay."""

    def test_quarantine_identity_stable(self, tmp_db):
        _ingest(tmp_db)
        q1 = set(_get_quarantine_pairs(tmp_db))
        assert len(q1) == 1

        _ingest(tmp_db)
        q2 = set(_get_quarantine_pairs(tmp_db))
        assert q2 == q1

    def test_quarantine_rows_double_on_duplicate_ingest(self, tmp_db):
        _ingest(tmp_db)
        q1 = _get_quarantine_pairs(tmp_db)

        _ingest(tmp_db)
        q2 = _get_quarantine_pairs(tmp_db)
        assert len(q2) == 2 * len(q1)


class TestDuplicateIngestRowsAndIdentity:
    """Group 3: duplicate ingest rows are expected; provenance identity remains same.

    This is replay/provenance behavior only.
    It must NOT be interpreted as provider truthfulness proof,
    and must NOT be interpreted as authorization for duplicate semantic consumption.
    """

    def test_duplicate_ingest_creates_duplicate_rows_same_identity(self, tmp_db):
        _ingest(tmp_db)
        _ingest(tmp_db)

        conn = sqlite3.connect(str(tmp_db))
        duplicates = conn.execute(
            """
            SELECT source_record_line, source_record_offset, COUNT(*) AS ingest_count
            FROM step_ingestion_provenance
            WHERE source_artifact_path = ? AND provider = 'codex'
            GROUP BY source_record_line, source_record_offset
            HAVING COUNT(*) > 1
            ORDER BY source_record_line, source_record_offset
            """,
            (str(FIXTURE_PATH.resolve()),),
        ).fetchall()
        conn.close()

        assert len(duplicates) == 2
        assert all(row[2] == 2 for row in duplicates)
