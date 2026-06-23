#!/usr/bin/env python3
"""Hermes no_agent multi-repo status checklist.

This script is intentionally narrow:
- explicit repo list only, from a reviewed JSON config;
- fixed read-only git command allowlist;
- stdout-only report generation for Hermes cron output capture;
- no fetch, pull, push, add, commit, checkout, reset, clean, stash, network, or
  repair behavior.

The resulting artifact is an observation candidate, not authority. Live git
state remains authoritative at review time.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "multi_repo_status.config.json"
CONFIG_ENV = "AI_GOV_MULTI_REPO_STATUS_CONFIG"
COMMAND_TIMEOUT_SECONDS = 10


def _load_config() -> dict[str, Any]:
    config_path = Path(os.environ.get(CONFIG_ENV, DEFAULT_CONFIG)).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("mode") != "hermes-cron-no-agent":
        raise SystemExit("config mode must be hermes-cron-no-agent")
    repos = data.get("repos")
    if not isinstance(repos, list) or not repos:
        raise SystemExit("config repos must be a non-empty list")
    return data


def _run_git(repo_path: Path, args: list[str]) -> tuple[int, str]:
    """Run one approved git command in a repo and return exit code + output."""
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo_path),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=COMMAND_TIMEOUT_SECONDS,
        check=False,
    )
    return completed.returncode, completed.stdout.strip()


def _run_git_timeout_safe(repo_path: Path, args: list[str]) -> tuple[str, str]:
    try:
        code, output = _run_git(repo_path, args)
    except subprocess.TimeoutExpired:
        return "timeout", ""
    if code != 0:
        return f"exit_{code}", output
    return "ok", output


def _repo_report(repo: dict[str, Any]) -> list[str]:
    name = str(repo.get("name", "unnamed"))
    raw_path = str(repo.get("path", ""))
    upstream = str(repo.get("upstream", ""))
    repo_path = Path(raw_path)

    lines = [f"## {name}", "", f"path={raw_path}"]

    if not repo_path.exists():
        lines.extend(["exists=false", ""])
        return lines
    if not (repo_path / ".git").exists():
        lines.extend(["exists=true", "git_status=not_a_git_repo", ""])
        return lines

    branch_status, branch = _run_git_timeout_safe(repo_path, ["branch", "--show-current"])
    head_status, head = _run_git_timeout_safe(repo_path, ["rev-parse", "--short", "HEAD"])
    upstream_status, detected_upstream = _run_git_timeout_safe(
        repo_path,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
    )
    status_status, status_output = _run_git_timeout_safe(
        repo_path,
        ["status", "--short", "--branch"],
    )

    ahead_behind = "unavailable"
    ahead_behind_status = "not_run"
    compare_upstream = upstream or detected_upstream
    if compare_upstream:
        ahead_behind_status, ahead_behind_output = _run_git_timeout_safe(
            repo_path,
            ["rev-list", "--left-right", "--count", f"HEAD...{compare_upstream}"],
        )
        if ahead_behind_status == "ok":
            ahead_behind = ahead_behind_output.replace("\t", "/")

    lines.extend(
        [
            "exists=true",
            f"branch={branch if branch_status == 'ok' else branch_status}",
            f"head={head if head_status == 'ok' else head_status}",
            f"configured_upstream={upstream}",
            f"detected_upstream={detected_upstream if upstream_status == 'ok' else upstream_status}",
            f"ahead_behind={ahead_behind}",
            f"ahead_behind_status={ahead_behind_status}",
            "status:",
            status_output if status_status == "ok" else status_status,
            "",
        ]
    )
    return lines


def main() -> int:
    config = _load_config()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        "# Multi-Repo Status Checklist",
        "",
        f"generated_at={generated_at}",
        "mode=hermes_cron_no_agent",
        "script=multi_repo_status.py",
        f"checklist_name={config.get('checklist_name', 'multi-repo-status')}",
        f"claim_ceiling={config.get('claim_ceiling', 'observation_only_not_authority')}",
        "",
    ]
    for repo in config["repos"]:
        lines.extend(_repo_report(repo))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
