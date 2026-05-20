"""
CodeBurn Claude Log Replay / Provenance Verification Tests (P4.2 / P4.3 / P4.4)

Verifies the three replay invariants and the non-idempotency contract
as specified in CODEBURN_CLAUDE_REPLAY_PROVENANCE_CONTRACT.md.

P4.2 -- valid record replay: same (line, offset) pairs after two ingests
P4.3 -- quarantine record replay: quarantined records share line/offset across ingests
P4.4 -- non-idempotency contract: two ingests = two times the rows (not a bug)

Key concept (from spec):
  Non-idempotency is a design decision, not a bug.
  Provenance identity (line, offset) is stable across replays.
  step_id is NOT stable -- it is a new UUID on every ingest.
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
    db_path = tmp_path / "replay_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("""
        INSERT INTO sessions(
            session_id, task, created_at, data_quality,
            comparability_token, comparability_duration, comparability_change
        ) VALUES('replay-test-001','replay','2026-05-20','complete',0,1,1)
    """)
    conn.commit()
    conn.close()
    return db_path


def _ingest(db_path, session_id="replay-test-001"):
    from codeburn.phase1.claude_log_ingestor import ingest
    return ingest(
        artifact_path=FIXTURE_PATH,
        session_id=session_id,
        db_path=db_path,
    )


def _get_provenance_pairs(db_path):
    """Return sorted (line, offset) pairs from step_ingestion_provenance for the fixture."""
    artifact_str = str(FIXTURE_PATH.resolve())
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT p.source_record_line, p.source_record_offset
        FROM step_ingestion_provenance p
        INNER JOIN steps s ON p.step_id = s.step_id
        WHERE p.source_artifact_path = ?
        ORDER BY p.source_record_line, p.source_record_offset
        """,
        (artifact_str,),
    ).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _get_quarantine_pairs(db_path):
    """Return sorted (line, offset) pairs from quarantined_records for the fixture."""
    artifact_str = str(FIXTURE_PATH.resolve())
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT source_record_line, source_record_offset
        FROM quarantined_records
        WHERE source_artifact_path = ?
        ORDER BY source_record_line, source_record_offset
        """,
        (artifact_str,),
    ).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


# ---------------------------------------------------------------------------
# P4.2 -- Valid Record Replay: line/offset stability
# ---------------------------------------------------------------------------

class TestValidRecordReplay:
    """R1 and R2: source_record_line and source_record_offset are stable across replays."""

    def test_first_ingest_produces_3_provenance_pairs(self, tmp_db):
        _ingest(tmp_db)
        pairs = _get_provenance_pairs(tmp_db)
        assert len(pairs) == 3, f"expected 3 provenance pairs after 1 ingest, got {len(pairs)}"

    def test_line_offset_pairs_are_deterministic_on_first_ingest(self, tmp_db):
        _ingest(tmp_db)
        pairs = _get_provenance_pairs(tmp_db)
        # All pairs must be unique on first ingest
        assert len(set(pairs)) == 3, (
            f"expected 3 unique (line, offset) pairs on first ingest, got {set(pairs)}"
        )

    def test_replay_produces_same_line_offset_pairs(self, tmp_db):
        """R1 + R2: same (line, offset) appear on both ingests."""
        _ingest(tmp_db)
        pairs_1 = _get_provenance_pairs(tmp_db)

        _ingest(tmp_db)
        pairs_2 = _get_provenance_pairs(tmp_db)

        # pairs_2 has 6 rows (2x), pairs_1 has 3 rows
        # Each pair from ingest 1 must appear in ingest 2
        set_1 = set(pairs_1)
        set_2 = set(pairs_2)
        assert set_1 == set_2, (
            f"provenance identity pairs changed across replay.\n"
            f"  ingest 1 unique pairs: {set_1}\n"
            f"  ingest 2 unique pairs: {set_2}"
        )

    def test_replay_doubles_row_count_for_provenance(self, tmp_db):
        """P4.4: non-idempotency -- 2 ingests = 2x rows in step_ingestion_provenance."""
        _ingest(tmp_db)
        pairs_1 = _get_provenance_pairs(tmp_db)

        _ingest(tmp_db)
        pairs_2 = _get_provenance_pairs(tmp_db)

        assert len(pairs_2) == 2 * len(pairs_1), (
            f"expected 2x rows after 2 ingests, got {len(pairs_1)} -> {len(pairs_2)}"
        )

    def test_source_record_line_is_stable(self, tmp_db):
        """R1: each assistant record always has the same source_record_line."""
        _ingest(tmp_db)
        lines_1 = sorted(line for line, _ in _get_provenance_pairs(tmp_db))

        _ingest(tmp_db)
        # All unique lines after 2 ingests must equal all unique lines after 1 ingest
        lines_2 = sorted(set(line for line, _ in _get_provenance_pairs(tmp_db)))

        assert lines_1 == lines_2, (
            f"source_record_line values changed across replay.\n"
            f"  ingest 1: {lines_1}\n"
            f"  ingest 2 unique: {lines_2}"
        )

    def test_source_record_offset_is_stable(self, tmp_db):
        """R2: each assistant record always has the same source_record_offset."""
        _ingest(tmp_db)
        offsets_1 = sorted(offset for _, offset in _get_provenance_pairs(tmp_db))

        _ingest(tmp_db)
        offsets_2 = sorted(set(offset for _, offset in _get_provenance_pairs(tmp_db)))

        assert offsets_1 == offsets_2, (
            f"source_record_offset values changed across replay.\n"
            f"  ingest 1: {offsets_1}\n"
            f"  ingest 2 unique: {offsets_2}"
        )

    def test_step_id_is_not_stable_across_replay(self, tmp_db):
        """step_id is NOT a provenance identity key -- it is regenerated each ingest."""
        conn = sqlite3.connect(str(db_path := tmp_db))
        artifact_str = str(FIXTURE_PATH.resolve())

        _ingest(tmp_db)
        step_ids_1 = set(
            row[0] for row in conn.execute(
                "SELECT p.step_id FROM step_ingestion_provenance p "
                "WHERE p.source_artifact_path = ?", (artifact_str,)
            ).fetchall()
        )

        _ingest(tmp_db)
        step_ids_2 = set(
            row[0] for row in conn.execute(
                "SELECT p.step_id FROM step_ingestion_provenance p "
                "WHERE p.source_artifact_path = ?", (artifact_str,)
            ).fetchall()
        )
        conn.close()

        # After 2 ingests there are 6 step_ids total; the first 3 should not overlap with new 3
        new_step_ids = step_ids_2 - step_ids_1
        assert len(new_step_ids) == 3, (
            f"expected 3 new step_ids on second ingest (replay generates new UUIDs), "
            f"got {len(new_step_ids)} new ids.\n"
            f"  All step_ids after ingest 2: {step_ids_2}"
        )


# ---------------------------------------------------------------------------
# P4.3 -- Quarantine Record Replay
# ---------------------------------------------------------------------------

class TestQuarantineRecordReplay:
    """R3: quarantine (line, offset) is stable across replays."""

    def test_first_ingest_quarantines_line_9(self, tmp_db):
        """Fixture line 9 is malformed JSON and must always be quarantined."""
        _ingest(tmp_db)
        pairs = _get_quarantine_pairs(tmp_db)
        assert len(pairs) == 1, f"expected 1 quarantine pair, got {len(pairs)}"
        line, offset = pairs[0]
        assert line == 9, f"expected malformed record at line 9, got line {line}"

    def test_quarantine_line_is_stable_across_replay(self, tmp_db):
        """R3: malformed line 9 always quarantined at line=9."""
        _ingest(tmp_db)
        pairs_1 = _get_quarantine_pairs(tmp_db)

        _ingest(tmp_db)
        pairs_2 = _get_quarantine_pairs(tmp_db)

        lines_1 = sorted(line for line, _ in pairs_1)
        lines_2 = sorted(set(line for line, _ in pairs_2))  # unique after dedup
        assert lines_1 == lines_2, (
            f"quarantine line numbers changed across replay.\n"
            f"  ingest 1: {lines_1}\n"
            f"  ingest 2 unique: {lines_2}"
        )

    def test_quarantine_offset_is_stable_across_replay(self, tmp_db):
        """R3: malformed record offset is stable on replay."""
        _ingest(tmp_db)
        pairs_1 = _get_quarantine_pairs(tmp_db)

        _ingest(tmp_db)
        pairs_2 = _get_quarantine_pairs(tmp_db)

        offsets_1 = sorted(off for _, off in pairs_1)
        offsets_2 = sorted(set(off for _, off in pairs_2))
        assert offsets_1 == offsets_2, (
            f"quarantine offsets changed across replay.\n"
            f"  ingest 1: {offsets_1}\n"
            f"  ingest 2 unique: {offsets_2}"
        )

    def test_quarantine_doubles_on_second_ingest(self, tmp_db):
        """P4.4: non-idempotency applies to quarantine too -- 2 ingests = 2 quarantine rows."""
        _ingest(tmp_db)
        pairs_1 = _get_quarantine_pairs(tmp_db)

        _ingest(tmp_db)
        pairs_2 = _get_quarantine_pairs(tmp_db)

        assert len(pairs_2) == 2 * len(pairs_1), (
            f"expected quarantine rows to double on second ingest, "
            f"got {len(pairs_1)} -> {len(pairs_2)}"
        )


# ---------------------------------------------------------------------------
# P4.4 -- Non-Idempotency Contract (explicit)
# ---------------------------------------------------------------------------

class TestNonIdempotencyContract:
    """Duplicate ingestion is allowed and expected. It is not a bug."""

    def test_two_ingests_double_steps_rows(self, tmp_db):
        result1 = _ingest(tmp_db)
        conn = sqlite3.connect(str(tmp_db))
        count_1 = conn.execute(
            "SELECT COUNT(*) FROM steps WHERE session_id = 'replay-test-001'"
        ).fetchone()[0]

        result2 = _ingest(tmp_db)
        count_2 = conn.execute(
            "SELECT COUNT(*) FROM steps WHERE session_id = 'replay-test-001'"
        ).fetchone()[0]
        conn.close()

        assert count_2 == 2 * count_1, (
            f"expected steps to double on duplicate ingest (non-idempotency contract), "
            f"got {count_1} -> {count_2}"
        )

    def test_two_ingests_double_provenance_rows(self, tmp_db):
        artifact_str = str(FIXTURE_PATH.resolve())
        conn = sqlite3.connect(str(tmp_db))

        _ingest(tmp_db)
        count_1 = conn.execute(
            "SELECT COUNT(*) FROM step_ingestion_provenance WHERE source_artifact_path = ?",
            (artifact_str,),
        ).fetchone()[0]

        _ingest(tmp_db)
        count_2 = conn.execute(
            "SELECT COUNT(*) FROM step_ingestion_provenance WHERE source_artifact_path = ?",
            (artifact_str,),
        ).fetchone()[0]
        conn.close()

        assert count_2 == 2 * count_1, (
            f"expected provenance rows to double (non-idempotency contract), "
            f"got {count_1} -> {count_2}"
        )

    def test_ingest_result_processed_count_is_consistent(self, tmp_db):
        """Each ingest call returns processed=3 regardless of prior state."""
        result1 = _ingest(tmp_db)
        result2 = _ingest(tmp_db)
        assert result1["processed"] == result2["processed"] == 3, (
            f"expected processed=3 on each ingest, got {result1['processed']} / {result2['processed']}"
        )

    def test_ingest_result_quarantined_count_is_consistent(self, tmp_db):
        """Each ingest call returns quarantined=1 regardless of prior state."""
        result1 = _ingest(tmp_db)
        result2 = _ingest(tmp_db)
        assert result1["quarantined"] == result2["quarantined"] == 1, (
            f"expected quarantined=1 on each ingest, got {result1['quarantined']} / {result2['quarantined']}"
        )

    def test_duplicate_detection_query_finds_duplicates_after_two_ingests(self, tmp_db):
        """The SQL duplicate detection query from the spec detects duplicate ingestion."""
        artifact_str = str(FIXTURE_PATH.resolve())
        _ingest(tmp_db)
        _ingest(tmp_db)

        conn = sqlite3.connect(str(tmp_db))
        # Spec SQL: detect same (path, line, offset) ingested more than once
        duplicates = conn.execute(
            """
            SELECT source_artifact_path, source_record_line, source_record_offset,
                   COUNT(*) as ingest_count
            FROM step_ingestion_provenance
            GROUP BY source_artifact_path, source_record_line, source_record_offset
            HAVING COUNT(*) > 1
            """,
        ).fetchall()
        conn.close()

        assert len(duplicates) == 3, (
            f"expected 3 duplicate groups (one per assistant record) after 2 ingests, "
            f"got {len(duplicates)}"
        )
        for _, line, offset, count in duplicates:
            assert count == 2, f"expected ingest_count=2, got {count} for line={line}"


# ---------------------------------------------------------------------------
# P4.1 -- Provenance Identity Helper
# ---------------------------------------------------------------------------

class TestProvenanceIdentityHelper:
    """Unit tests for the _provenance_identity helper (P4.1)."""

    def test_provenance_identity_returns_tuple(self):
        from codeburn.phase1.provenance_identity import provenance_identity
        result = provenance_identity(FIXTURE_PATH, 4, 480)
        assert isinstance(result, tuple), "provenance_identity must return a tuple"
        assert len(result) == 3, "tuple must have 3 elements"

    def test_provenance_identity_resolves_path(self):
        from codeburn.phase1.provenance_identity import provenance_identity
        result = provenance_identity(FIXTURE_PATH, 4, 480)
        # First element must be a resolved absolute path string
        assert result[0] == str(FIXTURE_PATH.resolve()), (
            f"expected resolved path, got {result[0]!r}"
        )

    def test_provenance_identity_preserves_line_and_offset(self):
        from codeburn.phase1.provenance_identity import provenance_identity
        result = provenance_identity(FIXTURE_PATH, 7, 1398)
        assert result[1] == 7
        assert result[2] == 1398

    def test_provenance_identity_allows_none_offset(self):
        from codeburn.phase1.provenance_identity import provenance_identity
        result = provenance_identity(FIXTURE_PATH, 4, None)
        assert result[2] is None

    def test_provenance_identities_match_db_after_ingest(self, tmp_db):
        """After ingest, DB (line, offset) pairs match provenance_identity tuples."""
        from codeburn.phase1.provenance_identity import (
            provenance_identity,
            extract_provenance_identities_from_db,
        )
        _ingest(tmp_db)
        conn = sqlite3.connect(str(tmp_db))
        db_ids = extract_provenance_identities_from_db(
            conn, "step_ingestion_provenance", FIXTURE_PATH
        )
        conn.close()

        for path_str, line, offset in db_ids:
            expected = provenance_identity(FIXTURE_PATH, line, offset)
            actual = (path_str, line, offset)
            assert actual == expected, (
                f"DB provenance identity {actual} does not match helper output {expected}"
            )
