#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def _format_duration_ms(ms: int | None) -> str:
    if ms is None or ms < 0:
        return "unknown"
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}m{seconds:02d}s"


def _resolve_session_id(conn: sqlite3.Connection, session_id: str | None) -> str | None:
    if session_id and session_id != "latest":
        row = conn.execute("SELECT session_id FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return str(row[0]) if row else None
    row = conn.execute("SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1").fetchone()
    return str(row[0]) if row else None


def build_analysis(db_path: Path, session_id: str | None = "latest") -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    resolved = _resolve_session_id(conn, session_id)
    if not resolved:
        return {"ok": False, "error": "session_not_found"}

    session = conn.execute("SELECT * FROM sessions WHERE session_id=?", (resolved,)).fetchone()
    steps = conn.execute(
        """
        SELECT step_id, step_kind, command, duration_ms, exit_code
        FROM steps
        WHERE session_id=?
        ORDER BY started_at ASC, step_id ASC
        """,
        (resolved,),
    ).fetchall()
    step_count = len(steps)
    total_duration_ms = sum(int(r["duration_ms"]) for r in steps if r["duration_ms"] is not None)
    slowest = None
    for row in steps:
        if row["duration_ms"] is None:
            continue
        if slowest is None or int(row["duration_ms"]) > int(slowest["duration_ms"]):
            slowest = row

    breakdown = {
        "planning": 0,
        "execution": 0,
        "test": 0,
        "retry": 0,
        "reflection": 0,
        "other": 0,
    }
    for row in steps:
        kind = str(row["step_kind"])
        breakdown[kind] = breakdown.get(kind, 0) + 1

    changed_files_rows = conn.execute(
        """
        SELECT DISTINCT cf.file_path
        FROM changed_files cf
        JOIN steps s ON s.step_id = cf.step_id
        WHERE s.session_id=?
        ORDER BY cf.file_path ASC
        """,
        (resolved,),
    ).fetchall()
    changed_files = [str(r["file_path"]) for r in changed_files_rows]

    signals_rows = conn.execute(
        """
        SELECT signal, confidence, source
        FROM signals
        WHERE session_id=?
        ORDER BY id ASC
        """,
        (resolved,),
    ).fetchall()
    signals = [
        {"signal": str(r["signal"]), "confidence": str(r["confidence"]), "source": str(r["source"])}
        for r in signals_rows
    ]

    analysis = {
        "ok": True,
        "session_id": resolved,
        "task": str(session["task"]),
        "data_quality": str(session["data_quality"]),
        "token_comparability": False,
        "step_count": step_count,
        "total_duration_ms": total_duration_ms,
        "step_breakdown": breakdown,
        "slowest_step": (
            {
                "step_kind": str(slowest["step_kind"]),
                "command": str(slowest["command"]),
                "duration_ms": int(slowest["duration_ms"]),
                "exit_code": slowest["exit_code"],
            }
            if slowest
            else None
        ),
        "changed_files": changed_files,
        "signals": signals,
        "observability_limits": {
            "token_usage": "unknown",
            "file_reads": "unsupported",
            "file_activity": "git-visible only",
        },
    }
    return analysis


def print_analysis_text(analysis: dict) -> None:
    print("CodeBurn Post-Job Analysis")
    print("")
    print("Session:")
    print(f"  Task: {analysis['task']}")
    print(f"  Data quality: {analysis['data_quality']}")
    print(f"  Token comparability: {'true' if analysis['token_comparability'] else 'false'}")
    print("")
    print("Execution:")
    print(f"  Steps: {analysis['step_count']}")
    print(f"  Total duration: {_format_duration_ms(analysis['total_duration_ms'])}")
    slowest = analysis["slowest_step"]
    if slowest:
        print("  Slowest step:")
        print(
            f"    {slowest['step_kind']} | {slowest['command']} | "
            f"{_format_duration_ms(slowest['duration_ms'])} | exit_code={slowest['exit_code']}"
        )
    else:
        print("  Slowest step: none")
    print("")
    print("Step breakdown:")
    for key in ["planning", "execution", "test", "retry", "reflection", "other"]:
        print(f"  {key}: {analysis['step_breakdown'].get(key, 0)}")
    print("")
    print("Git-visible changes:")
    if analysis["changed_files"]:
        print(f"  {len(analysis['changed_files'])} file(s) changed")
        for path in analysis["changed_files"]:
            print(f"  - {path}")
    else:
        print("  0 file(s) changed")
    print("")
    print("Signals:")
    if analysis["signals"]:
        for item in analysis["signals"]:
            print(f"  [ADVISORY] {item['signal']}")
            print(f"  confidence: {item['confidence']}")
            print(f"  source: {item['source']}")
    else:
        print("  none")
    print("")
    print("Observability limits:")
    print("  - Token usage: unknown")
    print("  - File reads: unsupported")
    print("  - File activity: git-visible only")


def main() -> int:
    parser = argparse.ArgumentParser(description="CodeBurn Phase 1 post-job analysis.")
    parser.add_argument("--db", default="codeburn/phase1/examples/phase1_demo.db")
    parser.add_argument("--session", default="latest")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    result = build_analysis(Path(args.db).resolve(), args.session)
    if not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_analysis_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
