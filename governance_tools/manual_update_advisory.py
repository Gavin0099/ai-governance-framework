#!/usr/bin/env python3
"""
Advisory-only detection for likely manual AI Governance update drift.

This checker is intended for local hooks and review preflights. It never
blocks, repairs, fetches, stages, or proves misuse. Signal 1 only reports when
local update-related paths are touched and the existing maturity summary says
framework.lock.json does not match the checked-out framework HEAD.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from governance_tools.governance_maturity_summary import build_governance_maturity_summary


REPORT_VERSION = "0.1"


@dataclass
class ManualUpdateAdvisory:
    report_version: str
    report_only: bool
    advisory_active: bool
    signal: str
    repo_root: str
    touched_update_paths: list[str] = field(default_factory=list)
    lock_consistency: str | None = None
    reasons: list[str] = field(default_factory=list)
    cannot_claim: list[str] = field(default_factory=list)
    recommended_action: str = (
        "If this is a manual update, report manual_update and do not claim "
        "completed/latest/full adoption. To complete a governed update, run "
        "the updater/F-7 path and relay the human_readable_adoption_summary table."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git_stdout(repo_root: Path, args: list[str]) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _changed_paths(repo_root: Path, *, include_worktree: bool) -> list[str]:
    paths: set[str] = set()
    staged = _git_stdout(repo_root, ["diff", "--cached", "--name-only"])
    if staged:
        paths.update(line.strip().replace("\\", "/") for line in staged.splitlines() if line.strip())
    if include_worktree:
        worktree = _git_stdout(repo_root, ["diff", "--name-only"])
        if worktree:
            paths.update(line.strip().replace("\\", "/") for line in worktree.splitlines() if line.strip())
    return sorted(paths)


def _gitmodule_framework_paths(repo_root: Path) -> list[str]:
    gitmodules = repo_root / ".gitmodules"
    if not gitmodules.is_file():
        return []

    paths: list[str] = []
    current_path: str | None = None
    current_url: str | None = None
    for raw_line in gitmodules.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("[submodule "):
            if _is_framework_submodule(current_path, current_url):
                paths.append(str(current_path).replace("\\", "/"))
            current_path = None
            current_url = None
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key == "path":
            current_path = value
        elif key == "url":
            current_url = value
    if _is_framework_submodule(current_path, current_url):
        paths.append(str(current_path).replace("\\", "/"))
    return sorted(set(paths))


def _is_framework_submodule(path: str | None, url: str | None) -> bool:
    text = f"{path or ''} {url or ''}".lower()
    return "ai-governance-framework" in text


def _candidate_framework_paths(repo_root: Path) -> list[str]:
    candidates = {
        "governance/framework.lock.json",
        "ai-governance-framework",
        ".ai-governance-framework",
        "additional/ai-governance-framework",
    }
    candidates.update(_gitmodule_framework_paths(repo_root))
    return sorted(candidates)


def _is_same_or_under(path: str, candidate: str) -> bool:
    return path == candidate or path.startswith(candidate.rstrip("/") + "/")


def _touched_update_paths(repo_root: Path, *, include_worktree: bool) -> list[str]:
    changed = _changed_paths(repo_root, include_worktree=include_worktree)
    candidates = _candidate_framework_paths(repo_root)
    touched = [
        path
        for path in changed
        if any(_is_same_or_under(path, candidate) for candidate in candidates)
    ]
    return sorted(set(touched))


def assess_manual_update_advisory(
    repo_root: Path,
    *,
    framework_root: Path | None = None,
    include_worktree: bool = False,
) -> ManualUpdateAdvisory:
    repo = repo_root.resolve()
    touched = _touched_update_paths(repo, include_worktree=include_worktree)
    if not touched:
        return ManualUpdateAdvisory(
            report_version=REPORT_VERSION,
            report_only=True,
            advisory_active=False,
            signal="lock_vs_checkout_mismatch",
            repo_root=str(repo),
            reasons=["no staged governance framework checkout or framework lock paths were touched"],
            cannot_claim=[
                "no manual update risk was evaluated for unrelated changes",
                "absence of advisory is not proof of governed update compliance",
            ],
        )

    try:
        summary = build_governance_maturity_summary(repo, framework_root=framework_root)
    except Exception as exc:  # pragma: no cover - defensive for hook safety
        return ManualUpdateAdvisory(
            report_version=REPORT_VERSION,
            report_only=True,
            advisory_active=True,
            signal="lock_vs_checkout_mismatch",
            repo_root=str(repo),
            touched_update_paths=touched,
            lock_consistency="unknown",
            reasons=[f"governance_maturity_summary failed: {type(exc).__name__}: {exc}"],
            cannot_claim=[
                "framework lock matches checked-out framework commit",
                "governed updater/F-7 path was used",
                "full governance adoption",
            ],
        )

    lock_value = str(summary.lock_consistency.value)
    active = lock_value not in {"consistent", "not_applicable"}
    reasons = list(summary.lock_consistency.reasons)
    if active:
        reasons.insert(0, "update-related paths changed while lock_consistency is not consistent")
    else:
        reasons.insert(0, "update-related paths changed but lock_consistency is consistent or not_applicable")

    cannot_claim = [
        "governed updater/F-7 path was used",
        "full governance adoption",
        "hook/CI enforcement",
    ]
    if active:
        cannot_claim.insert(0, "framework lock matches checked-out framework commit")

    return ManualUpdateAdvisory(
        report_version=REPORT_VERSION,
        report_only=True,
        advisory_active=active,
        signal="lock_vs_checkout_mismatch",
        repo_root=str(repo),
        touched_update_paths=touched,
        lock_consistency=lock_value,
        reasons=reasons,
        cannot_claim=cannot_claim,
    )


def format_human(report: ManualUpdateAdvisory) -> str:
    if not report.advisory_active:
        return ""
    lines = [
        "[governance] manual update advisory: framework lock and checkout are not consistent",
        f"  signal: {report.signal}",
        f"  lock_consistency: {report.lock_consistency}",
        "  touched_update_paths:",
        *[f"    - {path}" for path in report.touched_update_paths],
        "  reasons:",
        *[f"    - {reason}" for reason in report.reasons],
        f"  recommended_action: {report.recommended_action}",
        "  cannot_claim:",
        *[f"    - {item}" for item in report.cannot_claim],
        "  note: advisory only; commit is not blocked by this check",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Consumer repository root.")
    parser.add_argument("--framework-root", help="Resolved AI Governance framework root.")
    parser.add_argument(
        "--include-worktree",
        action="store_true",
        help="Also inspect unstaged working-tree changes. Pre-commit defaults to staged changes only.",
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    report = assess_manual_update_advisory(
        Path(args.repo),
        framework_root=Path(args.framework_root).resolve() if args.framework_root else None,
        include_worktree=args.include_worktree,
    )

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        rendered = format_human(report)
        if rendered:
            print(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
