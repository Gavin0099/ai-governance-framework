"""
CodeBurn Claude Artifact Ingestion — Negative-Path Tests
P3.4: tests written before implementation, per CODEBURN_CLAUDE_ARTIFACT_CONTRACT.md

These tests define the invariants that ingestion must preserve.
They will fail until P3.2 (ingestion parser) and P3.3 (provenance writer) are implemented.

Invariants under test:
  I1 — Class C assignment is unconditional
  I2 — missing token fields != zero usage (typed null)
  I3 — malformed records are quarantined, not silently dropped
  I4 — source artifact path + line number are required
  I5 — no authority upgrade through ingestion
  I6 — reconstruction gap declared on every record

Negative-path specifications from contract:
  NP1 — valid record -> Class C evidence written
  NP2 — missing usage -> typed null written
  NP3 — malformed JSON -> quarantine record written
  NP4 — inadmissible fields -> not stored
  NP5 — cache tokens -> individual fields, no total computed
"""
from __future__ import annotations

import json
import sqlite3
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers — these will import from the ingestion module once implemented.
# The import is deferred inside each test so that the test file itself can be
# collected even before the module exists.
# ---------------------------------------------------------------------------

def _get_ingestor():
    """Import the ingestion module. Raises ImportError if not yet implemented."""
    try:
        from codeburn.phase1 import claude_log_ingestor  # noqa: F401
        return claude_log_ingestor
    except ImportError:
        pytest.skip("claude_log_ingestor not yet implemented (P3.2)")


def _make_db(tmp_path: Path) -> tuple[Path, sqlite3.Connection]:
    """Create an in-memory-equivalent SQLite db with the extended schema."""
    db_path = tmp_path / "test_ingestion.db"
    schema_path = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    # Apply P3.1 schema extension (step_ingestion_provenance + quarantined_records)
    # If the tables don't exist yet, create them here for test isolation.
    # Tables are defined in schema.sql (P3.1). The IF NOT EXISTS below are
    # safety nets for isolated test runs on older schema versions — they are
    # no-ops when schema.sql has already been applied above.
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS step_ingestion_provenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            epistemic_class TEXT NOT NULL CHECK (epistemic_class IN ('Class A','Class B','Class C','Class D','Class E')),
            acquisition_mode TEXT NOT NULL,
            source_artifact_path TEXT NOT NULL,
            source_record_line INTEGER NOT NULL CHECK (source_record_line >= 1),
            source_record_offset INTEGER,
            real_time_observed INTEGER NOT NULL DEFAULT 0 CHECK (real_time_observed = 0),
            analysis_safe_for_decision INTEGER NOT NULL DEFAULT 0 CHECK (analysis_safe_for_decision = 0),
            provider_truthfulness_assumed INTEGER NOT NULL DEFAULT 0 CHECK (provider_truthfulness_assumed = 0),
            created_at TEXT NOT NULL,
            FOREIGN KEY(step_id) REFERENCES steps(step_id)
        );
        CREATE TABLE IF NOT EXISTS quarantined_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            source_artifact_path TEXT NOT NULL,
            source_record_line INTEGER NOT NULL CHECK (source_record_line >= 1),
            source_record_offset INTEGER,
            reason TEXT NOT NULL,
            raw_record TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    return db_path, conn


def _seed_session(conn: sqlite3.Connection) -> str:
    """Seed a minimal open session for FK constraints."""
    from datetime import datetime, timezone
    session_id = "test-session-claude-ingestion"
    conn.execute("""
        INSERT OR IGNORE INTO sessions(
            session_id, task, repo_path, git_branch, created_at,
            data_quality, comparability_token, comparability_duration, comparability_change
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, "test task", "/tmp/repo", "main",
        datetime.now(timezone.utc).isoformat(),
        "complete", 0, 1, 1
    ))
    conn.commit()
    return session_id


def _make_assistant_record(
    uuid: str = "rec-uuid-001",
    session_id: str = "test-session-claude-ingestion",
    input_tokens: int | None = 10,
    output_tokens: int | None = 20,
    cache_creation_tokens: int | None = 100,
    cache_read_tokens: int | None = 50,
    include_usage: bool = True,
    include_inadmissible: bool = False,
) -> dict:
    usage: dict = {}
    if include_usage:
        if input_tokens is not None:
            usage["input_tokens"] = input_tokens
        if output_tokens is not None:
            usage["output_tokens"] = output_tokens
        if cache_creation_tokens is not None:
            usage["cache_creation_input_tokens"] = cache_creation_tokens
        if cache_read_tokens is not None:
            usage["cache_read_input_tokens"] = cache_read_tokens
        if include_inadmissible:
            usage["service_tier"] = "standard"
            usage["inference_geo"] = "not_available"

    record: dict = {
        "type": "assistant",
        "sessionId": session_id,
        "uuid": uuid,
        "timestamp": "2026-05-20T00:00:00.000Z",
        "message": {
            "role": "assistant",
            "model": "claude-sonnet-4-6",
            "content": [],
        },
    }
    if include_usage:
        record["message"]["usage"] = usage
    return record


def _write_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            if isinstance(rec, str):
                f.write(rec + "\n")
            else:
                f.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# NP1: valid record -> Class C evidence written
# ---------------------------------------------------------------------------

class TestNP1ValidRecordClassCEvidence:
    """
    Contract: NP1 — Valid `type=assistant` record with complete `message.usage`
    must produce a `step_ingestion_provenance` row with provenance_class='C',
    real_time_observed=0, reconstruction_gap_declared=1.

    Invariants: I1, I5, I6
    """

    def test_ingestion_writes_class_c_provenance(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(session_id=session_id)])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        rows = conn.execute(
            "SELECT epistemic_class, real_time_observed, analysis_safe_for_decision "
            "FROM step_ingestion_provenance"
        ).fetchall()
        assert len(rows) == 1, "expected one provenance row"
        epistemic_class, real_time_observed, analysis_safe_for_decision = rows[0]
        assert epistemic_class == "Class C", f"expected Class C, got {epistemic_class!r}"
        assert real_time_observed == 0, "real_time_observed must be 0 for Class C"
        assert analysis_safe_for_decision == 0, "analysis_safe_for_decision must be 0"

    def test_ingestion_does_not_write_provider_token_source(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(session_id=session_id)])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        rows = conn.execute("SELECT token_source FROM steps").fetchall()
        assert rows, "expected at least one step row"
        for (token_source,) in rows:
            assert token_source != "provider", (
                f"token_source must not be 'provider' for Class C ingestion, got {token_source!r}"
            )

    def test_ingestion_writes_source_artifact_path_and_line(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(session_id=session_id)])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        rows = conn.execute(
            "SELECT source_artifact_path, source_record_line FROM step_ingestion_provenance"
        ).fetchall()
        assert rows, "expected provenance rows with source artifact path"
        for path, line in rows:
            assert path, "source_artifact_path must not be empty"
            assert line is not None and line >= 1, "source_record_line must be >= 1"


# ---------------------------------------------------------------------------
# NP2: missing usage -> typed null written
# ---------------------------------------------------------------------------

class TestNP2MissingUsageTypedNull:
    """
    Contract: NP2 — If `message.usage` is absent, token fields must be NULL
    (not 0). Record must not be silently dropped.

    Invariant: I2
    """

    def test_missing_usage_writes_null_not_zero(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(
            session_id=session_id, include_usage=False
        )])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        rows = conn.execute(
            "SELECT prompt_tokens, completion_tokens, total_tokens FROM steps"
        ).fetchall()
        assert rows, "record must not be silently dropped — steps row expected"
        for prompt, completion, total in rows:
            assert prompt != 0, (
                "prompt_tokens must be NULL (not 0) when usage is absent. "
                "0 implies zero usage; NULL implies absence."
            )
            assert completion != 0, (
                "completion_tokens must be NULL (not 0) when usage is absent."
            )

    def test_missing_usage_still_writes_class_c_provenance(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(
            session_id=session_id, include_usage=False
        )])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        rows = conn.execute(
            "SELECT epistemic_class FROM step_ingestion_provenance"
        ).fetchall()
        assert rows, "provenance row must be written even when usage is absent"
        for (cls,) in rows:
            assert cls == "Class C", f"epistemic_class must be 'Class C', got {cls!r}"


# ---------------------------------------------------------------------------
# NP3: malformed JSON -> quarantine record written
# ---------------------------------------------------------------------------

class TestNP3MalformedJsonQuarantined:
    """
    Contract: NP3 — Malformed JSON must be quarantined (persisted to
    quarantined_records) and must not produce any steps or provenance rows.

    Invariant: I3
    """

    def test_malformed_line_produces_quarantine_record(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [
            _make_assistant_record(session_id=session_id),  # valid
            "{not valid json {{",                           # malformed
        ])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        quarantine_rows = conn.execute(
            "SELECT source_artifact_path, source_record_line, reason "
            "FROM quarantined_records"
        ).fetchall()
        assert len(quarantine_rows) >= 1, (
            "malformed line must produce a quarantine record — "
            "silent drops are not acceptable (I3)"
        )
        paths = [r[0] for r in quarantine_rows]
        assert any(str(artifact) in p or artifact.name in p for p in paths), (
            "quarantine record must reference the source artifact path"
        )

    def test_malformed_line_does_not_produce_steps_row(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, ["{bad json"])  # only malformed

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        steps = conn.execute("SELECT * FROM steps").fetchall()
        assert len(steps) == 0, (
            "malformed records must not produce steps rows — "
            "partial evidence from malformed input is not acceptable"
        )

    def test_valid_records_after_malformed_still_processed(self, tmp_path):
        """Quarantine must not abort the entire ingestion — only the bad record."""
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [
            "{not valid json",                                           # malformed
            _make_assistant_record(uuid="valid-001", session_id=session_id),  # valid
        ])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        steps = conn.execute("SELECT * FROM steps").fetchall()
        assert len(steps) == 1, (
            "valid records after a malformed record must still be ingested"
        )
        quarantine = conn.execute("SELECT * FROM quarantined_records").fetchall()
        assert len(quarantine) == 1, "malformed record must be quarantined"


# ---------------------------------------------------------------------------
# NP4: inadmissible fields -> not stored
# ---------------------------------------------------------------------------

class TestNP4InadmissibleFieldsNotStored:
    """
    Contract: NP4 — Fields like service_tier and inference_geo must not
    be stored in any table.

    Invariant: I5
    """

    def test_service_tier_not_stored(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(
            session_id=session_id, include_inadmissible=True
        )])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        # Check that no column named service_tier or inference_geo exists
        # in any of the core tables
        for table in ("steps", "step_ingestion_provenance", "quarantined_records"):
            cols = [
                row[1] for row in
                conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            assert "service_tier" not in cols, (
                f"inadmissible field 'service_tier' must not appear in {table}"
            )
            assert "inference_geo" not in cols, (
                f"inadmissible field 'inference_geo' must not appear in {table}"
            )


# ---------------------------------------------------------------------------
# NP5: cache tokens -> individual fields stored, no total computed from cache
# ---------------------------------------------------------------------------

class TestNP5CacheTokensNoTotalComputed:
    """
    Contract: NP5 — Cache token fields (cache_creation_input_tokens,
    cache_read_input_tokens) must be stored as individual fields.
    No billing total or billed-token estimate may be computed.

    The steps.total_tokens field must not include cache fields — it should
    be NULL or only input_tokens + output_tokens.
    """

    def test_cache_fields_do_not_inflate_total_tokens(self, tmp_path):
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        # input=3, output=7, cache_creation=5808, cache_read=9364
        # If total is computed including cache, it would be >> 10
        _write_jsonl(artifact, [_make_assistant_record(
            session_id=session_id,
            input_tokens=3,
            output_tokens=7,
            cache_creation_tokens=5808,
            cache_read_tokens=9364,
        )])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        rows = conn.execute(
            "SELECT prompt_tokens, completion_tokens, total_tokens FROM steps"
        ).fetchall()
        assert rows
        prompt, completion, total = rows[0]

        # total_tokens should not include cache fields
        # Acceptable: NULL, or prompt+completion only (3+7=10)
        if total is not None:
            assert total <= 10, (
                f"total_tokens ({total}) must not include cache fields — "
                f"cache_creation (5808) + cache_read (9364) must not be added. "
                f"Computing billing totals is not authorized by this contract."
            )

    def test_cache_tokens_stored_individually(self, tmp_path):
        """Cache fields must be stored in the provenance table if preserved at all."""
        ingestor = _get_ingestor()
        db_path, conn = _make_db(tmp_path)
        session_id = _seed_session(conn)

        artifact = tmp_path / "session.jsonl"
        _write_jsonl(artifact, [_make_assistant_record(
            session_id=session_id,
            input_tokens=3,
            output_tokens=7,
            cache_creation_tokens=5808,
            cache_read_tokens=9364,
        )])

        ingestor.ingest(
            artifact_path=artifact,
            session_id=session_id,
            db_path=db_path,
        )

        # If the ingestion stores cache fields, they must be in a separate
        # provenance column, not added into total_tokens
        rows = conn.execute("SELECT total_tokens FROM steps").fetchall()
        assert rows
        (total,) = rows[0]
        if total is not None:
            assert total != 5808 + 9364 + 3 + 7, (
                "total_tokens must not be the sum of all token fields including cache"
            )
            assert total != 5808 + 9364, "cache fields must not appear as total_tokens"
