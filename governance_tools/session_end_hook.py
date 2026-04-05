#!/usr/bin/env python3
"""
Session end hook — reads artifacts/session-closeout.txt and closes out the governance session.

Intended to be called by Claude Code stop hook or manually.
Always runs at session stop — a missing or invalid closeout produces a
degraded verdict, not a skipped run.

Three cases:
  1. Closeout artifact exists and is parseable  → normal session_end with content
  2. Closeout artifact missing                  → session_end runs; verdict records closeout_missing
  3. Closeout artifact exists but insufficient  → session_end runs; verdict records closeout_insufficient

Usage:
    python -m governance_tools.session_end_hook --project-root .
    python -m governance_tools.session_end_hook --project-root . --format json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime_hooks.core.session_end import run_session_end


CLOSEOUT_FILE = "artifacts/session-closeout.txt"

REQUIRED_FIELDS = [
    "TASK_INTENT",
    "WORK_COMPLETED",
    "FILES_TOUCHED",
    "CHECKS_RUN",
    "OPEN_RISKS",
    "NOT_DONE",
    "RECOMMENDED_MEMORY_UPDATE",
]

# Fields where the stated value cannot be vague
VAGUE_MARKERS = {"worked on things", "made improvements", "various changes", "misc", "n/a"}

_DEFAULT_RUNTIME_CONTRACT: dict[str, Any] = {
    "task": "session",
    "rules": ["common"],
    "risk": "low",
    "oversight": "auto",
    "memory_mode": "candidate",
}


# ── Closeout status values ────────────────────────────────────────────────────

CLOSEOUT_VALID = "valid"
CLOSEOUT_MISSING = "closeout_missing"
CLOSEOUT_INSUFFICIENT = "closeout_insufficient"


# ── Artifact parsing ──────────────────────────────────────────────────────────

def _parse_closeout(text: str) -> dict[str, str]:
    """Parse key: value lines from the closeout artifact."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().upper()
            value = value.strip()
            if key in REQUIRED_FIELDS:
                fields[key] = value
    return fields


def _classify_closeout(path: Path) -> tuple[str, str, dict[str, str]]:
    """
    Returns (closeout_status, response_text, parsed_fields).

    closeout_status is one of: CLOSEOUT_VALID, CLOSEOUT_MISSING, CLOSEOUT_INSUFFICIENT
    response_text is the raw file content (empty string if missing/invalid)
    parsed_fields is the parsed key-value dict (empty if missing)
    """
    if not path.exists():
        return CLOSEOUT_MISSING, "", {}

    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        return CLOSEOUT_INSUFFICIENT, "", {}

    if not text:
        return CLOSEOUT_INSUFFICIENT, text, {}

    fields = _parse_closeout(text)

    # Check all required fields are present and non-empty
    missing_fields = [f for f in REQUIRED_FIELDS if not fields.get(f)]
    if missing_fields:
        return CLOSEOUT_INSUFFICIENT, text, fields

    # Check WORK_COMPLETED is not vague
    work = fields.get("WORK_COMPLETED", "").lower()
    if work and any(marker in work for marker in VAGUE_MARKERS):
        return CLOSEOUT_INSUFFICIENT, text, fields

    # Check CHECKS_RUN: if non-NONE, must contain at least one word that looks like a command
    checks = fields.get("CHECKS_RUN", "").strip()
    if checks and checks.upper() != "NONE" and len(checks.split()) < 2:
        return CLOSEOUT_INSUFFICIENT, text, fields

    return CLOSEOUT_VALID, text, fields


# ── Runtime contract ──────────────────────────────────────────────────────────

def _build_runtime_contract(fields: dict[str, str]) -> dict[str, Any]:
    contract = dict(_DEFAULT_RUNTIME_CONTRACT)
    task_intent = fields.get("TASK_INTENT", "").strip()
    if task_intent:
        contract["task"] = task_intent
    return contract


def _generate_session_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"session-{ts}-{short}"


# ── Main hook logic ───────────────────────────────────────────────────────────

def run_session_end_hook(project_root: Path) -> dict[str, Any]:
    closeout_path = project_root / CLOSEOUT_FILE
    closeout_status, response_text, fields = _classify_closeout(closeout_path)

    session_id = _generate_session_id()
    runtime_contract = _build_runtime_contract(fields)

    # Inject closeout_status into checks so session_end records it in the verdict
    checks: dict[str, Any] = {
        "closeout_status": closeout_status,
        "closeout_file": str(closeout_path),
        "closeout_fields_present": sorted(fields.keys()),
    }

    # For missing/insufficient closeout: pass empty response_text so session_end
    # skips snapshot creation and records the gap in memory_closeout.
    result = run_session_end(
        project_root=project_root,
        session_id=session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        response_text=response_text,
        summary=fields.get("TASK_INTENT", ""),
    )

    return {
        "ok": result["ok"] and closeout_status == CLOSEOUT_VALID,
        "session_id": session_id,
        "closeout_status": closeout_status,
        "closeout_file": str(closeout_path),
        "decision": result["decision"],
        "snapshot_created": result["snapshot"] is not None,
        "promoted": result["promotion"] is not None,
        "memory_closeout": result["memory_closeout"],
        "verdict_artifact": result["verdict_artifact"],
        "trace_artifact": result["trace_artifact"],
        "warnings": result["warnings"],
        "errors": result["errors"],
    }


# ── Output formatting ─────────────────────────────────────────────────────────

def format_human_result(result: dict[str, Any]) -> str:
    lines = [
        "[session_end_hook]",
        f"ok={result['ok']}",
        f"session_id={result['session_id']}",
        f"closeout_status={result['closeout_status']}",
        f"decision={result['decision']}",
        f"snapshot_created={result['snapshot_created']}",
        f"promoted={result['promoted']}",
    ]
    closeout = result.get("memory_closeout") or {}
    if closeout:
        lines.append(f"memory_closeout_decision={closeout.get('decision')}")
        lines.append(f"memory_closeout_reason={closeout.get('reason')}")
    for w in result["warnings"]:
        lines.append(f"warning: {w}")
    for e in result["errors"]:
        lines.append(f"error: {e}")

    if result["closeout_status"] == CLOSEOUT_MISSING:
        lines.append(f"hint: {CLOSEOUT_FILE} not found — write it before session ends")
        lines.append("hint: see docs/session-closeout-schema.md for required fields")
    elif result["closeout_status"] == CLOSEOUT_INSUFFICIENT:
        lines.append(f"hint: {CLOSEOUT_FILE} exists but failed completeness check")
        lines.append("hint: check all required fields are present and non-vague")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Session end hook — reads session-closeout.txt and closes out the governance session. "
            "Always runs; missing or invalid closeout produces a degraded verdict."
        )
    )
    parser.add_argument("--project-root", default=".", help="Consuming repo root")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    result = run_session_end_hook(project_root=project_root)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
