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
    )

    proposal = build_change_proposal(
        project_root=project_root,
        task_text=task_text,
        rules=rules,
        impact_before_files=impact_before_files,
        impact_after_files=impact_after_files,
    )

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
        "state": state,
        "pre_task_check": pre_task,
    }


def format_human_result(result: dict) -> str:
    lines = [
        f"ok={result['ok']}",
        f"rules={','.join(result['runtime_contract'].get('rules', []))}",
    ]
    if result.get("suggested_rules_preview"):
        lines.append(f"suggested_rules_preview={','.join(result['suggested_rules_preview'])}")
    if result.get("suggested_skills"):
        lines.append(f"suggested_skills={','.join(result['suggested_skills'])}")
    if result.get("suggested_agent"):
        lines.append(f"suggested_agent={result['suggested_agent']}")

    guidance = result.get("proposal_guidance") or {}
    if guidance:
        lines.append(f"recommended_risk={guidance.get('recommended_risk')}")
        lines.append(f"recommended_oversight={guidance.get('recommended_oversight')}")
        validators = guidance.get("expected_validators") or []
        if validators:
            lines.append(f"expected_validators={','.join(validators)}")
        evidence = guidance.get("required_evidence") or []
        if evidence:
            lines.append(f"required_evidence={','.join(evidence)}")

    proposal = result.get("change_proposal") or {}
    requested_rules = proposal.get("requested_rules") or []
    if requested_rules:
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
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else format_human_result(result)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
