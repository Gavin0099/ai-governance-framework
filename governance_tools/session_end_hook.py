#!/usr/bin/env python3
"""
Session end hook — reads artifacts/session-closeout.txt and closes out the governance session.

Intended to be called by Claude Code stop hook or manually.
Always runs at session stop.

Four independent classification layers:

  presence            file exists and is readable
  schema_validity     all required fields present
  content_sufficiency fields contain specific, non-vague content with observable anchors
  evidence_consistency claimed files/tools cross-referenced against filesystem + execution artifacts

"Observable anchors" for content_sufficiency:
  - WORK_COMPLETED must contain a filename (word.ext) or known tool name — or NONE
  - CHECKS_RUN must name a specific check/command — or NONE

evidence_consistency is an inconsistency signal, not proof of execution.
It raises the cost of fake claims. It does not eliminate them.

Memory promotion tiers:
  working_state_update  content_sufficient — allows state tracking even when evidence is unchecked
  verified_state_update valid (all 4 layers) — full memory promotion

This prevents governance over-strictness from starving memory.
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
from governance_tools.gate_policy import (
    load_policy,
    classify_artifact,
    evaluate_gate,
    ARTIFACT_STATE_ABSENT,
    ARTIFACT_STATE_OK,
)


CLOSEOUT_FILE = "artifacts/session-closeout.txt"

# Standard path where test_result_ingestor writes the ingested test result.
# Gate decisions are delegated entirely to gate_policy.py — session_end_hook
# never hardcodes blocking logic.
_TEST_RESULT_ARTIFACT = "artifacts/runtime/test-results/latest.json"

REQUIRED_FIELDS = [
    "TASK_INTENT",
    "WORK_COMPLETED",
    "FILES_TOUCHED",
    "CHECKS_RUN",
    "OPEN_RISKS",
    "NOT_DONE",
    "RECOMMENDED_MEMORY_UPDATE",
]

_VAGUE_PHRASES = frozenset({
    "worked on things", "made improvements", "various changes", "misc",
    "updated files", "ran checks", "fixed stuff", "general updates",
    "some work", "various fixes",
})

_FILENAME_PATTERN = re.compile(r"\b\w[\w/-]*\.\w{1,6}\b")

_TOOL_ANCHORS = frozenset({
    "pytest", "python", "quickstart_smoke", "session_end_hook",
    "governance_drift_checker", "adopt_governance", "pre_task_check",
    "post_task_check", "session_start", "external_repo_readiness",
    "external_project_facts_intake", "npm", "cargo", "go", "make",
    "mypy", "ruff", "pylint", "flake8", "black",
})

# Maps tool names to directories/patterns that indicate the tool was run
_TOOL_ARTIFACT_SIGNALS: dict[str, list[str]] = {
    "pytest": [".pytest_cache", "test-results", ".tox"],
    "session_end_hook": ["artifacts/runtime/verdicts"],
    "quickstart_smoke": ["artifacts/runtime/verdicts", "scratch_quickstart_smoke"],
    "governance_drift_checker": [".governance-state.yaml", ".governance-audit"],
    "adopt_governance": [".governance/baseline.yaml"],
    "pre_task_check": ["artifacts/runtime/traces"],
    "post_task_check": ["artifacts/runtime/traces"],
}

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

# Memory promotion tiers
MEMORY_TIER_VERIFIED = "verified_state_update"   # all 4 layers pass
MEMORY_TIER_WORKING = "working_state_update"     # content_sufficient, evidence unchecked/failed
MEMORY_TIER_NONE = "no_update"                   # schema or content failed

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


# ── Layer 3: Content sufficiency ──────────────────────────────────────────────

def _has_observable_anchor(value: str) -> bool:
    if _FILENAME_PATTERN.search(value):
        return True
    tokens = set(re.split(r"[\s,/\-]+", value.lower()))
    return bool(tokens & _TOOL_ANCHORS)


def _is_vague(value: str) -> bool:
    lower = value.lower().strip()
    return any(phrase in lower for phrase in _VAGUE_PHRASES)


def _check_content(fields: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    issues: list[dict[str, str]] = []

    def _assess(field: str, require_anchor: bool = True) -> None:
        value = fields.get(field, "").strip()
        if value.upper() in {"NONE", "NO_UPDATE"}:
            return
        if _is_vague(value):
            issues.append({
                "field": field,
                "type": "vague_phrase",
                "guidance": "Avoid generic phrases. State specific files, commands, or outcomes.",
            })
            return
        if require_anchor and not _has_observable_anchor(value):
            issues.append({
                "field": field,
                "type": "no_observable_anchor",
                "guidance": (
                    "Include at least one filename (e.g. foo.py) or tool name "
                    "(e.g. pytest, session_end_hook) to allow cross-referencing."
                ),
            })

    _assess("WORK_COMPLETED", require_anchor=True)
    _assess("CHECKS_RUN", require_anchor=True)
    _assess("TASK_INTENT", require_anchor=False)

    return (CONTENT_INSUFFICIENT, issues) if issues else (CONTENT_SUFFICIENT, [])


# ── Layer 4: Evidence consistency (cross-reference) ───────────────────────────

def _extract_tool_names(text: str) -> list[str]:
    """Extract known tool names mentioned in a field value."""
    tokens = set(re.split(r"[\s,/()\-]+", text.lower()))
    return [t for t in _TOOL_ANCHORS if t in tokens]


def _check_evidence(
    fields: dict[str, str], project_root: Path
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """
    Cross-reference claimed files and tools against filesystem + artifacts.

    Returns (evidence_consistency, inconsistencies, cross_reference_results).

    cross_reference_results records what was checked and found, so
    failure_signals can map to root causes.
    """
    inconsistencies: list[str] = []
    cross_refs: list[dict[str, Any]] = []
    has_checkable = False

    # FILES_TOUCHED: each file must exist
    files_touched = fields.get("FILES_TOUCHED", "").strip()
    if files_touched and files_touched.upper() not in {"NONE", ""}:
        has_checkable = True
        claimed_files = [f.strip() for f in files_touched.split(",") if f.strip()]
        for claimed in claimed_files:
            exists = (project_root / claimed).exists() or Path(claimed).exists()
            cross_refs.append({
                "type": "file_existence",
                "claimed": claimed,
                "found": exists,
            })
            if not exists:
                inconsistencies.append(
                    f"FILES_TOUCHED: '{claimed}' not found on filesystem"
                )

    # CHECKS_RUN: extract tool names, check for corresponding artifacts
    checks_run = fields.get("CHECKS_RUN", "").strip()
    if checks_run and checks_run.upper() not in {"NONE", ""}:
        has_checkable = True
        found_tools = _extract_tool_names(checks_run)
        for tool in found_tools:
            signals = _TOOL_ARTIFACT_SIGNALS.get(tool, [])
            artifact_found = any(
                (project_root / sig).exists() for sig in signals
            )
            cross_refs.append({
                "type": "tool_artifact_signal",
                "tool": tool,
                "checked_paths": signals,
                "artifact_found": artifact_found,
            })
            if signals and not artifact_found:
                inconsistencies.append(
                    f"CHECKS_RUN: '{tool}' claimed but no corresponding artifact found "
                    f"(checked: {signals})"
                )

    if not has_checkable:
        return EVIDENCE_UNCHECKED, [], cross_refs

    return (
        (EVIDENCE_INCONSISTENT, inconsistencies, cross_refs)
        if inconsistencies
        else (EVIDENCE_CONSISTENT, [], cross_refs)
    )


# ── Failure signals ───────────────────────────────────────────────────────────

def _build_failure_signals(
    schema_validity: str,
    missing_fields: list[str],
    content_sufficiency: str,
    content_issues: list[dict[str, str]],
    evidence_consistency: str,
    inconsistencies: list[str],
) -> list[dict[str, Any]]:
    """
    Map per-layer failures to root-cause signals.

    This lets reviewers see WHY something failed, not just WHAT failed.
    Multiple layers can share the same root cause (e.g. no specific content
    causes both content and evidence failures).
    """
    signals: list[dict[str, Any]] = []

    if schema_validity == SCHEMA_INVALID:
        signals.append({
            "type": "missing_required_fields",
            "affects": ["schema_validity"],
            "detail": missing_fields,
            "guidance": "All 7 fields must be present. See docs/session-closeout-schema.md.",
        })

    for issue in content_issues:
        if issue["type"] == "vague_phrase":
            signals.append({
                "type": "vague_phrase_detected",
                "affects": ["content_sufficiency"],
                "field": issue["field"],
                "guidance": issue["guidance"],
            })
        elif issue["type"] == "no_observable_anchor":
            signals.append({
                "type": "no_observable_anchor",
                "affects": ["content_sufficiency", "evidence_consistency"],
                "field": issue["field"],
                "guidance": issue["guidance"],
            })

    for inc in inconsistencies:
        signals.append({
            "type": "cross_reference_failed",
            "affects": ["evidence_consistency"],
            "detail": inc,
            "guidance": "Verify the file exists or the tool was actually run.",
        })

    return signals


# ── Readiness level detection (metadata only, never decision input) ───────────

def detect_readiness_level(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """
    Detect the structural readiness level of the consuming repo (0-3).

    Returns two independent dimensions:

      level (0-3)                 Structural capability — what governance
                                  infrastructure is in place. Determined by
                                  capability checklist, not session history.

      closeout_activation_state   Whether the cross-reference loop has been
        "active"                  observed in practice (verdict artifacts exist).
        "pending"                 Structural prerequisites met but no verdicts yet.
        "unknown"                 Structural level too low to activate.

    These two dimensions are SEPARATE. A repo can be structural Level 3 with
    activation=pending (all capability in place, no run yet). A repo can be
    activation=active at Level 1 (has run, but content governance incomplete).

    Prior verdict artifacts affect activation_state only. They do NOT affect level.
    Level is determined purely by structural capability checklist.

    IMPORTANT: This result is injected into verdict/trace artifacts as metadata.
    It is NEVER read back as decision input. A Level 0 repo can produce a valid
    closeout. A Level 3 repo can produce closeout_missing.

    See docs/closeout-readiness-spectrum.md for level definitions.
    """
    checks: dict[str, Any] = {}

    # ── Level 0: hook can run + artifacts writable ────────────────────────────
    artifacts_dir = project_root / "artifacts"
    l0 = {
        "hook_callable": True,  # always true if we got here
        "artifacts_writable": _can_write(artifacts_dir),
    }
    checks["level_0"] = l0
    if not all(l0.values()):
        return {
            "level": 0,
            "checklist": checks,
            "limiting_factor": "artifacts_not_writable",
            "suggested_next_step": "mkdir -p artifacts/runtime && chmod -R u+w artifacts/",
            "closeout_activation_state": "unknown",
            "activation_recency": None,
            "activation_gap": "structural_prerequisites_missing",
        }

    # ── Level 1: schema doc + AGENTS.base.md closeout obligation ─────────────
    schema_doc = (framework_root / "docs" / "session-closeout-schema.md").exists()
    agents_base = _agents_base_has_obligation(project_root)
    l1 = {
        "schema_doc_present": schema_doc,
        "agents_base_has_obligation": agents_base,
    }
    checks["level_1"] = l1
    if not all(l1.values()):
        limiting = _first_false(l1)
        next_step = (
            "python -m governance_tools.upgrade_closeout --repo <repo>"
            if limiting == "agents_base_has_obligation"
            else "Ensure docs/session-closeout-schema.md is present in the framework repo"
        )
        return {
            "level": 0,
            "checklist": checks,
            "limiting_factor": limiting,
            "suggested_next_step": next_step,
            "closeout_activation_state": "unknown",
            "activation_recency": None,
            "activation_gap": "structural_prerequisites_missing",
        }

    # ── Level 2: content governance aligned ──────────────────────────────────
    agents_has_anchors = _agents_base_has_anchor_guidance(project_root)
    l2 = {
        "agents_base_has_anchor_guidance": agents_has_anchors,
    }
    checks["level_2"] = l2
    if not all(l2.values()):
        activation = _detect_activation_state(project_root)
        return {
            "level": 1,
            "checklist": checks,
            "limiting_factor": _first_false(l2),
            "suggested_next_step": (
                "python -m governance_tools.upgrade_closeout --repo <repo>  "
                "(re-run to patch anchor guidance)"
            ),
            **activation,
        }

    # ── Level 3: cross-reference capability ──────────────────────────────────
    # Cross-reference (FILES_TOUCHED existence + CHECKS_RUN artifact signals)
    # is always active in the current framework code. Level 3 structural
    # capability is achieved whenever Level 2 is met.
    # Prior verdict artifacts are an ACTIVATION signal, not a structural one.
    l3 = {
        "tool_artifact_signals_configured": True,  # always true in current code
        "working_vs_verified_split_active": True,  # always true in current code
    }
    checks["level_3"] = l3

    activation = _detect_activation_state(project_root)
    return {
        "level": 3,
        "checklist": checks,
        "limiting_factor": None,
        "suggested_next_step": None,
        **activation,
    }


_ACTIVATION_RECENCY_DAYS = 30  # verdicts older than this are considered stale


def _detect_activation_state(project_root: Path) -> dict[str, Any]:
    """
    Compute closeout_activation_state independently of structural level.

    Values:
      observed  — at least one verdict artifact file exists in artifacts/runtime/verdicts/
      pending   — structural prerequisites met but no verdict artifacts yet

    IMPORTANT SEMANTIC NOTE:
      'observed' answers "has the stop hook ever written a verdict?" — not
      "is this repo currently reliable?" or "did recent sessions pass?".
      observed ≠ trustworthy. observed = hook was invoked at least once.

    activation_recency (only set when observed):
      recent  — most recent verdict FILE mtime is within _ACTIVATION_RECENCY_DAYS days
      stale   — verdict files exist but most recent mtime exceeds that threshold

    What recency does NOT check:
      - Whether the session produced closeout_status=valid
      - Whether memory was promoted
      - Whether the closeout content was sufficient

    recent is an operational heuristic (was the hook invoked recently?), not a
    health guarantee (is the governance working?).

    activation_state reduces the risk of completely unverified operation.
    It does not eliminate errors or adversarial behavior.
    """
    verdicts_dir = project_root / "artifacts" / "runtime" / "verdicts"
    if not verdicts_dir.exists():
        return {
            "closeout_activation_state": "pending",
            "activation_recency": None,
            "activation_gap": "no_prior_verdict_artifacts",
        }

    verdict_files = sorted(verdicts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not verdict_files:
        return {
            "closeout_activation_state": "pending",
            "activation_recency": None,
            "activation_gap": "no_prior_verdict_artifacts",
        }

    # Most recent verdict file
    latest = verdict_files[-1]
    age_seconds = datetime.now(tz=timezone.utc).timestamp() - latest.stat().st_mtime
    age_days = age_seconds / 86400
    recency = "recent" if age_days <= _ACTIVATION_RECENCY_DAYS else "stale"

    return {
        "closeout_activation_state": "observed",
        "activation_recency": recency,
        "activation_gap": None,
    }


def _can_write(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".write_test"
        test.write_text("x")
        test.unlink()
        return True
    except Exception:
        return False


def _agents_base_has_obligation(project_root: Path) -> bool:
    for candidate in ["AGENTS.base.md", "AGENTS.md"]:
        f = project_root / candidate
        if f.exists():
            try:
                return "Session Closeout Obligation" in f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return False


def _agents_base_has_anchor_guidance(project_root: Path) -> bool:
    for candidate in ["AGENTS.base.md", "AGENTS.md"]:
        f = project_root / candidate
        if f.exists():
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                return "observable anchor" in text.lower() or "vague" in text.lower()
            except Exception:
                pass
    return False


def _first_false(d: dict[str, Any]) -> str:
    return next((k for k, v in d.items() if not v), "unknown")


# ── Memory promotion tier ─────────────────────────────────────────────────────

def _determine_memory_tier(
    closeout_status: str,
    content_sufficiency: str,
    evidence_consistency: str,
) -> str:
    """
    Two-tier memory promotion:

    verified_state_update  all four layers pass (closeout_status == valid)
    working_state_update   content is sufficient but evidence is unchecked or inconsistent
    no_update              schema or content failed — content cannot be trusted

    Rationale: governance over-strictness that blocks ALL memory updates when
    evidence_consistency fails causes "clean-death" — memory never updates,
    state tracking breaks. working_state_update allows session state tracking
    without claiming verified completeness.
    """
    if closeout_status == STATUS_VALID:
        return MEMORY_TIER_VERIFIED
    if content_sufficiency == CONTENT_SUFFICIENT:
        # content is meaningful even if evidence cross-ref failed or was unchecked
        return MEMORY_TIER_WORKING
    return MEMORY_TIER_NONE


# ── Classification aggregate ──────────────────────────────────────────────────

def classify_closeout(path: Path, project_root: Path) -> dict[str, Any]:
    presence, raw_text = _check_presence(path)

    if presence == MISSING:
        return {
            "presence": MISSING,
            "schema_validity": SCHEMA_INVALID,
            "content_sufficiency": CONTENT_INSUFFICIENT,
            "evidence_consistency": EVIDENCE_UNCHECKED,
            "closeout_status": STATUS_MISSING,
            "memory_tier": MEMORY_TIER_NONE,
            "per_layer_results": {
                "missing_fields": REQUIRED_FIELDS[:],
                "content_issues": [],
                "inconsistencies": [],
                "cross_reference_results": [],
            },
            "failure_signals": [{
                "type": "closeout_file_missing",
                "affects": ["presence", "schema_validity", "content_sufficiency"],
                "guidance": f"Write {CLOSEOUT_FILE} before session ends. See docs/session-closeout-schema.md.",
            }],
            "fields": {},
            "response_text": "",
        }

    fields = _parse_fields(raw_text)
    schema_validity, missing_fields = _check_schema(fields)
    content_sufficiency, content_issues = _check_content(fields)
    evidence_consistency, inconsistencies, cross_refs = _check_evidence(fields, project_root)

    # Worst-layer status
    if schema_validity == SCHEMA_INVALID:
        status = STATUS_SCHEMA_INVALID
    elif content_sufficiency == CONTENT_INSUFFICIENT:
        status = STATUS_CONTENT_INSUFFICIENT
    elif evidence_consistency == EVIDENCE_INCONSISTENT:
        status = STATUS_EVIDENCE_INCONSISTENT
    else:
        status = STATUS_VALID

    memory_tier = _determine_memory_tier(status, content_sufficiency, evidence_consistency)

    failure_signals = _build_failure_signals(
        schema_validity, missing_fields,
        content_sufficiency, content_issues,
        evidence_consistency, inconsistencies,
    )

    return {
        "presence": presence,
        "schema_validity": schema_validity,
        "content_sufficiency": content_sufficiency,
        "evidence_consistency": evidence_consistency,
        "closeout_status": status,
        "memory_tier": memory_tier,
        "per_layer_results": {
            "missing_fields": missing_fields,
            "content_issues": content_issues,
            "inconsistencies": inconsistencies,
            "cross_reference_results": cross_refs,
        },
        "failure_signals": failure_signals,
        "fields": fields,
        "response_text": raw_text,
    }


# ── Runtime helpers ───────────────────────────────────────────────────────────

def _build_runtime_contract(fields: dict[str, str], memory_tier: str) -> dict[str, Any]:
    contract = dict(_DEFAULT_RUNTIME_CONTRACT)
    task_intent = fields.get("TASK_INTENT", "").strip()
    if task_intent:
        contract["task"] = task_intent
    # working_state updates use candidate mode — they go through normal promotion policy
    # but are tagged so reviewers know the confidence level
    if memory_tier == MEMORY_TIER_NONE:
        contract["memory_mode"] = "stateless"
    return contract


def _generate_session_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"session-{ts}-{uuid.uuid4().hex[:6]}"


# ── Main hook logic ───────────────────────────────────────────────────────────

def run_session_end_hook(project_root: Path) -> dict[str, Any]:
    closeout_path = project_root / CLOSEOUT_FILE
    clf = classify_closeout(closeout_path, project_root)

    closeout_status = clf["closeout_status"]
    memory_tier = clf["memory_tier"]
    fields = clf["fields"]

    session_id = _generate_session_id()
    runtime_contract = _build_runtime_contract(fields, memory_tier)

    # Detect readiness level as metadata — NEVER used as decision input.
    # Injected into checks so it appears in verdict/trace artifacts for
    # reviewer context and adoption debugging.
    framework_root = Path(__file__).resolve().parents[1]
    readiness = detect_readiness_level(project_root, framework_root)

    checks: dict[str, Any] = {
        "closeout_status": closeout_status,
        "closeout_file": str(closeout_path),
        "closeout_presence": clf["presence"],
        "closeout_schema_validity": clf["schema_validity"],
        "closeout_content_sufficiency": clf["content_sufficiency"],
        "closeout_evidence_consistency": clf["evidence_consistency"],
        "closeout_memory_tier": memory_tier,
        "closeout_per_layer_results": clf["per_layer_results"],
        "closeout_failure_signals": clf["failure_signals"],
        # Readiness metadata — context only, never decision input
        "repo_readiness_level": readiness["level"],
        "repo_readiness_limiting_factor": readiness["limiting_factor"],
        "repo_closeout_activation_state": readiness.get("closeout_activation_state", "unknown"),
        "repo_activation_recency": readiness.get("activation_recency"),
        "repo_activation_gap": readiness.get("activation_gap"),
    }

    # Pass response_text for working_state and verified tiers.
    # memory_mode=stateless blocks memory for MEMORY_TIER_NONE at the contract level.
    effective_response = (
        clf["response_text"]
        if memory_tier in {MEMORY_TIER_VERIFIED, MEMORY_TIER_WORKING}
        else ""
    )

    result = run_session_end(
        project_root=project_root,
        session_id=session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        response_text=effective_response,
        summary=fields.get("TASK_INTENT", ""),
    )

    # Gate evaluation — policy-driven, not hardcoded.
    # load_policy reads governance/gate_policy.yaml; falls back to defaults.
    # classify_artifact determines absent/malformed/stale/ok.
    # evaluate_gate applies fail_mode + blocking_actions + unknown_treatment.
    policy = load_policy()
    artifact_path = project_root / _TEST_RESULT_ARTIFACT
    artifact_result = classify_artifact(artifact_path, policy)
    gate = evaluate_gate(artifact_result, policy)

    failure_disposition_data = artifact_result.failure_disposition

    base_ok = result["ok"] and closeout_status == STATUS_VALID and not gate.blocked
    gate_errors: list[str] = list(result["errors"]) + gate.errors
    gate_warnings: list[str] = list(result["warnings"]) + gate.warnings

    return {
        "ok": base_ok,
        "session_id": session_id,
        "closeout_status": closeout_status,
        "memory_tier": memory_tier,
        "repo_readiness_level": readiness["level"],
        "repo_readiness_limiting_factor": readiness["limiting_factor"],
        "repo_closeout_activation_state": readiness.get("closeout_activation_state", "unknown"),
        "repo_activation_recency": readiness.get("activation_recency"),
        "repo_activation_gap": readiness.get("activation_gap"),
        "closeout_classification": {
            "presence": clf["presence"],
            "schema_validity": clf["schema_validity"],
            "content_sufficiency": clf["content_sufficiency"],
            "evidence_consistency": clf["evidence_consistency"],
        },
        "per_layer_results": clf["per_layer_results"],
        "failure_signals": clf["failure_signals"],
        "failure_disposition": failure_disposition_data,
        "gate_policy": {
            "fail_mode": policy.fail_mode,
            "artifact_state": artifact_result.state,
            "blocked": gate.blocked,
            "source": policy.source,
        },
        "closeout_file": str(closeout_path),
        "decision": result["decision"],
        "snapshot_created": result["snapshot"] is not None,
        "promoted": result["promotion"] is not None,
        "memory_closeout": result["memory_closeout"],
        "verdict_artifact": result["verdict_artifact"],
        "trace_artifact": result["trace_artifact"],
        "warnings": gate_warnings,
        "errors": gate_errors,
    }


# ── Output formatting ─────────────────────────────────────────────────────────

def format_human_result(result: dict[str, Any]) -> str:
    lines = [
        "[session_end_hook]",
        f"ok={result['ok']}",
        f"session_id={result['session_id']}",
        f"closeout_status={result['closeout_status']}",
        f"memory_tier={result['memory_tier']}",
        f"repo_readiness_level={result['repo_readiness_level']}"
        + (f" (limited by: {result['repo_readiness_limiting_factor']})" if result['repo_readiness_limiting_factor'] else "")
        + f"  activation={result.get('repo_closeout_activation_state', 'unknown')}"
        + (f"/{result['repo_activation_recency']}" if result.get('repo_activation_recency') else "")
        + (f" (gap: {result['repo_activation_gap']})" if result.get('repo_activation_gap') else ""),
    ]

    clf = result.get("closeout_classification") or {}
    if clf:
        lines.append(f"  presence={clf.get('presence')}")
        lines.append(f"  schema_validity={clf.get('schema_validity')}")
        lines.append(f"  content_sufficiency={clf.get('content_sufficiency')}")
        lines.append(f"  evidence_consistency={clf.get('evidence_consistency')}")

    per = result.get("per_layer_results") or {}
    if per.get("missing_fields"):
        lines.append(f"  missing_fields={per['missing_fields']}")
    for issue in per.get("content_issues", []):
        lines.append(f"  content_issue: {issue['field']} ({issue['type']})")
    for inc in per.get("inconsistencies", []):
        lines.append(f"  inconsistency: {inc}")
    for ref in per.get("cross_reference_results", []):
        if ref["type"] == "file_existence":
            status = "found" if ref["found"] else "NOT FOUND"
            lines.append(f"  file_check: {ref['claimed']} → {status}")
        elif ref["type"] == "tool_artifact_signal":
            status = "artifact found" if ref["artifact_found"] else "no artifact"
            lines.append(f"  tool_check: {ref['tool']} → {status}")

    for sig in result.get("failure_signals", []):
        lines.append(
            f"  signal[{sig['type']}] affects={sig['affects']}: {sig.get('guidance', '')}"
        )

    disp = result.get("failure_disposition") or {}
    if disp:
        lines.append(
            f"failure_disposition: verdict_blocked={disp.get('verdict_blocked')} "
            f"unknown={disp.get('unknown_count', 0)} total={disp.get('total', 0)}"
        )
        by_action = disp.get("by_action") or {}
        if by_action.get("production_fix_required", 0) > 0:
            lines.append(
                f"  [GATE] production_fix_required={by_action['production_fix_required']}: "
                f"agent must not continue without fixing production code"
            )
        if disp.get("taxonomy_expansion_signal"):
            lines.append(
                f"  [SIGNAL] taxonomy_expansion_signal: unknown_count={disp.get('unknown_count', 0)}"
            )

    gp = result.get("gate_policy") or {}
    if gp:
        lines.append(
            f"gate_policy: fail_mode={gp.get('fail_mode')} "
            f"artifact_state={gp.get('artifact_state')} "
            f"blocked={gp.get('blocked')}"
        )

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

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Session end hook. Four-layer closeout classification with cross-reference, "
            "failure_signals, and two-tier memory promotion. Always runs."
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
