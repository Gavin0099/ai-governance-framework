#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path


def _load_phase1_bootstrap_module():
    module_path = Path(__file__).resolve().with_name("_phase1_cli_bootstrap.py")
    spec = importlib.util.spec_from_file_location("_phase1_cli_bootstrap", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load phase1 bootstrap: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BOOTSTRAP = _load_phase1_bootstrap_module()
token_observability_level = _BOOTSTRAP.load_token_observability_level()


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
    if token_source_summary in {"estimated", "unknown"}:
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
        "SELECT token_source, prompt_tokens, completion_tokens, total_tokens FROM steps WHERE session_id=?",
        (session_id,),
    ).fetchall()
    observability_level = token_observability_level(token_rows)
    token_source_summary = _token_source_summary(token_rows, observability_level)
    prompt_values = [row["prompt_tokens"] for row in token_rows if row["prompt_tokens"] is not None]
    completion_values = [row["completion_tokens"] for row in token_rows if row["completion_tokens"] is not None]
    total_values = [row["total_tokens"] for row in token_rows if row["total_tokens"] is not None]
    manual_count = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM step_ingestion_provenance p
            INNER JOIN steps s ON s.step_id = p.step_id
            WHERE s.session_id = ?
              AND p.acquisition_mode = 'manual_reported_usage'
            """,
            (session_id,),
        ).fetchone()[0]
    )
    return {
        "step_count": step_count,
        "token_comparability": token_provider_steps > 0,
        "token_count": {
            "prompt_tokens": int(sum(prompt_values)) if prompt_values else None,
            "completion_tokens": int(sum(completion_values)) if completion_values else None,
            "total_tokens": int(sum(total_values)) if total_values else None,
        },
        "token_observability_level": observability_level,
        "token_source_summary": token_source_summary,
        "provenance_warning": _provenance_warning(token_source_summary),
        "manual_reported_usage_count": manual_count,
        "manual_reported_usage_present": manual_count > 0,
    }


def _run_token_rows(conn: sqlite3.Connection, session_id: str, limit: int = 100) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT step_id, provider, started_at, command, prompt_tokens, completion_tokens, total_tokens, token_source
        FROM steps
        WHERE session_id=?
        ORDER BY started_at ASC, rowid ASC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "step_id": str(row["step_id"]),
                "provider": str(row["provider"]) if row["provider"] is not None else None,
                "started_at": str(row["started_at"]),
                "command": str(row["command"]),
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "total_tokens": row["total_tokens"],
                "token_source": str(row["token_source"]) if row["token_source"] is not None else None,
            }
        )
    return result


def build_report(db_path: Path, session_id: str | None, include_runs: bool = False, run_limit: int = 100) -> dict:
    conn = sqlite3.connect(db_path)
    row = _resolve_session(conn, session_id)
    if not row:
        return {"ok": False, "error": "session_not_found"}
    metrics = _session_metrics(conn, str(row["session_id"]))
    run_rows = _run_token_rows(conn, str(row["session_id"]), limit=run_limit) if include_runs else []
    return {
        "ok": True,
        "phase": "phase1",
        "status": "closed",
        "decision_usage_allowed": False,
        "decision_safety": "NON_DECISIONAL",
        "session_id": str(row["session_id"]),
        "task": str(row["task"]),
        "data_quality": str(row["data_quality"]),
        "token_comparability": metrics["token_comparability"],
        "token_count": metrics["token_count"],
        "token_observability_level": metrics["token_observability_level"],
        "token_source_summary": metrics["token_source_summary"],
        "provenance_warning": metrics["provenance_warning"],
        "manual_reported_usage_count": metrics["manual_reported_usage_count"],
        "manual_reported_usage_present": metrics["manual_reported_usage_present"],
        "non_authoritative_notice": "Token fields are observational only and MUST NOT be used for automated decision, gating, or quality inference.",
        "observability_boundary_disclosed": True,
        "step_count": metrics["step_count"],
        "runs": run_rows if include_runs else [],
        "file_activity": {
            "git_visible_only": True,
            "file_reads": 0,
            "file_writes": 0,
            "file_reads_visible": False,
        },
        "file_reads": "unsupported",
        "analysis_safe_for_decision": False,
        "governance_decision_usage_allowed": False,
        "operational_guard_usage_allowed": False,
        "non_authoritative_fields": [
            "token_count",
            "token_observability_level",
            "token_source_summary",
            "provenance_warning",
            "manual_reported_usage_count",
            "manual_reported_usage_present",
        ],
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
    print(
        "Token count: "
        f"prompt={report['token_count']['prompt_tokens']}, "
        f"completion={report['token_count']['completion_tokens']}, "
        f"total={report['token_count']['total_tokens']}"
    )
    if report["provenance_warning"] != "none":
        print(f"Provenance warning: {report['provenance_warning']}")
    print(report["non_authoritative_notice"])
    print("File activity: git-visible only")
    print("File reads: unsupported")
    print(f"Step count: {report['step_count']}")
    if report.get("runs"):
        print("Runs:")
        for run in report["runs"]:
            p = run["prompt_tokens"]
            c = run["completion_tokens"]
            t = run["total_tokens"]
            print(
                f"  {run['started_at']}  provider={run['provider']}  "
                f"p={p} c={c} t={t}  source={run['token_source']}"
            )


def main() -> int:
    print_phase1_header = _BOOTSTRAP.load_print_phase1_header()
    print_phase1_header()
    parser = argparse.ArgumentParser(description="CodeBurn Phase 1 report.")
    parser.add_argument("--db", default="codeburn/phase1/examples/phase1_demo.db")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--show-runs", action="store_true")
    parser.add_argument("--run-limit", type=int, default=100)
    args = parser.parse_args()

    report = build_report(
        Path(args.db).resolve(),
        args.session_id,
        include_runs=args.show_runs,
        run_limit=args.run_limit,
    )
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
