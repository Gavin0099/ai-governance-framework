#!/usr/bin/env python3
"""Report-only census for an explicit composite-workspace repo allowlist.

This module intentionally does not discover workspace members, invoke F-7,
install governance, modify repositories, stage files, commit, or push.  It
inspects exactly one coordinator root and the sibling roots supplied by the
operator, then preserves each repository's independent status.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.governance_maturity_summary import (
    build_governance_maturity_summary,
)
from governance_tools.governance_update_reporting import print_console_safe


REPORT_VERSION = "0.1"
_CONFLICT_CODES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
_STATUS_MEANINGS = {
    "full_candidate": "治理面完整候選，但仍不是 full adoption 證明",
    "partial": "部分治理可用",
    "minimal": "只有最低治理面",
    "not_governed": "尚未治理",
    "unknown": "狀態不明",
}


@dataclass
class DirtyState:
    clean: bool
    staged: bool
    unstaged: bool
    untracked: bool
    conflicted: bool
    entries: list[str] = field(default_factory=list)


@dataclass
class RemoteEvidence:
    name: str
    fetch_urls: list[str] = field(default_factory=list)


@dataclass
class MemberCensus:
    role: str
    requested_path: str
    resolved_path: str
    exists: bool
    git_root: str | None = None
    git_identity_status: str = "unresolved"
    git_identity: str | None = None
    remotes: list[RemoteEvidence] = field(default_factory=list)
    head: str | None = None
    branch: str | None = None
    dirty_state: DirtyState | None = None
    governance_status: str = "not_checked"
    readiness_gaps: list[str] = field(default_factory=list)
    capability_states: dict[str, str] = field(default_factory=dict)
    membership_status: str = "discovered_candidate"
    claim_ceiling: str | None = None
    cannot_claim: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class OperatorDecisionSummary:
    checked: str
    usable_now: str
    missing: str
    next_action: str


@dataclass
class CompositeWorkspaceCensus:
    report_version: str
    report_only: bool
    authority_model: str
    coordinator_root: str
    explicit_sibling_allowlist: list[str]
    operator_decision_summary: OperatorDecisionSummary
    members: list[MemberCensus]
    cannot_claim: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class _GitResult:
    returncode: int
    stdout: str
    stderr: str


def _run_git(repo: Path, args: Sequence[str]) -> _GitResult:
    """Run one allowlisted read-only Git command."""

    command = tuple(args)
    is_read_only = command in {
        ("remote",),
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "HEAD"),
        ("status", "--porcelain=v1", "--untracked-files=normal"),
        ("symbolic-ref", "--quiet", "--short", "HEAD"),
    } or (
        len(command) == 4
        and command[:3] == ("remote", "get-url", "--all")
        and bool(command[3])
    )
    if not is_read_only:
        raise ValueError(f"non-read-only git command rejected: {list(args)}")
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _GitResult(1, "", str(exc))
    return _GitResult(
        completed.returncode,
        completed.stdout.rstrip("\r\n"),
        completed.stderr.strip(),
    )


def _inspect_dirty_state(git_root: Path) -> tuple[DirtyState | None, str | None]:
    result = _run_git(
        git_root,
        ["status", "--porcelain=v1", "--untracked-files=normal"],
    )
    if result.returncode != 0:
        return None, result.stderr or "git status failed"

    entries = [line for line in result.stdout.splitlines() if line]
    status_codes = [line[:2] if len(line) >= 2 else line for line in entries]
    staged = any(code[:1] not in {" ", "?"} for code in status_codes)
    unstaged = any(
        len(code) >= 2 and code[1] != " " and code != "??"
        for code in status_codes
    )
    untracked = any(code == "??" for code in status_codes)
    conflicted = any(code in _CONFLICT_CODES for code in status_codes)
    return (
        DirtyState(
            clean=not entries,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            conflicted=conflicted,
            entries=entries,
        ),
        None,
    )


def _inspect_remotes(git_root: Path) -> tuple[list[RemoteEvidence], str, str | None]:
    result = _run_git(git_root, ["remote"])
    if result.returncode != 0:
        return [], "unresolved", None

    remotes: list[RemoteEvidence] = []
    unique_urls: set[str] = set()
    for name in sorted(filter(None, result.stdout.splitlines()), key=str.casefold):
        urls_result = _run_git(git_root, ["remote", "get-url", "--all", name])
        urls = sorted(
            set(filter(None, urls_result.stdout.splitlines())),
            key=str.casefold,
        )
        remotes.append(RemoteEvidence(name=name, fetch_urls=urls))
        unique_urls.update(urls)

    if not unique_urls:
        return remotes, "missing", None
    if len(unique_urls) == 1:
        return remotes, "resolved", next(iter(unique_urls))
    return remotes, "ambiguous", None


def _inspect_member(role: str, requested_root: str | Path) -> MemberCensus:
    requested_path = Path(requested_root).expanduser()
    lexical_path = Path(os.path.abspath(os.fspath(requested_path)))
    resolved_path = requested_path.resolve(strict=False)
    member = MemberCensus(
        role=role,
        requested_path=str(requested_path),
        resolved_path=str(resolved_path),
        exists=os.path.lexists(lexical_path),
    )
    lexical_identity = os.path.normcase(str(lexical_path))
    resolved_identity = os.path.normcase(str(resolved_path))
    if lexical_identity != resolved_identity:
        member.errors.append(
            "candidate path crosses a symlink or junction boundary; no repository inspection performed"
        )
        return member
    member.exists = lexical_path.is_dir()
    if not member.exists:
        member.errors.append("candidate path is missing or is not a directory")
        return member

    top_result = _run_git(resolved_path, ["rev-parse", "--show-toplevel"])
    if top_result.returncode != 0 or not top_result.stdout:
        member.errors.append(top_result.stderr or "candidate path is not a Git repository")
        return member

    git_root = Path(top_result.stdout).resolve(strict=False)
    member.git_root = str(git_root)
    member.membership_status = "unratified"
    if git_root != resolved_path:
        member.warnings.append(
            "requested path resolved inside a Git repository; identity uses Git toplevel"
        )

    head_result = _run_git(git_root, ["rev-parse", "HEAD"])
    if head_result.returncode == 0 and head_result.stdout:
        member.head = head_result.stdout
    else:
        member.errors.append(head_result.stderr or "unable to resolve HEAD")

    branch_result = _run_git(git_root, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    member.branch = branch_result.stdout or None

    remotes, identity_status, identity = _inspect_remotes(git_root)
    member.remotes = remotes
    member.git_identity_status = identity_status
    member.git_identity = identity
    if identity_status != "resolved":
        member.warnings.append(
            "repository identity is not uniquely resolved from configured fetch remotes"
        )

    dirty_state, dirty_error = _inspect_dirty_state(git_root)
    member.dirty_state = dirty_state
    if dirty_error:
        member.errors.append(dirty_error)

    try:
        maturity = build_governance_maturity_summary(git_root)
    except Exception as exc:  # report the member without hiding the other repos
        member.errors.append(f"governance maturity inspection failed: {exc}")
        return member

    member.governance_status = str(maturity.user_facing_status.value)
    member.readiness_gaps = sorted(set(maturity.missing_surfaces), key=str.casefold)
    member.capability_states = {
        name: capability.state
        for name, capability in sorted(maturity.capability_states.items())
    }
    member.claim_ceiling = str(maturity.claim_ceiling.value)
    member.cannot_claim = list(maturity.cannot_claim)
    return member


def _member_label(member: MemberCensus) -> str:
    name = Path(member.git_root or member.resolved_path).name or member.role
    return f"{member.role}:{name}"


def _build_operator_summary(members: list[MemberCensus]) -> OperatorDecisionSummary:
    coordinator_count = sum(member.role == "coordinator" for member in members)
    sibling_count = sum(member.role == "sibling" for member in members)
    checked = (
        f"已檢查 {coordinator_count} 個 coordinator 與 {sibling_count} 個明確列出的 sibling；"
        "沒有從 .code-workspace 或其他目錄自動擴張範圍。"
    )

    usable_items: list[str] = []
    missing_items: list[str] = []
    for member in members:
        label = _member_label(member)
        if member.git_root is None:
            usable_items.append(f"{label}=無法檢查")
        else:
            meaning = _STATUS_MEANINGS.get(member.governance_status, "狀態需人工判讀")
            usable_items.append(f"{label}={member.governance_status}（{meaning}）")

        gaps = list(member.readiness_gaps)
        gaps.extend(member.errors)
        if gaps:
            missing_items.append(f"{label}: {', '.join(gaps)}")
        else:
            missing_items.append(f"{label}: 未發現列入本報告的缺口")

    usable_now = "；".join(usable_items) if usable_items else "沒有可判讀的 repository。"
    missing = "；".join(missing_items) if missing_items else "沒有成員可供檢查。"
    next_action = (
        "目前只完成只讀盤點；有效 repository 的 membership 仍為 unratified。"
        "若要寫入 sibling，必須另案建立 bilateral opt-in；本工具不執行 F-7、commit 或 push。"
    )
    return OperatorDecisionSummary(
        checked=checked,
        usable_now=usable_now,
        missing=missing,
        next_action=next_action,
    )


def build_composite_workspace_census(
    coordinator_root: str | Path,
    sibling_roots: Sequence[str | Path],
) -> CompositeWorkspaceCensus:
    """Inspect exactly the explicitly supplied roots and return a report."""

    coordinator = _inspect_member("coordinator", coordinator_root)
    sibling_inputs = sorted(
        (str(Path(item).expanduser()) for item in sibling_roots),
        key=str.casefold,
    )
    members = [coordinator]
    members.extend(_inspect_member("sibling", item) for item in sibling_inputs)

    seen_git_roots: dict[str, str] = {}
    for member in members:
        if member.git_root is None:
            continue
        identity_key = str(Path(member.git_root).resolve()).casefold()
        if identity_key in seen_git_roots:
            member.membership_status = "duplicate_identity"
            member.errors.append(
                f"same Git root already listed as {seen_git_roots[identity_key]}"
            )
        else:
            seen_git_roots[identity_key] = _member_label(member)

    coordinator_resolved = str(Path(coordinator_root).expanduser().resolve(strict=False))
    sibling_resolved = [
        str(Path(item).expanduser().resolve(strict=False)) for item in sibling_inputs
    ]
    return CompositeWorkspaceCensus(
        report_version=REPORT_VERSION,
        report_only=True,
        authority_model="explicit_allowlist_discovery_only",
        coordinator_root=coordinator_resolved,
        explicit_sibling_allowlist=sibling_resolved,
        operator_decision_summary=_build_operator_summary(members),
        members=members,
        cannot_claim=[
            "workspace membership is ratified",
            "sibling repositories are governed or ready for mutation",
            "workspace-wide F-7 completion",
            "workspace-wide adoption, enforcement, commit, or push authority",
            "the explicit allowlist transfers authority between repositories",
        ],
    )


def format_json(report: CompositeWorkspaceCensus) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def format_human(report: CompositeWorkspaceCensus) -> str:
    summary = report.operator_decision_summary
    lines = [
        "[operator_decision_summary]",
        f"1. 這次檢查了什麼：{summary.checked}",
        f"2. 現在哪些 repo 可用：{summary.usable_now}",
        f"3. 哪些 repo 還缺什麼：{summary.missing}",
        f"4. 下一步應做什麼：{summary.next_action}",
        "",
        "[composite_workspace_census]",
        f"report_version={report.report_version}",
        f"report_only={str(report.report_only).lower()}",
        f"authority_model={report.authority_model}",
        f"coordinator_root={report.coordinator_root}",
        f"explicit_sibling_count={len(report.explicit_sibling_allowlist)}",
    ]
    for member in report.members:
        lines.extend(
            [
                "",
                f"[member {_member_label(member)}]",
                f"requested_path={member.requested_path}",
                f"resolved_path={member.resolved_path}",
                f"git_root={member.git_root}",
                f"git_identity_status={member.git_identity_status}",
                f"git_identity={member.git_identity}",
                f"head={member.head}",
                f"branch={member.branch}",
                f"membership_status={member.membership_status}",
                f"governance_status={member.governance_status}",
                "readiness_gaps="
                + (", ".join(member.readiness_gaps) if member.readiness_gaps else "<none>"),
            ]
        )
        if member.dirty_state is not None:
            lines.extend(
                [
                    f"dirty.clean={str(member.dirty_state.clean).lower()}",
                    f"dirty.staged={str(member.dirty_state.staged).lower()}",
                    f"dirty.unstaged={str(member.dirty_state.unstaged).lower()}",
                    f"dirty.untracked={str(member.dirty_state.untracked).lower()}",
                    f"dirty.conflicted={str(member.dirty_state.conflicted).lower()}",
                ]
            )
        for warning in member.warnings:
            lines.append(f"warning={warning}")
        for error in member.errors:
            lines.append(f"error={error}")

    lines.append("")
    lines.append("[cannot_claim]")
    lines.extend(f"- {item}" for item in report.cannot_claim)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report the independent Git and governance state of one coordinator "
            "and an explicit sibling allowlist without modifying any repository."
        )
    )
    parser.add_argument("--coordinator", required=True, help="Coordinator repository root.")
    parser.add_argument(
        "--sibling",
        action="append",
        required=True,
        help=(
            "Explicit sibling repository root; repeat for each sibling. "
            "Paths that traverse symlinks or junctions are rejected."
        ),
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_composite_workspace_census(args.coordinator, args.sibling)
    rendered = format_json(report) if args.format == "json" else format_human(report)
    print_console_safe(rendered)
    coordinator = report.members[0]
    return 0 if coordinator.git_root is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
