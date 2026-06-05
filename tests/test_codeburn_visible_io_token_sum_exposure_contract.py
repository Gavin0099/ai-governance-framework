from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from codeburn.phase2.visible_io_token_sum_summary import (
    build_same_provider_visible_io_token_sum_summary,
)


ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "codeburn" / "phase1" / "schema.sql"


REQUIRED_EXPOSURE_FIELDS = {
    "provider",
    "summary_scope",
    "evidence_class",
    "acquisition_mode",
    "visible_io_token_sum",
    "visible_io_token_sum_authority",
    "billing_truth",
    "decision_usage_allowed",
    "analysis_safe_for_decision",
    "cross_provider_comparable",
    "efficiency_inference_allowed",
    "missing_field_policy",
    "missing_field_reason",
}


def _make_db(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "visible_io_exposure.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO sessions(session_id, task, created_at, data_quality)
        VALUES('s1', 'visible-io-exposure-test', '2026-06-05T00:00:00Z', 'partial')
        """,
    )
    return conn


def _insert_step(
    conn: sqlite3.Connection,
    *,
    provider: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    step_id: str = "step-1",
) -> None:
    conn.execute(
        """
        INSERT INTO steps(
            step_id, session_id, step_kind, command, started_at, provider,
            prompt_tokens, completion_tokens, total_tokens, token_source
        ) VALUES(?, 's1', 'other', 'seed', '2026-06-05T00:00:01Z', ?, ?, ?, NULL, 'estimated')
        """,
        (step_id, provider, prompt_tokens, completion_tokens),
    )


def test_future_exposure_payload_contains_required_observation_disclosures(tmp_path):
    conn = _make_db(tmp_path)
    _insert_step(conn, provider="codex", prompt_tokens=120, completion_tokens=30)

    payload = build_same_provider_visible_io_token_sum_summary(conn, provider="codex")

    assert REQUIRED_EXPOSURE_FIELDS <= set(payload)
    assert payload["visible_io_token_sum"] == 150
    assert payload["evidence_class"] == "Class C"
    assert payload["visible_io_token_sum_authority"] == "observation_only"
    assert payload["billing_truth"] is False
    assert payload["decision_usage_allowed"] is False
    assert payload["analysis_safe_for_decision"] is False
    assert payload["cross_provider_comparable"] is False
    assert payload["efficiency_inference_allowed"] is False
    assert "total_tokens" not in payload

    # Future report/CLI surfaces must be able to emit the same conservative
    # disclosure payload without adding non-contract fields.
    json.dumps(payload, sort_keys=True)


def test_future_exposure_payload_preserves_null_not_zero_missing_field_boundary(tmp_path):
    conn = _make_db(tmp_path)
    _insert_step(conn, provider="claude-code", prompt_tokens=None, completion_tokens=30)

    payload = build_same_provider_visible_io_token_sum_summary(
        conn,
        provider="claude-code",
    )

    assert REQUIRED_EXPOSURE_FIELDS <= set(payload)
    assert payload["visible_io_token_sum"] is None
    assert payload["prompt_tokens_observed"] is None
    assert payload["completion_tokens_observed"] is None
    assert payload["missing_field_policy"] == "null_not_zero"
    assert payload["missing_field_reason"] == "prompt_tokens_missing"
    assert "total_tokens" not in payload


def test_future_exposure_contract_does_not_create_report_or_cli_surface():
    report_or_cli_files = [
        ROOT / "codeburn" / "phase1" / "codeburn_report.py",
        ROOT / "codeburn" / "phase1" / "codeburn_session_display.py",
        ROOT / "codeburn" / "phase1" / "codeburn_run.py",
        ROOT / "codeburn" / "phase2" / "codeburn_codex_smoke.py",
        ROOT / "codeburn" / "phase2" / "codeburn_copilot_smoke.py",
        ROOT / "codeburn" / "phase2" / "codeburn_manual_usage_ingest.py",
    ]

    offenders = [
        str(path.relative_to(ROOT))
        for path in report_or_cli_files
        if "visible_io_token_sum" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
