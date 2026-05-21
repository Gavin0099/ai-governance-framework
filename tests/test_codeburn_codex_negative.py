"""
CodeBurn Codex Artifact Ingestion — Negative-Path Contract Tests
P5.1: written before P5.3 (parser), per CODEBURN_CODEX_INGESTOR_SPEC.md

These tests define what the Codex ingestor MUST NOT do.
All tests are XFAIL until P5.3 (ingest_codex_session implementation) is complete.
When P5.3 is done, all tests must pass.

Negative-path contracts under test:

  NC-1  — total_token_usage MUST NOT be stored as per-turn evidence (IAF-1)
  NC-2  — reasoning_output_tokens MUST NOT appear in any DB column (IAF-2)
  NC-3  — total_tokens MUST be NULL even when Codex provides the value (IAF-3)
  NC-4  — cached_input_tokens MUST NOT be stored (IAF-4)
  NC-5  — SQLite surface MUST be inadmissible (IAF-8): no sqlite path accepted
  NC-6  — session with no token_count records MUST NOT produce zero-token rows
  NC-7  — first-turn camouflage: even when total==last, extraction path is last_token_usage
  NC-8  — multi-turn: total_token_usage diverges; only last_token_usage values stored
  NC-9  — all Codex rows have epistemic_class = 'Class C'
  NC-10 — analysis_safe_for_decision = 0 always
  NC-11 — provider_truthfulness_assumed = 0 always
  NC-12 — Codex rows have provider_name = 'codex', not 'claude' (NST-1 separation)
"""
from __future__ import annotations

import json
import sqlite3
import textwrap
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _get_ingestor():
    """Import the Codex ingestor module."""
    from codeburn.phase2 import codex_log_ingestor
    return codex_log_ingestor


def _make_db(tmp_path: Path) -> tuple[Path, sqlite3.Connection]:
    """Create a test DB with the CodeBurn schema applied."""
    db_path = tmp_path / "test_codex.db"
    schema_path = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()
    return db_path, conn


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _call_ingest(ingestor, jsonl_path: Path, session_id: str, conn: sqlite3.Connection):
    """Call ingest_codex_session; xfail if NotImplementedError (P5.3 not done yet)."""
    try:
        return ingestor.ingest_codex_session(str(jsonl_path), session_id, conn)
    except NotImplementedError:
        pytest.xfail("ingest_codex_session not yet implemented (P5.3)")


# ---------------------------------------------------------------------------
# JSONL record builders
# ---------------------------------------------------------------------------

_SESSION_META = {
    "timestamp": "2026-05-21T01:00:00.000Z",
    "type": "session_meta",
    "payload": {
        "id": "test-session-uuid-0001",
        "cli_version": "0.130.0-alpha.5",
        "model_provider": "openai",
        "cwd": "/home/user/project",
    },
}


def _token_count_record(
    last_input: int,
    last_output: int,
    *,
    last_reasoning: int = 0,
    last_cached: int = 0,
    last_total: int | None = None,
    total_input: int | None = None,
    total_output: int | None = None,
    total_reasoning: int = 0,
    total_cached: int = 0,
    total_total: int | None = None,
    timestamp: str = "2026-05-21T01:01:00.000Z",
) -> dict[str, Any]:
    """Build a Codex event_msg.token_count record with explicit values."""
    if last_total is None:
        last_total = last_input + last_output
    if total_input is None:
        total_input = last_input
    if total_output is None:
        total_output = last_output
    if total_total is None:
        total_total = total_input + total_output

    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": total_input,
                    "cached_input_tokens": total_cached,
                    "output_tokens": total_output,
                    "reasoning_output_tokens": total_reasoning,
                    "total_tokens": total_total,
                },
                "last_token_usage": {
                    "input_tokens": last_input,
                    "cached_input_tokens": last_cached,
                    "output_tokens": last_output,
                    "reasoning_output_tokens": last_reasoning,
                    "total_tokens": last_total,
                },
                "model_context_window": 258400,
            },
            "rate_limits": {
                "used_percent": 5,
                "resets_at": "2026-05-21T02:00:00Z",
            },
        },
    }


_NON_TOKEN_RECORD = {
    "timestamp": "2026-05-21T01:00:30.000Z",
    "type": "response_item",
    "payload": {"content": "some response text"},
}

_SESSION_ID = "test-session-uuid-0001"


# ---------------------------------------------------------------------------
# NC-1: total_token_usage MUST NOT be stored as per-turn evidence (IAF-1)
# ---------------------------------------------------------------------------

def test_nc1_total_token_usage_not_stored_as_per_turn(tmp_path):
    """
    IAF-1: total_token_usage contains cumulative values.
    The per-turn values must come from last_token_usage only.

    This is the non-diverged case (total != last even on a hypothetical turn
    where we force total_input > last_input).
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    # total_input (5000) != last_input (1000) -- must store 1000
    record = _token_count_record(
        last_input=1000, last_output=80,
        total_input=5000, total_output=400,  # larger cumulative values
    )
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    rows = conn.execute(
        "SELECT prompt_tokens, completion_tokens FROM steps WHERE provider = 'codex'"
    ).fetchall()
    assert len(rows) == 1, "Expected exactly one step row"
    # Must store last_token_usage values, NOT total_token_usage values
    assert rows[0]["prompt_tokens"] == 1000, (
        f"NC-1 FAIL: prompt_tokens={rows[0]['prompt_tokens']} but expected 1000 "
        f"(last_token_usage.input_tokens). Got total_token_usage.input_tokens=5000 instead."
    )
    assert rows[0]["completion_tokens"] == 80, (
        f"NC-1 FAIL: completion_tokens={rows[0]['completion_tokens']} but expected 80."
    )


# ---------------------------------------------------------------------------
# NC-2: reasoning_output_tokens MUST NOT appear in any DB column (IAF-2)
# ---------------------------------------------------------------------------

def test_nc2_reasoning_output_tokens_not_in_any_column(tmp_path):
    """
    IAF-2 / Reasoning Separation Principle:
    reasoning_output_tokens must not be stored in any column.
    It must not be added to completion_tokens either.
    completion_tokens = last_token_usage.output_tokens (already excludes reasoning).
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    # last_output=80, last_reasoning=40 → completion_tokens MUST be 80, NOT 120
    record = _token_count_record(
        last_input=1000, last_output=80, last_reasoning=40,
    )
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    # Check that 40 (the reasoning value) does not appear in any numeric column
    row = conn.execute(
        "SELECT * FROM steps WHERE provider = 'codex'"
    ).fetchone()
    assert row is not None

    # completion_tokens must be 80 (output only), not 120 (output + reasoning)
    assert row["completion_tokens"] == 80, (
        f"NC-2 FAIL: completion_tokens={row['completion_tokens']} "
        "should be 80 (output only), not 80+40=120 (reasoning folded in)."
    )
    assert row["completion_tokens"] != 120, (
        "NC-2 FAIL: reasoning_output_tokens was folded into completion_tokens."
    )

    # Verify no column in steps holds the value 40 (reasoning)
    # The sentinel value 40 must not appear anywhere in the row
    for col in row.keys():
        val = row[col]
        if isinstance(val, int) and val == 40:
            pytest.fail(
                f"NC-2 FAIL: reasoning_output_tokens value (40) found in column '{col}'. "
                "reasoning_output_tokens must not be stored in any column (IAF-2)."
            )


# ---------------------------------------------------------------------------
# NC-3: total_tokens MUST be NULL even when Codex provides the value (IAF-3)
# ---------------------------------------------------------------------------

def test_nc3_total_tokens_null_when_codex_provides_it(tmp_path):
    """
    IAF-3: total_tokens policy -- NULL always.
    Codex log explicitly provides total_tokens = 1100.
    The DB must store NULL, not 1100.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    # last_total = 1100 (explicitly set in the record)
    record = _token_count_record(
        last_input=1000, last_output=100, last_total=1100,
        total_total=1100,
    )
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    row = conn.execute(
        "SELECT total_tokens FROM steps WHERE provider = 'codex'"
    ).fetchone()
    assert row is not None
    assert row["total_tokens"] is None, (
        f"NC-3 FAIL: total_tokens={row['total_tokens']} but must be NULL. "
        "Codex explicitly provides total_tokens=1100 in the log, "
        "but IAF-3 forbids storing it."
    )


# ---------------------------------------------------------------------------
# NC-4: cached_input_tokens MUST NOT be stored (IAF-4)
# ---------------------------------------------------------------------------

def test_nc4_cached_input_tokens_not_stored(tmp_path):
    """
    IAF-4: cached_input_tokens -- billing computation forbidden.
    The value 300 must not appear in any column.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    record = _token_count_record(
        last_input=1000, last_output=80, last_cached=300,
    )
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    row = conn.execute(
        "SELECT * FROM steps WHERE provider = 'codex'"
    ).fetchone()
    assert row is not None

    # 300 (cached_input_tokens) must not appear in any column
    for col in row.keys():
        val = row[col]
        if isinstance(val, int) and val == 300:
            pytest.fail(
                f"NC-4 FAIL: cached_input_tokens value (300) found in column '{col}'. "
                "cached_input_tokens must not be stored (IAF-4)."
            )


# ---------------------------------------------------------------------------
# NC-5: SQLite surface MUST be inadmissible (IAF-8)
# ---------------------------------------------------------------------------

def test_nc5_ingest_function_accepts_only_jsonl_path(tmp_path):
    """
    IAF-8 / Dual Acquisition Surface Rule:
    ingest_codex_session() must accept a JSONL file path, not a SQLite path.
    Passing a .sqlite file must raise ValueError (or equivalent rejection).
    There must be no code path that reads from SQLite.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    # Create a fake SQLite file path (doesn't need to exist for this test)
    fake_sqlite_path = tmp_path / "state_5.sqlite"
    fake_sqlite_path.write_bytes(b"SQLite format 3\x00")  # minimal SQLite header

    try:
        ingestor.ingest_codex_session(str(fake_sqlite_path), _SESSION_ID, conn)
    except NotImplementedError:
        pytest.xfail("ingest_codex_session not yet implemented (P5.3)")
    except (ValueError, IOError, TypeError):
        pass  # correct: SQLite path rejected
    else:
        pytest.fail(
            "NC-5 FAIL: ingest_codex_session accepted a .sqlite file path without error. "
            "IAF-8: SQLite acquisition surface must be inadmissible."
        )


def test_nc5b_ingest_function_signature_has_no_sqlite_param(tmp_path):
    """
    IAF-8: The ingest_codex_session function must not have a SQLite path parameter.
    Verified by inspecting the function signature.
    """
    import inspect
    ingestor = _get_ingestor()
    sig = inspect.signature(ingestor.ingest_codex_session)
    param_names = list(sig.parameters.keys())

    sqlite_params = [p for p in param_names if "sqlite" in p.lower() or "db_path" == p]
    assert not sqlite_params, (
        f"NC-5b FAIL: ingest_codex_session has SQLite-related parameter(s): {sqlite_params}. "
        "IAF-8: no SQLite acquisition path is permitted."
    )


# ---------------------------------------------------------------------------
# NC-6: session with no token_count records MUST NOT produce zero-token rows
# ---------------------------------------------------------------------------

def test_nc6_empty_session_produces_no_token_rows(tmp_path):
    """
    A Codex session with no event_msg.token_count records:
    - MUST produce 0 rows in steps
    - MUST NOT produce 1 row with prompt_tokens=0, completion_tokens=0

    Absence is the observation. It must not be coerced into zero.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    # Session with only a session_meta and a response_item, no token_count
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, _NON_TOKEN_RECORD])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    rows = conn.execute(
        "SELECT * FROM steps WHERE provider = 'codex'"
    ).fetchall()
    assert len(rows) == 0, (
        f"NC-6 FAIL: {len(rows)} step row(s) created for a session with no token_count records. "
        "A session with no token_count records must produce zero step rows, "
        "not a row with zero tokens."
    )


# ---------------------------------------------------------------------------
# NC-7: first-turn camouflage -- total==last on turn 1, source path still matters
# ---------------------------------------------------------------------------

def test_nc7_first_turn_total_equals_last_uses_last_extraction_path(tmp_path):
    """
    AR-1b (First-Turn Cumulative Camouflage):
    On turn 1, total_token_usage == last_token_usage.
    This is the camouflage window -- both read the same value.
    The implementation MUST read from last_token_usage path, not total_token_usage.
    This is verified via NC-8 (multi-turn) where they diverge.
    NC-7 documents the turn-1 baseline.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    # Turn 1: total == last (both 1000/80) -- this is normal for turn 1
    record = _token_count_record(
        last_input=1000, last_output=80,
        total_input=1000, total_output=80,  # equal on turn 1
    )
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    row = conn.execute(
        "SELECT prompt_tokens, completion_tokens FROM steps WHERE provider = 'codex'"
    ).fetchone()
    assert row is not None
    # Values are the same whether from last or total -- but path must be last
    assert row["prompt_tokens"] == 1000
    assert row["completion_tokens"] == 80
    # The actual path enforcement is proven by NC-8


# ---------------------------------------------------------------------------
# NC-8: multi-turn -- total diverges from last; only last values stored
# ---------------------------------------------------------------------------

def test_nc8_multiturn_second_turn_uses_last_not_total(tmp_path):
    """
    AR-1b + NC-1 combined: multi-turn verification.

    Turn 1: total_input=1000, last_input=1000 (equal -- camouflage)
    Turn 2: total_input=3000, last_input=2000 (diverge -- trap)

    Stored turn 2 prompt_tokens MUST be 2000, NOT 3000.
    If implementation uses total_token_usage, it would store 3000.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    turn1 = _token_count_record(
        last_input=1000, last_output=80,
        total_input=1000, total_output=80,
        timestamp="2026-05-21T01:01:00.000Z",
    )
    turn2 = _token_count_record(
        last_input=2000, last_output=200,       # per-turn: 2000
        total_input=3000, total_output=280,      # cumulative: 3000 = 1000 + 2000
        timestamp="2026-05-21T01:02:00.000Z",
    )

    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, turn1, turn2])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    rows = conn.execute(
        "SELECT prompt_tokens, completion_tokens FROM steps WHERE provider = 'codex' "
        "ORDER BY started_at"
    ).fetchall()
    assert len(rows) == 2, f"Expected 2 step rows (one per turn), got {len(rows)}"

    # Turn 1
    assert rows[0]["prompt_tokens"] == 1000, (
        f"NC-8 FAIL: Turn 1 prompt_tokens={rows[0]['prompt_tokens']}, expected 1000."
    )
    # Turn 2 -- critical assertion
    assert rows[1]["prompt_tokens"] == 2000, (
        f"NC-8 FAIL: Turn 2 prompt_tokens={rows[1]['prompt_tokens']}, expected 2000 "
        "(last_token_usage.input_tokens). "
        f"If 3000 was stored, total_token_usage was used instead of last_token_usage."
    )
    assert rows[1]["completion_tokens"] == 200, (
        f"NC-8 FAIL: Turn 2 completion_tokens={rows[1]['completion_tokens']}, expected 200."
    )


# ---------------------------------------------------------------------------
# NC-9: all Codex rows have epistemic_class = 'Class C'
# ---------------------------------------------------------------------------

def test_nc9_all_codex_rows_are_class_c(tmp_path):
    """
    Epistemic invariant: all Codex ingested rows must have epistemic_class = 'Class C'.
    Class C is not configurable and not upgradeable by any ingestion parameter.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    record = _token_count_record(last_input=500, last_output=40)
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    provenance_rows = conn.execute(
        "SELECT epistemic_class FROM step_ingestion_provenance WHERE provider = 'codex'"
    ).fetchall()
    assert len(provenance_rows) >= 1, "Expected at least one provenance row"
    for row in provenance_rows:
        assert row["epistemic_class"] == "Class C", (
            f"NC-9 FAIL: epistemic_class='{row['epistemic_class']}', expected 'Class C'. "
            "Codex evidence is Class C unconditionally."
        )


# ---------------------------------------------------------------------------
# NC-10: analysis_safe_for_decision = 0 always
# ---------------------------------------------------------------------------

def test_nc10_analysis_safe_for_decision_is_zero(tmp_path):
    """
    Authority Ceiling Contract AC4:
    analysis_safe_for_decision must be 0 for all Codex rows.
    The schema CHECK constraint also enforces this, but the ingestor
    must never attempt to set it to 1.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    record = _token_count_record(last_input=500, last_output=40)
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    rows = conn.execute(
        "SELECT analysis_safe_for_decision FROM step_ingestion_provenance WHERE provider = 'codex'"
    ).fetchall()
    assert len(rows) >= 1
    for row in rows:
        assert row["analysis_safe_for_decision"] == 0, (
            f"NC-10 FAIL: analysis_safe_for_decision={row['analysis_safe_for_decision']}, "
            "must be 0. Class C evidence is never analysis-safe for decision."
        )


# ---------------------------------------------------------------------------
# NC-11: provider_truthfulness_assumed = 0 always
# ---------------------------------------------------------------------------

def test_nc11_provider_truthfulness_assumed_is_zero(tmp_path):
    """
    Authority Ceiling Contract AC5:
    provider_truthfulness_assumed must be 0 for all Codex rows.
    CodeBurn observes what Codex reports; it cannot verify Codex's computation.
    This applies to Codex identically to Claude.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    record = _token_count_record(last_input=500, last_output=40)
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    rows = conn.execute(
        "SELECT provider_truthfulness_assumed FROM step_ingestion_provenance "
        "WHERE provider = 'codex'"
    ).fetchall()
    assert len(rows) >= 1
    for row in rows:
        assert row["provider_truthfulness_assumed"] == 0, (
            f"NC-11 FAIL: provider_truthfulness_assumed={row['provider_truthfulness_assumed']}, "
            "must be 0. CodeBurn does not assume provider truthfulness (FSP-4)."
        )


# ---------------------------------------------------------------------------
# NC-12: Codex rows have provider = 'codex', not 'claude' (NST-1 separation)
# ---------------------------------------------------------------------------

def test_nc12_codex_rows_have_codex_provider_name(tmp_path):
    """
    NST-1 / Schema separation:
    Codex rows must carry provider = 'codex', distinct from 'claude'.
    This label is the primary enforcement mechanism preventing cross-provider aggregation.
    A query for provider='claude' must not return Codex rows.
    """
    ingestor = _get_ingestor()
    _, conn = _make_db(tmp_path)

    record = _token_count_record(last_input=500, last_output=40)
    jsonl_path = tmp_path / "session.jsonl"
    _write_jsonl(jsonl_path, [_SESSION_META, record])

    _call_ingest(ingestor, jsonl_path, _SESSION_ID, conn)

    # Provider must be 'codex'
    codex_rows = conn.execute(
        "SELECT provider FROM steps WHERE provider = 'codex'"
    ).fetchall()
    assert len(codex_rows) >= 1, (
        "NC-12 FAIL: No step rows with provider='codex'. "
        "Codex ingestion must label rows with provider='codex'."
    )

    # Provider must NOT be 'claude'
    misclassified = conn.execute(
        "SELECT provider FROM steps WHERE provider = 'claude'"
    ).fetchall()
    assert len(misclassified) == 0, (
        f"NC-12 FAIL: {len(misclassified)} step row(s) have provider='claude' "
        "after Codex ingestion. Codex rows must be labeled 'codex', not 'claude'."
    )
