#!/usr/bin/env python3
"""
Build a session-start governance context from state generation plus pre-task checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from governance_tools.change_proposal_builder import build_change_proposal
from governance_tools.domain_governance_metadata import domain_risk_tier
from governance_tools.domain_validator_loader import preflight_domain_validators
from governance_tools.state_generator import generate_state
from runtime_hooks.core.pre_task_check import run_pre_task_check


def build_session_start_context(
    *,
    project_root: Path,
    plan_path: Path,
    rules: str,
    risk: str,
    oversight: str,
    memory_mode: str,
    task_text: str = "",
    impact_before_files: list[Path] | None = None,
    impact_after_files: list[Path] | None = None,
    contract_file: Path | None = None,
) -> dict:
    impact_before_files = impact_before_files or []
    impact_after_files = impact_after_files or []

    state = generate_state(
        plan_path=plan_path,
        rules=rules,
        risk=risk,
        oversight=oversight,
        memory_mode=memory_mode,
        project_root=project_root,
        task_text=task_text or None,
        impact_before_files=impact_before_files,
        impact_after_files=impact_after_files,
    )

    pre_task = run_pre_task_check(
        project_root=project_root,
        rules=rules,
        risk=risk,
        oversight=oversight,
        memory_mode=memory_mode,
        task_text=task_text,
        impact_before_files=impact_before_files,
        impact_after_files=impact_after_files,
        contract_file=contract_file,
    )

    proposal = build_change_proposal(
        project_root=project_root,
        task_text=task_text,
        rules=rules,
        impact_before_files=impact_before_files,
        impact_after_files=impact_after_files,
    )
    resolved_contract_file = Path(pre_task["resolved_contract_file"]) if pre_task.get("resolved_contract_file") else None
    domain_contract = pre_task.get("domain_contract")
    validator_preflight = preflight_domain_validators(resolved_contract_file) if resolved_contract_file else None

    return {
        "ok": state.get("error") is None and pre_task["ok"],
        "project_root": str(project_root),
        "task_text": task_text,
        "runtime_contract": pre_task["runtime_contract"],
        "suggested_rules_preview": pre_task.get("suggested_rules_preview", []),
        "suggested_skills": pre_task.get("suggested_skills", []),
        "suggested_agent": pre_task.get("suggested_agent"),
        "rule_pack_suggestions": pre_task.get("rule_pack_suggestions", {}),
        "architecture_impact_preview": pre_task.get("architecture_impact_preview"),
        "proposal_guidance": state.get("proposal_guidance"),
        "change_proposal": proposal,
        "proposal_summary": proposal.get("proposal_summary"),
        "resolved_contract_file": str(resolved_contract_file) if resolved_contract_file else None,
        "contract_resolution": pre_task.get("contract_resolution"),
        "domain_contract": domain_contract,
        "validator_preflight": validator_preflight,
        "state": state,
        "pre_task_check": pre_task,
    }


def format_human_result(result: dict) -> str:
    def _first_line(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    lines = [
        "[session_start]",
        f"ok={result['ok']}",
        f"rules={','.join(result['runtime_contract'].get('rules', []))}",
    ]
    domain_contract = result.get("domain_contract") or {}
    domain_raw = domain_contract.get("raw") or {}
    contract_label = domain_raw.get("domain") or domain_contract.get("name")
    contract_risk = domain_risk_tier(domain_raw.get("domain") or domain_contract.get("name"))
    summary_parts = [
        f"ok={result['ok']}",
        f"rules={','.join(result['runtime_contract'].get('rules', []))}",
    ]
    if contract_label:
        summary_parts.append(
            f"contract={contract_label}/{contract_risk}" if contract_risk != "unknown" else f"contract={contract_label}"
        )
    proposal_summary = result.get("proposal_summary") or {}
    if proposal_summary.get("recommended_risk"):
        summary_parts.append(f"proposal_risk={proposal_summary.get('recommended_risk')}")
    lines.append(f"summary={' | '.join(summary_parts)}")
    if result.get("suggested_rules_preview"):
        lines.append(f"suggested_rules_preview={','.join(result['suggested_rules_preview'])}")
    if result.get("suggested_skills"):
        lines.append(f"suggested_skills={','.join(result['suggested_skills'])}")
    if result.get("suggested_agent"):
        lines.append(f"suggested_agent={result['suggested_agent']}")
    contract_resolution = result.get("contract_resolution") or {}
    if contract_resolution.get("source"):
        lines.append(f"contract_source={contract_resolution['source']}")
    if contract_resolution.get("path"):
        lines.append(f"contract_path={contract_resolution['path']}")
    if contract_label:
        lines.append(f"contract={contract_label}")
        lines.append(f"contract_risk_tier={contract_risk}")
    if domain_contract:
        lines.append(f"domain_contract={domain_contract.get('name')}")
        if domain_contract.get("rule_roots"):
            lines.append(f"domain_rule_roots={len(domain_contract['rule_roots'])}")
        validators = domain_contract.get("validators") or []
        if validators:
            lines.append(f"domain_validators={','.join(item['name'] for item in validators)}")
        validator_preflight = result.get("validator_preflight") or {}
        if validator_preflight:
            lines.append(f"validator_preflight_ok={validator_preflight.get('ok')}")
            lines.append(f"validator_preflight_count={validator_preflight.get('count')}")
        documents = domain_contract.get("documents") or []
        if documents:
            lines.append(f"domain_documents={','.join(Path(item['path']).name for item in documents)}")
            for item in documents:
                preview = _first_line(item.get("content", ""))
                if preview:
                    lines.append(f"document_preview[{Path(item['path']).name}]={preview}")
        overrides = domain_contract.get("ai_behavior_override") or []
        if overrides:
            lines.append(f"domain_behavior_overrides={','.join(Path(item['path']).name for item in overrides)}")
            for item in overrides:
                preview = _first_line(item.get("content", ""))
                if preview:
                    lines.append(f"behavior_preview[{Path(item['path']).name}]={preview}")
        for item in (validator_preflight or {}).get("validators", []):
            lines.append(f"validator_preflight[{item['name']}]={item['ok']}")

    summary = proposal_summary
    guidance = result.get("proposal_guidance") or {}
    if guidance:
        lines.append("[proposal_guidance]")
        lines.append(f"recommended_risk={summary.get('recommended_risk')}")
        lines.append(f"recommended_oversight={summary.get('recommended_oversight')}")
        validators = summary.get("expected_validators") or []
        if validators:
            lines.append(f"expected_validators={','.join(validators)}")
        evidence = summary.get("required_evidence") or []
        if evidence:
            lines.append(f"required_evidence={','.join(evidence)}")
        concerns = summary.get("concerns") or []
        if concerns:
            lines.append(f"concerns={','.join(concerns)}")

    proposal = result.get("change_proposal") or {}
    requested_rules = proposal.get("requested_rules") or []
    if requested_rules:
        lines.append("[change_proposal]")
        lines.append(f"proposal_rules={','.join(requested_rules)}")

    for warning in result["pre_task_check"].get("warnings", []):
        lines.append(f"warning: {warning}")
    for error in result["pre_task_check"].get("errors", []):
        lines.append(f"error: {error}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a session-start governance context.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan", default="PLAN.md")
    parser.add_argument("--rules", default="common")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--oversight", default="auto")
    parser.add_argument("--memory-mode", default="candidate")
    parser.add_argument("--task-text", default="")
    parser.add_argument("--impact-before", action="append", default=[])
    parser.add_argument("--impact-after", action="append", default=[])
    parser.add_argument("--contract")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = build_session_start_context(
        project_root=Path(args.project_root).resolve(),
        plan_path=Path(args.plan),
        rules=args.rules,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
        task_text=args.task_text,
        impact_before_files=[Path(path) for path in args.impact_before],
        impact_after_files=[Path(path) for path in args.impact_after],
        contract_file=Path(args.contract).resolve() if args.contract else None,
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else format_human_result(result)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
