#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeburn.phase2.copilot_billing_report import build_copilot_billing_report

_REQUIRED_FIELDS = {
    "report_mode",
    "scope_basis",
    "grouped_by_model",
    "total_aic_quantity",
    "authoritative_aggregate_emitted",
    "aggregate_suppression_reason",
    "warning_codes",
}


def build_copilot_billing_summary_from_contract(report: dict[str, Any]) -> dict[str, Any]:
    warning_codes = list(report.get("warning_codes") or [])
    missing = sorted(_REQUIRED_FIELDS - set(report.keys()))
    if missing:
        warning_codes.append("CONTRACT_INVALID")
        return {
            "ok": False,
            "summary_mode": "contract_invalid",
            "aggregate_total_rendered": False,
            "aggregate_total": None,
            "scope_label": None,
            "grouped_by_model": [],
            "warning_codes": warning_codes,
            "contract_errors": [f"missing_required_fields:{','.join(missing)}"],
        }

    report_mode = report["report_mode"]
    grouped_by_model = report["grouped_by_model"]

    if report_mode == "grouped_by_model_only":
        return {
            "ok": True,
            "summary_mode": "grouped_only",
            "aggregate_total_rendered": False,
            "aggregate_total": None,
            "scope_label": "scope required",
            "grouped_by_model": grouped_by_model,
            "warning_codes": warning_codes,
            "contract_errors": [],
        }

    if report_mode == "scoped_total":
        scope = report.get("model_scope")
        return {
            "ok": True,
            "summary_mode": "scoped_total",
            "aggregate_total_rendered": True,
            "aggregate_total": report["total_aic_quantity"],
            "scope_label": f"model_scope={scope}",
            "grouped_by_model": grouped_by_model,
            "warning_codes": warning_codes,
            "contract_errors": [],
        }

    if report_mode == "implicit_single_model_total":
        return {
            "ok": True,
            "summary_mode": "implicit_single_model_total",
            "aggregate_total_rendered": True,
            "aggregate_total": report["total_aic_quantity"],
            "scope_label": "implicit single-model scope",
            "grouped_by_model": grouped_by_model,
            "warning_codes": warning_codes,
            "contract_errors": [],
        }

    warning_codes.append("CONTRACT_INVALID")
    return {
        "ok": False,
        "summary_mode": "contract_invalid",
        "aggregate_total_rendered": False,
        "aggregate_total": None,
        "scope_label": None,
        "grouped_by_model": [],
        "warning_codes": warning_codes,
        "contract_errors": [f"unknown_report_mode:{report_mode}"],
    }


def build_copilot_billing_summary(
    db_path: Path,
    report_date: str | None = None,
    model_scope: str | None = None,
) -> dict[str, Any]:
    report = build_copilot_billing_report(
        db_path=db_path,
        report_date=report_date,
        model_scope=model_scope,
    )
    return build_copilot_billing_summary_from_contract(report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Copilot billing summary consumer (CP-4).")
    parser.add_argument("--db", required=True, help="Path to CodeBurn SQLite DB")
    parser.add_argument("--report-date", default=None)
    parser.add_argument("--model-scope", default=None)
    args = parser.parse_args()

    summary = build_copilot_billing_summary(
        db_path=Path(args.db),
        report_date=args.report_date,
        model_scope=args.model_scope,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())

