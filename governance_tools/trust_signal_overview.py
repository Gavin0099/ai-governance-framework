#!/usr/bin/env python3
"""
Aggregate high-level adoption and trust signals into one reviewer-friendly overview.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.contract_context import contract_label
from governance_tools.domain_governance_metadata import domain_risk_tier
from governance_tools.example_readiness import assess_examples
from governance_tools.governance_auditor import audit_governance
from governance_tools.human_summary import build_summary_line
from governance_tools.quickstart_smoke import run_quickstart_smoke
from governance_tools.release_readiness import assess_release_readiness


def assess_trust_signal_overview(
    *,
    project_root: Path,
    plan_path: Path,
    release_version: str,
    contract_file: Path | None = None,
    strict_runtime: bool = False,
) -> dict[str, Any]:
    quickstart = run_quickstart_smoke(
        project_root=project_root,
        plan_path=plan_path,
        contract_file=contract_file,
        task_text="Trust-signal overview quickstart",
    )
    examples = assess_examples(project_root, strict_runtime=strict_runtime)
    release = assess_release_readiness(project_root, version=release_version)
    auditor = audit_governance(project_root, release_version=release_version)

    return {
        "ok": quickstart["ok"] and examples["ok"] and release["ok"] and auditor["ok"],
        "project_root": str(project_root),
        "plan_path": str(plan_path),
        "release_version": release_version,
        "contract_path": str(contract_file.resolve()) if contract_file else None,
        "strict_runtime": strict_runtime,
        "quickstart": quickstart,
        "examples": examples,
        "release": release,
        "auditor": auditor,
    }


def format_human_result(result: dict[str, Any]) -> str:
    quickstart = result["quickstart"]
    examples = result["examples"]
    release = result["release"]
    auditor = result["auditor"]

    contract_context = quickstart.get("contract_context") or {}
    label = contract_label(contract_context)
    risk_tier = contract_context.get("risk_tier") or domain_risk_tier(contract_context.get("domain"))
    contract_part = None
    if label and risk_tier and risk_tier != "unknown":
        contract_part = f"contract={label}/{risk_tier}"
    elif label:
        contract_part = f"contract={label}"

    runnable_examples = sum(
        1 for item in examples["examples"] if item["kind"] in {"runnable-demo", "domain-contract"}
    )
    lines = [
        "[trust_signal_overview]",
        build_summary_line(
            f"ok={result['ok']}",
            f"quickstart={quickstart['ok']}",
            f"examples={examples['ok']}",
            f"release={release['ok']}",
            f"auditor={auditor['ok']}",
            contract_part,
        ),
        f"project_root={result['project_root']}",
        f"plan_path={result['plan_path']}",
        f"release_version={result['release_version']}",
        f"contract_path={result.get('contract_path')}",
        f"strict_runtime={result['strict_runtime']}",
        f"quickstart_ok={quickstart['ok']}",
        f"examples_ok={examples['ok']}",
        f"release_ok={release['ok']}",
        f"auditor_ok={auditor['ok']}",
        f"example_count={len(examples['examples'])}",
        f"runnable_examples={runnable_examples}",
        f"release_checks={len(release['checks'])}",
        f"auditor_checks={len(auditor['checks'])}",
    ]

    if label:
        lines.append(f"contract={label}")
    if risk_tier:
        lines.append(f"contract_risk_tier={risk_tier}")

    if release.get("warnings"):
        lines.append(f"release_warnings={len(release['warnings'])}")
    if auditor.get("warnings"):
        lines.append(f"auditor_warnings={len(auditor['warnings'])}")

    top_issues = (auditor.get("external_onboarding") or {}).get("top_issues") or []
    for item in top_issues:
        lines.append(
            "external_top_issue="
            + " | ".join(
                [
                    item["repo_root"],
                    f"reasons={','.join(item['reasons'])}",
                    f"suggested_command={item.get('suggested_command')}",
                ]
            )
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate high-level onboarding and trust signals.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan", default="PLAN.md")
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--contract")
    parser.add_argument("--strict-runtime", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = assess_trust_signal_overview(
        project_root=Path(args.project_root).resolve(),
        plan_path=Path(args.plan),
        release_version=args.release_version,
        contract_file=Path(args.contract).resolve() if args.contract else None,
        strict_runtime=args.strict_runtime,
    )
    if args.format == "json":
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        rendered = format_human_result(result)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
