#!/usr/bin/env python3
"""
CodeBurn Stop Hook — Session Token Display (P6)

Triggered by Claude Code Stop hook after each session.
Displays per-session token reconstruction + rolling 5h/7d windows.

Epistemic contract (V-1, P6 Scope Constraints):
  - All displayed values are Class C: observer-reconstructed, not provider-measured
  - analysis_safe_for_decision = 0 — display is for observability only
  - Codex rate_limits.used_percent: read from JSONL, not stored in DB
  - Claude 5h/7d: rolling window from DB (token counts, not % — limit unknown)
  - Fail-silent by design (hook always exits 0)

Usage:
  Called via Stop hook: python codeburn/phase1/codeburn_session_display.py
  Or manually: python codeburn/phase1/codeburn_session_display.py --transcript PATH

DB path (persistent, for rolling windows):
  Env CODEBURN_DB  → override path
  Default: ~/.codeburn/codeburn.db
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Persistent DB helpers
# ---------------------------------------------------------------------------

def _get_db_path() -> Path:
    env = os.environ.get("CODEBURN_DB")
    if env:
        return Path(env)
    return Path.home() / ".codeburn" / "codeburn.db"


def _ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn


def _rolling_window(conn: sqlite3.Connection, provider: str, hours: int) -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) for provider in last N hours."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(prompt_tokens), 0)     AS pt,
            COALESCE(SUM(completion_tokens), 0) AS ct
        FROM steps
        WHERE provider = ? AND started_at >= ?
        """,
        (provider, cutoff),
    ).fetchone()
    return (row["pt"] if row else 0), (row["ct"] if row else 0)


# ---------------------------------------------------------------------------
# JSONL parsers
# ---------------------------------------------------------------------------

def _parse_claude_jsonl(path: Path) -> dict:
    """Parse Claude Code session JSONL. Returns session summary."""
    prompt_total = 0
    completion_total = 0
    turns = 0
    first_ts = None
    last_ts = None

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = rec.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts
                if rec.get("type") != "assistant":
                    continue
                usage = rec.get("message", {}).get("usage") or {}
                inp = usage.get("input_tokens")
                out = usage.get("output_tokens")
                if inp is not None or out is not None:
                    prompt_total += inp or 0
                    completion_total += out or 0
                    turns += 1
    except Exception:
        pass

    return {
        "provider": "claude",
        "turns": turns,
        "prompt_tokens": prompt_total,
        "completion_tokens": completion_total,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "rate_used_pct": None,
        "rate_resets_at": None,
    }


def _parse_codex_jsonl(path: Path) -> dict:
    """Parse Codex session JSONL. Returns session summary + rate_limits."""
    prompt_total = 0
    completion_total = 0
    turns = 0
    first_ts = None
    last_ts = None
    rate_used_pct = None
    rate_resets_at = None

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = rec.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts
                if rec.get("type") != "event_msg":
                    continue
                payload = rec.get("payload", {})
                if payload.get("type") != "token_count":
                    continue
                info = payload.get("info", {})
                last_usage = info.get("last_token_usage", {})
                inp = last_usage.get("input_tokens")
                out = last_usage.get("output_tokens")
                if inp is not None or out is not None:
                    prompt_total += inp or 0
                    completion_total += out or 0
                    turns += 1
                # rate_limits: read for display, not stored in DB (not an IAF field)
                rl = payload.get("rate_limits", {})
                if rl.get("used_percent") is not None:
                    rate_used_pct = rl["used_percent"]
                    rate_resets_at = rl.get("resets_at")
    except Exception:
        pass

    return {
        "provider": "codex",
        "turns": turns,
        "prompt_tokens": prompt_total,
        "completion_tokens": completion_total,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "rate_used_pct": rate_used_pct,
        "rate_resets_at": rate_resets_at,
    }


def _detect_provider(path: Path) -> str:
    """Detect provider from JSONL content heuristics."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                # Codex has event_msg + token_count
                if rec.get("type") == "event_msg":
                    if rec.get("payload", {}).get("type") == "token_count":
                        return "codex"
                # Claude has assistant + message.usage
                if rec.get("type") == "assistant" and "message" in rec:
                    return "claude"
    except Exception:
        pass
    return "claude"  # default


# ---------------------------------------------------------------------------
# Ingest session into persistent DB for rolling window tracking
# ---------------------------------------------------------------------------

def _ingest_into_persistent_db(
    conn: sqlite3.Connection,
    session_id: str,
    summary: dict,
) -> None:
    """Write session token records into persistent DB for rolling window queries."""
    provider = summary["provider"]
    turns = summary["turns"]
    if turns == 0:
        return

    # Ensure session row exists
    existing = conn.execute(
        "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO sessions (session_id, provider_summary) VALUES (?, ?)",
            (session_id, f"provider={provider}"),
        )

    # Check if already ingested (avoid double-counting)
    already = conn.execute(
        "SELECT COUNT(*) as n FROM steps WHERE session_id = ? AND provider = ?",
        (session_id, provider),
    ).fetchone()
    if already and already["n"] > 0:
        return  # already ingested this session

    # Write a single aggregate step for the session (not turn-by-turn)
    # This is sufficient for rolling window queries
    ts = summary.get("last_ts") or datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO steps
            (session_id, provider, step_kind, started_at,
             prompt_tokens, completion_tokens, total_tokens,
             token_source, real_time_observed)
        VALUES (?, ?, 'execution', ?, ?, ?, NULL, 'unknown', 0)
        """,
        (
            session_id,
            provider,
            ts,
            summary["prompt_tokens"],
            summary["completion_tokens"],
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _fmt(n: int) -> str:
    """Format token count with commas."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,}"
    return str(n)


def _bar(pct: float, width: int = 20) -> str:
    """ASCII progress bar for percentage."""
    filled = int(round(pct / 100 * width))
    filled = max(0, min(width, filled))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct:.0f}%"


def _resets_in(resets_at: Optional[str]) -> str:
    if not resets_at:
        return ""
    try:
        reset_dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = reset_dt - now
        if delta.total_seconds() <= 0:
            return " (resetting…)"
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        return f" (resets in {h}h {m:02d}m)"
    except Exception:
        return ""


def display(
    session_id: str,
    summary: dict,
    conn: Optional[sqlite3.Connection],
) -> None:
    provider = summary["provider"]
    turns = summary["turns"]
    pt = summary["prompt_tokens"]
    ct = summary["completion_tokens"]
    rate_pct = summary["rate_used_pct"]
    rate_resets = summary["rate_resets_at"]

    W = 64
    sep = "-" * W

    print()
    print(f"+{sep}+")
    print(f"|  CodeBurn | Session Token Summary | Class C{' ' * (W - 45)}|")
    print(f"|  observer-reconstructed | not decision-authoritative{' ' * (W - 53)}|")
    print(f"+{sep}+")
    print(f"|  provider : {provider:<51}|")
    print(f"|  session  : {session_id[:8]}...{' ' * (W - 22)}|")
    print(f"|  turns    : {turns:<51}|")
    print(f"|  input    : {_fmt(pt):>10}  tokens (reconstructed){' ' * (W - 46)}|")
    print(f"|  output   : {_fmt(ct):>10}  tokens (reconstructed){' ' * (W - 46)}|")

    # Codex: 5h rate limit from JSONL
    if provider == "codex" and rate_pct is not None:
        reset_str = _resets_in(rate_resets)
        bar = _bar(rate_pct)
        print(f"+{sep}+")
        line = f"  5h window  {bar}{reset_str}"
        print(f"|{line:<{W}}|")

    # Rolling windows from DB
    if conn is not None:
        print(f"+{sep}+")
        print(f"|  Rolling windows (Class C | all sessions){' ' * (W - 42)}|")
        pt5, ct5 = _rolling_window(conn, provider, 5)
        pt7d, ct7d = _rolling_window(conn, provider, 24 * 7)
        line5h = f"  last 5h : in={_fmt(pt5)}  out={_fmt(ct5)}"
        line7d = f"  last 7d : in={_fmt(pt7d)}  out={_fmt(ct7d)}"
        print(f"|{line5h:<{W}}|")
        print(f"|{line7d:<{W}}|")

    print(f"+{sep}+")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="CodeBurn session token display (Stop hook)",
        add_help=True,
    )
    parser.add_argument("--transcript", help="Path to session JSONL (overrides stdin)")
    parser.add_argument("--session-id", help="Session ID (overrides detection)")
    parser.add_argument("--no-db", action="store_true", help="Skip persistent DB (display only)")
    args = parser.parse_args()

    # 1. Get transcript path
    transcript_path: Optional[Path] = None
    session_id: Optional[str] = None

    if args.transcript:
        transcript_path = Path(args.transcript)
        session_id = args.session_id or transcript_path.stem
    else:
        # Read Stop hook stdin
        try:
            if not sys.stdin.isatty():
                hook_data = json.load(sys.stdin)
                tp = hook_data.get("transcript_path")
                if tp:
                    transcript_path = Path(tp)
                session_id = hook_data.get("session_id") or (transcript_path.stem if transcript_path else None)
        except Exception:
            pass

    if transcript_path is None or not transcript_path.exists():
        return 0  # fail-silent: no transcript available

    if session_id is None:
        session_id = transcript_path.stem

    # 2. Detect provider and parse
    provider = _detect_provider(transcript_path)
    if provider == "codex":
        summary = _parse_codex_jsonl(transcript_path)
    else:
        summary = _parse_claude_jsonl(transcript_path)

    if summary["turns"] == 0:
        return 0  # no token records — nothing to display

    # 3. Persistent DB for rolling windows
    conn = None
    if not args.no_db:
        try:
            db_path = _get_db_path()
            conn = _ensure_db(db_path)
            _ingest_into_persistent_db(conn, session_id, summary)
        except Exception:
            conn = None  # fail-silent: display without DB

    # 4. Display
    try:
        display(session_id, summary, conn)
    except Exception:
        pass  # fail-silent

    if conn:
        try:
            conn.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
