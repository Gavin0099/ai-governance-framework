from __future__ import annotations

import sqlite3
from pathlib import Path

from codeburn.phase2.copilot_billing_ingestor import ingest_copilot_csv
from codeburn.phase2.copilot_billing_report import build_copilot_billing_report
from codeburn.phase2.copilot_billing_summary import (
    build_copilot_billing_summary,
    build_copilot_billing_summary_from_contract,
)

SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"
MULTI_MODEL_FIXTURE = (
    Path(__file__).parent.parent
    / "codeburn"
    / "phase2"
    / "examples"
    / "copilot_gap_multi_model_mix.csv"
)


def _seed_multi_model_db(tmp_path: Path) -> Path:
    db = tmp_path / "cp4_multi.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    ingest_copilot_csv(str(MULTI_MODEL_FIXTURE), conn, mark_final=False)
    conn.commit()
    conn.close()
    return db


def _seed_single_model_db(tmp_path: Path) -> Path:
    db = tmp_path / "cp4_single.db"
    csv_path = tmp_path / "single_model_cp4.csv"
    csv_path.write_text(
        "date,user_login,model,aic_quantity,aic_gross_amount\n"
        "2026-05-21,alice,gpt-4.1,4.0,0.11\n"
        "2026-05-21,bob,gpt-4.1,5.0,0.12\n",
        encoding="utf-8",
    )
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    ingest_copilot_csv(str(csv_path), conn, mark_final=False)
    conn.commit()
    conn.close()
    return db


def test_consumer_multi_model_no_scope_must_not_render_aggregate_total(tmp_path):
    db = _seed_multi_model_db(tmp_path)
    summary = build_copilot_billing_summary(db)
    assert summary["ok"] is True
    assert summary["summary_mode"] == "grouped_only"
    assert summary["aggregate_total_rendered"] is False
    assert summary["aggregate_total"] is None
    assert len(summary["grouped_by_model"]) >= 2


def test_consumer_explicit_scope_may_render_scoped_total_with_scope_label(tmp_path):
    db = _seed_multi_model_db(tmp_path)
    report = build_copilot_billing_report(db)
    model_scope = report["grouped_by_model"][0]["model"]
    summary = build_copilot_billing_summary(db, model_scope=model_scope)
    assert summary["ok"] is True
    assert summary["summary_mode"] == "scoped_total"
    assert summary["aggregate_total_rendered"] is True
    assert summary["aggregate_total"] is not None
    assert summary["scope_label"] == f"model_scope={model_scope}"


def test_consumer_single_model_implicit_total_with_scope_label(tmp_path):
    db = _seed_single_model_db(tmp_path)
    summary = build_copilot_billing_summary(db)
    assert summary["ok"] is True
    assert summary["summary_mode"] == "implicit_single_model_total"
    assert summary["aggregate_total_rendered"] is True
    assert summary["aggregate_total"] == 9.0
    assert summary["scope_label"] == "implicit single-model scope"


def test_consumer_contract_missing_field_fails_closed_with_contract_invalid_warning():
    malformed_contract = {
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "grouped_by_model": [],
        "total_aic_quantity": None,
        "authoritative_aggregate_emitted": False,
        # missing: aggregate_suppression_reason
        "warning_codes": [],
    }
    summary = build_copilot_billing_summary_from_contract(malformed_contract)
    assert summary["ok"] is False
    assert summary["summary_mode"] == "contract_invalid"
    assert summary["aggregate_total_rendered"] is False
    assert "CONTRACT_INVALID" in summary["warning_codes"]

