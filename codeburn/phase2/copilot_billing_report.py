#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def _build_where(report_date: str | None, model_scope: str | None) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []
    if report_date:
        clauses.append("report_date = ?")
        params.append(report_date)
    if model_scope:
        clauses.append("model = ?")
        params.append(model_scope)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def build_copilot_billing_report(
    db_path: Path,
    report_date: str | None = None,
    model_scope: str | None = None,
) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        where, params = _build_where(report_date, model_scope)
        grouped_rows = conn.execute(
            f"""
            SELECT model, SUM(aic_quantity) AS aic_total, COUNT(*) AS row_count
            FROM copilot_billing_events
            {where}
            GROUP BY model
            ORDER BY model ASC
            """,
            params,
        ).fetchall()

        groups = [
            {
                "model": str(r["model"]),
                "aic_total": float(r["aic_total"] or 0.0),
                "row_count": int(r["row_count"] or 0),
            }
            for r in grouped_rows
        ]
        distinct_models = [g["model"] for g in groups]
        multi_model = len(distinct_models) > 1

        if model_scope:
            scoped = conn.execute(
                f"""
                SELECT SUM(aic_quantity) AS aic_total, COUNT(*) AS row_count
                FROM copilot_billing_events
                {where}
                """,
                params,
            ).fetchone()
            return {
                "ok": True,
                "provider": "copilot",
                "acquisition_mode": "billing_report_daily_aggregate",
                "analysis_safe_for_decision": False,
                "decision_authority": "none",
                "report_mode": "scoped_total",
                "scope_basis": "explicit_model_scope",
                "query_mode": "model_scoped_total",
                "model_scope": model_scope,
                "report_date": report_date,
                "authoritative_aggregate_emitted": True,
                "cross_model_aggregate_blocked": False,
                "aggregate_suppression_reason": None,
                "warning_codes": [],
                "total_aic_quantity": float((scoped["aic_total"] if scoped else 0.0) or 0.0),
                "row_count": int((scoped["row_count"] if scoped else 0) or 0),
                "grouped_by_model": groups,
            }

        if multi_model:
            return {
                "ok": True,
                "provider": "copilot",
                "acquisition_mode": "billing_report_daily_aggregate",
                "analysis_safe_for_decision": False,
                "decision_authority": "none",
                "report_mode": "grouped_by_model_only",
                "scope_basis": "multi_model_result_set_without_explicit_scope",
                "query_mode": "grouped_by_model_only",
                "model_scope": None,
                "report_date": report_date,
                "authoritative_aggregate_emitted": False,
                "cross_model_aggregate_blocked": True,
                "aggregate_suppression_reason": "MULTI_MODEL_SCOPE_REQUIRED",
                "warning_codes": ["MULTI_MODEL_SCOPE_REQUIRED"],
                "total_aic_quantity": None,
                "row_count": sum(g["row_count"] for g in groups),
                "grouped_by_model": groups,
                "reason_code": "MODEL_SCOPE_REQUIRED_FOR_AGGREGATE",
            }

        single_total = groups[0]["aic_total"] if groups else 0.0
        single_rows = groups[0]["row_count"] if groups else 0
        return {
            "ok": True,
            "provider": "copilot",
            "acquisition_mode": "billing_report_daily_aggregate",
            "analysis_safe_for_decision": False,
            "decision_authority": "none",
            "report_mode": "implicit_single_model_total",
            "scope_basis": "single_model_result_set",
            "query_mode": "single_model_implicit_scope",
            "model_scope": None,
            "report_date": report_date,
            "authoritative_aggregate_emitted": True,
            "cross_model_aggregate_blocked": False,
            "aggregate_suppression_reason": None,
            "warning_codes": [],
            "total_aic_quantity": float(single_total),
            "row_count": int(single_rows),
            "grouped_by_model": groups,
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Copilot billing report with CP-2 query guard.")
    parser.add_argument("--db", required=True, help="Path to CodeBurn SQLite DB")
    parser.add_argument("--report-date", default=None, help="Optional YYYY-MM-DD report date filter")
    parser.add_argument("--model-scope", default=None, help="Optional model filter")
    args = parser.parse_args()

    report = build_copilot_billing_report(
        db_path=Path(args.db),
        report_date=args.report_date,
        model_scope=args.model_scope,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
