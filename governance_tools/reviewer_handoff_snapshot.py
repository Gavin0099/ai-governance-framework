#!/usr/bin/env python3
"""
Generate a persistent reviewer-handoff snapshot bundle from reviewer_handoff_summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.reviewer_handoff_summary import (
    assess_reviewer_handoff,
    format_human_result,
    format_markdown_result,
)


def build_reviewer_handoff_snapshot(
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
    handoff = assess_reviewer_handoff(
        project_root=project_root,
        plan_path=plan_path,
        release_version=release_version,
        contract_file=contract_file,
        external_contract_repos=external_contract_repos,
        strict_runtime=strict_runtime,
        release_bundle_manifest=release_bundle_manifest,
        release_publication_manifest=release_publication_manifest,
    )
    return {
        "ok": handoff["ok"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "plan_path": str(plan_path),
        "release_version": release_version,
        "contract_path": str(contract_file.resolve()) if contract_file else None,
        "external_contract_repos": [str(path.resolve()) for path in (external_contract_repos or [])],
        "strict_runtime": strict_runtime,
        "handoff": handoff,
    }


def _history_stem(snapshot: dict[str, Any]) -> str:
    dt = datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00"))
    return dt.strftime("%Y%m%d_%H%M%S")


def resolve_bundle_dir(
    *,
    project_root: Path,
    release_version: str,
    write_bundle: str | None = None,
) -> Path | None:
    if write_bundle:
        return Path(write_bundle).resolve()
    return project_root / "artifacts" / "reviewer-handoff" / release_version


def format_index(history_dir: Path) -> str:
    json_files = sorted(history_dir.glob("*.json"))
    lines = ["[reviewer_handoff_snapshot_index]", f"history_dir={history_dir}", f"reports={len(json_files)}"]
    if json_files:
        lines.append("[reports]")
        for path in reversed(json_files):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                lines.append(f"{path.name} | unreadable")
                continue
            handoff = payload.get("handoff") or {}
            trust = handoff.get("trust_signal") or {}
            release = handoff.get("release_surface") or {}
            lines.append(
                " | ".join(
                    [
                        path.name,
                        f"ok={payload.get('ok')}",
                        f"release_version={payload.get('release_version')}",
                        f"trust={trust.get('ok')}",
                        f"release={release.get('ok')}",
                        f"generated_at={payload.get('generated_at')}",
                    ]
                )
            )
    return "\n".join(lines)


def write_snapshot_bundle(snapshot: dict[str, Any], bundle_dir: Path) -> dict[str, str]:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    history_dir = bundle_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    stem = _history_stem(snapshot)
    latest_json = bundle_dir / "latest.json"
    latest_txt = bundle_dir / "latest.txt"
    latest_md = bundle_dir / "latest.md"
    history_json = history_dir / f"{stem}.json"
    history_txt = history_dir / f"{stem}.txt"
    history_md = history_dir / f"{stem}.md"
    index_md = bundle_dir / "INDEX.md"
    manifest_json = bundle_dir / "MANIFEST.json"
    publication_manifest_json = bundle_dir / "PUBLICATION_MANIFEST.json"
    publication_index_md = bundle_dir / "PUBLICATION_INDEX.md"
    readme_md = bundle_dir / "README.md"

    handoff = snapshot["handoff"]
    trust = handoff.get("trust_signal") or {}
    release = handoff.get("release_surface") or {}
    json_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    human_text = format_human_result(handoff) + "\n"
    markdown_text = format_markdown_result(handoff) + "\n"

    latest_json.write_text(json_text, encoding="utf-8")
    latest_txt.write_text(human_text, encoding="utf-8")
    latest_md.write_text(markdown_text, encoding="utf-8")
    history_json.write_text(json_text, encoding="utf-8")
    history_txt.write_text(human_text, encoding="utf-8")
    history_md.write_text(markdown_text, encoding="utf-8")
    index_md.write_text(format_index(history_dir) + "\n", encoding="utf-8")
    manifest_json.write_text(
        json.dumps(
            {
                "generated_at": snapshot["generated_at"],
                "project_root": snapshot["project_root"],
                "plan_path": snapshot["plan_path"],
                "release_version": snapshot["release_version"],
                "contract_path": snapshot.get("contract_path"),
                "external_contract_repos": snapshot.get("external_contract_repos") or [],
                "external_contract_repo_count": len(snapshot.get("external_contract_repos") or []),
                "strict_runtime": snapshot["strict_runtime"],
                "ok": snapshot["ok"],
                "trust_ok": trust.get("ok"),
                "release_ok": release.get("ok"),
                "latest": {
                    "json": str(latest_json),
                    "text": str(latest_txt),
                    "markdown": str(latest_md),
                },
                "history": {
                    "json": str(history_json),
                    "text": str(history_txt),
                    "markdown": str(history_md),
                },
                "index": str(index_md),
                "readme": str(readme_md),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    publication_manifest_json.write_text(
        json.dumps(
            {
                "ok": snapshot["ok"],
                "generated_at": snapshot["generated_at"],
                "project_root": snapshot["project_root"],
                "publication_root": str(bundle_dir),
                "publication_scope": "bundle",
                "plan_path": snapshot["plan_path"],
                "release_version": snapshot["release_version"],
                "contract_path": snapshot.get("contract_path"),
                "external_contract_repos": snapshot.get("external_contract_repos") or [],
                "external_contract_repo_count": len(snapshot.get("external_contract_repos") or []),
                "strict_runtime": snapshot["strict_runtime"],
                "trust_ok": trust.get("ok"),
                "release_ok": release.get("ok"),
                "latest_json": str(latest_json),
                "latest_txt": str(latest_txt),
                "latest_md": str(latest_md),
                "history_json": str(history_json),
                "history_txt": str(history_txt),
                "history_md": str(history_md),
                "index_md": str(index_md),
                "manifest_json": str(manifest_json),
                "readme_md": str(readme_md),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    publication_index_md.write_text(
        "\n".join(
            [
                "# Reviewer Handoff Publication Index",
                "",
                f"- Publication scope: `bundle`",
                f"- Release version: `{snapshot['release_version']}`",
                f"- Generated at: `{snapshot['generated_at']}`",
                f"- OK: `{snapshot['ok']}`",
                "",
                "## Paths",
                "",
                f"- Latest JSON: `{latest_json}`",
                f"- Latest Text: `{latest_txt}`",
                f"- Latest Markdown: `{latest_md}`",
                f"- History JSON: `{history_json}`",
                f"- History Text: `{history_txt}`",
                f"- History Markdown: `{history_md}`",
                f"- Bundle Index: `{index_md}`",
                f"- Bundle Manifest: `{manifest_json}`",
                f"- Bundle README: `{readme_md}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    readme_md.write_text(
        "\n".join(
            [
                "# Reviewer Handoff Snapshot",
                "",
                "This directory contains generated reviewer-handoff snapshots.",
                "",
                f"- Generated at: `{snapshot['generated_at']}`",
                f"- Release version: `{snapshot['release_version']}`",
                f"- Summary: `ok={snapshot['ok']} | trust={trust.get('ok')} | release={release.get('ok')}`",
                "",
                "## Entry Points",
                "",
                "- [Latest Markdown Summary](latest.md)",
                "- [Latest Human Summary](latest.txt)",
                "- [Latest JSON Snapshot](latest.json)",
                "- [History Index](INDEX.md)",
                "- `MANIFEST.json`",
                "- `PUBLICATION_MANIFEST.json`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "latest_json": str(latest_json),
        "latest_txt": str(latest_txt),
        "latest_md": str(latest_md),
        "history_json": str(history_json),
        "history_txt": str(history_txt),
        "history_md": str(history_md),
        "index_md": str(index_md),
        "manifest_json": str(manifest_json),
        "publication_manifest_json": str(publication_manifest_json),
        "publication_index_md": str(publication_index_md),
        "readme_md": str(readme_md),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reviewer-handoff snapshot bundle.")
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
    parser.add_argument("--write-bundle")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=Path(args.plan),
        release_version=args.release_version,
        contract_file=Path(args.contract).resolve() if args.contract else None,
        external_contract_repos=[Path(item).resolve() for item in args.external_contract_repo],
        strict_runtime=args.strict_runtime,
        release_bundle_manifest=Path(args.release_bundle_manifest).resolve() if args.release_bundle_manifest else None,
        release_publication_manifest=(
            Path(args.release_publication_manifest).resolve() if args.release_publication_manifest else None
        ),
    )
    handoff = snapshot["handoff"]
    if args.format == "json":
        rendered = json.dumps(snapshot, ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        rendered = format_markdown_result(handoff)
    else:
        rendered = format_human_result(handoff)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)

    bundle_dir = resolve_bundle_dir(
        project_root=project_root,
        release_version=args.release_version,
        write_bundle=args.write_bundle,
    )
    if bundle_dir is not None:
        paths = write_snapshot_bundle(snapshot, bundle_dir)
        if args.format == "human":
            print("")
            print("[reviewer_handoff_snapshot]")
            for key, value in paths.items():
                print(f"{key}={value}")

    return 0 if snapshot["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
