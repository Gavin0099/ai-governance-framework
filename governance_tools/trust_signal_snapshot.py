#!/usr/bin/env python3
"""
Generate a persistent trust-signal snapshot bundle from trust_signal_overview.
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

from governance_tools.trust_signal_overview import (
    assess_trust_signal_overview,
    format_human_result,
    format_markdown_result,
)


def _external_contract_policy_ok(snapshot: dict[str, Any]) -> bool | None:
    overview = snapshot.get("overview") or {}
    policy = overview.get("external_contract_policy") or {}
    return policy.get("ok")


def _external_contract_policy_entries(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    overview = snapshot.get("overview") or {}
    policy = overview.get("external_contract_policy") or {}
    summarized: list[dict[str, Any]] = []
    for entry in policy.get("entries") or []:
        payload: dict[str, Any] = {
            "repo_root": entry.get("repo_root"),
            "ok": entry.get("ok"),
        }
        if not entry.get("ok"):
            payload["error"] = entry.get("error")
            summarized.append(payload)
            continue
        payload.update(
            {
                "domain": entry.get("domain"),
                "risk_tier": entry.get("risk_tier"),
                "enforcement_profile": entry.get("enforcement_profile"),
                "validator_ready_count": entry.get("validator_ready_count"),
                "validator_count": entry.get("validator_count"),
                "hard_stop_rules": list(entry.get("hard_stop_rules") or []),
            }
        )
        summarized.append(payload)
    return summarized


def _external_contract_profile_counts(snapshot: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in _external_contract_policy_entries(snapshot):
        profile = "error"
        if entry.get("ok"):
            profile = str(entry.get("enforcement_profile") or "unknown")
        counts[profile] = counts.get(profile, 0) + 1
    return counts


def _external_contract_profile_summary(snapshot: dict[str, Any]) -> str:
    counts = _external_contract_profile_counts(snapshot)
    if not counts:
        return "none"
    return ",".join(f"{key}={counts[key]}" for key in sorted(counts))


def build_trust_signal_snapshot(
    *,
    project_root: Path,
    plan_path: Path,
    release_version: str,
    contract_file: Path | None = None,
    external_contract_repos: list[Path] | None = None,
    strict_runtime: bool = False,
) -> dict[str, Any]:
    overview = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=plan_path,
        release_version=release_version,
        contract_file=contract_file,
        external_contract_repos=external_contract_repos,
        strict_runtime=strict_runtime,
    )
    return {
        "ok": overview["ok"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": overview["project_root"],
        "plan_path": overview["plan_path"],
        "release_version": overview["release_version"],
        "contract_path": overview.get("contract_path"),
        "external_contract_repos": overview.get("external_contract_repos") or [],
        "strict_runtime": overview["strict_runtime"],
        "overview": overview,
    }


def _history_stem(snapshot: dict[str, Any]) -> str:
    dt = datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00"))
    return dt.strftime("%Y%m%d_%H%M%S")


def format_index(history_dir: Path) -> str:
    json_files = sorted(history_dir.glob("*.json"))
    lines = ["[trust_signal_snapshot_index]", f"history_dir={history_dir}", f"reports={len(json_files)}"]
    if json_files:
        lines.append("[reports]")
        for path in reversed(json_files):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                lines.append(f"{path.name} | unreadable")
                continue
            lines.append(
                " | ".join(
                    [
                        path.name,
                        f"ok={payload.get('ok')}",
                        f"release_version={payload.get('release_version')}",
                        f"contract_path={payload.get('contract_path')}",
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

    overview = snapshot["overview"]
    json_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    human_text = format_human_result(overview) + "\n"
    markdown_text = format_markdown_result(overview) + "\n"

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
                "release_version": snapshot["release_version"],
                "contract_path": snapshot.get("contract_path"),
                "external_contract_repos": snapshot.get("external_contract_repos") or [],
                "external_contract_policy_ok": _external_contract_policy_ok(snapshot),
                "external_contract_repo_count": len(snapshot.get("external_contract_repos") or []),
                "external_contract_profile_counts": _external_contract_profile_counts(snapshot),
                "external_contract_policies": _external_contract_policy_entries(snapshot),
                "strict_runtime": snapshot["strict_runtime"],
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
            },
            ensure_ascii=False,
            indent=2,
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
    }


def format_published_status_page(snapshot: dict[str, Any]) -> str:
    lines = [
        "# Published Trust Signal Snapshot",
        "",
        "> This page is generated. Rebuild it with `governance_tools/trust_signal_snapshot.py`.",
        "",
        f"- Generated at: `{snapshot['generated_at']}`",
        f"- Release version: `{snapshot['release_version']}`",
        f"- Project root: `{snapshot['project_root']}`",
        f"- Contract path: `{snapshot.get('contract_path')}`",
        f"- External contract repos: `{len(snapshot.get('external_contract_repos') or [])}`",
        f"- External contract profiles: `{_external_contract_profile_summary(snapshot)}`",
        f"- Strict runtime: `{snapshot['strict_runtime']}`",
        "",
        format_markdown_result(snapshot["overview"]),
    ]
    return "\n".join(lines)


def format_published_index(history_dir: Path) -> str:
    json_files = sorted(history_dir.glob("*.json"))
    lines = ["# Published Trust Signal Index", "", f"- History dir: `{history_dir}`", f"- Reports: `{len(json_files)}`"]
    if json_files:
        lines.extend(["", "| Snapshot | OK | Release | Contract | Generated |", "| --- | --- | --- | --- | --- |"])
        for path in reversed(json_files):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                lines.append(f"| `{path.name}` | unreadable | - | - | - |")
                continue
            lines.append(
                " | ".join(
                    [
                        f"| `{path.name}`",
                        f"`{payload.get('ok')}`",
                        f"`{payload.get('release_version')}`",
                        f"`{payload.get('contract_path')}`",
                        f"`{payload.get('generated_at')}` |",
                    ]
                )
            )
    return "\n".join(lines)


def write_published_status(snapshot: dict[str, Any], publish_dir: Path) -> dict[str, str]:
    publish_dir.mkdir(parents=True, exist_ok=True)
    history_dir = publish_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stem = _history_stem(snapshot)
    latest_md = publish_dir / "trust-signal-latest.md"
    latest_json = publish_dir / "trust-signal-latest.json"
    readme_md = publish_dir / "README.md"
    history_md = history_dir / f"{stem}.md"
    history_json = history_dir / f"{stem}.json"
    index_md = publish_dir / "INDEX.md"
    manifest_json = publish_dir / "manifest.json"

    markdown_text = format_published_status_page(snapshot) + "\n"
    json_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"

    latest_md.write_text(markdown_text, encoding="utf-8")
    latest_json.write_text(json_text, encoding="utf-8")
    history_md.write_text(markdown_text, encoding="utf-8")
    history_json.write_text(json_text, encoding="utf-8")
    index_md.write_text(format_published_index(history_dir) + "\n", encoding="utf-8")
    readme_md.write_text(
        "\n".join(
            [
                "# Published Status Index",
                "",
                "This directory contains generated trust-signal status pages.",
                "",
                "- [Latest Markdown Snapshot](trust-signal-latest.md)",
                "- [Latest JSON Snapshot](trust-signal-latest.json)",
                "- [History Index](INDEX.md)",
                "- `manifest.json`",
                "",
                f"Latest generated_at: `{snapshot['generated_at']}`",
                f"Release version: `{snapshot['release_version']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_json.write_text(
        json.dumps(
            {
                "generated_at": snapshot["generated_at"],
                "release_version": snapshot["release_version"],
                "contract_path": snapshot.get("contract_path"),
                "external_contract_repos": snapshot.get("external_contract_repos") or [],
                "external_contract_policy_ok": _external_contract_policy_ok(snapshot),
                "external_contract_repo_count": len(snapshot.get("external_contract_repos") or []),
                "external_contract_profile_counts": _external_contract_profile_counts(snapshot),
                "external_contract_policies": _external_contract_policy_entries(snapshot),
                "strict_runtime": snapshot["strict_runtime"],
                "published": {
                    "markdown": str(latest_md),
                    "json": str(latest_json),
                    "readme": str(readme_md),
                    "index": str(index_md),
                },
                "history": {
                    "markdown": str(history_md),
                    "json": str(history_json),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "latest_md": str(latest_md),
        "latest_json": str(latest_json),
        "readme_md": str(readme_md),
        "history_md": str(history_md),
        "history_json": str(history_json),
        "index_md": str(index_md),
        "manifest_json": str(manifest_json),
    }


def format_publication_index(
    snapshot: dict[str, Any],
    *,
    bundle_paths: dict[str, str] | None = None,
    published_paths: dict[str, str] | None = None,
) -> str:
    lines = [
        "# Trust Signal Publication Index",
        "",
        f"- Generated at: `{snapshot['generated_at']}`",
        f"- Release version: `{snapshot['release_version']}`",
        f"- Contract path: `{snapshot.get('contract_path')}`",
        f"- External contract repos: `{len(snapshot.get('external_contract_repos') or [])}`",
        f"- External contract policy OK: `{_external_contract_policy_ok(snapshot)}`",
        f"- External contract profiles: `{_external_contract_profile_summary(snapshot)}`",
        f"- Strict runtime: `{snapshot['strict_runtime']}`",
        "",
        "## Surfaces",
        "",
        f"- Bundle published: `{bundle_paths is not None}`",
        f"- Status pages published: `{published_paths is not None}`",
    ]

    if bundle_paths:
        lines.extend(
            [
                "",
                "## Bundle Paths",
                "",
                f"- Latest JSON: `{bundle_paths['latest_json']}`",
                f"- Latest Text: `{bundle_paths['latest_txt']}`",
                f"- Latest Markdown: `{bundle_paths['latest_md']}`",
                f"- History JSON: `{bundle_paths['history_json']}`",
                f"- History Text: `{bundle_paths['history_txt']}`",
                f"- History Markdown: `{bundle_paths['history_md']}`",
                f"- Index: `{bundle_paths['index_md']}`",
                f"- Manifest: `{bundle_paths['manifest_json']}`",
            ]
        )

    if published_paths:
        lines.extend(
            [
                "",
                "## Published Status Paths",
                "",
                f"- Latest Markdown: `{published_paths['latest_md']}`",
                f"- Latest JSON: `{published_paths['latest_json']}`",
                f"- Readme: `{published_paths['readme_md']}`",
                f"- History Markdown: `{published_paths['history_md']}`",
                f"- History JSON: `{published_paths['history_json']}`",
                f"- Index: `{published_paths['index_md']}`",
                f"- Manifest: `{published_paths['manifest_json']}`",
            ]
        )

    return "\n".join(lines)


def write_publication_manifest(
    snapshot: dict[str, Any],
    root_dir: Path,
    *,
    bundle_paths: dict[str, str] | None = None,
    published_paths: dict[str, str] | None = None,
) -> dict[str, str]:
    root_dir.mkdir(parents=True, exist_ok=True)
    manifest_json = root_dir / "PUBLICATION_MANIFEST.json"
    index_md = root_dir / "PUBLICATION_INDEX.md"
    manifest_payload = {
        "ok": snapshot["ok"],
        "generated_at": snapshot["generated_at"],
        "project_root": snapshot["project_root"],
        "publication_root": str(root_dir),
        "release_version": snapshot["release_version"],
        "contract_path": snapshot.get("contract_path"),
        "external_contract_repos": snapshot.get("external_contract_repos") or [],
        "external_contract_policy_ok": _external_contract_policy_ok(snapshot),
        "external_contract_repo_count": len(snapshot.get("external_contract_repos") or []),
        "external_contract_profile_counts": _external_contract_profile_counts(snapshot),
        "external_contract_policies": _external_contract_policy_entries(snapshot),
        "strict_runtime": snapshot["strict_runtime"],
        "bundle_published": bundle_paths is not None,
        "status_pages_published": published_paths is not None,
        "bundle": bundle_paths,
        "published": published_paths,
    }

    manifest_json.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    index_md.write_text(
        format_publication_index(snapshot, bundle_paths=bundle_paths, published_paths=published_paths) + "\n",
        encoding="utf-8",
    )

    return {
        "manifest_json": str(manifest_json),
        "index_md": str(index_md),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a trust-signal snapshot bundle.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan", default="PLAN.md")
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--contract")
    parser.add_argument("--external-contract-repo", action="append", default=[])
    parser.add_argument("--strict-runtime", action="store_true")
    parser.add_argument("--format", choices=("human", "json", "markdown"), default="human")
    parser.add_argument("--output")
    parser.add_argument("--write-bundle")
    parser.add_argument("--publish-status-dir")
    args = parser.parse_args()

    snapshot = build_trust_signal_snapshot(
        project_root=Path(args.project_root).resolve(),
        plan_path=Path(args.plan),
        release_version=args.release_version,
        contract_file=Path(args.contract).resolve() if args.contract else None,
        external_contract_repos=[Path(item).resolve() for item in args.external_contract_repo],
        strict_runtime=args.strict_runtime,
    )

    overview = snapshot["overview"]
    if args.format == "json":
        rendered = json.dumps(snapshot, ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        rendered = format_markdown_result(overview)
    else:
        rendered = format_human_result(overview)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    if args.write_bundle:
        paths = write_snapshot_bundle(snapshot, Path(args.write_bundle))
        if args.format == "human":
            print("")
            print("[snapshot_bundle]")
            for key, value in paths.items():
                print(f"{key}={value}")
    else:
        paths = None
    if args.publish_status_dir:
        published = write_published_status(snapshot, Path(args.publish_status_dir))
        if args.format == "human":
            print("")
            print("[published_status]")
            for key, value in published.items():
                print(f"{key}={value}")
    else:
        published = None

    publication = None
    publication_root = None
    if args.write_bundle:
        publication_root = Path(args.write_bundle)
    elif args.publish_status_dir:
        publication_root = Path(args.publish_status_dir)
    if publication_root is not None:
        publication = write_publication_manifest(
            snapshot,
            publication_root,
            bundle_paths=paths,
            published_paths=published,
        )
        if args.format == "human":
            print("")
            print("[publication_manifest]")
            for key, value in publication.items():
                print(f"{key}={value}")

    print(rendered)
    return 0 if snapshot["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

