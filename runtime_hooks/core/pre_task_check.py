#!/usr/bin/env python3
"""
Runtime pre-task governance checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from governance_tools.plan_freshness import check_freshness
from governance_tools.rule_pack_loader import describe_rule_selection, load_rule_content, parse_rule_list
from governance_tools.rule_pack_suggester import suggest_rule_packs


def _append_suggestion_warnings(warnings: list[str], requested_rules: list[str], suggestions: dict) -> None:
    active = set(requested_rules)

    for item in suggestions.get("language_packs", []):
        if item["name"] not in active and item.get("confidence") == "high":
            reason = ", ".join(item.get("reasons", [])[:2])
            warnings.append(f"Suggested language pack '{item['name']}' is not active; repo signals: {reason}")

    for item in suggestions.get("framework_packs", []):
        if item["name"] not in active and item.get("confidence") in {"high", "medium"}:
            reason = ", ".join(item.get("reasons", [])[:2])
            warnings.append(f"Suggested framework pack '{item['name']}' is not active; repo signals: {reason}")

    for item in suggestions.get("scope_packs", []):
        if item["name"] not in active:
            reason = ", ".join(item.get("reasons", [])[:2])
            warnings.append(f"Advisory scope pack '{item['name']}' is suggested by task text but not active; signals: {reason}")


def run_pre_task_check(
    project_root: Path,
    rules: str,
    risk: str,
    oversight: str,
    memory_mode: str,
    task_text: str = "",
) -> dict:
    plan_path = project_root / "PLAN.md"
    freshness = check_freshness(plan_path)
    requested_rules = parse_rule_list(rules)
    rule_packs = describe_rule_selection(requested_rules)
    active_rules = load_rule_content(requested_rules)
    rule_pack_suggestions = suggest_rule_packs(project_root, task_text=task_text)

    errors = []
    warnings = []

    if freshness.status in {"CRITICAL", "ERROR"}:
        errors.append(f"PLAN.md freshness is {freshness.status}")
    elif freshness.status == "STALE":
        warnings.append("PLAN.md is STALE")

    if not rule_packs["valid"]:
        errors.append(f"Unknown rule packs: {rule_packs['missing']}")

    if risk == "high" and oversight == "auto":
        errors.append("High-risk tasks require oversight != auto")

    _append_suggestion_warnings(warnings, requested_rules, rule_pack_suggestions)

    return {
        "ok": len(errors) == 0,
        "project_root": str(project_root),
        "plan_path": str(plan_path),
        "freshness": {
            "status": freshness.status,
            "days_since_update": freshness.days_since_update,
            "threshold_days": freshness.threshold_days,
        },
        "runtime_contract": {
            "rules": requested_rules,
            "risk": risk,
            "oversight": oversight,
            "memory_mode": memory_mode,
        },
        "suggested_rules_preview": rule_pack_suggestions.get("suggested_rules_preview", []),
        "rule_pack_suggestions": rule_pack_suggestions,
        "rule_packs": rule_packs,
        "active_rules": active_rules,
        "errors": errors,
        "warnings": warnings,
    }


def format_human_result(result: dict) -> str:
    lines = [
        f"ok={result['ok']}",
        f"freshness={result['freshness']['status']}",
        f"rules={', '.join(result['runtime_contract']['rules'])}",
    ]
    preview = result.get("suggested_rules_preview") or []
    if preview:
        lines.append(f"suggested_rules_preview={','.join(preview)}")
    for warning in result["warnings"]:
        lines.append(f"warning: {warning}")
    for error in result["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pre-task governance checks.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--rules", default="common")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--oversight", default="auto")
    parser.add_argument("--memory-mode", default="candidate")
    parser.add_argument("--task-text", default="")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    result = run_pre_task_check(
        Path(args.project_root).resolve(),
        rules=args.rules,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
        task_text=args.task_text,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
