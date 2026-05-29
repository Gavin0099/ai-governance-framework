#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def find_latest_codeburn_db(repo_path: Path) -> Path | None:
    patterns = [
        "codeburn/phase1/examples/*.db",
        "artifacts/codeburn*.db",
        "artifacts/*codeburn*.db",
    ]
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(repo_path.glob(pat))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _session_token_sums(conn: sqlite3.Connection, session_id: str) -> tuple[int, int] | None:
    row = conn.execute(
        """
        SELECT
          SUM(CASE WHEN prompt_tokens IS NOT NULL THEN prompt_tokens ELSE 0 END),
          SUM(CASE WHEN completion_tokens IS NOT NULL THEN completion_tokens ELSE 0 END)
        FROM steps
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None
    return int(row[0] or 0), int(row[1] or 0)


def _latest_session_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1").fetchone()
    if not row:
        return None
    return str(row[0])


def build_codeburn_token_observation(repo_path: Path, preferred_session_id: str | None = None) -> dict[str, Any]:
    db_path = find_latest_codeburn_db(repo_path)
    if db_path is None:
        return {
            "summary_text": "tokens=NA; reason=no_codeburn_record; authority=analysis-only; decision_authority=none",
            "scope": "NA",
            "warning": "",
            "reason": "no_codeburn_record",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
    try:
        conn = sqlite3.connect(str(db_path))
        target_session_id: str | None = None
        scope = "latest_db_record_unbound"
        warning = "not_bound_to_current_closeout"
        reason = ""
        sums: tuple[int, int] | None = None

        if preferred_session_id:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? LIMIT 1",
                (preferred_session_id,),
            ).fetchone()
            if row is not None:
                target_session_id = preferred_session_id
                sums = _session_token_sums(conn, target_session_id)
                scope = "current_session"
                warning = ""

        if sums is None:
            target_session_id = _latest_session_id(conn)
            if target_session_id is None:
                conn.close()
                return {
                    "summary_text": "tokens=NA; reason=no_codeburn_record; authority=analysis-only; decision_authority=none",
                    "scope": "NA",
                    "warning": "",
                    "reason": "no_codeburn_record",
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                }
            sums = _session_token_sums(conn, target_session_id)

        conn.close()
        if not sums:
            return {
                "summary_text": "tokens=NA; reason=no_codeburn_record; authority=analysis-only; decision_authority=none",
                "scope": "NA",
                "warning": "",
                "reason": "no_codeburn_record",
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            }
        prompt = int(sums[0] or 0)
        completion = int(sums[1] or 0)
        total = prompt + completion
        warning_part = f"; warning={warning}" if warning else ""
        reason_part = f"; reason={reason}" if reason else ""
        text = (
            f"tokens=input:{prompt}, output:{completion}, total:{total}; "
            f"scope={scope}{warning_part}{reason_part}; "
            "authority=analysis-only; decision_authority=none"
        )
        return {
            "summary_text": text,
            "scope": scope,
            "warning": warning,
            "reason": reason,
            "input_tokens": prompt,
            "output_tokens": completion,
            "total_tokens": total,
        }
    except Exception:
        return {
            "summary_text": "tokens=NA; reason=token_lookup_error; authority=analysis-only; decision_authority=none",
            "scope": "NA",
            "warning": "",
            "reason": "token_lookup_error",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }


def compute_codeburn_token_summary(repo_path: Path, preferred_session_id: str | None = None) -> str:
    return str(build_codeburn_token_observation(repo_path, preferred_session_id).get("summary_text", "tokens=NA; reason=token_lookup_error; authority=analysis-only; decision_authority=none"))
