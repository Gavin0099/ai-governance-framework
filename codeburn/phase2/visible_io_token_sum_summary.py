from __future__ import annotations

import sqlite3
from typing import Any


SUPPORTED_PROVIDERS = {"codex", "claude-code"}


def build_same_provider_visible_io_token_sum_summary(
    conn: sqlite3.Connection,
    *,
    provider: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build a same-provider visible I/O token observation summary.

    This helper intentionally does not expose a CLI/report surface and does not
    write to the database. The derived value is observation-only and is not a
    billing total, efficiency metric, or cross-provider comparable unit.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            "provider must be one of: " + ", ".join(sorted(SUPPORTED_PROVIDERS))
        )

    where = ["provider = ?"]
    params: list[str] = [provider]
    if session_id is not None:
        where.append("session_id = ?")
        params.append(session_id)

    query = f"""
        SELECT prompt_tokens, completion_tokens
        FROM steps
        WHERE {' AND '.join(where)}
        ORDER BY started_at, rowid
    """
    rows = conn.execute(query, params).fetchall()
    row_count = len(rows)

    missing_prompt = sum(1 for row in rows if row[0] is None)
    missing_completion = sum(1 for row in rows if row[1] is None)
    complete_rows = row_count - max(missing_prompt, missing_completion)

    prompt_sum = None
    completion_sum = None
    visible_sum = None
    missing_reason = None

    if row_count == 0:
        missing_reason = "no_rows"
    elif missing_prompt or missing_completion:
        reasons = []
        if missing_prompt:
            reasons.append("prompt_tokens_missing")
        if missing_completion:
            reasons.append("completion_tokens_missing")
        missing_reason = "+".join(reasons)
    else:
        prompt_sum = sum(int(row[0]) for row in rows)
        completion_sum = sum(int(row[1]) for row in rows)
        visible_sum = prompt_sum + completion_sum

    return {
        "provider": provider,
        "session_id": session_id,
        "summary_scope": "same_provider_session_log_observation",
        "evidence_class": "Class C",
        "acquisition_mode": "session_log_ingestion",
        "visible_io_token_sum": visible_sum,
        "visible_io_token_sum_authority": "observation_only",
        "prompt_tokens_observed": prompt_sum,
        "completion_tokens_observed": completion_sum,
        "row_count": row_count,
        "complete_row_count": complete_rows,
        "missing_prompt_token_rows": missing_prompt,
        "missing_completion_token_rows": missing_completion,
        "missing_field_policy": "null_not_zero",
        "missing_field_reason": missing_reason,
        "billing_truth": False,
        "decision_usage_allowed": False,
        "analysis_safe_for_decision": False,
        "cross_provider_comparable": False,
        "efficiency_inference_allowed": False,
    }

