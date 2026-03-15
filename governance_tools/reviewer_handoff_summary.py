#!/usr/bin/env python3
"""
Aggregate trust-signal and release-surface summaries into one reviewer handoff view.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.human_summary import build_summary_line
from governance_tools.release_surface_overview import assess_release_surface
from governance_tools.trust_signal_overview import assess_trust_signal_overview


def _commands(release_version: str, contract_file: Path | None = None) -> list[dict[str, str]]:
    contract_arg = f" --contract {contract_file}" if contract_file else ""
    return [
        {
            "name": "trust_signal_overview",
            "command": "python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md "
            f"--release-version {release_version}{contract_arg} --format human",
        },
        {
            "name": "release_surface_overview",
            "command": f"python governance_tools/release_surface_overview.py --version {release_version} --format human",
        },
        {
            "name": "phase_gates",
            "command": "bash scripts/verify_phase_gates.sh",
        },
    ]


def assess_reviewer_handoff(
    *,
    project_root: Path,
    plan_path: Path,
    release_version: str,
    contract_file: Path | None = None,
    external_contract_repos: list[Path] | None = None,
    strict_runtime: bool = False,
    release_bundle_manifest: Path | None = None,
    release_publication_manifest: Path | None = None,
) -> dict[str, Any]:
    trust = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=plan_path,
        release_version=release_version,
        contract_file=contract_file,
        external_contract_repos=external_contract_repos,
        strict_runtime=strict_runtime,
    )
    release = assess_release_surface(
        project_root,
        version=release_version,
        bundle_manifest=release_bundle_manifest,
        publication_manifest=release_publication_manifest,
    )

    return {
        "ok": trust["ok"] and release["ok"],
        "project_root": str(project_root),
        "plan_path": str(plan_path),
        "release_version": release_version,
        "contract_path": str(contract_file.resolve()) if contract_file else None,
        "external_contract_repos": [str(path.resolve()) for path in (external_contract_repos or [])],
        "strict_runtime": strict_runtime,
        "trust_signal": trust,
        "release_surface": release,
        "commands": _commands(release_version, contract_file),
    }


def format_human_result(result: dict[str, Any]) -> str:
    trust = result["trust_signal"]
    release = result["release_surface"]
    summary_line = build_summary_line(
        f"ok={result['ok']}",
        f"trust={trust['ok']}",
        f"release={release['ok']}",
        f"release_version={result['release_version']}",
        f"contract={result.get('contract_path') or 'none'}",
    )
    lines = [
        summary_line,
        "[reviewer_handoff_summary]",
        f"project_root={result['project_root']}",
        f"plan_path={result['plan_path']}",
        f"release_version={result['release_version']}",
        f"contract_path={result.get('contract_path')}",
        f"strict_runtime={result['strict_runtime']}",
        f"external_contract_repo_count={len(result['external_contract_repos'])}",
        "[trust_signal]",
        f"ok={trust['ok']}",
        f"quickstart_ok={trust['quickstart']['ok']}",
        f"examples_ok={trust['examples']['ok']}",
        f"release_ok={trust['release']['ok']}",
        f"auditor_ok={trust['auditor']['ok']}",
        "[release_surface]",
        f"ok={release['ok']}",
        f"readiness_ok={release['readiness']['ok']}",
        f"package_ok={release['package']['ok']}",
        f"bundle_available={release['bundle_manifest']['available']}",
        f"publication_available={release['publication_manifest']['available']}",
        f"bundle_source={release['bundle_manifest']['source']}",
        f"publication_source={release['publication_manifest']['source']}",
    ]
    if release["bundle_manifest"].get("manifest_file"):
        lines.append(f"bundle_manifest_file={release['bundle_manifest']['manifest_file']}")
    if release["publication_manifest"].get("manifest_file"):
        lines.append(f"publication_manifest_file={release['publication_manifest']['manifest_file']}")
    lines.append("[commands]")
    for item in result["commands"]:
        lines.append(f"{item['name']}={item['command']}")
    return "\n".join(lines)


def format_markdown_result(result: dict[str, Any]) -> str:
    trust = result["trust_signal"]
    release = result["release_surface"]
    summary_line = build_summary_line(
        f"ok={result['ok']}",
        f"trust={trust['ok']}",
        f"release={release['ok']}",
        f"release_version={result['release_version']}",
        f"contract={result.get('contract_path') or 'none'}",
    )
    lines = [
        "# Reviewer Handoff Summary",
        "",
        f"- Summary: `{summary_line}`",
        f"- Project root: `{result['project_root']}`",
        f"- Plan path: `{result['plan_path']}`",
        f"- Release version: `{result['release_version']}`",
        f"- Contract path: `{result.get('contract_path')}`",
        "",
        "## Handoff Status",
        "",
        "| Surface | OK | Detail |",
        "| --- | --- | --- |",
        f"| Trust signal | `{trust['ok']}` | quickstart=`{trust['quickstart']['ok']}` examples=`{trust['examples']['ok']}` auditor=`{trust['auditor']['ok']}` |",
        f"| Release surface | `{release['ok']}` | readiness=`{release['readiness']['ok']}` package=`{release['package']['ok']}` bundle=`{'missing' if not release['bundle_manifest']['available'] else release['bundle_manifest']['ok']}` publication=`{'missing' if not release['publication_manifest']['available'] else release['publication_manifest']['ok']}` |",
        "",
        "## Suggested Commands",
        "",
    ]
    for item in result["commands"]:
        lines.append(f"- `{item['command']}`")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the current reviewer handoff surfaces.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan", default="PLAN.md")
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--contract")
    parser.add_argument("--external-contract-repo", action="append", default=[])
    parser.add_argument("--strict-runtime", action="store_true")
    parser.add_argument("--release-bundle-manifest")
    parser.add_argument("--release-publication-manifest")
    parser.add_argument("--format", choices=("human", "json", "markdown"), default="human")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = assess_reviewer_handoff(
        project_root=Path(args.project_root).resolve(),
        plan_path=Path(args.plan),
        release_version=args.release_version,
        contract_file=Path(args.contract).resolve() if args.contract else None,
        external_contract_repos=[Path(item).resolve() for item in args.external_contract_repo],
        strict_runtime=args.strict_runtime,
        release_bundle_manifest=Path(args.release_bundle_manifest).resolve() if args.release_bundle_manifest else None,
        release_publication_manifest=Path(args.release_publication_manifest).resolve() if args.release_publication_manifest else None,
    )
    if args.format == "json":
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        rendered = format_markdown_result(result)
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
