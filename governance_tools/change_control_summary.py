#!/usr/bin/env python3
"""
Build a reviewable change-control summary from session-start and session-end artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_session_start_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("event_type") == "session_start" and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def _normalize_session_end_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("event_type") == "session_end" and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def build_change_control_summary(
    *,
    session_start: dict[str, Any] | None = None,
    session_end: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session_start = _normalize_session_start_payload(session_start or {})
    session_end = _normalize_session_end_payload(session_end or {})

    proposal_summary = session_start.get("proposal_summary") or {}
    runtime_contract = session_start.get("runtime_contract") or {}
    contract_resolution = session_start.get("contract_resolution") or {}
    domain_contract = session_start.get("domain_contract") or {}
    domain_raw = domain_contract.get("raw") or {}
    end_summary = session_end

    return {
        "task": session_start.get("task_text") or end_summary.get("task") or runtime_contract.get("task"),
        "requested_rules": proposal_summary.get("requested_rules", []) or [],
        "active_rules": runtime_contract.get("rules", []) or end_summary.get("rules", []) or [],
        "suggested_rules_preview": session_start.get("suggested_rules_preview", []) or [],
        "suggested_skills": session_start.get("suggested_skills", []) or [],
        "suggested_agent": session_start.get("suggested_agent"),
        "contract_resolution": {
            "source": contract_resolution.get("source"),
            "path": contract_resolution.get("path") or session_start.get("resolved_contract_file"),
            "name": domain_contract.get("name"),
            "domain": domain_raw.get("domain"),
            "plugin_version": domain_raw.get("plugin_version"),
        },
        "proposal": {
            "recommended_risk": proposal_summary.get("recommended_risk"),
            "recommended_oversight": proposal_summary.get("recommended_oversight"),
            "expected_validators": proposal_summary.get("expected_validators", []) or [],
            "required_evidence": proposal_summary.get("required_evidence", []) or [],
            "concerns": proposal_summary.get("concerns", []) or [],
        },
        "runtime": {
            "decision": end_summary.get("decision"),
            "risk": end_summary.get("risk") or runtime_contract.get("risk"),
            "oversight": end_summary.get("oversight") or runtime_contract.get("oversight"),
            "public_api_diff_present": bool(end_summary.get("public_api_diff_present")),
            "public_api_added_count": end_summary.get("public_api_added_count", 0),
            "public_api_removed_count": end_summary.get("public_api_removed_count", 0),
            "warning_count": end_summary.get("warning_count", 0),
            "error_count": end_summary.get("error_count", 0),
            "promoted": bool(end_summary.get("promoted")),
        },
    }


def format_human_result(result: dict[str, Any]) -> str:
    proposal = result.get("proposal") or {}
    runtime = result.get("runtime") or {}
    contract_resolution = result.get("contract_resolution") or {}
    lines = ["[change_control_summary]"]
    summary_parts = []
    if result.get("task"):
        summary_parts.append(f"task={result['task']}")
    if proposal.get("recommended_risk"):
        summary_parts.append(f"proposal_risk={proposal.get('recommended_risk')}")
    if runtime.get("decision"):
        summary_parts.append(f"runtime_decision={runtime.get('decision')}")
    if runtime.get("promoted") is not None:
        summary_parts.append(f"promoted={runtime.get('promoted')}")
    contract_label = contract_resolution.get("domain") or contract_resolution.get("name")
    if contract_label:
        summary_parts.append(f"contract={contract_label}")
    if summary_parts:
        lines.append(f"summary={' | '.join(summary_parts)}")

    if result.get("task"):
        lines.append(f"task={result['task']}")
    if result.get("requested_rules"):
        lines.append(f"requested_rules={','.join(result['requested_rules'])}")
    if result.get("active_rules"):
        lines.append(f"active_rules={','.join(result['active_rules'])}")
    if result.get("suggested_rules_preview"):
        lines.append(f"suggested_rules_preview={','.join(result['suggested_rules_preview'])}")
    if result.get("suggested_skills"):
        lines.append(f"suggested_skills={','.join(result['suggested_skills'])}")
    if result.get("suggested_agent"):
        lines.append(f"suggested_agent={result['suggested_agent']}")
    if any(contract_resolution.get(key) for key in ("source", "path", "name", "domain", "plugin_version")):
        lines.append("[contract_resolution]")
        lines.append(f"contract_source={contract_resolution.get('source')}")
        lines.append(f"contract_path={contract_resolution.get('path')}")
        lines.append(f"contract_name={contract_resolution.get('name')}")
        lines.append(f"contract_domain={contract_resolution.get('domain')}")
        lines.append(f"plugin_version={contract_resolution.get('plugin_version')}")

    lines.append("[proposal]")
    lines.append(f"recommended_risk={proposal.get('recommended_risk')}")
    lines.append(f"recommended_oversight={proposal.get('recommended_oversight')}")
    if proposal.get("expected_validators"):
        lines.append(f"expected_validators={','.join(proposal['expected_validators'])}")
    if proposal.get("required_evidence"):
        lines.append(f"required_evidence={','.join(proposal['required_evidence'])}")
    if proposal.get("concerns"):
        lines.append(f"concerns={','.join(proposal['concerns'])}")

    lines.append("[runtime]")
    lines.append(f"decision={runtime.get('decision')}")
    lines.append(f"risk={runtime.get('risk')}")
    lines.append(f"oversight={runtime.get('oversight')}")
    lines.append(f"public_api_diff_present={runtime.get('public_api_diff_present')}")
    lines.append(f"public_api_added_count={runtime.get('public_api_added_count')}")
    lines.append(f"public_api_removed_count={runtime.get('public_api_removed_count')}")
    lines.append(f"warning_count={runtime.get('warning_count')}")
    lines.append(f"error_count={runtime.get('error_count')}")
    lines.append(f"promoted={runtime.get('promoted')}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a change-control summary.")
    parser.add_argument("--session-start-file")
    parser.add_argument("--session-end-file")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = build_change_control_summary(
        session_start=_load_json(Path(args.session_start_file)) if args.session_start_file else None,
        session_end=_load_json(Path(args.session_end_file)) if args.session_end_file else None,
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else format_human_result(result)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
