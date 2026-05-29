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
    db = tmp_path / "cp6_multi.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    ingest_copilot_csv(str(MULTI_MODEL_FIXTURE), conn, mark_final=False)
    conn.commit()
    conn.close()
    return db


def test_contract_receipt_multi_model_no_scope_is_non_authoritative_end_to_end(tmp_path):
    db = _seed_multi_model_db(tmp_path)
    receipt = build_copilot_billing_contract_receipt(
        db_path=db,
        model_scope=None,
        input_status="valid",
    )
    assert receipt["contract_version"] == "0.2"
    assert receipt["input_status"] == "valid"
    assert receipt["report_mode"] == "grouped_by_model_only"
    assert receipt["scope_basis"] == "multi_model_result_set_without_explicit_scope"
    assert receipt["authoritative_aggregate_emitted"] is False
    assert receipt["aggregate_rendered"] is False
    assert receipt["aggregate_suppression_reason"] == "MULTI_MODEL_SCOPE_REQUIRED"
    assert receipt["consumer_guard_status"] == "passed"
    assert "MULTI_MODEL_SCOPE_REQUIRED" in receipt["warning_codes"]
    assert receipt["invariant_codes"] == []
    assert receipt["safe_for_audit"] is True


def test_contract_receipt_scoped_total_is_authorized_when_scope_explicit(tmp_path):
    db = _seed_multi_model_db(tmp_path)
    receipt = build_copilot_billing_contract_receipt(
        db_path=db,
        model_scope="gpt-4.1",
        input_status="valid",
    )
    assert receipt["report_mode"] == "scoped_total"
    assert receipt["scope_basis"] == "explicit_model_scope"
    assert receipt["authoritative_aggregate_emitted"] is True
    assert receipt["aggregate_rendered"] is True
    assert receipt["aggregate_suppression_reason"] is None
    assert receipt["consumer_guard_status"] == "passed"
    assert receipt["invariant_codes"] == []
    assert receipt["safe_for_audit"] is True


def test_receipt_invariant_non_authoritative_cannot_render_aggregate():
    report = {
        "ok": True,
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "authoritative_aggregate_emitted": False,
        "aggregate_suppression_reason": "MULTI_MODEL_SCOPE_REQUIRED",
        "total_aic_quantity": None,
        "warning_codes": [],
    }
    summary = {
        "ok": True,
        "aggregate_total_rendered": True,
        "warning_codes": [],
    }
    guard = {"ok": True}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard, input_status="valid")
    assert INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY in receipt["warning_codes"]
    assert INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY in receipt["invariant_codes"]
    assert receipt["safe_for_audit"] is False


def test_receipt_invariant_grouped_mode_requires_suppression_reason_and_no_total():
    report = {
        "ok": True,
        "report_mode": "grouped_by_model_only",
        "scope_basis": "multi_model_result_set_without_explicit_scope",
        "authoritative_aggregate_emitted": False,
        "aggregate_suppression_reason": None,
        "total_aic_quantity": 123.0,
        "warning_codes": [],
    }
    summary = {
        "ok": True,
        "aggregate_total_rendered": False,
        "warning_codes": [],
    }
    guard = {"ok": True}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard)
    assert INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN in receipt["warning_codes"]
    assert INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED in receipt["warning_codes"]
    assert INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN in receipt["invariant_codes"]
    assert INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED in receipt["invariant_codes"]
    assert receipt["safe_for_audit"] is False


def test_receipt_invariant_consumer_guard_failed_marks_unsafe():
    report = {
        "ok": True,
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_suppression_reason": None,
        "total_aic_quantity": 10.0,
        "warning_codes": [],
    }
    summary = {
        "ok": True,
        "aggregate_total_rendered": True,
        "warning_codes": [],
    }
    guard = {"ok": False}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard)
    assert "CONSUMER_GUARD_FAILED" in receipt["warning_codes"]
    assert INV_CONSUMER_GUARD_NOT_PASSED in receipt["warning_codes"]
    assert INV_CONSUMER_GUARD_NOT_PASSED in receipt["invariant_codes"]
    assert receipt["consumer_guard_status"] == "failed"
    assert receipt["safe_for_audit"] is False


def test_receipt_invariant_contract_invalid_forces_no_render_and_contract_invalid_code():
    report = {
        "ok": True,
        "report_mode": "scoped_total",
        "scope_basis": "explicit_model_scope",
        "authoritative_aggregate_emitted": True,
        "aggregate_suppression_reason": None,
        "total_aic_quantity": 10.0,
        "warning_codes": [],
    }
    summary = {
        "ok": False,
        "aggregate_total_rendered": True,
        "warning_codes": ["CONTRACT_INVALID"],
    }
    guard = {"ok": True}
    receipt = build_copilot_billing_contract_receipt_from_layers(report, summary, guard)
    assert "CONTRACT_INVALID" in receipt["warning_codes"]
    assert INV_CONTRACT_INVALID_RENDERED_AGGREGATE in receipt["warning_codes"]
    assert INV_CONTRACT_INVALID_RENDERED_AGGREGATE in receipt["invariant_codes"]
    assert receipt["safe_for_audit"] is False
