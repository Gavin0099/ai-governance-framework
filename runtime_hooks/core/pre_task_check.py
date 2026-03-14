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
from governance_tools.architecture_impact_estimator import estimate_architecture_impact
from governance_tools.contract_resolver import resolve_contract
from governance_tools.domain_governance_metadata import domain_risk_tier
from governance_tools.domain_contract_loader import load_domain_contract
from governance_tools.rule_pack_loader import describe_rule_selection, load_rule_content, parse_rule_list
from governance_tools.rule_pack_suggester import suggest_rule_packs


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
OVERSIGHT_ORDER = {"auto": 0, "review-required": 1, "human-approval": 2}


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


def _infer_scope(requested_rules: list[str], suggestions: dict) -> str:
    if "refactor" in requested_rules:
        return "refactor"
    for item in suggestions.get("scope_packs", []):
        if item.get("name") == "refactor":
            return "refactor"
    return "feature"


def _append_impact_warnings(warnings: list[str], impact_preview: dict | None, risk: str, oversight: str) -> None:
    if not impact_preview:
        return

    preview_risk = impact_preview.get("recommended_risk")
    preview_oversight = impact_preview.get("recommended_oversight")

    if preview_risk and RISK_ORDER.get(preview_risk, 0) > RISK_ORDER.get(risk, 0):
        warnings.append(
            f"Architecture impact preview recommends risk '{preview_risk}' but contract risk is '{risk}'"
        )

    if preview_oversight and OVERSIGHT_ORDER.get(preview_oversight, 0) > OVERSIGHT_ORDER.get(oversight, 0):
        warnings.append(
            "Architecture impact preview recommends "
            f"oversight '{preview_oversight}' but contract oversight is '{oversight}'"
        )


def run_pre_task_check(
    project_root: Path,
    rules: str,
    risk: str,
    oversight: str,
    memory_mode: str,
    task_text: str = "",
    impact_before_files: list[Path] | None = None,
    impact_after_files: list[Path] | None = None,
    contract_file: Path | None = None,
) -> dict:
    plan_path = project_root / "PLAN.md"
    freshness = check_freshness(plan_path)
    requested_rules = parse_rule_list(rules)
    contract_resolution = resolve_contract(contract_file, project_root=project_root)
    resolved_contract_file = contract_resolution.path
    domain_contract = load_domain_contract(resolved_contract_file) if resolved_contract_file else None
    rules_roots = [Path(path) for path in (domain_contract or {}).get("rule_roots", [])] + [Path(__file__).resolve().parents[2] / "governance" / "rules"]
    rule_packs = describe_rule_selection(requested_rules, rules_roots)
    active_rules = load_rule_content(requested_rules, rules_roots)
    rule_pack_suggestions = suggest_rule_packs(project_root, task_text=task_text)
    impact_before_files = impact_before_files or []
    impact_after_files = impact_after_files or []
    impact_preview = None

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

    warnings.extend(contract_resolution.warnings)
    if contract_resolution.error:
        errors.append(contract_resolution.error)

    _append_suggestion_warnings(warnings, requested_rules, rule_pack_suggestions)
    if impact_before_files or impact_after_files:
        impact_preview = estimate_architecture_impact(
            impact_before_files,
            impact_after_files,
            scope=_infer_scope(requested_rules, rule_pack_suggestions),
            active_rules=requested_rules,
        )
        _append_impact_warnings(warnings, impact_preview, risk, oversight)

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
        "suggested_skills": rule_pack_suggestions.get("suggested_skills", []),
        "suggested_agent": rule_pack_suggestions.get("suggested_agent"),
        "rule_pack_suggestions": rule_pack_suggestions,
        "architecture_impact_preview": impact_preview,
        "rule_packs": rule_packs,
        "active_rules": active_rules,
        "contract_resolution": {
            "source": contract_resolution.source,
            "path": str(resolved_contract_file) if resolved_contract_file else None,
            "warnings": contract_resolution.warnings,
            "error": contract_resolution.error,
        },
        "domain_contract": domain_contract,
        "resolved_contract_file": str(resolved_contract_file) if resolved_contract_file else None,
        "errors": errors,
        "warnings": warnings,
    }


def format_human_result(result: dict) -> str:
    domain_contract = result.get("domain_contract") or {}
    domain_raw = domain_contract.get("raw") or {}
    contract_label = domain_raw.get("domain") or domain_contract.get("name")
    contract_risk = domain_risk_tier(domain_raw.get("domain") or domain_contract.get("name"))
    lines = [
        "[pre_task_check]",
        f"ok={result['ok']}",
        f"freshness={result['freshness']['status']}",
        f"rules={', '.join(result['runtime_contract']['rules'])}",
    ]
    summary_parts = [
        f"ok={result['ok']}",
        f"freshness={result['freshness']['status']}",
        f"rules={','.join(result['runtime_contract']['rules'])}",
    ]
    if contract_label:
        summary_parts.append(
            f"contract={contract_label}/{contract_risk}" if contract_risk != "unknown" else f"contract={contract_label}"
        )
    lines.append(f"summary={' | '.join(summary_parts)}")
    preview = result.get("suggested_rules_preview") or []
    if preview:
        lines.append(f"suggested_rules_preview={','.join(preview)}")
    suggested_skills = result.get("suggested_skills") or []
    if suggested_skills:
        lines.append(f"suggested_skills={','.join(suggested_skills)}")
    suggested_agent = result.get("suggested_agent")
    if suggested_agent:
        lines.append(f"suggested_agent={suggested_agent}")
    contract_resolution = result.get("contract_resolution") or {}
    if contract_resolution.get("source"):
        lines.append(f"contract_source={contract_resolution['source']}")
    if contract_resolution.get("path"):
        lines.append(f"contract_path={contract_resolution['path']}")
    if contract_label:
        lines.append(f"contract={contract_label}")
        lines.append(f"contract_risk_tier={contract_risk}")
    impact_preview = result.get("architecture_impact_preview") or {}
    if impact_preview:
        lines.append(f"impact_risk={impact_preview.get('recommended_risk')}")
        lines.append(f"impact_oversight={impact_preview.get('recommended_oversight')}")
        concerns = impact_preview.get("concerns") or []
        if concerns:
            lines.append(f"impact_concerns={','.join(concerns)}")
        validators = impact_preview.get("expected_validators") or []
        if validators:
            lines.append(f"impact_validators={','.join(validators)}")
        evidence = impact_preview.get("required_evidence") or []
        if evidence:
            lines.append(f"impact_evidence={','.join(evidence)}")
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
    parser.add_argument("--impact-before", action="append", default=[])
    parser.add_argument("--impact-after", action="append", default=[])
    parser.add_argument("--contract")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    result = run_pre_task_check(
        Path(args.project_root).resolve(),
        rules=args.rules,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
        task_text=args.task_text,
        impact_before_files=[Path(path) for path in args.impact_before],
        impact_after_files=[Path(path) for path in args.impact_after],
        contract_file=Path(args.contract).resolve() if args.contract else None,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
