#!/usr/bin/env python3
"""
Session end hook — reads artifacts/session-closeout.txt and closes out the governance session.

Intended to be called by Claude Code stop hook or manually.
Always runs at session stop — missing or invalid closeout produces a degraded
verdict, not a skipped run.

Closeout is classified across four independent layers:

  presence          file exists or not
  schema_validity   all required fields present
  content_sufficiency   fields have non-vague, specific content
  evidence_consistency  claimed files/checks can be partially cross-referenced

The overall closeout_status is the worst layer that failed.
ok=True only when all four layers pass.

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

# Phrases that indicate vague / non-verifiable content
_VAGUE_PHRASES = {
    "worked on things",
    "made improvements",
    "various changes",
    "misc",
    "updated files",
    "ran checks",
    "fixed stuff",
    "general updates",
}

# ── Layer result constants ────────────────────────────────────────────────────

# Presence
PRESENT = "present"
MISSING = "missing"

# Schema validity
SCHEMA_VALID = "valid"
SCHEMA_INVALID = "invalid"

# Content sufficiency
CONTENT_SUFFICIENT = "sufficient"
CONTENT_INSUFFICIENT = "insufficient"

# Evidence consistency
EVIDENCE_CONSISTENT = "consistent"
EVIDENCE_INCONSISTENT = "inconsistent"
EVIDENCE_UNCHECKED = "unchecked"  # nothing to cross-reference

# Overall closeout_status (worst-layer wins)
STATUS_VALID = "valid"
STATUS_MISSING = "closeout_missing"
STATUS_SCHEMA_INVALID = "schema_invalid"
STATUS_CONTENT_INSUFFICIENT = "content_insufficient"
STATUS_EVIDENCE_INCONSISTENT = "evidence_inconsistent"

_DEFAULT_RUNTIME_CONTRACT: dict[str, Any] = {
    "task": "session",
    "rules": ["common"],
    "risk": "low",
    "oversight": "auto",
    "memory_mode": "candidate",
}


# ── Layer 1: Presence ─────────────────────────────────────────────────────────

def _check_presence(path: Path) -> tuple[str, str]:
    """Returns (presence, raw_text)."""
    if not path.exists():
        return MISSING, ""
    try:
        return PRESENT, path.read_text(encoding="utf-8").strip()
    except Exception:
        return MISSING, ""


# ── Layer 2: Schema validity ──────────────────────────────────────────────────

def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().upper()
            value = value.strip()
            if key in REQUIRED_FIELDS:
                fields[key] = value
    return fields


def _check_schema(fields: dict[str, str]) -> tuple[str, list[str]]:
    """Returns (schema_validity, missing_fields)."""
    missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
    if missing:
        return SCHEMA_INVALID, missing
    return SCHEMA_VALID, []


# ── Layer 3: Content sufficiency ──────────────────────────────────────────────

def _is_vague(value: str) -> bool:
    lower = value.lower().strip()
    if any(phrase in lower for phrase in _VAGUE_PHRASES):
        return True
    # Single word values for fields that need substance
    if len(lower.split()) == 1 and lower not in {"none", "no_update"}:
        return True
    return False


def _check_content(fields: dict[str, str]) -> tuple[str, list[str]]:
    """Returns (content_sufficiency, insufficient_fields)."""
    insufficient = []

    work = fields.get("WORK_COMPLETED", "")
    if work.upper() not in {"NONE"} and _is_vague(work):
        insufficient.append("WORK_COMPLETED")

    checks = fields.get("CHECKS_RUN", "")
    if checks.upper() not in {"NONE"} and _is_vague(checks):
        insufficient.append("CHECKS_RUN")

    task = fields.get("TASK_INTENT", "")
    if _is_vague(task):
        insufficient.append("TASK_INTENT")

    if insufficient:
        return CONTENT_INSUFFICIENT, insufficient
    return CONTENT_SUFFICIENT, []


# ── Layer 4: Evidence consistency (best-effort) ───────────────────────────────

def _check_evidence(fields: dict[str, str], project_root: Path) -> tuple[str, list[str]]:
    """
    Best-effort cross-reference of claimed artifacts against the filesystem.

    Returns (evidence_consistency, inconsistencies).

    This is not exhaustive — it only flags what can be checked without
    running commands. Passing this layer does not prove claims are true.
    """
    inconsistencies = []

    # Check FILES_TOUCHED: if non-NONE, verify each listed file exists
    files_touched = fields.get("FILES_TOUCHED", "").strip()
    if files_touched.upper() not in {"NONE", ""}:
        claimed_files = [f.strip() for f in files_touched.split(",") if f.strip()]
        missing_files = []
        for claimed in claimed_files:
            # Try relative to project root
            candidate = project_root / claimed
            if not candidate.exists():
                # Also try as absolute path
                abs_candidate = Path(claimed)
                if not abs_candidate.exists():
                    missing_files.append(claimed)
        if missing_files:
            inconsistencies.append(
                f"FILES_TOUCHED claims files not found: {missing_files}"
            )

    # Check CHECKS_RUN: if it mentions governance tools, check artifacts exist
    checks_run = fields.get("CHECKS_RUN", "").strip()
    if checks_run.upper() not in {"NONE", ""} and "session_end_hook" in checks_run.lower():
        # If claiming session_end_hook was run, there should be prior verdicts
        verdicts_dir = project_root / "artifacts" / "runtime" / "verdicts"
        if not verdicts_dir.exists() or not any(verdicts_dir.glob("*.json")):
            inconsistencies.append(
                "CHECKS_RUN claims session_end_hook was run but no prior verdicts found"
            )

    if not fields.get("FILES_TOUCHED") and not fields.get("CHECKS_RUN"):
        return EVIDENCE_UNCHECKED, []

    if inconsistencies:
        return EVIDENCE_INCONSISTENT, inconsistencies

    return EVIDENCE_CONSISTENT, []


# ── Classification aggregate ──────────────────────────────────────────────────

def classify_closeout(path: Path, project_root: Path) -> dict[str, Any]:
    """
    Run all four classification layers and return a structured result.

    Layers are independent — all run regardless of prior failures.
    Overall closeout_status is the worst-layer result.
    """
    presence, raw_text = _check_presence(path)

    if presence == MISSING:
        return {
            "presence": MISSING,
            "schema_validity": SCHEMA_INVALID,
            "content_sufficiency": CONTENT_INSUFFICIENT,
            "evidence_consistency": EVIDENCE_UNCHECKED,
            "closeout_status": STATUS_MISSING,
            "missing_fields": REQUIRED_FIELDS,
            "insufficient_fields": [],
            "inconsistencies": [],
            "fields": {},
            "response_text": "",
        }

    fields = _parse_fields(raw_text)
    schema_validity, missing_fields = _check_schema(fields)
    content_sufficiency, insufficient_fields = _check_content(fields)
    evidence_consistency, inconsistencies = _check_evidence(fields, project_root)

    # Determine overall status (worst layer wins)
    if schema_validity == SCHEMA_INVALID:
        status = STATUS_SCHEMA_INVALID
    elif content_sufficiency == CONTENT_INSUFFICIENT:
        status = STATUS_CONTENT_INSUFFICIENT
    elif evidence_consistency == EVIDENCE_INCONSISTENT:
        status = STATUS_EVIDENCE_INCONSISTENT
    else:
        status = STATUS_VALID

    return {
        "presence": presence,
        "schema_validity": schema_validity,
        "content_sufficiency": content_sufficiency,
        "evidence_consistency": evidence_consistency,
        "closeout_status": status,
        "missing_fields": missing_fields,
        "insufficient_fields": insufficient_fields,
        "inconsistencies": inconsistencies,
        "fields": fields,
        "response_text": raw_text,
    }


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
    classification = classify_closeout(closeout_path, project_root)

    closeout_status = classification["closeout_status"]
    fields = classification["fields"]
    response_text = classification["response_text"]

    session_id = _generate_session_id()
    runtime_contract = _build_runtime_contract(fields)

    # Inject all four classification layers into checks so they are
    # recorded in the session_end verdict and trace artifacts.
    checks: dict[str, Any] = {
        "closeout_status": closeout_status,
        "closeout_file": str(closeout_path),
        "closeout_presence": classification["presence"],
        "closeout_schema_validity": classification["schema_validity"],
        "closeout_content_sufficiency": classification["content_sufficiency"],
        "closeout_evidence_consistency": classification["evidence_consistency"],
        "closeout_missing_fields": classification["missing_fields"],
        "closeout_insufficient_fields": classification["insufficient_fields"],
        "closeout_inconsistencies": classification["inconsistencies"],
    }

    # Only pass response_text when closeout is fully valid —
    # insufficient content must not reach memory.
    effective_response = response_text if closeout_status == STATUS_VALID else ""

    result = run_session_end(
        project_root=project_root,
        session_id=session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        response_text=effective_response,
        summary=fields.get("TASK_INTENT", ""),
    )

    return {
        "ok": result["ok"] and closeout_status == STATUS_VALID,
        "session_id": session_id,
        "closeout_status": closeout_status,
        "closeout_classification": {
            "presence": classification["presence"],
            "schema_validity": classification["schema_validity"],
            "content_sufficiency": classification["content_sufficiency"],
            "evidence_consistency": classification["evidence_consistency"],
        },
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
    ]

    clf = result.get("closeout_classification") or {}
    if clf:
        lines.append(f"  presence={clf.get('presence')}")
        lines.append(f"  schema_validity={clf.get('schema_validity')}")
        lines.append(f"  content_sufficiency={clf.get('content_sufficiency')}")
        lines.append(f"  evidence_consistency={clf.get('evidence_consistency')}")

    lines += [
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

    status = result["closeout_status"]
    if status == STATUS_MISSING:
        lines.append(f"hint: {CLOSEOUT_FILE} not found — write it before session ends")
        lines.append("hint: see docs/session-closeout-schema.md for required fields")
    elif status == STATUS_SCHEMA_INVALID:
        lines.append("hint: closeout file is missing required fields")
        lines.append("hint: see docs/session-closeout-schema.md for required fields")
    elif status == STATUS_CONTENT_INSUFFICIENT:
        lines.append("hint: closeout content is vague — use specific, verifiable claims")
        lines.append("hint: vague values in WORK_COMPLETED or CHECKS_RUN will be rejected")
    elif status == STATUS_EVIDENCE_INCONSISTENT:
        lines.append("hint: closeout claims could not be cross-referenced against filesystem")
        lines.append("hint: check FILES_TOUCHED lists files that actually exist")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Session end hook — classifies session-closeout.txt across four layers "
            "(presence / schema_validity / content_sufficiency / evidence_consistency) "
            "and closes out the governance session. Always runs."
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
