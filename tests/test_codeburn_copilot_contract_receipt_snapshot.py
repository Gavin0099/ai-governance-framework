from __future__ import annotations

import sqlite3
from pathlib import Path

from codeburn.phase2.copilot_billing_contract_receipt import (
    INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY,
    INV_CONSUMER_GUARD_NOT_PASSED,
    INV_CONTRACT_INVALID_RENDERED_AGGREGATE,
    INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED,
    INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN,
    build_copilot_billing_contract_receipt,
    build_copilot_billing_contract_receipt_from_layers,
)
from codeburn.phase2.copilot_billing_ingestor import ingest_copilot_csv

SCHEMA_PATH = Path(__file__).parent.parent / "codeburn" / "phase1" / "schema.sql"
MULTI_MODEL_FIXTURE = (
    Path(__file__).parent.parent
    / "codeburn"
    / "phase2"
    / "examples"
    / "copilot_gap_multi_model_mix.csv"
)


def _seed_multi_model_db(tmp_path: Path) -> Path:
    db = tmp_path / "cp8_multi.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    ingest_copilot_csv(str(MULTI_MODEL_FIXTURE), conn, mark_final=False)
    conn.commit()
    conn.close()
    return db


def _seed_single_model_db(tmp_path: Path) -> Path:
    db = tmp_path / "cp8_single.db"
    csv_path = tmp_path / "single_model_cp8.csv"
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


def _snapshot_projection(receipt: dict) -> dict:
    return {
        "contract_version": receipt["contract_version"],
        "report_mode": receipt["report_mode"],
        "scope_basis": receipt["scope_basis"],
        "authoritative_aggregate_emitted": receipt["authoritative_aggregate_emitted"],
        "aggregate_rendered": receipt["aggregate_rendered"],
        "aggregate_suppression_reason": receipt["aggregate_suppression_reason"],
        "consumer_guard_status": receipt["consumer_guard_status"],
        "invariant_codes": receipt["invariant_codes"],
        "warning_codes": receipt["warning_codes"],
        "safe_for_audit": receipt["safe_for_audit"],
    }


def test_receipt_snapshot_multi_model_no_scope_safe_suppressed(tmp_path):
    db = _seed_multi_model_db(tmp_path)
    receipt = build_copilot_billing_contract_receipt(db_path=db, input_status="valid")
    assert _snapshot_projection(receipt) == {
        "contract_version": "0.2",
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "authoritative_aggregate_emitted": False,
        "aggregate_rendered": False,
        "aggregate_suppression_reason": "MULTI_MODEL_SCOPE_REQUIRED",
        "consumer_guard_status": "passed",
        "invariant_codes": [],
        "warning_codes": ["MULTI_MODEL_SCOPE_REQUIRED"],
        "safe_for_audit": True,
    }


def test_receipt_snapshot_explicit_scoped_total_safe(tmp_path):
    db = _seed_multi_model_db(tmp_path)
    receipt = build_copilot_billing_contract_receipt(db_path=db, model_scope="gpt-4.1", input_status="valid")
    assert _snapshot_projection(receipt) == {
        "contract_version": "0.2",
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_rendered": True,
        "aggregate_suppression_reason": None,
        "consumer_guard_status": "passed",
        "invariant_codes": [],
        "warning_codes": [],
        "safe_for_audit": True,
    }


def test_receipt_snapshot_implicit_single_model_safe(tmp_path):
    db = _seed_single_model_db(tmp_path)
    receipt = build_copilot_billing_contract_receipt(db_path=db, input_status="valid")
    assert _snapshot_projection(receipt) == {
        "contract_version": "0.2",
        "report_mode": "implicit_single_model_total",
        "scope_basis": "single_model_result_set",
        "authoritative_aggregate_emitted": True,
        "aggregate_rendered": True,
        "aggregate_suppression_reason": None,
        "consumer_guard_status": "passed",
        "invariant_codes": [],
        "warning_codes": [],
        "safe_for_audit": True,
    }


def test_receipt_snapshot_invariant_violation_unsafe():
    report = {
        "ok": True,
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "authoritative_aggregate_emitted": False,
        "aggregate_suppression_reason": None,
        "total_aic_quantity": 5.0,
        "warning_codes": [],
    }
    summary = {"ok": True, "aggregate_total_rendered": True, "warning_codes": []}
    guard = {"ok": True}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard)
    assert _snapshot_projection(receipt) == {
        "contract_version": "0.2",
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "authoritative_aggregate_emitted": False,
        "aggregate_rendered": True,
        "aggregate_suppression_reason": None,
        "consumer_guard_status": "passed",
        "invariant_codes": [
            INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY,
            INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN,
            INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED,
        ],
        "warning_codes": [
            INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY,
            INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN,
            INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED,
        ],
        "safe_for_audit": False,
    }


def test_receipt_snapshot_consumer_guard_failed_unsafe():
    report = {
        "ok": True,
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_suppression_reason": None,
        "total_aic_quantity": 10.0,
        "warning_codes": [],
    }
    summary = {"ok": True, "aggregate_total_rendered": True, "warning_codes": []}
    guard = {"ok": False}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard)
    assert _snapshot_projection(receipt) == {
        "contract_version": "0.2",
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_rendered": True,
        "aggregate_suppression_reason": None,
        "consumer_guard_status": "failed",
        "invariant_codes": [INV_CONSUMER_GUARD_NOT_PASSED],
        "warning_codes": ["CONSUMER_GUARD_FAILED", INV_CONSUMER_GUARD_NOT_PASSED],
        "safe_for_audit": False,
    }


def test_receipt_snapshot_malformed_contract_invalid_unsafe():
    report = {
        "ok": True,
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_suppression_reason": None,
        "total_aic_quantity": 10.0,
        "warning_codes": [],
    }
    summary = {"ok": False, "aggregate_total_rendered": True, "warning_codes": ["CONTRACT_INVALID"]}
    guard = {"ok": True}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard)
    assert _snapshot_projection(receipt) == {
        "contract_version": "0.2",
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_rendered": True,
        "aggregate_suppression_reason": None,
        "consumer_guard_status": "passed",
        "invariant_codes": [INV_CONTRACT_INVALID_RENDERED_AGGREGATE, "CONTRACT_INVALID"],
        "warning_codes": ["CONTRACT_INVALID", INV_CONTRACT_INVALID_RENDERED_AGGREGATE],
        "safe_for_audit": False,
    }

