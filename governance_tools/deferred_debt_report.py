#!/usr/bin/env python3
"""
Read-only deferred-debt report over canonical daily memory files.

Scope is fixed by the PLAN checkpoint "Deferred-debt report implementation
checkpoint (decided 2026-06-13)". The report covers exactly four
machine-decidable observables:

  1. counts of session-derived records by plan_reconciliation value
  2. deferred breakdown by taxonomy reason
  3. oldest age per deferred reason (days since the record's file date)
  4. not_declared count and oldest age

Claim ceiling (normative, do not extend in code):
  - observation-class only: no thresholds, no pass/fail, not a gate input
  - a deferred declaration with a taxonomy reason is a legal honest state,
    not a failure; not_declared is advisory-era data, not a violation
  - semantic detection of "PLAN-touched" work is NOT performed and NOT
    claimed; not_declared / deferred are the observable proxies
  - records pre-dating the field (file date before 2026-06-12) are
    bucketed as pre_field: expected history, not debt
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from governance_tools.memory_record import (
        PLAN_RECONCILIATION_DEFERRED_PREFIX,
        PLAN_RECONCILIATION_NOT_APPLICABLE,
        PLAN_RECONCILIATION_NOT_DECLARED,
        PLAN_RECONCILIATION_UPDATED,
        validate_plan_reconciliation,
    )
except ImportError:  # direct script execution from governance_tools/
    from memory_record import (
        PLAN_RECONCILIATION_DEFERRED_PREFIX,
        PLAN_RECONCILIATION_NOT_APPLICABLE,
        PLAN_RECONCILIATION_NOT_DECLARED,
        PLAN_RECONCILIATION_UPDATED,
        validate_plan_reconciliation,
    )

TOOL_ID = "governance_tools.deferred_debt_report"
REPORT_FORMAT_VERSION = "1.0"

# The plan_reconciliation field first appeared in canonical records on this
# date (P1-D). Records in files dated earlier cannot carry it; counting them
# as not_declared would fabricate silent debt out of expected history.
FIELD_INTRODUCED_DATE = date(2026, 6, 12)

_DAILY_FILE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")
_RECORD_START = "- memory_type: session-derived"
_FIELD_LINE_RE = re.compile(r"^  ([a-z_]+): (.*)$")

BUCKET_UPDATED = "updated"
BUCKET_NOT_APPLICABLE = "not_applicable"
BUCKET_DEFERRED = "deferred"
BUCKET_NOT_DECLARED = "not_declared"
BUCKET_PRE_FIELD = "pre_field"
BUCKET_MALFORMED = "malformed"


def _daily_file_date(path: Path) -> date | None:
    match = _DAILY_FILE_RE.match(path.name)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def parse_session_derived_records(text: str) -> list[dict[str, str]]:
    """Parse session-derived record blocks from a daily memory file."""
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if line.strip() == _RECORD_START.strip() and line.startswith("- "):
            current = {"memory_type": "session-derived"}
            records.append(current)
            continue
        if line.startswith("- "):
            current = None  # a different list item / record type
            continue
        if current is not None:
            field = _FIELD_LINE_RE.match(line)
            if field:
                current[field.group(1)] = field.group(2)
    return records


def classify_record(record: dict[str, str], file_date: date) -> tuple[str, str | None]:
    """
    Returns (bucket, deferred_reason). deferred_reason is set only for the
    deferred bucket.
    """
    raw = record.get("plan_reconciliation")
    if raw is None:
        if file_date < FIELD_INTRODUCED_DATE:
            return BUCKET_PRE_FIELD, None
        return BUCKET_NOT_DECLARED, None
    raw = raw.strip()
    # "not_declared" is a legal recorded value (writer normalizes omission to
    # it) but not a legal CLI input, so check it before the input validator.
    if raw == PLAN_RECONCILIATION_NOT_DECLARED:
        return BUCKET_NOT_DECLARED, None
    normalized, error = validate_plan_reconciliation(raw)
    if error is not None:
        return BUCKET_MALFORMED, None
    if normalized == PLAN_RECONCILIATION_UPDATED:
        return BUCKET_UPDATED, None
    if normalized == PLAN_RECONCILIATION_NOT_APPLICABLE:
        return BUCKET_NOT_APPLICABLE, None
    if normalized.startswith(PLAN_RECONCILIATION_DEFERRED_PREFIX):
        return BUCKET_DEFERRED, normalized[len(PLAN_RECONCILIATION_DEFERRED_PREFIX):]
    # validate_plan_reconciliation only returns the three shapes above; this
    # is unreachable but fail toward visibility, not silence.
    return BUCKET_MALFORMED, None


def build_report(*, memory_root: Path, as_of: date) -> dict:
    counts = {
        BUCKET_UPDATED: 0,
        BUCKET_NOT_APPLICABLE: 0,
        BUCKET_DEFERRED: 0,
        BUCKET_NOT_DECLARED: 0,
        BUCKET_PRE_FIELD: 0,
        BUCKET_MALFORMED: 0,
    }
    deferred_by_reason: dict[str, dict] = {}
    not_declared = {"count": 0, "oldest_age_days": None, "oldest_record_date": None}
    files_scanned = 0
    records_total = 0
    files_with_decode_errors: list[str] = []

    daily_files = sorted(
        p for p in memory_root.glob("*.md") if _daily_file_date(p) is not None
    )
    for path in daily_files:
        file_date = _daily_file_date(path)
        assert file_date is not None
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Known historical encoding debt (e.g. cp950-era files). Count
            # records on a lossy decode and surface the file name; repairing
            # encodings is out of scope for an observation-class report.
            text = path.read_text(encoding="utf-8", errors="replace")
            files_with_decode_errors.append(path.name)
        for record in parse_session_derived_records(text):
            records_total += 1
            bucket, reason = classify_record(record, file_date)
            counts[bucket] += 1
            age_days = (as_of - file_date).days
            if bucket == BUCKET_DEFERRED and reason is not None:
                slot = deferred_by_reason.setdefault(
                    reason,
                    {"count": 0, "oldest_age_days": None, "oldest_record_date": None},
                )
                slot["count"] += 1
                if slot["oldest_age_days"] is None or age_days > slot["oldest_age_days"]:
                    slot["oldest_age_days"] = age_days
                    slot["oldest_record_date"] = file_date.isoformat()
            elif bucket == BUCKET_NOT_DECLARED:
                not_declared["count"] += 1
                if (
                    not_declared["oldest_age_days"] is None
                    or age_days > not_declared["oldest_age_days"]
                ):
                    not_declared["oldest_age_days"] = age_days
                    not_declared["oldest_record_date"] = file_date.isoformat()

    return {
        "tool": TOOL_ID,
        "report_format_version": REPORT_FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": as_of.isoformat(),
        "memory_root": str(memory_root),
        "field_introduced_date": FIELD_INTRODUCED_DATE.isoformat(),
        "files_scanned": files_scanned,
        "files_with_decode_errors": files_with_decode_errors,
        "session_derived_records_total": records_total,
        "counts_by_plan_reconciliation": counts,
        "deferred_by_reason": dict(sorted(deferred_by_reason.items())),
        "not_declared": not_declared,
        "claim_ceiling": (
            "observation-class only; no thresholds, no pass/fail, not a gate "
            "input; deferred-with-reason is a legal honest state; "
            "not_declared is advisory-era data; pre_field records are "
            "expected history, not debt; semantic PLAN-touch detection is "
            "not performed"
        ),
    }


def format_human(report: dict) -> str:
    lines = [
        f"[deferred_debt_report] as of {report['as_of_date']} "
        f"({report['files_scanned']} files, "
        f"{report['session_derived_records_total']} session-derived records)",
        "counts by plan_reconciliation:",
    ]
    for key, value in report["counts_by_plan_reconciliation"].items():
        lines.append(f"  {key}: {value}")
    if report["deferred_by_reason"]:
        lines.append("deferred by reason (count, oldest age days):")
        for reason, slot in report["deferred_by_reason"].items():
            lines.append(
                f"  {reason}: {slot['count']}, oldest {slot['oldest_age_days']}d "
                f"({slot['oldest_record_date']})"
            )
    else:
        lines.append("deferred by reason: none")
    nd = report["not_declared"]
    if nd["count"]:
        lines.append(
            f"not_declared: {nd['count']}, oldest {nd['oldest_age_days']}d "
            f"({nd['oldest_record_date']})"
        )
    else:
        lines.append("not_declared: none")
    lines.append(f"claim ceiling: {report['claim_ceiling']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only deferred-debt report over canonical daily memory "
            "files (observation-class; no thresholds, not a gate input)."
        )
    )
    parser.add_argument("--project-root", default=".", help="Repository root (default: .)")
    parser.add_argument("--format", choices=("json", "human"), default="human")
    parser.add_argument(
        "--as-of",
        default=None,
        help="Report date YYYY-MM-DD for age computation (default: today)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to also write the JSON report to",
    )
    args = parser.parse_args(argv)

    memory_root = Path(args.project_root).resolve() / "memory"
    if not memory_root.is_dir():
        print(f"[deferred_debt_report] error: memory root not found: {memory_root}")
        return 2
    if args.as_of is not None:
        try:
            as_of = date.fromisoformat(args.as_of)
        except ValueError:
            print(f"[deferred_debt_report] error: invalid --as-of date: {args.as_of}")
            return 2
    else:
        as_of = datetime.now().astimezone().date()

    report = build_report(memory_root=memory_root, as_of=as_of)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
