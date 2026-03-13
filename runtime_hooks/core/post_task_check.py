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
from memory_pipeline.session_snapshot import create_session_snapshot


def _merge_runtime_checks(errors: list[str], warnings: list[str], checks: dict | None) -> None:
    if not checks:
        return

    for warning in checks.get("warnings", []):
        warnings.append(f"runtime-check: {warning}")

    for error in checks.get("errors", []):
        errors.append(f"runtime-check: {error}")


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
) -> dict:
    validation = validate_contract(response_text)
    errors = list(validation.errors)
    warnings = list(validation.warnings)
    fields = validation.fields
    resolved_memory_mode = memory_mode or fields.get("MEMORY_MODE", "").strip() or "candidate"
    snapshot_result = None

    if not validation.contract_found:
        errors.append("Missing governance contract in task output")

    if risk == "high" and oversight == "auto":
        errors.append("High-risk task completed without required oversight")

    if resolved_memory_mode == "durable" and oversight == "auto":
        errors.append("Durable memory requires oversight != auto")

    if resolved_memory_mode == "durable" and oversight == "review-required":
        warnings.append("Durable memory should typically be promoted after explicit review completion")

    _merge_runtime_checks(errors, warnings, checks)

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
        "snapshot": snapshot_result,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


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
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"contract_found={result['contract_found']}")
        print(f"compliant={result['compliant']}")
        print(f"memory_mode={result['memory_mode']}")
        if result["snapshot"]:
            print(f"snapshot={result['snapshot']['snapshot_path']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
