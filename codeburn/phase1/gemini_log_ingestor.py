"""
CodeBurn — Gemini CLI Log Ingestor

Ingests Gemini CLI .jsonl (and legacy .json) session logs as Class C
(observer-reconstructed) evidence.

Epistemic contract:
  - All evidence produced is Class C unconditionally
  - real_time_observed = 0 always (schema also enforces this)
  - analysis_safe_for_decision = 0 always (schema also enforces this)
  - provider_truthfulness_assumed = 0 always (schema also enforces this)
  - missing token fields -> NULL, never 0
  - malformed records -> quarantined_records, never silently dropped
  - no aggregation, no estimation, no billing computation
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_PROVIDER = "gemini"
_EPISTEMIC_CLASS = "Class C"
_ACQUISITION_MODE = "session_log_ingestion"
_REAL_TIME_OBSERVED = 0
_ANALYSIS_SAFE_FOR_DECISION = 0
_PROVIDER_TRUTHFULNESS_ASSUMED = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).resolve().with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def _quarantine(
    conn: sqlite3.Connection,
    source_artifact_path: str,
    source_record_line: int,
    source_record_offset: Optional[int],
    reason: str,
    raw_record: Optional[str],
) -> None:
    """Persist a malformed or inadmissible record to quarantined_records."""
    conn.execute(
        """
        INSERT INTO quarantined_records(
            provider, source_artifact_path, source_record_line, source_record_offset,
            reason, raw_record, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _PROVIDER,
            source_artifact_path,
            source_record_line,
            source_record_offset,
            reason,
            raw_record[:4096] if raw_record else None,
            _now_iso(),
        ),
    )
    conn.commit()


def _write_class_c_evidence(
    conn: sqlite3.Connection,
    session_id: str,
    source_artifact_path: str,
    source_record_line: int,
    source_record_offset: Optional[int],
    source_record_id: Optional[str],
    source_record_timestamp: Optional[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> str:
    """Write one Class C step + provenance row."""
    step_id = str(uuid.uuid4())
    started_at = source_record_timestamp or _now_iso()

    conn.execute(
        """
        INSERT INTO steps(
            step_id, session_id, step_kind, command,
            started_at, provider,
            prompt_tokens, completion_tokens, total_tokens,
            token_source
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            step_id,
            session_id,
            "other",
            f"gemini-log-ingestion:{source_record_id or 'unknown'}",
            started_at,
            _PROVIDER,
            prompt_tokens,
            completion_tokens,
            None,
            "estimated",
        ),
    )

    conn.execute(
        """
        INSERT INTO step_ingestion_provenance(
            step_id, provider, epistemic_class, acquisition_mode,
            source_artifact_path, source_record_line, source_record_offset,
            real_time_observed, analysis_safe_for_decision,
            provider_truthfulness_assumed, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            step_id,
            _PROVIDER,
            _EPISTEMIC_CLASS,
            _ACQUISITION_MODE,
            source_artifact_path,
            source_record_line,
            source_record_offset,
            _REAL_TIME_OBSERVED,
            _ANALYSIS_SAFE_FOR_DECISION,
            _PROVIDER_TRUTHFULNESS_ASSUMED,
            _now_iso(),
        ),
    )

    conn.commit()
    return step_id


def ingest(
    artifact_path: "Path | str",
    session_id: str,
    db_path: "Path | str",
) -> dict:
    """Ingest a Gemini CLI .jsonl session log as Class C evidence."""
    artifact_path = Path(artifact_path).resolve()
    db_path = Path(db_path)
    source_path_str = str(artifact_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_schema(conn)

    processed = 0
    skipped = 0
    quarantined = 0

    with open(artifact_path, "r", encoding="utf-8", errors="replace") as f:
        byte_offset = 0
        for line_number, raw_line in enumerate(f, start=1):
            line_byte_offset = byte_offset
            byte_offset += len(raw_line.encode("utf-8", errors="replace"))
            raw_stripped = raw_line.rstrip("\n\r")
            if not raw_stripped.strip():
                skipped += 1
                continue

            try:
                record = json.loads(raw_stripped)
            except json.JSONDecodeError as exc:
                _quarantine(
                    conn,
                    source_path_str,
                    line_number,
                    line_byte_offset,
                    f"json_parse_error: {exc}",
                    raw_stripped,
                )
                quarantined += 1
                continue

            if not isinstance(record, dict):
                _quarantine(
                    conn,
                    source_path_str,
                    line_number,
                    line_byte_offset,
                    "unexpected_structure: record is not a dict",
                    raw_stripped,
                )
                quarantined += 1
                continue

            record_type = record.get("type")
            if record_type != "gemini":
                skipped += 1
                continue

            tokens = record.get("tokens")
            if tokens is not None and not isinstance(tokens, dict):
                _quarantine(
                    conn,
                    source_path_str,
                    line_number,
                    line_byte_offset,
                    "unexpected_structure: tokens is not a dict",
                    raw_stripped,
                )
                quarantined += 1
                continue

            source_record_id = record.get("id") if isinstance(record.get("id"), str) else None
            source_record_timestamp = (
                record.get("timestamp") if isinstance(record.get("timestamp"), str) else None
            )

            prompt_tokens: Optional[int] = None
            completion_tokens: Optional[int] = None
            if isinstance(tokens, dict):
                raw_input = tokens.get("input")
                raw_output = tokens.get("output")
                if isinstance(raw_input, int) and not isinstance(raw_input, bool):
                    prompt_tokens = raw_input
                if isinstance(raw_output, int) and not isinstance(raw_output, bool):
                    completion_tokens = raw_output

            _write_class_c_evidence(
                conn,
                session_id,
                source_path_str,
                line_number,
                line_byte_offset,
                source_record_id,
                source_record_timestamp,
                prompt_tokens,
                completion_tokens,
            )
            processed += 1

    conn.close()

    return {
        "ok": True,
        "artifact_path": source_path_str,
        "session_id": session_id,
        "processed": processed,
        "skipped": skipped,
        "quarantined": quarantined,
        "epistemic_class": _EPISTEMIC_CLASS,
        "real_time_observed": False,
        "analysis_safe_for_decision": False,
        "provider_truthfulness_assumed": False,
    }
