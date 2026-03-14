#!/usr/bin/env python3
"""
Runtime post-task governance checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from governance_tools.contract_validator import validate_contract
from governance_tools.contract_resolver import resolve_contract
from governance_tools.domain_governance_metadata import domain_risk_tier
from governance_tools.domain_contract_loader import load_domain_contract
from governance_tools.domain_validator_loader import build_domain_validation_payload, run_domain_validators
from governance_tools.driver_evidence_validator import validate_driver_evidence
from governance_tools.failure_completeness_validator import validate_failure_completeness
from governance_tools.public_api_diff_checker import check_public_api_diff
from governance_tools.refactor_evidence_validator import validate_refactor_evidence
from governance_tools.rule_pack_loader import available_rule_packs, describe_rule_selection, parse_rule_list
from memory_pipeline.session_snapshot import create_session_snapshot


def _merge_runtime_checks(errors: list[str], warnings: list[str], checks: dict | None) -> None:
    if not checks:
        return

    for warning in checks.get("warnings", []):
        warnings.append(f"runtime-check: {warning}")

    for error in checks.get("errors", []):
        errors.append(f"runtime-check: {error}")


def _merge_refactor_evidence_checks(errors: list[str], warnings: list[str], checks: dict | None, rules: list[str]) -> dict | None:
    if "refactor" not in rules:
        return None

    result = validate_refactor_evidence(checks)
    for warning in result["warnings"]:
        warnings.append(f"refactor-evidence: {warning}")
    for error in result["errors"]:
        errors.append(f"refactor-evidence: {error}")
    return result


def _merge_public_api_diff_checks(
    errors: list[str],
    warnings: list[str],
    checks: dict | None,
    rules: list[str],
    api_before_files: list[Path] | None,
    api_after_files: list[Path] | None,
) -> dict | None:
    if "refactor" not in rules:
        return None

    result = None
    if checks and checks.get("public_api_diff"):
        result = checks["public_api_diff"]
    elif api_before_files and api_after_files:
        result = check_public_api_diff(api_before_files, api_after_files)
    else:
        return None

    for warning in result.get("warnings", []):
        warnings.append(f"public-api-diff: {warning}")
    for error in result.get("errors", []):
        errors.append(f"public-api-diff: {error}")
    return result


def _merge_failure_completeness_checks(errors: list[str], warnings: list[str], checks: dict | None, rules: list[str]) -> dict | None:
    if not checks:
        return None

    result = validate_failure_completeness(checks, require_cleanup=("refactor" in rules))
    for warning in result["warnings"]:
        warnings.append(f"failure-completeness: {warning}")
    for error in result["errors"]:
        errors.append(f"failure-completeness: {error}")
    return result


def _merge_driver_evidence_checks(errors: list[str], warnings: list[str], checks: dict | None, rules: list[str]) -> dict | None:
    if "kernel-driver" not in rules:
        return None

    result = validate_driver_evidence(checks)
    for warning in result["warnings"]:
        warnings.append(f"driver-evidence: {warning}")
    for error in result["errors"]:
        errors.append(f"driver-evidence: {error}")
    return result


def _merge_domain_validator_results(errors: list[str], warnings: list[str], results: list[dict]) -> None:
    for item in results:
        for warning in item.get("warnings", []):
            warnings.append(f"domain-validator:{item['name']}: {warning}")
        for violation in item.get("violations", []):
            warnings.append(f"domain-validator:{item['name']}: {violation}")
        for error in item.get("errors", []):
            errors.append(f"domain-validator:{item['name']}: {error}")


def run_post_task_check(
    response_text: str,
    risk: str,
    oversight: str,
    memory_mode: str | None = None,
    memory_root: Path | None = None,
    snapshot_task: str | None = None,
    snapshot_summary: str | None = None,
    create_snapshot: bool = False,
    checks: dict | None = None,
    api_before_files: list[Path] | None = None,
    api_after_files: list[Path] | None = None,
    contract_file: Path | None = None,
    project_root: Path | None = None,
    evidence_paths: list[Path] | None = None,
) -> dict:
    contract_resolution = resolve_contract(
        contract_file,
        project_root=project_root,
        extra_paths=evidence_paths,
    )
    resolved_contract_file = contract_resolution.path
    domain_contract = load_domain_contract(resolved_contract_file) if resolved_contract_file else None
    contract_rules_roots = [Path(path) for path in domain_contract.get("rule_roots", [])] if domain_contract else []
    available_rules = available_rule_packs(contract_rules_roots + [Path(__file__).resolve().parents[2] / "governance" / "rules"])
    validation = validate_contract(response_text, available_rules=available_rules if domain_contract else None)
    errors = list(validation.errors)
    warnings = list(validation.warnings)
    fields = validation.fields
    resolved_memory_mode = memory_mode or fields.get("MEMORY_MODE", "").strip() or "candidate"
    resolved_rules = parse_rule_list(fields.get("RULES", ""))
    snapshot_result = None
    effective_checks = dict(checks or {})

    if not validation.contract_found:
        errors.append("Missing governance contract in task output")

    if risk == "high" and oversight == "auto":
        errors.append("High-risk task completed without required oversight")

    if resolved_memory_mode == "durable" and oversight == "auto":
        errors.append("Durable memory requires oversight != auto")

    if resolved_memory_mode == "durable" and oversight == "review-required":
        warnings.append("Durable memory should typically be promoted after explicit review completion")
    warnings.extend(contract_resolution.warnings)
    if contract_resolution.error:
        errors.append(contract_resolution.error)

    if domain_contract:
        rules_roots = contract_rules_roots + [Path(__file__).resolve().parents[2] / "governance" / "rules"]
        resolved_rule_packs = describe_rule_selection(resolved_rules, rules_roots)
        if not resolved_rule_packs["valid"]:
            errors.append(f"Unknown rule packs: {resolved_rule_packs['missing']}")
    else:
        resolved_rule_packs = None

    _merge_runtime_checks(errors, warnings, effective_checks)
    public_api_diff = _merge_public_api_diff_checks(
        errors,
        warnings,
        effective_checks,
        resolved_rules,
        api_before_files,
        api_after_files,
    )
    if public_api_diff:
        effective_checks["public_api_diff"] = public_api_diff
        effective_checks["interface_stability_verified"] = public_api_diff.get("ok", False)
    failure_completeness = _merge_failure_completeness_checks(errors, warnings, effective_checks, resolved_rules)
    refactor_evidence = _merge_refactor_evidence_checks(errors, warnings, effective_checks, resolved_rules)
    driver_evidence = _merge_driver_evidence_checks(errors, warnings, effective_checks, resolved_rules)
    domain_validator_results = []
    if domain_contract:
        domain_payload = build_domain_validation_payload(
            response_text=response_text,
            checks=effective_checks,
            fields=fields,
            resolved_rules=resolved_rules,
            domain_contract=domain_contract,
        )
        domain_validator_results = run_domain_validators(
            contract_file=resolved_contract_file,
            payload=domain_payload,
            active_rule_ids=resolved_rules,
        )
        _merge_domain_validator_results(errors, warnings, domain_validator_results)

    if create_snapshot and validation.contract_found and validation.compliant and not errors:
        if memory_root is None:
            errors.append("Snapshot creation requested without memory_root")
        else:
            snapshot_result = create_session_snapshot(
                memory_root=memory_root,
                task=snapshot_task or fields.get("PLAN", "unspecified-task"),
                summary=snapshot_summary or "Post-task candidate memory snapshot",
                source_text=response_text,
                risk=risk,
                oversight=oversight,
            )

    return {
        "ok": validation.contract_found and validation.compliant and len(errors) == 0,
        "contract_found": validation.contract_found,
        "compliant": validation.compliant,
        "fields": fields,
        "memory_mode": resolved_memory_mode,
        "rules": resolved_rules,
        "snapshot": snapshot_result,
        "checks": effective_checks if effective_checks else None,
        "resolved_contract_file": str(resolved_contract_file) if resolved_contract_file else None,
        "contract_resolution": {
            "source": contract_resolution.source,
            "path": str(resolved_contract_file) if resolved_contract_file else None,
            "warnings": contract_resolution.warnings,
            "error": contract_resolution.error,
        },
        "public_api_diff": public_api_diff,
        "failure_completeness": failure_completeness,
        "refactor_evidence": refactor_evidence,
        "driver_evidence": driver_evidence,
        "domain_validator_results": domain_validator_results,
        "domain_contract": domain_contract,
        "rule_packs": resolved_rule_packs,
        "errors": errors,
        "warnings": warnings,
    }


def format_human_result(result: dict) -> str:
    domain_contract = result.get("domain_contract") or {}
    domain_raw = domain_contract.get("raw") or {}
    contract_label = domain_raw.get("domain") or domain_contract.get("name")
    contract_risk = domain_risk_tier(domain_raw.get("domain") or domain_contract.get("name"))
    lines = [
        "[post_task_check]",
        f"ok={result['ok']}",
        f"contract_found={result['contract_found']}",
        f"compliant={result['compliant']}",
        f"memory_mode={result['memory_mode']}",
    ]
    summary_parts = [
        f"ok={result['ok']}",
        f"compliant={result['compliant']}",
        f"memory_mode={result['memory_mode']}",
    ]
    if contract_label:
        summary_parts.append(
            f"contract={contract_label}/{contract_risk}" if contract_risk != "unknown" else f"contract={contract_label}"
        )
    lines.append(f"summary={' | '.join(summary_parts)}")
    if result["snapshot"]:
        lines.append(f"snapshot={result['snapshot']['snapshot_path']}")
    if result["public_api_diff"]:
        lines.append(f"public_api_removed={len(result['public_api_diff']['removed'])}")
        lines.append(f"public_api_added={len(result['public_api_diff']['added'])}")
        lines.append(f"public_api_ok={result['public_api_diff']['ok']}")
    if result["failure_completeness"] is not None:
        lines.append(f"failure_completeness_ok={result['failure_completeness']['ok']}")
    if result["refactor_evidence"] is not None:
        lines.append(f"refactor_evidence_ok={result['refactor_evidence']['ok']}")
    if result["driver_evidence"] is not None:
        lines.append(f"driver_evidence_ok={result['driver_evidence']['ok']}")
    if result.get("domain_validator_results"):
        lines.append(f"domain_validator_count={len(result['domain_validator_results'])}")
    contract_resolution = result.get("contract_resolution") or {}
    if contract_resolution.get("source"):
        lines.append(f"contract_source={contract_resolution['source']}")
    if contract_resolution.get("path"):
        lines.append(f"contract_path={contract_resolution['path']}")
    if contract_label:
        lines.append(f"contract={contract_label}")
        lines.append(f"contract_risk_tier={contract_risk}")
    if result.get("domain_contract"):
        lines.append(f"domain_contract={result['domain_contract']['name']}")
    for warning in result["warnings"]:
        lines.append(f"warning: {warning}")
    for error in result["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run post-task governance checks.")
    parser.add_argument("--file", "-f", help="Response file; defaults to stdin")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--oversight", default="auto")
    parser.add_argument("--memory-mode")
    parser.add_argument("--memory-root")
    parser.add_argument("--snapshot-task")
    parser.add_argument("--snapshot-summary")
    parser.add_argument("--create-snapshot", action="store_true")
    parser.add_argument("--checks-file")
    parser.add_argument("--api-before", action="append", default=[])
    parser.add_argument("--api-after", action="append", default=[])
    parser.add_argument("--project-root")
    parser.add_argument("--contract")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    if args.file:
        response_text = Path(args.file).read_text(encoding="utf-8")
    else:
        response_text = sys.stdin.read()

    checks = json.loads(Path(args.checks_file).read_text(encoding="utf-8")) if args.checks_file else None

    result = run_post_task_check(
        response_text,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
        memory_root=Path(args.memory_root) if args.memory_root else None,
        snapshot_task=args.snapshot_task,
        snapshot_summary=args.snapshot_summary,
        create_snapshot=args.create_snapshot,
        checks=checks,
        api_before_files=[Path(path) for path in args.api_before],
        api_after_files=[Path(path) for path in args.api_after],
        project_root=Path(args.project_root).resolve() if args.project_root else None,
        evidence_paths=[Path(path).resolve() for path in [args.file, args.checks_file] if path],
        contract_file=Path(args.contract).resolve() if args.contract else None,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
