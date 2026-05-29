#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeburn.phase2.copilot_billing_consumer_guard import validate_consumer_bypass_guard
from codeburn.phase2.copilot_billing_report import build_copilot_billing_report
from codeburn.phase2.copilot_billing_summary import build_copilot_billing_summary_from_contract

CONTRACT_VERSION = "0.2"
INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY = "AGGREGATE_RENDERED_WITHOUT_AUTHORITY"
INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN = "GROUPED_BY_MODEL_TOTAL_FORBIDDEN"
INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED = "GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED"
INV_CONSUMER_GUARD_NOT_PASSED = "CONSUMER_GUARD_NOT_PASSED"
INV_CONTRACT_INVALID_RENDERED_AGGREGATE = "CONTRACT_INVALID_RENDERED_AGGREGATE"


def _consistency_codes(report: dict[str, Any], summary: dict[str, Any], guard: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    authoritative = bool(report.get("authoritative_aggregate_emitted"))
    rendered = bool(summary.get("aggregate_total_rendered"))
    report_mode = report.get("report_mode")
    suppression_reason = report.get("aggregate_suppression_reason")
    total = report.get("total_aic_quantity")

    if (not authoritative) and rendered:
        codes.append(INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY)

    if report_mode == "grouped_by_model_only":
        if total is not None:
            codes.append(INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN)
        if rendered:
            if INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY not in codes:
                codes.append(INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY)
        if not suppression_reason:
            codes.append(INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED)

    if not guard.get("ok", False):
        codes.append(INV_CONSUMER_GUARD_NOT_PASSED)

    if (not report.get("ok", False)) or (not summary.get("ok", False)) or ("CONTRACT_INVALID" in list(summary.get("warning_codes") or [])):
        if rendered:
            codes.append(INV_CONTRACT_INVALID_RENDERED_AGGREGATE)
        if "CONTRACT_INVALID" not in codes:
            codes.append("CONTRACT_INVALID")

    return list(dict.fromkeys(codes))


def build_copilot_billing_contract_receipt_from_layers(
    report: dict[str, Any],
    summary: dict[str, Any],
    guard: dict[str, Any],
    input_status: str = "unknown",
) -> dict[str, Any]:
    warning_codes: list[str] = []
    warning_codes.extend(list(report.get("warning_codes") or []))
    warning_codes.extend(list(summary.get("warning_codes") or []))
    if not guard.get("ok", False):
        warning_codes.append("CONSUMER_GUARD_FAILED")
    invariant_codes = _consistency_codes(report, summary, guard)
    warning_codes.extend(invariant_codes)
    warning_codes = list(dict.fromkeys(warning_codes))

    safe_for_audit = (
        report.get("ok", False)
        and summary.get("ok", False)
        and guard.get("ok", False)
        and not any(code in {
            INV_AGGREGATE_RENDERED_WITHOUT_AUTHORITY,
            INV_GROUPED_BY_MODEL_TOTAL_FORBIDDEN,
            INV_GROUPED_BY_MODEL_SUPPRESSION_REASON_REQUIRED,
            INV_CONSUMER_GUARD_NOT_PASSED,
            INV_CONTRACT_INVALID_RENDERED_AGGREGATE,
        } for code in warning_codes)
        and ("CONTRACT_INVALID" not in warning_codes)
    )

    return {
        "contract_version": CONTRACT_VERSION,
        "provider": "copilot",
        "input_status": input_status,
        "report_mode": report.get("report_mode"),
        "scope_basis": report.get("scope_basis"),
        "authoritative_aggregate_emitted": bool(report.get("authoritative_aggregate_emitted")),
        "aggregate_rendered": bool(summary.get("aggregate_total_rendered")),
        "aggregate_suppression_reason": report.get("aggregate_suppression_reason"),
        "consumer_guard_status": "passed" if guard.get("ok") else "failed",
        "invariant_codes": invariant_codes,
        "warning_codes": warning_codes,
        "report_contract_ok": bool(report.get("ok")),
        "summary_contract_ok": bool(summary.get("ok")),
        "safe_for_audit": bool(safe_for_audit),
    }


def build_copilot_billing_contract_receipt(
    db_path: Path,
    report_date: str | None = None,
    model_scope: str | None = None,
    input_status: str = "unknown",
) -> dict[str, Any]:
    report = build_copilot_billing_report(
        db_path=db_path,
        report_date=report_date,
        model_scope=model_scope,
    )
    summary = build_copilot_billing_summary_from_contract(report)
    guard = validate_consumer_bypass_guard(Path(__file__).resolve().parent)

    return build_copilot_billing_contract_receipt_from_layers(
        report=report,
        summary=summary,
        guard=guard,
        input_status=input_status,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Copilot billing contract receipt (CP-6).")
    parser.add_argument("--db", required=True, help="Path to CodeBurn SQLite DB")
    parser.add_argument("--report-date", default=None)
    parser.add_argument("--model-scope", default=None)
    parser.add_argument("--input-status", default="unknown")
    args = parser.parse_args()

    receipt = build_copilot_billing_contract_receipt(
        db_path=Path(args.db),
        report_date=args.report_date,
        model_scope=args.model_scope,
        input_status=args.input_status,
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
