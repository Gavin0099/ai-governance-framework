from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from governance_tools.deferred_debt_report import (
    BUCKET_DEFERRED,
    BUCKET_MALFORMED,
    BUCKET_NOT_DECLARED,
    BUCKET_PRE_FIELD,
    BUCKET_UPDATED,
    build_report,
    classify_record,
    format_human,
    parse_session_derived_records,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _record(plan_reconciliation: str | None) -> str:
    lines = [
        "- memory_type: session-derived",
        "  record_format_version: 1.0",
        "  writer: governance_tools.memory_record",
        "  what_changed: x",
        "  commit: abc1234",
        "  commit_hash: abc1234",
        "  session_id: t",
        "  memory_binding: bound",
        "  test_evidence: t",
        "  next_step: t",
    ]
    if plan_reconciliation is not None:
        lines.append(f"  plan_reconciliation: {plan_reconciliation}")
    return "\n".join(lines) + "\n"


def _write_memory(tmp_path: Path, name: str, *records: str) -> None:
    memory = tmp_path / "memory"
    memory.mkdir(exist_ok=True)
    (memory / name).write_text(f"# {name[:-3]}\n\n" + "\n".join(records), encoding="utf-8")


def test_parser_extracts_only_session_derived_blocks():
    text = (
        "# 2026-06-13\n\n"
        + _record("updated")
        + "\n- memory_type: other-type\n  plan_reconciliation: updated\n\n"
        + _record("not_applicable")
    )
    records = parse_session_derived_records(text)
    assert len(records) == 2
    assert [r["plan_reconciliation"] for r in records] == ["updated", "not_applicable"]


def test_pre_field_guard_records_before_field_are_not_silent_debt():
    # Implementation guard (checkpoint): records before plan_reconciliation
    # existed must be counted as pre_field, not not_declared.
    assert classify_record({}, date(2026, 6, 11)) == (BUCKET_PRE_FIELD, None)
    assert classify_record({}, date(2026, 6, 12)) == (BUCKET_NOT_DECLARED, None)


def test_classify_buckets():
    d = date(2026, 6, 13)
    assert classify_record({"plan_reconciliation": "updated"}, d) == (BUCKET_UPDATED, None)
    assert classify_record({"plan_reconciliation": "not_declared"}, d) == (
        BUCKET_NOT_DECLARED,
        None,
    )
    assert classify_record(
        {"plan_reconciliation": "deferred:requires-human-plan-review"}, d
    ) == (BUCKET_DEFERRED, "requires-human-plan-review")
    assert classify_record({"plan_reconciliation": "deferred:later"}, d) == (
        BUCKET_MALFORMED,
        None,
    )
    assert classify_record({"plan_reconciliation": "done"}, d) == (BUCKET_MALFORMED, None)


def test_report_counts_ages_and_oldest_dates(tmp_path: Path):
    _write_memory(tmp_path, "2026-06-10.md", _record(None))
    _write_memory(
        tmp_path,
        "2026-06-12.md",
        _record("updated"),
        _record("not_declared"),
        _record("deferred:awaiting-reviewer-verdict"),
    )
    _write_memory(
        tmp_path,
        "2026-06-13.md",
        _record("deferred:awaiting-reviewer-verdict"),
        _record("not_applicable"),
    )
    report = build_report(memory_root=tmp_path / "memory", as_of=date(2026, 6, 14))

    assert report["files_scanned"] == 3
    assert report["session_derived_records_total"] == 6
    counts = report["counts_by_plan_reconciliation"]
    assert counts[BUCKET_PRE_FIELD] == 1
    assert counts[BUCKET_UPDATED] == 1
    assert counts[BUCKET_NOT_DECLARED] == 1
    assert counts[BUCKET_DEFERRED] == 2
    assert counts["not_applicable"] == 1
    assert counts[BUCKET_MALFORMED] == 0

    slot = report["deferred_by_reason"]["awaiting-reviewer-verdict"]
    assert slot["count"] == 2
    assert slot["oldest_age_days"] == 2  # 2026-06-12 -> 2026-06-14
    assert slot["oldest_record_date"] == "2026-06-12"

    nd = report["not_declared"]
    assert nd["count"] == 1
    assert nd["oldest_age_days"] == 2
    assert nd["oldest_record_date"] == "2026-06-12"


def test_non_daily_files_are_ignored(tmp_path: Path):
    _write_memory(tmp_path, "2026-06-13.md", _record("updated"))
    (tmp_path / "memory" / "01_active_task.md").write_text(
        "# Active Task\n" + _record("updated"), encoding="utf-8"
    )
    report = build_report(memory_root=tmp_path / "memory", as_of=date(2026, 6, 14))
    assert report["files_scanned"] == 1
    assert report["session_derived_records_total"] == 1


def test_report_is_read_only(tmp_path: Path):
    _write_memory(tmp_path, "2026-06-13.md", _record("updated"))
    memory = tmp_path / "memory"
    before = {p.name: p.read_bytes() for p in memory.iterdir()}
    build_report(memory_root=memory, as_of=date(2026, 6, 14))
    after = {p.name: p.read_bytes() for p in memory.iterdir()}
    assert before == after


def test_report_carries_claim_ceiling_and_no_verdict_fields(tmp_path: Path):
    _write_memory(tmp_path, "2026-06-13.md", _record("updated"))
    report = build_report(memory_root=tmp_path / "memory", as_of=date(2026, 6, 14))
    assert "claim_ceiling" in report
    # Observation-class: the report must not emit gate-like verdicts.
    for forbidden in ("ok", "passed", "failed", "blockers", "severity", "threshold"):
        assert forbidden not in report


def test_cli_json_output_and_optional_output_file(tmp_path: Path):
    _write_memory(tmp_path, "2026-06-13.md", _record("deferred:scope-split-next-slice"))
    out_file = tmp_path / "out" / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "governance_tools.deferred_debt_report",
            "--project-root",
            str(tmp_path),
            "--format",
            "json",
            "--as-of",
            "2026-06-14",
            "--output",
            str(out_file),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    stdout_report = json.loads(proc.stdout)
    file_report = json.loads(out_file.read_text(encoding="utf-8"))
    assert stdout_report["counts_by_plan_reconciliation"]["deferred"] == 1
    # Deterministic given the same inputs, apart from the generation timestamp.
    stdout_report.pop("generated_at")
    file_report.pop("generated_at")
    assert stdout_report == file_report


def test_cli_human_format_runs(tmp_path: Path):
    _write_memory(tmp_path, "2026-06-13.md", _record("updated"))
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "governance_tools.deferred_debt_report",
            "--project-root",
            str(tmp_path),
            "--as-of",
            "2026-06-14",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    assert "counts by plan_reconciliation" in proc.stdout
    assert "claim ceiling" in proc.stdout


def test_cli_errors_on_missing_memory_root(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "governance_tools.deferred_debt_report",
            "--project-root",
            str(tmp_path / "nope"),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        encoding="utf-8",
    )
    assert proc.returncode == 2


def test_non_utf8_daily_file_is_counted_and_surfaced(tmp_path: Path):
    # Historical encoding debt (cp950-era files) must not crash the report,
    # must still contribute record counts via lossy decode, and must be
    # surfaced by file name - observed, not repaired.
    memory = tmp_path / "memory"
    memory.mkdir()
    content = "# 2026-04-10\n\n" + _record(None)
    (memory / "2026-04-10.md").write_bytes(
        content.encode("utf-8").replace(b"x", b"\xa1\xff", 1)
    )
    _write_memory(tmp_path, "2026-06-13.md", _record("updated"))
    report = build_report(memory_root=memory, as_of=date(2026, 6, 14))
    assert report["files_with_decode_errors"] == ["2026-04-10.md"]
    assert report["counts_by_plan_reconciliation"][BUCKET_PRE_FIELD] == 1
    assert report["counts_by_plan_reconciliation"][BUCKET_UPDATED] == 1


def test_format_human_handles_empty_state(tmp_path: Path):
    (tmp_path / "memory").mkdir()
    report = build_report(memory_root=tmp_path / "memory", as_of=date(2026, 6, 14))
    text = format_human(report)
    assert "deferred by reason: none" in text
    assert "not_declared: none" in text
