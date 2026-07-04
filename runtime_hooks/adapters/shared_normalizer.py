#!/usr/bin/env python3
"""
Shared helpers for normalizing harness-specific payloads into the runtime event contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _first_value(payload: dict, *keys, default=None):
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return default


def _first_value_with_key(payload: dict, *keys, default=None) -> tuple[object, str | None]:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key], key
    return default, None


def _normalize_rules(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()]


# Every payload key the normalizer actually consumes. A gate-relevant key
# outside this set is silently dropped (the B2 blind spot): the downstream gate
# never sees it, so a missing alias reads as under-enforcement rather than
# fail-closed. See:
# docs/governance/self-governance-normalizer-alias-miss-mutation-contract-2026-07-04.md
_KNOWN_CONSUMED_KEYS = frozenset({
    "task", "prompt", "request", "goal", "title",
    "response_file", "output_file", "assistant_response_path",
    "transcript_path", "result_file",
    "checks_file", "checks_path", "evidence_file", "evidence_path",
    "project_root", "cwd", "workspace", "repo_root",
    "plan_path", "plan",
    "rules", "rule_packs", "active_rules",
    "risk", "risk_level",
    "oversight", "oversight_mode",
    "memory_mode", "memory",
    "impact_before_files", "impact_before",
    "impact_after_files", "impact_after",
    "create_snapshot", "snapshot", "emit_snapshot",
    "snapshot_summary", "summary",
    "contract", "contract_file",
    "session_id", "conversation_id", "run_id",
    "hook_event_name", "event", "event_name",
})

# Substrings that mark a key as carrying governance-relevant input, where a
# silent drop weakens evidence/contract/risk visibility. Intentionally scoped to
# the evidence/contract/risk/response class; broader lexical tokens are omitted
# to keep this an advisory low-false-positive signal, not a strict gate.
_GATE_RELEVANT_TOKENS = (
    "evidence", "check", "contract", "proof", "artifact",
    "attestation", "receipt", "oversight", "risk", "response", "transcript",
)


def detect_unmapped_gate_keys(payload: dict) -> list[str]:
    """Report payload keys that look gate-relevant but map to no consumed field.

    Report-only: this does not change what the gate enforces. It surfaces the
    silent-drop blind spot so a reviewer/agent can see that a governance-relevant
    key was supplied under a name the normalizer does not recognize.
    """
    if not isinstance(payload, dict):
        return []
    unmapped: list[str] = []
    for key in payload:
        key_text = str(key)
        if key_text in _KNOWN_CONSUMED_KEYS:
            continue
        lowered = key_text.lower()
        if any(token in lowered for token in _GATE_RELEVANT_TOKENS):
            unmapped.append(key_text)
    return sorted(unmapped)


def normalize_payload(payload: dict, harness: str, event_type: str) -> dict:
    task, task_key = _first_value_with_key(payload, "task", "prompt", "request", "goal", "title")
    response_file = _first_value(
        payload,
        "response_file",
        "output_file",
        "assistant_response_path",
        "transcript_path",
        "result_file",
    )
    checks_file = _first_value(
        payload,
        "checks_file",
        "checks_path",
        "evidence_file",
        "evidence_path",
    )

    normalized = {
        "event_type": event_type,
        "project_root": _first_value(payload, "project_root", "cwd", "workspace", "repo_root", default="."),
        "plan_path": _first_value(payload, "plan_path", "plan", default="PLAN.md"),
        "task": task,
        "rules": _normalize_rules(_first_value(payload, "rules", "rule_packs", "active_rules")),
        "risk": _first_value(payload, "risk", "risk_level", default="medium"),
        "oversight": _first_value(payload, "oversight", "oversight_mode", default="review-required"),
        "memory_mode": _first_value(payload, "memory_mode", "memory", default="candidate"),
        "response_file": response_file,
        "impact_before_files": _normalize_rules(_first_value(payload, "impact_before_files", "impact_before")),
        "impact_after_files": _normalize_rules(_first_value(payload, "impact_after_files", "impact_after")),
        "create_snapshot": bool(
            _first_value(payload, "create_snapshot", "snapshot", "emit_snapshot", default=(event_type == "post_task"))
        ),
        "snapshot_summary": _first_value(payload, "snapshot_summary", "summary"),
        "metadata": {
            "harness": harness,
            "session_id": _first_value(payload, "session_id", "conversation_id", "run_id"),
            "native_event_type": _first_value(payload, "hook_event_name", "event", "event_name", default=event_type),
            "task_source_key": task_key or "none",
            # Advisory-only: gate-relevant keys supplied under an unrecognized
            # name (silently dropped). Empty list = clean. Does not change gating.
            "unmapped_gate_relevant_keys": detect_unmapped_gate_keys(payload),
        },
    }
    contract = _first_value(payload, "contract", "contract_file")
    if contract not in (None, ""):
        normalized["contract"] = contract
    if checks_file not in (None, ""):
        normalized["checks_file"] = checks_file
    return normalized


def _load_payload(file_path: str | None) -> dict:
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
    return json.loads(sys.stdin.read())


def cli_main(harness: str) -> None:
    parser = argparse.ArgumentParser(description=f"Normalize {harness} payloads into the runtime event contract.")
    parser.add_argument("--event-type", choices=["session_start", "pre_task", "post_task"], required=True)
    parser.add_argument("--file", "-f", help="JSON payload file; defaults to stdin")
    args = parser.parse_args()

    payload = _load_payload(args.file)
    normalized = normalize_payload(payload, harness=harness, event_type=args.event_type)
    print(json.dumps(normalized, ensure_ascii=False, indent=2))
