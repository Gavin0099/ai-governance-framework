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


def build_trust_signal_snapshot(
    *,
    project_root: Path,
    plan_path: Path,
    release_version: str,
    contract_file: Path | None = None,
    strict_runtime: bool = False,
) -> dict[str, Any]:
    overview = assess_trust_signal_overview(
        project_root=project_root,
        plan_path=plan_path,
        release_version=release_version,
        contract_file=contract_file,
        strict_runtime=strict_runtime,
    )
    return {
        "ok": overview["ok"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": overview["project_root"],
        "plan_path": overview["plan_path"],
        "release_version": overview["release_version"],
        "contract_path": overview.get("contract_path"),
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

    return {
        "latest_json": str(latest_json),
        "latest_txt": str(latest_txt),
        "latest_md": str(latest_md),
        "history_json": str(history_json),
        "history_txt": str(history_txt),
        "history_md": str(history_md),
        "index_md": str(index_md),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a trust-signal snapshot bundle.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan", default="PLAN.md")
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--contract")
    parser.add_argument("--strict-runtime", action="store_true")
    parser.add_argument("--format", choices=("human", "json", "markdown"), default="human")
    parser.add_argument("--output")
    parser.add_argument("--write-bundle")
    args = parser.parse_args()

    snapshot = build_trust_signal_snapshot(
        project_root=Path(args.project_root).resolve(),
        plan_path=Path(args.plan),
        release_version=args.release_version,
        contract_file=Path(args.contract).resolve() if args.contract else None,
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

    print(rendered)
    return 0 if snapshot["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
