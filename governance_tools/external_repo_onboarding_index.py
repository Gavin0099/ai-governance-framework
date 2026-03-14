#!/usr/bin/env python3
"""
Build a cross-repo index over external onboarding report artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_latest_report(repo_root: Path) -> dict | None:
    latest_path = repo_root / "memory" / "governance_onboarding" / "latest.json"
    if not latest_path.is_file():
        return None
    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    payload["_latest_path"] = str(latest_path)
    payload["_repo_root"] = str(repo_root.resolve())
    return payload


def _entry_priority(entry: dict) -> tuple[int, int, str]:
    ok_rank = 0 if entry.get("ok") is False else 1
    smoke_ok = (entry.get("smoke") or {}).get("ok")
    smoke_rank = 0 if smoke_ok is False else 1
    repo_root = entry.get("_repo_root", "")
    return (ok_rank, smoke_rank, repo_root)


def build_external_repo_onboarding_index(repo_roots: list[Path]) -> dict:
    entries = []
    missing = []

    for repo_root in repo_roots:
        repo_root = repo_root.resolve()
        payload = _load_latest_report(repo_root)
        if payload is None:
            missing.append(str(repo_root))
            continue
        readiness = payload.get("readiness") or {}
        smoke = payload.get("smoke") or {}
        entries.append(
            {
                "repo_root": str(repo_root),
                "latest_path": payload.get("_latest_path"),
                "ok": payload.get("ok"),
                "generated_at": payload.get("generated_at"),
                "contract_path": payload.get("contract_path"),
                "readiness_ready": readiness.get("ready"),
                "smoke_ok": smoke.get("ok"),
                "rules": smoke.get("rules") or [],
                "readiness_errors": len(readiness.get("errors") or []),
                "smoke_errors": len(smoke.get("errors") or []),
            }
        )

    ordered_entries = sorted(entries, key=_entry_priority)
    return {
        "ok": len(missing) == 0 and all(entry.get("ok") for entry in ordered_entries),
        "repo_count": len(repo_roots),
        "indexed_count": len(ordered_entries),
        "missing_reports": missing,
        "entries": ordered_entries,
    }


def format_human(result: dict) -> str:
    lines = [
        "[external_repo_onboarding_index]",
        f"ok={result['ok']}",
        f"repo_count={result['repo_count']}",
        f"indexed_count={result['indexed_count']}",
    ]

    missing = result.get("missing_reports") or []
    if missing:
        lines.append("[missing_reports]")
        for item in missing:
            lines.append(item)

    entries = result.get("entries") or []
    if entries:
        lines.append("[repos]")
        for entry in entries:
            lines.append(
                " | ".join(
                    [
                        entry["repo_root"],
                        f"ok={entry['ok']}",
                        f"readiness={entry['readiness_ready']}",
                        f"smoke={entry['smoke_ok']}",
                        f"rules={','.join(entry['rules'])}",
                        f"generated_at={entry['generated_at']}",
                    ]
                )
            )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a framework-level index for external onboarding reports.")
    parser.add_argument("--repo", action="append", default=[], help="External repo root to include. Can be repeated.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_roots = [Path(item) for item in args.repo]
    result = build_external_repo_onboarding_index(repo_roots)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else format_human(result)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
