#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from codeburn.phase1.token_observability import token_observability_level


def _bool_text(flag: bool) -> str:
    return "true" if flag else "false"


def _token_source_summary(token_rows: list[sqlite3.Row], observability_level: str) -> str:
    sources = {
        str(row["token_source"]).strip()
        for row in token_rows
        if str(row["token_source"] or "").strip() in {"provider", "estimated", "unknown"}
    }

    if "provider" in sources and "estimated" in sources:
        return "mixed(provider, estimated)"
    if observability_level == "step_level" and "provider" in sources and "unknown" in sources:
        return "mixed(provider, unknown)"
    if sources == {"provider"}:
        return "provider"
    if sources == {"estimated"}:
        return "estimated"
    if sources == {"unknown"} or not sources:
        return "unknown"
    if "provider" in sources:
        return "mixed(provider, unknown)"
    if "estimated" in sources and "unknown" in sources:
        return "mixed(estimated, unknown)"
    return "unknown"


def _provenance_warning(token_source_summary: str) -> str:
    if token_source_summary.startswith("mixed("):
        return "mixed_sources"
    if token_source_summary == "unknown":
        return "provenance_unverified"
    return "none"


def _resolve_session(conn: sqlite3.Connection, session_id: str | None) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    if session_id:
        return conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    return conn.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT 1").fetchone()


def _session_metrics(conn: sqlite3.Connection, session_id: str) -> dict:
    step_count = int(conn.execute("SELECT COUNT(*) FROM steps WHERE session_id=?", (session_id,)).fetchone()[0])
    token_provider_steps = int(
        conn.execute(
            "SELECT COUNT(*) FROM steps WHERE session_id=? AND token_source='provider'",
            (session_id,),
        ).fetchone()[0]
    )
    token_rows = conn.execute(
        "SELECT token_source, total_tokens FROM steps WHERE session_id=?",
        (session_id,),
    ).fetchall()
    observability_level = token_observability_level(token_rows)
    token_source_summary = _token_source_summary(token_rows, observability_level)
    return {
        "step_count": step_count,
        "token_comparability": token_provider_steps > 0,
        "token_observability_level": observability_level,
        "token_source_summary": token_source_summary,
        "provenance_warning": _provenance_warning(token_source_summary),
    }


def build_report(db_path: Path, session_id: str | None) -> dict:
    conn = sqlite3.connect(db_path)
    row = _resolve_session(conn, session_id)
    if not row:
        return {"ok": False, "error": "session_not_found"}
    metrics = _session_metrics(conn, str(row["session_id"]))
    return {
        "ok": True,
        "phase": "phase1",
        "status": "closed",
        "decision_usage_allowed": False,
        "session_id": str(row["session_id"]),
        "task": str(row["task"]),
        "data_quality": str(row["data_quality"]),
        "token_comparability": metrics["token_comparability"],
        "token_observability_level": metrics["token_observability_level"],
        "token_source_summary": metrics["token_source_summary"],
        "provenance_warning": metrics["provenance_warning"],
        "observability_boundary_disclosed": True,
        "step_count": metrics["step_count"],
        "file_activity": {
            "git_visible_only": True,
            "file_reads": 0,
            "file_writes": 0,
            "file_reads_visible": False,
        },
        "file_reads": "unsupported",
        "analysis_safe_for_decision": False,
    }


def _print_text(report: dict) -> None:
    print("CodeBurn Report")
    print("Interpretation notice: This analysis is observational. It is not a basis for optimization or correctness decisions.")
    print(f"Session: {report['session_id']}")
    print(f"Task: {report['task']}")
    print(f"Data quality: {report['data_quality']}")
    print(f"Token comparability: {_bool_text(bool(report['token_comparability']))}")
    print(f"Token observability level: {report['token_observability_level']}")
    print(f"Token source summary: {report['token_source_summary']}")
    if report["provenance_warning"] != "none":
        print(f"Provenance warning: {report['provenance_warning']}")
    print("File activity: git-visible only")
    print("File reads: unsupported")
    print(f"Step count: {report['step_count']}")


def main() -> int:
    from codeburn_phase1_header import print_phase1_header  # noqa: PLC0415
    print_phase1_header()
    parser = argparse.ArgumentParser(description="CodeBurn Phase 1 report.")
    parser.add_argument("--db", default="codeburn/phase1/examples/phase1_demo.db")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    report = build_report(Path(args.db).resolve(), args.session_id)
    if not report.get("ok"):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
