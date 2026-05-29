"""
CodeBurn -- Claude Code JSONL Ingestor (Phase 2)

Discovers and ingests Claude Code session JSONL from ~/.claude/projects/ as
Class C (observer-reconstructed) evidence.

Epistemic contract:
  - All evidence produced is Class C unconditionally
  - real_time_observed = 0 always (schema also enforces this)
  - analysis_safe_for_decision = 0 always (schema also enforces this)
  - provider_truthfulness_assumed = 0 always (schema also enforces this)
  - total_tokens = NULL always (no billing computation authorized)
  - missing token fields → NULL, never 0
  - malformed records → quarantined_records, never silently dropped
  - cache token fields (cache_creation_input_tokens, cache_read_input_tokens)
    are not stored — no billing total authorized
  - inadmissible fields (costUSD, service_tier, inference_geo) not read or stored

Source format (Claude Code JSONL, ~/.claude/projects/**/*.jsonl):
  - type="assistant" rows carry token evidence
  - message.usage.input_tokens  → prompt_tokens
  - message.usage.output_tokens → completion_tokens
  - Other types (human, tool_use, tool_result, system, etc.) are skipped

Independent implementation: this module does not import from or depend on
codeburn/phase1/claude_log_ingestor.py.  The formats are the same, but the
ingestors are separate to allow divergent provenance tracking.

Acquisition authority: L1.5 maximum (CODEBURN_ACQUISITION_AUTHORITY_MODEL.md)
This module never wraps, intercepts, or modifies AI runtime invocations.

provider = 'claude-code' (distinct from phase1 'claude', NST-1 principle).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Hard-coded epistemic constants — not configurable
_PROVIDER = "claude-code"
_EPISTEMIC_CLASS = "Class C"
_ACQUISITION_MODE = "session_log_ingestion"
_REAL_TIME_OBSERVED = 0           # Class C is always post-hoc
_ANALYSIS_SAFE_FOR_DECISION = 0   # permanent per Authority Ceiling Contract AC4
_PROVIDER_TRUTHFULNESS_ASSUMED = 0  # CodeBurn observes reports, not computation


@dataclass
class ClaudeCodeIngestResult:
    """Result of ingesting one Claude Code JSONL session file.

    Counts are informational only. They do not imply completeness
    or correctness of the underlying Claude Code log.
    """
    session_id: str
    source_artifact_path: str
    records_scanned: int = 0
    records_admitted: int = 0
    records_skipped: int = 0      # non-assistant records (structurally valid)
    records_quarantined: int = 0  # malformed assistant records
    step_ids: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quarantine(
    conn: sqlite3.Connection,
    source_artifact_path: str,
    source_record_line: int,
    source_record_offset: Optional[int],
    reason: str,
    raw_record: Optional[str],
) -> None:
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
            f"claude-code-auto-ingestion:{source_record_id or 'unknown'}",
            started_at,
            _PROVIDER,
            prompt_tokens,      # NULL if absent — invariant I2
            completion_tokens,  # NULL if absent — invariant I2
            None,               # total_tokens: never computed — billing contract
            "estimated",        # Class C evidence is 'estimated', not 'provider'
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
    return step_id


def _ensure_session_row(conn: sqlite3.Connection, session_id: str) -> None:
    existing = conn.execute(
        "SELECT 1 FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if existing is not None:
        return
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO sessions(
            session_id, task, created_at, data_quality
        ) VALUES(?, ?, ?, ?)
        """,
        (session_id, "claude_code_auto_ingestion", now, "partial"),
    )


def find_claude_session_jsonl(
    claude_session_id: Optional[str] = None,
) -> Optional[Path]:
    """Discover the Claude Code session JSONL from ~/.claude/projects/.

    If claude_session_id is provided (the Claude Code internal session UUID),
    tries exact filename stem match first across all project directories.

    Falls back to the most recently modified JSONL in ~/.claude/projects/
    when no exact match is found.

    Returns None if ~/.claude/projects/ does not exist or no JSONL is found.

    This function is fail-silent: any filesystem error returns None.
    """
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return None

    # 1) Exact stem match by Claude Code session UUID
    if claude_session_id:
        try:
            for p in root.rglob("*.jsonl"):
                if p.stem == claude_session_id:
                    return p
        except Exception:
            pass

    # 2) Most recently modified JSONL in ~/.claude/projects/
    newest_path: Optional[Path] = None
    newest_mtime: float = -1.0
    try:
        for p in root.rglob("*.jsonl"):
            name = p.name.lower()
            # Exclude known non-session JSONL artifacts
            if name == "session_index.jsonl":
                continue
            if "observed-usage" in name:
                continue
            try:
                mtime = p.stat().st_mtime
            except Exception:
                continue
            if mtime > newest_mtime:
                newest_mtime = mtime
                newest_path = p
    except Exception:
        pass

    return newest_path


def ingest_claude_code_session(
    session_jsonl_path: str,
    session_id: str,
    conn: sqlite3.Connection,
) -> ClaudeCodeIngestResult:
    """Ingest one Claude Code session JSONL file as Class C evidence.

    Reads type="assistant" records and extracts message.usage.input_tokens
    and message.usage.output_tokens.  All other record types are skipped.

    Parameters
    ----------
    session_jsonl_path:
        Absolute path to the Claude Code session JSONL file.
    session_id:
        The governance closeout session_id.  This is the DB key — it is not
        the Claude Code internal session UUID.
    conn:
        Open SQLite connection. Schema must already be applied.

    Returns
    -------
    ClaudeCodeIngestResult
        Ingestion summary.

    Raises
    ------
    FileNotFoundError
        If session_jsonl_path does not exist.
    ValueError
        If session_id is empty or session_jsonl_path is not a .jsonl file.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be non-empty")
    if not session_jsonl_path.lower().endswith(".jsonl"):
        raise ValueError("session_jsonl_path must point to a .jsonl file")

    artifact_path = Path(session_jsonl_path)
    if not artifact_path.exists():
        raise FileNotFoundError(session_jsonl_path)

    source_path_str = str(artifact_path.resolve())
    _ensure_session_row(conn, session_id)
    result = ClaudeCodeIngestResult(
        session_id=session_id,
        source_artifact_path=source_path_str,
    )

    byte_offset = 0
    with artifact_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line_offset = byte_offset
            byte_offset += len(raw_line.encode("utf-8", errors="replace"))
            raw_stripped = raw_line.rstrip("\n\r")
            result.records_scanned += 1

            # Step 1: parse JSON — malformed → quarantine
            try:
                record = json.loads(raw_stripped)
            except json.JSONDecodeError as exc:
                _quarantine(
                    conn,
                    source_path_str,
                    line_number,
                    line_offset,
                    f"json_parse_error: {exc}",
                    raw_stripped,
                )
                result.records_quarantined += 1
                continue

            if not isinstance(record, dict):
                result.records_skipped += 1
                continue

            # Step 2: record type filter — only type=assistant carries token evidence
            if record.get("type") != "assistant":
                result.records_skipped += 1
                continue

            # Step 3: structural validation
            message = record.get("message")
            if not isinstance(message, dict):
                _quarantine(
                    conn,
                    source_path_str,
                    line_number,
                    line_offset,
                    "unexpected_structure: message is not a dict",
                    raw_stripped,
                )
                result.records_quarantined += 1
                continue

            # Step 4: extract admissible fields
            source_record_id = record.get("uuid") or record.get("requestId")
            source_record_timestamp = record.get("timestamp")

            # Step 5: extract token usage — may be absent (valid state)
            usage = message.get("usage")
            prompt_tokens: Optional[int] = None
            completion_tokens: Optional[int] = None

            if isinstance(usage, dict):
                raw_input = usage.get("input_tokens")
                raw_output = usage.get("output_tokens")
                # Accept only integer values — do not infer or estimate
                if isinstance(raw_input, int):
                    prompt_tokens = raw_input
                if isinstance(raw_output, int):
                    completion_tokens = raw_output
                # Explicitly NOT reading:
                #   cache_creation_input_tokens — no billing computation authorized
                #   cache_read_input_tokens     — no billing computation authorized
                #   costUSD                     — inadmissible (billing metric)
                #   service_tier                — inadmissible (operational metadata)

            # Step 6: write Class C evidence
            step_id = _write_class_c_evidence(
                conn,
                session_id,
                source_path_str,
                line_number,
                line_offset,
                source_record_id,
                source_record_timestamp,
                prompt_tokens,
                completion_tokens,
            )
            result.step_ids.append(step_id)
            result.records_admitted += 1

    conn.commit()
    return result
