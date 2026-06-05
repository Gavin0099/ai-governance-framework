from __future__ import annotations

import sqlite3
from pathlib import Path

from codeburn.phase2.copilot_billing_ingestor import ingest_copilot_csv
from codeburn.phase2.copilot_billing_report import build_copilot_billing_report

SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"
MULTI_MODEL_FIXTURE = (
    Path(__file__).parent.parent
    / "codeburn"
    / "phase2"
    / "examples"
    / "copilot_gap_multi_model_mix.csv"
)


def _prepare_db(tmp_path: Path) -> Path:
    db = tmp_path / "copilot_report_guard.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    ingest_copilot_csv(str(MULTI_MODEL_FIXTURE), conn, mark_final=False)
    conn.commit()
    conn.close()
    return db


def _prepare_single_model_db(tmp_path: Path) -> Path:
    db = tmp_path / "copilot_report_guard_single_model.db"
    csv_path = tmp_path / "single_model.csv"
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


def test_cp2_guard_blocks_cross_model_authoritative_total_without_scope(tmp_path):
    db = _prepare_db(tmp_path)
    report = build_copilot_billing_report(db)

    assert report["ok"] is True
    assert report["report_mode"] == "grouped_by_model_only"
    assert report["scope_basis"] == "multi_model_result_set_without_explicit_scope"
    assert report["query_mode"] == "grouped_by_model_only"
    assert report["cross_model_aggregate_blocked"] is True
    assert report["authoritative_aggregate_emitted"] is False
    assert report["total_aic_quantity"] is None
    assert report["aggregate_suppression_reason"] == "MULTI_MODEL_SCOPE_REQUIRED"
    assert report["warning_codes"] == ["MULTI_MODEL_SCOPE_REQUIRED"]
    assert report["reason_code"] == "MODEL_SCOPE_REQUIRED_FOR_AGGREGATE"
    assert len(report["grouped_by_model"]) >= 2


def test_cp2_guard_allows_authoritative_total_with_explicit_model_scope(tmp_path):
    db = _prepare_db(tmp_path)
    grouped = build_copilot_billing_report(db)
    target_model = grouped["grouped_by_model"][0]["model"]
    target_total = grouped["grouped_by_model"][0]["aic_total"]

    scoped = build_copilot_billing_report(db, model_scope=target_model)
    assert scoped["ok"] is True
    assert scoped["report_mode"] == "scoped_total"
    assert scoped["scope_basis"] == "explicit_model_scope"
    assert scoped["query_mode"] == "model_scoped_total"
    assert scoped["cross_model_aggregate_blocked"] is False
    assert scoped["authoritative_aggregate_emitted"] is True
    assert scoped["aggregate_suppression_reason"] is None
    assert scoped["warning_codes"] == []
    assert scoped["model_scope"] == target_model
    assert scoped["total_aic_quantity"] == target_total


def test_cp2_guard_allows_implicit_total_when_result_is_single_model(tmp_path):
    db = _prepare_single_model_db(tmp_path)
    implicit = build_copilot_billing_report(db)
    assert implicit["report_mode"] == "implicit_single_model_total"
    assert implicit["scope_basis"] == "single_model_result_set"
    assert implicit["query_mode"] == "single_model_implicit_scope"
    assert implicit["authoritative_aggregate_emitted"] is True
    assert implicit["cross_model_aggregate_blocked"] is False
    assert implicit["aggregate_suppression_reason"] is None
    assert implicit["warning_codes"] == []
    assert implicit["total_aic_quantity"] > 0
