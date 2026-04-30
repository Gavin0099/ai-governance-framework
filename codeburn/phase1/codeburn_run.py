#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def _get_open_session(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        """
        SELECT session_id
        FROM sessions
        WHERE ended_at IS NULL OR ended_at = ''
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    return str(row[0]) if row else None


def _git_status(repo: Path) -> str:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return ""


def _git_changed_files(repo: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "diff", "--name-only"], cwd=repo, capture_output=True, text=True, check=True)
        lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
        return [ln.replace("\\", "/") for ln in lines]
    except Exception:
        return []


def _mark_session_partial(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("UPDATE sessions SET data_quality='partial' WHERE session_id=?", (session_id,))
    conn.commit()


def run_step(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    schema = Path(args.schema).resolve()
    repo = Path(args.repo).resolve()

    conn = sqlite3.connect(db_path)
    _ensure_schema(conn, schema)

    session_id = _get_open_session(conn)
    if not session_id:
        print('{"ok":false,"error":"no_open_session"}')
        return 1

    step_id = str(uuid.uuid4())
    started_at = _now_iso()
    git_before = _git_status(repo)

    cmd_text = " ".join(args.command).strip()
    if not cmd_text:
        print('{"ok":false,"error":"empty_command"}')
        return 1

    launched = True
    exit_code = None
    duration_ms = None
    stdout_bytes = 0
    stderr_bytes = 0
    stderr_text = ""
    ended_at = None

    start_dt = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            cmd_text,
            cwd=repo,
            shell=True,
            capture_output=True,
            text=False,
        )
        end_dt = datetime.now(timezone.utc)
        ended_at = end_dt.isoformat()
        duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
        exit_code = int(proc.returncode)
        stdout_bytes = len(proc.stdout or b"")
        stderr_bytes = len(proc.stderr or b"")
    except Exception as exc:
        launched = False
        end_dt = datetime.now(timezone.utc)
        ended_at = end_dt.isoformat()
        stderr_text = str(exc)
        stderr_bytes = len(stderr_text.encode("utf-8", errors="ignore"))
        _mark_session_partial(conn, session_id)

    git_after = _git_status(repo)

    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider,
          started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes,
          prompt_tokens, completion_tokens, total_tokens, token_source,
          retry_of, git_status_before, git_status_after
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?)
        """,
        (
            step_id,
            session_id,
            args.step_kind,
            cmd_text,
            args.provider,
            started_at,
            ended_at,
            duration_ms,
            exit_code,
            stdout_bytes,
            stderr_bytes,
            args.token_source,
            args.retry_of,
            git_before,
            git_after,
        ),
    )

    changed = _git_changed_files(repo)
    for path in changed:
        conn.execute(
            "INSERT INTO changed_files(step_id, file_path, change_kind, source) VALUES(?, ?, ?, ?)",
            (step_id, path, "modified", "git_diff_name_only"),
        )

    # Hard rule: failed to start -> session data_quality must be partial.
    if not launched:
        _mark_session_partial(conn, session_id)

    conn.commit()

    result = {
        "ok": True,
        "session_id": session_id,
        "step_id": step_id,
        "launched": launched,
        "step_kind": args.step_kind,
        "command": cmd_text,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "changed_files_count": len(changed),
    }
    import json

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if launched and exit_code == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="CodeBurn Phase1 run wrapper.")
    parser.add_argument("--db", default="codeburn/phase1/examples/phase1_demo.db")
    parser.add_argument("--schema", default="codeburn/phase1/schema.sql")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--step-kind", required=True, choices=["planning", "execution", "test", "retry", "reflection", "other"])
    parser.add_argument("--provider", default="local")
    parser.add_argument("--token-source", default="unknown", choices=["provider", "estimated", "unknown"])
    parser.add_argument("--retry-of", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    # allow: codeburn_run.py ... -- <command>
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    return run_step(args)


if __name__ == "__main__":
    raise SystemExit(main())
