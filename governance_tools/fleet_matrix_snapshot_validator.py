#!/usr/bin/env python3
"""
Validate fleet matrix snapshot metadata (P1-G).

Checks that a governance_repo_matrix_snapshot_*.json artifact carries the
reproducibility metadata required since the generator was registered as
scripts/governance_repo_matrix.ps1: explicit UTC generation time, tool
identity, tool commit, source repo set provenance, and freshness window.

CLAIM CEILING: a valid snapshot proves the artifact is attributable and
reproducible. It does not prove fleet evidence is fresh, the cadence is
solved, or the monitored repo set is correct.
"""
from __future__ import annotations

import json
from pathlib import Path

TOOL_NAME = "fleet_matrix_snapshot_validator"

REQUIRED_TOP_LEVEL_KEYS = (
    "matrix_version",
    "matrix_generated_at",
    "generation_tool",
    "generation_tool_commit",
    "source_repo_set",
    "evidence_window_days",
    "framework_repo",
    "repo_inventory",
)

REQUIRED_SOURCE_REPO_SET_KEYS = (
    "definition",
    "company_repos",
    "private_repos",
)


def validate_snapshot_metadata(snapshot: dict) -> dict:
    """Return {"ok": bool, "missing": [...], "problems": [...]}."""
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in snapshot]
    problems: list[str] = []

    source_repo_set = snapshot.get("source_repo_set")
    if isinstance(source_repo_set, dict):
        for key in REQUIRED_SOURCE_REPO_SET_KEYS:
            if key not in source_repo_set:
                problems.append(f"source_repo_set missing key: {key}")
    elif "source_repo_set" not in missing:
        problems.append("source_repo_set must be an object")

    tool_commit = snapshot.get("generation_tool_commit")
    if tool_commit is not None and not str(tool_commit).strip():
        problems.append("generation_tool_commit must be non-empty")

    window = snapshot.get("evidence_window_days")
    if window is not None and (not isinstance(window, int) or window < 1):
        problems.append("evidence_window_days must be a positive integer")

    return {
        "ok": not missing and not problems,
        "missing": missing,
        "problems": problems,
    }


def load_snapshot(path: Path) -> dict:
    # Snapshots are written by PowerShell and may carry a UTF-8 BOM.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate fleet matrix snapshot reproducibility metadata."
    )
    parser.add_argument("--snapshot", required=True, help="Snapshot JSON path")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    path = Path(args.snapshot)
    if not path.is_file():
        result = {"ok": False, "missing": [], "problems": [f"snapshot not found: {path}"]}
    else:
        try:
            result = validate_snapshot_metadata(load_snapshot(path))
        except (json.JSONDecodeError, OSError) as exc:
            result = {"ok": False, "missing": [], "problems": [f"unreadable snapshot: {exc}"]}

    if args.format == "json":
        print(json.dumps({"tool": TOOL_NAME, "snapshot": str(path), **result}))
    else:
        print(f"[{TOOL_NAME}]")
        print(f"ok={result['ok']}")
        print(f"snapshot={path}")
        for key in result["missing"]:
            print(f"missing={key}")
        for problem in result["problems"]:
            print(f"problem={problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
