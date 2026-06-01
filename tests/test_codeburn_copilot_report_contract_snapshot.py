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


def _seed_db_with_fixture(tmp_path: Path, fixture: Path, filename: str) -> Path:
    db = tmp_path / filename
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    ingest_copilot_csv(str(fixture), conn, mark_final=False)
    conn.commit()
    conn.close()
    return db


def _seed_single_model_db(tmp_path: Path) -> Path:
    csv_path = tmp_path / "single_model_snapshot.csv"
    csv_path.write_text(
        "date,user_login,model,aic_quantity,aic_gross_amount\n"
        "2026-05-21,alice,gpt-4.1,4.0,0.11\n"
        "2026-05-21,bob,gpt-4.1,5.0,0.12\n",
        encoding="utf-8",
    )
    return _seed_db_with_fixture(tmp_path, csv_path, "single_model_snapshot.db")


def _contract_projection(report: dict) -> dict:
    return {
        "report_mode": report["report_mode"],
        "scope_basis": report["scope_basis"],
        "grouped_by_model": report["grouped_by_model"],
        "total_aic_quantity": report["total_aic_quantity"],
        "authoritative_aggregate_emitted": report["authoritative_aggregate_emitted"],
        "aggregate_suppression_reason": report["aggregate_suppression_reason"],
        "warning_codes": report["warning_codes"],
    }


def test_contract_snapshot_multi_model_without_scope(tmp_path):
    db = _seed_db_with_fixture(tmp_path, MULTI_MODEL_FIXTURE, "multi_snapshot.db")
    report = build_copilot_billing_report(db)
    assert _contract_projection(report) == {
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "grouped_by_model": [
            {"model": "claude-3.7", "aic_total": 5.0, "row_count": 1},
            {"model": "gemini-1.5-pro", "aic_total": 3.0, "row_count": 1},
            {"model": "gpt-4.1", "aic_total": 35.5, "row_count": 3},
        ],
        "total_aic_quantity": None,
        "authoritative_aggregate_emitted": False,
        "aggregate_suppression_reason": "MULTI_MODEL_SCOPE_REQUIRED",
        "warning_codes": ["MULTI_MODEL_SCOPE_REQUIRED"],
    }


def test_contract_snapshot_explicit_model_scope(tmp_path):
    db = _seed_db_with_fixture(tmp_path, MULTI_MODEL_FIXTURE, "multi_scope_snapshot.db")
    report = build_copilot_billing_report(db, model_scope="gpt-4.1")
    assert _contract_projection(report) == {
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "grouped_by_model": [
            {"model": "gpt-4.1", "aic_total": 35.5, "row_count": 3},
        ],
        "total_aic_quantity": 35.5,
        "authoritative_aggregate_emitted": True,
        "aggregate_suppression_reason": None,
        "warning_codes": [],
    }


def test_contract_snapshot_implicit_single_model_total(tmp_path):
    db = _seed_single_model_db(tmp_path)
    report = build_copilot_billing_report(db)
    assert _contract_projection(report) == {
        "report_mode": "implicit_single_model_total",
        "scope_basis": "single_model_result_set",
        "grouped_by_model": [
            {"model": "gpt-4.1", "aic_total": 9.0, "row_count": 2},
        ],
        "total_aic_quantity": 9.0,
        "authoritative_aggregate_emitted": True,
        "aggregate_suppression_reason": None,
        "warning_codes": [],
    }

