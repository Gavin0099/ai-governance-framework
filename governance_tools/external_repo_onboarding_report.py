#!/usr/bin/env python3
"""
Generate a combined onboarding report for an external governance repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.external_repo_readiness import assess_external_repo
from governance_tools.external_repo_smoke import run_external_repo_smoke


@dataclass
class ExternalRepoOnboardingReport:
    ok: bool
    repo_root: str
    contract_path: str | None
    readiness: dict
    smoke: dict


def build_onboarding_report(
    repo_root: Path,
    *,
    contract_file: str | Path | None = None,
    risk: str = "medium",
    oversight: str = "review-required",
    memory_mode: str = "candidate",
    task_text: str = "External governance onboarding smoke test",
) -> ExternalRepoOnboardingReport:
    readiness = assess_external_repo(repo_root, contract_path=contract_file)
    smoke = run_external_repo_smoke(
        repo_root,
        contract_file=contract_file,
        risk=risk,
        oversight=oversight,
        memory_mode=memory_mode,
        task_text=task_text,
    )
    return ExternalRepoOnboardingReport(
        ok=readiness.ready and smoke.ok,
        repo_root=str(Path(repo_root).resolve()),
        contract_path=smoke.contract_path,
        readiness={
            "ready": readiness.ready,
            "checks": readiness.checks,
            "contract": readiness.contract,
            "plan": readiness.plan,
            "hooks": readiness.hooks,
            "warnings": readiness.warnings,
            "errors": readiness.errors,
        },
        smoke={
            "ok": smoke.ok,
            "rules": smoke.rules,
            "plan_path": smoke.plan_path,
            "contract_path": smoke.contract_path,
            "pre_task_ok": smoke.pre_task_ok,
            "session_start_ok": smoke.session_start_ok,
            "warnings": smoke.warnings,
            "errors": smoke.errors,
        },
    )


def format_human(report: ExternalRepoOnboardingReport) -> str:
    lines = [
        "External Repo Onboarding Report",
        "",
        f"ok                = {report.ok}",
        f"repo_root         = {report.repo_root}",
        f"contract_path     = {report.contract_path or '<missing>'}",
        f"readiness_ready   = {report.readiness.get('ready')}",
        f"smoke_ok          = {report.smoke.get('ok')}",
        "",
        "[readiness]",
    ]
    for key, value in sorted((report.readiness.get("checks") or {}).items()):
        lines.append(f"{key:<24} = {value}")

    lines.extend(
        [
            "",
            "[smoke]",
            f"rules             = {','.join(report.smoke.get('rules') or [])}",
            f"pre_task_ok       = {report.smoke.get('pre_task_ok')}",
            f"session_start_ok  = {report.smoke.get('session_start_ok')}",
        ]
    )

    all_errors = [
        *(f"readiness: {item}" for item in (report.readiness.get("errors") or [])),
        *(f"smoke: {item}" for item in (report.smoke.get("errors") or [])),
    ]
    if all_errors:
        lines.append("")
        lines.append(f"errors: {len(all_errors)}")
        for item in all_errors:
            lines.append(f"- {item}")

    all_warnings = [
        *(f"readiness: {item}" for item in (report.readiness.get("warnings") or [])),
        *(f"smoke: {item}" for item in (report.smoke.get("warnings") or [])),
    ]
    if all_warnings:
        lines.append("")
        lines.append(f"warnings: {len(all_warnings)}")
        for item in all_warnings:
            lines.append(f"- {item}")

    return "\n".join(lines)


def format_json(report: ExternalRepoOnboardingReport) -> str:
    return json.dumps(
        {
            "ok": report.ok,
            "repo_root": report.repo_root,
            "contract_path": report.contract_path,
            "readiness": report.readiness,
            "smoke": report.smoke,
        },
        ensure_ascii=False,
        indent=2,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a combined onboarding report for an external governance repo.")
    parser.add_argument("--repo", default=".", help="Target repo root.")
    parser.add_argument("--contract", help="Optional explicit contract.yaml path.")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--oversight", default="review-required")
    parser.add_argument("--memory-mode", default="candidate")
    parser.add_argument("--task-text", default="External governance onboarding smoke test")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--output", help="Optional output file path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_onboarding_report(
        Path(args.repo),
        contract_file=args.contract,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
        task_text=args.task_text,
    )
    rendered = format_json(report) if args.format == "json" else format_human(report)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
