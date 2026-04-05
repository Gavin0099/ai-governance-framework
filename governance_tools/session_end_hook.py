#!/usr/bin/env python3
"""
Session end hook — reads artifacts/session-closeout.txt and closes out the governance session.

Intended to be called by Claude Code stop hook or manually.
Always runs at session stop — missing or invalid closeout produces a degraded
verdict, not a skipped run.

Four independent classification layers:

  presence            file exists and is readable
  schema_validity     all required fields present
  content_sufficiency fields contain specific, non-vague content with observable anchors
  evidence_consistency claimed files/checks cross-referenced against filesystem (best-effort)

"Observable anchors" for content_sufficiency:
  - WORK_COMPLETED must contain at least one filename (word with a dot extension)
    or at least one specific tool/command name — or explicitly claim NONE
  - CHECKS_RUN must name a specific check/command — or explicitly claim NONE

evidence_consistency is an inconsistency signal, not a proof of execution.
Passing it does not prove claims are true. It only means no detectable
filesystem inconsistency was found.

All layers run regardless of prior failures.
Overall closeout_status = worst layer that failed.
ok=True only when all four layers pass.

Memory promotion only occurs when closeout_status == valid.
"""

from __future__ import annotations

import argparse
import json
import re
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

# Vague phrases that indicate non-verifiable content
_VAGUE_PHRASES = frozenset({
    "worked on things",
    "made improvements",
    "various changes",
    "misc",
    "updated files",
    "ran checks",
    "fixed stuff",
    "general updates",
    "some work",
    "various fixes",
})

# Pattern for a filename-like token (word with a dot extension)
_FILENAME_PATTERN = re.compile(r"\b\w[\w/-]*\.\w{1,6}\b")

# Known governance / test tool names that count as observable anchors
_TOOL_ANCHORS = frozenset({
    "pytest", "python", "quickstart_smoke", "session_end_hook",
    "governance_drift_checker", "adopt_governance", "pre_task_check",
    "post_task_check", "session_start", "external_repo_readiness",
    "external_project_facts_intake", "npm", "cargo", "go", "make",
    "mypy", "ruff", "pylint", "flake8", "black",
})

# ── Layer result constants ────────────────────────────────────────────────────

PRESENT = "present"
MISSING = "missing"

SCHEMA_VALID = "valid"
SCHEMA_INVALID = "invalid"

CONTENT_SUFFICIENT = "sufficient"
CONTENT_INSUFFICIENT = "insufficient"

EVIDENCE_CONSISTENT = "consistent"
EVIDENCE_INCONSISTENT = "inconsistent"
EVIDENCE_UNCHECKED = "unchecked"

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
    missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
    return (SCHEMA_INVALID, missing) if missing else (SCHEMA_VALID, [])


# ── Layer 3: Content sufficiency (with observable anchors) ────────────────────

def _has_observable_anchor(value: str) -> bool:
    """
    Returns True if value contains at least one observable anchor:
    - a filename-like token (word.ext), OR
    - a known tool/command name
    """
    if _FILENAME_PATTERN.search(value):
        return True
    lower_tokens = set(re.split(r"[\s,/\-]+", value.lower()))
    return bool(lower_tokens & _TOOL_ANCHORS)


def _is_vague(value: str) -> bool:
    lower = value.lower().strip()
    return any(phrase in lower for phrase in _VAGUE_PHRASES)


def _check_content(fields: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    """
    Returns (content_sufficiency, issues).

    Each issue has: field, reason, guidance.
    Checks both vague-phrase rejection and observable-anchor presence.
    """
    issues: list[dict[str, str]] = []

    def _assess(field: str, require_anchor: bool = True) -> None:
        value = fields.get(field, "").strip()
        upper = value.upper()
        if upper in {"NONE", "NO_UPDATE"}:
            return  # explicit null is always acceptable

        if _is_vague(value):
            issues.append({
                "field": field,
                "reason": "vague_phrase",
                "guidance": "Avoid generic phrases. State specific files, commands, or outcomes.",
            })
            return  # no need to also check anchor

        if require_anchor and not _has_observable_anchor(value):
            issues.append({
                "field": field,
                "reason": "no_observable_anchor",
                "guidance": (
                    "Include at least one filename (e.g. foo.py) or tool name "
                    "(e.g. pytest, quickstart_smoke) so the claim can be cross-referenced."
                ),
            })

    _assess("WORK_COMPLETED", require_anchor=True)
    _assess("CHECKS_RUN", require_anchor=True)
    _assess("TASK_INTENT", require_anchor=False)  # intent doesn't need a filename

    return (CONTENT_INSUFFICIENT, issues) if issues else (CONTENT_SUFFICIENT, [])


# ── Layer 4: Evidence consistency (best-effort inconsistency signal) ──────────

def _check_evidence(fields: dict[str, str], project_root: Path) -> tuple[str, list[str]]:
    """
    Best-effort filesystem cross-reference.

    This is an inconsistency signal, not a proof of execution.
    Passing this layer does not prove claims are true.
    """
    inconsistencies: list[str] = []

    files_touched = fields.get("FILES_TOUCHED", "").strip()
    if files_touched and files_touched.upper() not in {"NONE", ""}:
        claimed_files = [f.strip() for f in files_touched.split(",") if f.strip()]
        missing_files = [
            f for f in claimed_files
            if not (project_root / f).exists() and not Path(f).exists()
        ]
        if missing_files:
            inconsistencies.append(
                f"FILES_TOUCHED lists files not found on filesystem: {missing_files}"
            )

    checks_run = fields.get("CHECKS_RUN", "").strip()
    if checks_run and checks_run.upper() not in {"NONE", ""}:
        if "session_end_hook" in checks_run.lower():
            verdicts_dir = project_root / "artifacts" / "runtime" / "verdicts"
            if not verdicts_dir.exists() or not any(verdicts_dir.glob("*.json")):
                inconsistencies.append(
                    "CHECKS_RUN claims session_end_hook was run but no prior verdicts found"
                )

    # No checkable claims → unchecked
    has_checkable = (
        files_touched and files_touched.upper() not in {"NONE", ""}
    ) or (
        checks_run and checks_run.upper() not in {"NONE", ""}
    )
    if not has_checkable:
        return EVIDENCE_UNCHECKED, []

    return (EVIDENCE_INCONSISTENT, inconsistencies) if inconsistencies else (EVIDENCE_CONSISTENT, [])


# ── Classification aggregate ──────────────────────────────────────────────────

def classify_closeout(path: Path, project_root: Path) -> dict[str, Any]:
    """
    Run all four layers independently. Return per-layer results and overall status.

    Overall status = worst layer that failed.
    per_layer_results is always preserved so reviewers see all failures,
    not just the first one.
    """
    presence, raw_text = _check_presence(path)

    if presence == MISSING:
        return {
            "presence": MISSING,
            "schema_validity": SCHEMA_INVALID,
            "content_sufficiency": CONTENT_INSUFFICIENT,
            "evidence_consistency": EVIDENCE_UNCHECKED,
            "closeout_status": STATUS_MISSING,
            "per_layer_results": {
                "missing_fields": REQUIRED_FIELDS[:],
                "content_issues": [],
                "inconsistencies": [],
            },
            "fields": {},
            "response_text": "",
        }

    fields = _parse_fields(raw_text)

    schema_validity, missing_fields = _check_schema(fields)
    content_sufficiency, content_issues = _check_content(fields)
    evidence_consistency, inconsistencies = _check_evidence(fields, project_root)

    # Worst-layer status
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
        "per_layer_results": {
            "missing_fields": missing_fields,
            "content_issues": content_issues,
            "inconsistencies": inconsistencies,
        },
        "fields": fields,
        "response_text": raw_text,
    }


# ── Runtime helpers ───────────────────────────────────────────────────────────

def _build_runtime_contract(fields: dict[str, str]) -> dict[str, Any]:
    contract = dict(_DEFAULT_RUNTIME_CONTRACT)
    task_intent = fields.get("TASK_INTENT", "").strip()
    if task_intent:
        contract["task"] = task_intent
    return contract


def _generate_session_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"session-{ts}-{uuid.uuid4().hex[:6]}"


# ── Main hook logic ───────────────────────────────────────────────────────────

def run_session_end_hook(project_root: Path) -> dict[str, Any]:
    closeout_path = project_root / CLOSEOUT_FILE
    clf = classify_closeout(closeout_path, project_root)

    closeout_status = clf["closeout_status"]
    fields = clf["fields"]

    session_id = _generate_session_id()
    runtime_contract = _build_runtime_contract(fields)

    # All four layer results go into checks so they appear in verdict/trace artifacts.
    checks: dict[str, Any] = {
        "closeout_status": closeout_status,
        "closeout_file": str(closeout_path),
        "closeout_presence": clf["presence"],
        "closeout_schema_validity": clf["schema_validity"],
        "closeout_content_sufficiency": clf["content_sufficiency"],
        "closeout_evidence_consistency": clf["evidence_consistency"],
        "closeout_per_layer_results": clf["per_layer_results"],
    }

    # Only pass content to session_end when all four layers pass.
    # Insufficient content must never reach memory even if schema is valid.
    effective_response = clf["response_text"] if closeout_status == STATUS_VALID else ""

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
            "presence": clf["presence"],
            "schema_validity": clf["schema_validity"],
            "content_sufficiency": clf["content_sufficiency"],
            "evidence_consistency": clf["evidence_consistency"],
        },
        "per_layer_results": clf["per_layer_results"],
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

    # Always show per_layer_results so multi-failure cases are visible
    per = result.get("per_layer_results") or {}
    if per.get("missing_fields"):
        lines.append(f"  missing_fields={per['missing_fields']}")
    if per.get("content_issues"):
        for issue in per["content_issues"]:
            lines.append(f"  content_issue: {issue['field']} — {issue['reason']}: {issue['guidance']}")
    if per.get("inconsistencies"):
        for inc in per["inconsistencies"]:
            lines.append(f"  inconsistency: {inc}")

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
        lines.append("hint: closeout file is missing required fields (see missing_fields above)")
    elif status == STATUS_CONTENT_INSUFFICIENT:
        lines.append("hint: include specific filenames or tool names — see content_issue above")
    elif status == STATUS_EVIDENCE_INCONSISTENT:
        lines.append("hint: FILES_TOUCHED lists files not found on filesystem")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Session end hook. Classifies session-closeout.txt across four independent layers "
            "(presence / schema_validity / content_sufficiency / evidence_consistency). "
            "Always runs. Missing or degraded closeout produces an auditable verdict."
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
