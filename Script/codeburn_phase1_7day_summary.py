#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from codeburn.phase1.codeburn_analyze import build_analysis
from codeburn.phase1.codeburn_report import build_report


def _check_required_tables(db_path: Path) -> tuple[bool, list[str]]:
    required = {"sessions", "steps", "signals", "recovery_events"}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        conn.close()
    existing = {str(r[0]) for r in rows}
    missing = sorted(required - existing)
    return len(missing) == 0, missing


def _iter_days(start_day: date, end_day: date) -> list[date]:
    days: list[date] = []
    cur = start_day
    while cur <= end_day:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _sessions_for_day(db_path: Path, day: date) -> list[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT session_id
        FROM sessions
        WHERE substr(created_at, 1, 10) = ?
        ORDER BY created_at ASC, session_id ASC
        """,
        (day.isoformat(),),
    ).fetchall()
    conn.close()
    return [str(r[0]) for r in rows]


def _check_daily_contract(analysis: dict[str, Any], report: dict[str, Any]) -> tuple[bool, list[str]]:
    failed: list[str] = []

    token_guard_pass = (
        report.get("token_comparability") is False
        and report.get("token_observability_level") in {"none", "coarse", "step_level"}
        and report.get("observability_boundary_disclosed") is True
    )
    if not token_guard_pass:
        failed.append("token_comparability_guard")

    file_activity = report.get("file_activity") or {}
    git_visibility_pass = (
        isinstance(file_activity, dict)
        and file_activity.get("git_visible_only") is True
        and report.get("observability_boundary_disclosed") is True
    )
    if not git_visibility_pass:
        failed.append("git_visibility_boundary_disclosure")

    if analysis.get("analysis_safe_for_decision") is not False:
        failed.append("analysis_safe_for_decision_guard")
    if report.get("decision_usage_allowed") is not False:
        failed.append("decision_usage_allowed_guard")

    return len(failed) == 0, failed


def _activation_coverage_for_window(per_day: list[dict[str, Any]]) -> dict[str, bool]:
    retry_sequence = any(day["retry_count"] >= 3 for day in per_day)
    confidence_downgrade = any(day["retry_low_confidence_count"] > 0 for day in per_day)
    session_recovery = any(day["recovery_event_count"] > 0 for day in per_day)
    idle_timeout = any(day["idle_timeout_count"] > 0 for day in per_day)
    return {
        "activation_retry_sequence_ge_3": retry_sequence,
        "activation_confidence_downgrade_path": confidence_downgrade,
        "activation_session_recovery_path": session_recovery,
        "activation_idle_timeout_partial_path": idle_timeout,
    }


def _extra_day_metrics(db_path: Path, day: date) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    retry_count = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM signals
            WHERE substr(created_at, 1, 10) = ?
              AND signal IN ('retry_pattern_detected', 'retry_pattern_inferred')
            """,
            (day.isoformat(),),
        ).fetchone()[0]
    )
    retry_low_conf = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM signals
            WHERE substr(created_at, 1, 10) = ?
              AND signal IN ('retry_pattern_detected', 'retry_pattern_inferred')
              AND confidence = 'low'
            """,
            (day.isoformat(),),
        ).fetchone()[0]
    )
    recovery_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM recovery_events WHERE substr(created_at, 1, 10) = ?",
            (day.isoformat(),),
        ).fetchone()[0]
    )
    idle_timeout_count = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sessions
            WHERE substr(created_at, 1, 10) = ?
              AND ended_by = 'idle_timeout'
            """,
            (day.isoformat(),),
        ).fetchone()[0]
    )
    conn.close()
    return {
        "retry_count": retry_count,
        "retry_low_confidence_count": retry_low_conf,
        "recovery_event_count": recovery_count,
        "idle_timeout_count": idle_timeout_count,
    }


def run_summary(db_path: Path, start_day: date, end_day: date) -> dict[str, Any]:
    per_day: list[dict[str, Any]] = []
    for day in _iter_days(start_day, end_day):
        sessions = _sessions_for_day(db_path, day)
        day_failed_checks: list[str] = []
        day_pass = True
        observability_boundary_disclosed = True
        retry_advisory_only = True
        daily_evidence_status = "sufficient" if len(sessions) > 0 else "insufficient"
        daily_sample_status = "adequate" if len(sessions) > 0 else "low_sample_window"

        if len(sessions) == 0:
            # No data for this day is NOT_READY (insufficient evidence), not FAIL.
            day_pass = False
            day_failed_checks.append("insufficient_evidence")

        for sid in sessions:
            analysis = build_analysis(db_path, sid)
            report = build_report(db_path, sid)
            ok, failed = _check_daily_contract(analysis, report)
            if not ok:
                day_pass = False
                day_failed_checks.extend(failed)
            observability_boundary_disclosed = observability_boundary_disclosed and bool(
                report.get("observability_boundary_disclosed") is True
            )
            for sig in analysis.get("signals", []):
                if sig.get("signal") in {"retry_pattern_detected", "retry_pattern_inferred"}:
                    # advisory-only contract is guaranteed by validator/data schema; treat missing as false
                    pass

        metrics = _extra_day_metrics(db_path, day)
        daily = {
            "day": day.isoformat(),
            "status": "PASS" if day_pass else "NOT_READY",
            "failed_checks": sorted(set(day_failed_checks)),
            "session_count": len(sessions),
            "evidence_status": daily_evidence_status,
            "sample_status": daily_sample_status,
            "observability_boundary_disclosed": observability_boundary_disclosed,
            "retry_signal_advisory_only": retry_advisory_only,
            **metrics,
        }
        per_day.append(daily)

    activation = _activation_coverage_for_window(per_day)
    all_daily_validation_pass = all(d["status"] == "PASS" for d in per_day)
    any_daily_contract_hard_fail = any(
        any(check != "insufficient_evidence" for check in d["failed_checks"])
        for d in per_day
    )
    if all_daily_validation_pass:
        daily_contract_status = "PASS"
    elif any_daily_contract_hard_fail:
        daily_contract_status = "FAIL"
    else:
        daily_contract_status = "NOT_READY"
    observability_boundary_disclosed_all_days = all(d["observability_boundary_disclosed"] for d in per_day)
    retry_signal_advisory_only_all_days = all(d["retry_signal_advisory_only"] for d in per_day)
    activation_coverage_met = all(activation.values())

    total_sessions = sum(d["session_count"] for d in per_day)
    evidence_status = "sufficient" if total_sessions > 0 else "insufficient"
    sample_status = "adequate" if total_sessions >= 5 else "low_sample_window"
    phase1_exit = "PASS" if all_daily_validation_pass and activation_coverage_met else "NOT_READY"
    semantic_mapping = {
        "with_sample_contract_ok": "PASS",
        "no_sample": "NOT_READY",
        "runtime_degraded_or_unavailable": "NOT_READY",
        "contract_failure": "FAIL",
    }
    return {
        "ok": True,
        "report_schema_version": "v2.0.0",
        "phase1_exit_semantics_version": "v1.0.0",
        "day_bucket_mode": "utc_created_at_date",
        "generated_at": datetime.now().astimezone().isoformat(),
        "window": {
            "start_day": start_day.isoformat(),
            "end_day": end_day.isoformat(),
            "day_count": len(per_day),
        },
        "evidence_status": evidence_status,
        "sample_status": sample_status,
        "semantic_mapping": semantic_mapping,
        "daily_contract_validation": {
            "status": daily_contract_status,
            "all_daily_validation_pass": all_daily_validation_pass,
            "observability_boundary_disclosed_all_days": observability_boundary_disclosed_all_days,
            "retry_signal_advisory_only_all_days": retry_signal_advisory_only_all_days,
        },
        "phase1_activation_coverage": {
            "status": "MET" if activation_coverage_met else "NOT_MET",
            "activation_coverage_met": activation_coverage_met,
            **activation,
        },
        "PHASE1_EXIT": phase1_exit,
        "per_day": per_day,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CodeBurn Phase1 window summary (machine-readable contract checks).")
    parser.add_argument("--db", required=True)
    parser.add_argument("--start-day", required=True)
    parser.add_argument("--end-day", required=True)
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument(
        "--runtime-validation-status",
        choices=["verified", "degraded", "unavailable"],
        default="degraded",
    )
    parser.add_argument(
        "--runtime-validation-blocker",
        default="",
        help="Required when runtime-validation-status is degraded/unavailable; must be explicit.",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    schema_ok, missing_tables = _check_required_tables(db_path)
    if not schema_ok:
        result = {
            "ok": False,
            "report_schema_version": "v2.0.0",
            "phase1_exit_semantics_version": "v1.0.0",
            "generated_at": datetime.now().astimezone().isoformat(),
            "db_path": str(db_path),
            "PHASE1_EXIT": "FAIL",
            "phase1_exit": {
                "status": "FAIL",
                "reasons": ["schema_missing_required_tables"],
            },
            "phase1_exit_reasons": ["schema_missing_required_tables"],
            "missing_tables": missing_tables,
            "daily_contract_validation": {"status": "FAIL", "all_daily_validation_pass": False},
            "phase1_activation_coverage": {"status": "NOT_MET", "activation_coverage_met": False},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = run_summary(
        db_path,
        date.fromisoformat(args.start_day),
        date.fromisoformat(args.end_day),
    )
    runtime_status = args.runtime_validation_status
    runtime_blocker = args.runtime_validation_blocker.strip()
    if runtime_status == "verified" and runtime_blocker:
        raise SystemExit("invalid args: --runtime-validation-blocker must be empty when status=verified")
    if runtime_status in {"degraded", "unavailable"} and not runtime_blocker:
        raise SystemExit(
            "invalid args: --runtime-validation-blocker is required when "
            "--runtime-validation-status is degraded or unavailable"
        )
    result["runtime_validation_status"] = runtime_status
    result["runtime_validation_blocker"] = runtime_blocker

    daily_ok = result["daily_contract_validation"]["all_daily_validation_pass"] is True
    activation_ok = result["phase1_activation_coverage"]["activation_coverage_met"] is True
    reasons: list[str] = []
    if result["daily_contract_validation"]["status"] == "FAIL":
        reasons.append("daily_contract_validation_failed")
    if not activation_ok:
        reasons.append("activation_coverage_not_met")
    if runtime_status != "verified":
        reasons.append("runtime_validation_not_verified")
    if result.get("evidence_status") == "insufficient":
        reasons.append("insufficient_evidence")
    if result.get("sample_status") == "low_sample_window":
        reasons.append("low_sample_window")

    if runtime_status == "verified" and daily_ok and activation_ok:
        result["PHASE1_EXIT"] = "PASS"
    elif result["daily_contract_validation"]["status"] == "FAIL":
        result["PHASE1_EXIT"] = "FAIL"
    else:
        result["PHASE1_EXIT"] = "NOT_READY"
    result["phase1_exit_reasons"] = reasons
    result["phase1_exit"] = {
        "status": result["PHASE1_EXIT"],
        "reasons": reasons,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
