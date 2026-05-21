"""
CodeBurn -- Codex Log Ingestor (P5.3 stub)

Ingests Codex CLI session JSONL logs as Class C (observer-reconstructed) evidence.

Epistemic contract (CODEBURN_CODEX_ARTIFACT_CONTRACT.md):
  - All evidence produced is Class C unconditionally
  - real_time_observed = 0 always (schema also enforces this)
  - analysis_safe_for_decision = 0 always (schema also enforces this)
  - provider_truthfulness_assumed = 0 always (schema also enforces this)
  - total_tokens = NULL always (even when Codex log provides it explicitly)
  - missing token fields → NULL, never 0
  - malformed records → quarantined_records, never silently dropped
  - total_token_usage.* → NEVER stored (IAF-1, cumulative not turn-scoped)
  - reasoning_output_tokens → NEVER stored (IAF-2, Reasoning Separation Principle)
  - cached_input_tokens → NEVER stored (IAF-4, billing computation forbidden)
  - SQLite surface → NEVER used as acquisition path (IAF-8)
  - provider = 'codex', distinct from 'claude' (NST-1 cross-comparability prevention)

Acquisition authority: L1.5 maximum (CODEBURN_ACQUISITION_AUTHORITY_MODEL.md)
This module never wraps, intercepts, or modifies AI runtime invocations.

Status: P5.3 stub -- raises NotImplementedError until implementation.
Negative-path tests in tests/test_codeburn_codex_negative.py are XFAIL until
this stub is replaced with a real implementation.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

# Hard-coded epistemic constants — not configurable
_PROVIDER = "codex"
_EPISTEMIC_CLASS = "Class C"
_ACQUISITION_MODE = "session_log_ingestion"
_REAL_TIME_OBSERVED = 0           # Class C is always post-hoc
_ANALYSIS_SAFE_FOR_DECISION = 0   # permanent per Authority Ceiling Contract AC4
_PROVIDER_TRUTHFULNESS_ASSUMED = 0  # CodeBurn observes reports, not computation


@dataclass
class CodexIngestResult:
    """Result of ingesting one Codex JSONL session file.

    Counts are informational only. They do not imply completeness
    or correctness of the underlying Codex log.
    """
    session_id: str
    source_artifact_path: str
    records_scanned: int = 0
    records_admitted: int = 0
    records_skipped: int = 0      # non-token records (structurally valid, not token_count)
    records_quarantined: int = 0  # malformed token_count records
    step_ids: list[str] = field(default_factory=list)


def ingest_codex_session(
    session_jsonl_path: str,
    session_id: str,
    conn: sqlite3.Connection,
) -> CodexIngestResult:
    """Ingest one Codex CLI session JSONL file.

    Parameters
    ----------
    session_jsonl_path:
        Absolute path to the Codex session JSONL file.
    session_id:
        The Codex session UUID. Caller is responsible for extraction
        (from filename UUID portion or session_meta.payload.id).
    conn:
        Open SQLite connection. Schema must already be applied.

    Returns
    -------
    CodexIngestResult
        Ingestion summary. Does not include token values -- callers
        must query the DB directly for token evidence.

    Raises
    ------
    NotImplementedError
        Until P5.3 implementation is complete.
    FileNotFoundError
        If session_jsonl_path does not exist.
    ValueError
        If session_id is empty or session_jsonl_path is not a JSONL file.
    """
    raise NotImplementedError(
        "ingest_codex_session not yet implemented (P5.3). "
        "See CODEBURN_CODEX_INGESTOR_SPEC.md for the contract. "
        "Negative-path tests in test_codeburn_codex_negative.py define what "
        "the implementation MUST NOT do."
    )
