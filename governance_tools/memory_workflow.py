#!/usr/bin/env python3
"""
Report-only dispatcher for governed repo memory work.

MEM-DISPATCH-1 answered whether a memory diff requires canonical workflow.
MEM-DISPATCH-2 adds task classification and an optional authority-guard summary
while keeping the tool advisory/report-only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.memory_authority_guard import (
    filter_active_non_canonical_writer_violations,
    load_blocking_policy,
    run_guard,
)
from governance_tools.memory_policy_attestation import (
    policy_disable_attestation_warnings,
)


MEMORY_REQUIRED = "memory_workflow_required"
MEMORY_NOT_REQUIRED = "no_memory_workflow_required"
POSSIBLE_MEMORY_TASK = "possible_memory_task"
TASK_GOVERNED = "governed_memory_task"
TASK_POSSIBLE = "possible_memory_task"
TASK_NOT_MEMORY = "not_memory_task"
_B0_CODE = "session_like_non_session_memory_type"
_BACKGROUND_WARNING_CODES = frozenset(
    {
        "unbound_memory",
        "test_evidence_provenance_not_found",
        "test_evidence_linked_commit_mismatch",
    }
)

_MEMORY_KEYWORDS = (
    "memory",
    "remember",
    "backfill",
    "daily memory",
    "active task",
    "review log",
    "knowledge base",
)


@dataclass
class MemoryWorkflowDispatchResult:
    status: str
    repo_root: str
    repo_root_resolved: bool
    memory_files_in_diff: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    canonical_writer_required: bool = False
    memory_protocol_path: str | None = None
    canonical_writer_path: str | None = None
    authority_guard_path: str | None = None
    recommended_workflow: list[str] = field(default_factory=list)
    task_classification: str = TASK_NOT_MEMORY
    guard_ran: bool = False
    guard_summary: dict[str, int] = field(default_factory=dict)
    completion_claim_allowed: bool = True
    warnings: list[str] = field(default_factory=list)
    background_warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _run_git(repo: Path, args: Sequence[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return (
        completed.returncode,
        (completed.stdout or "").strip(),
        (completed.stderr or "").strip(),
    )


def _resolve_repo_root(start: Path) -> tuple[Path, bool]:
    start = start.resolve()
    if not (start / ".git").exists():
        return start, False
    code, stdout, _stderr = _run_git(start, ["rev-parse", "--show-toplevel"])
    if code == 0 and stdout:
        return Path(stdout).resolve(), True
    return start, False


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_changed_file(path_text: str) -> str:
    return path_text.strip().replace("\\", "/").lstrip("./")


def _git_changed_files(repo_root: Path) -> list[str]:
    changed: set[str] = set()
    commands = (
        ["diff", "--name-only"],
        ["diff", "--cached", "--name-only"],
        ["ls-files", "--others", "--exclude-standard"],
    )
    for args in commands:
        code, stdout, _stderr = _run_git(repo_root, args)
        if code != 0 or not stdout:
            continue
        for line in stdout.splitlines():
            normalized = _normalize_changed_file(line)
            if normalized:
                changed.add(normalized)
    return sorted(changed)


def _resolve_hook_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git / "hooks"
    if dot_git.is_file():
        code, stdout, _stderr = _run_git(repo_root, ["rev-parse", "--git-common-dir"])
        common_dir = stdout.strip()
        if code == 0 and common_dir:
            common_path = Path(common_dir)
            if not common_path.is_absolute():
                common_path = repo_root / common_path
            return common_path.resolve() / "hooks"
    return dot_git / "hooks"


def _framework_root_from_hook_config(repo_root: Path) -> Path | None:
    root_file = _resolve_hook_dir(repo_root) / "ai-governance-framework-root"
    if not root_file.is_file():
        return None
    try:
        raw = root_file.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return None
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    return candidate.resolve()


def _is_memory_file(path_text: str) -> bool:
    normalized = _normalize_changed_file(path_text)
    return normalized == "memory" or normalized.startswith("memory/")


def _violation_memory_path(violation: dict) -> str | None:
    filename = str(violation.get("file") or "").strip().replace("\\", "/")
    if not filename:
        return None
    if filename.startswith("memory/"):
        return filename
    return f"memory/{filename}"


def _count_current_diff_violations(
    result: dict,
    changed_files: Sequence[str] | None,
    code: str,
) -> int:
    if changed_files is None:
        return 0
    changed_memory_set = {
        _normalize_changed_file(item)
        for item in changed_files
        if _is_memory_file(item)
    }
    if not changed_memory_set:
        return 0
    return sum(
        1
        for violation in result.get("violations", [])
        if violation.get("code") == code
        and _violation_memory_path(violation) in changed_memory_set
    )


def _count_blocking_violations(result: dict, code: str) -> int:
    return sum(
        1
        for violation in result.get("violations", [])
        if violation.get("code") == code
        and violation.get("enforcement") == "block"
    )


def _count_current_diff_blocking_violations(
    result: dict,
    changed_files: Sequence[str] | None,
    code: str,
) -> int:
    if changed_files is None:
        return 0
    changed_memory_set = {
        _normalize_changed_file(item)
        for item in changed_files
        if _is_memory_file(item)
    }
    if not changed_memory_set:
        return 0
    return sum(
        1
        for violation in result.get("violations", [])
        if violation.get("code") == code
        and violation.get("enforcement") == "block"
        and _violation_memory_path(violation) in changed_memory_set
    )


def _is_background_warning(
    result: dict,
    changed_files: Sequence[str] | None,
    code: str,
) -> bool:
    if code not in _BACKGROUND_WARNING_CODES:
        return False
    return _count_current_diff_violations(result, changed_files, code) == 0


def _has_memory_keyword(task_text: str | None) -> bool:
    if not task_text:
        return False
    lowered = task_text.lower()
    return any(keyword in lowered for keyword in _MEMORY_KEYWORDS)


def _find_framework_surface(repo_root: Path) -> tuple[str | None, str | None, str | None]:
    hook_root = _framework_root_from_hook_config(repo_root)
    candidates = [
        item
        for item in (
            hook_root,
            repo_root,
            repo_root / "ai-governance-framework",
            repo_root / ".ai-governance-framework",
        )
        if item is not None
    ]
    for root in candidates:
        protocol = root / "governance" / "MEMORY_PROTOCOL.md"
        writer = root / "governance_tools" / "memory_record.py"
        guard = root / "governance_tools" / "memory_authority_guard.py"
        if writer.is_file() or guard.is_file() or protocol.is_file():
            return (
                _rel(repo_root, protocol) if protocol.is_file() else None,
                _rel(repo_root, writer) if writer.is_file() else None,
                _rel(repo_root, guard) if guard.is_file() else None,
            )
    return None, None, None


def _summarize_guard(result: dict) -> dict[str, int]:
    counts = result.get("violation_counts_by_code") or {}
    active = result.get("active_non_canonical_writer") or {}
    return {
        "non_canonical_writer": int(counts.get("non_canonical_writer") or 0),
        "active_non_canonical_writer": int(active.get("count") or 0),
        "missing_canonical_memory": int(counts.get("missing_canonical_memory") or 0),
        "unbound_memory": int(counts.get("unbound_memory") or 0),
        "test_evidence_provenance_not_found": int(
            counts.get("test_evidence_provenance_not_found") or 0
        ),
        "session_like_non_session_memory_type": int(
            counts.get("session_like_non_session_memory_type") or 0
        ),
        "non_daily_session_shaped_memory_entry": int(
            counts.get("non_daily_session_shaped_memory_entry") or 0
        ),
        "authority_override_rejected": int(
            counts.get("authority_override_rejected") or 0
        ),
        "test_evidence_artifact_metadata_missing": int(
            counts.get("test_evidence_artifact_metadata_missing") or 0
        ),
        "test_evidence_artifact_metadata_invalid": int(
            counts.get("test_evidence_artifact_metadata_invalid") or 0
        ),
        "test_evidence_exit_code_contradicts_claim": int(
            counts.get("test_evidence_exit_code_contradicts_claim") or 0
        ),
        "test_evidence_linked_commit_mismatch": int(
            counts.get("test_evidence_linked_commit_mismatch") or 0
        ),
        "test_evidence_artifact_not_durable": int(
            counts.get("test_evidence_artifact_not_durable") or 0
        ),
    }


def _run_authority_guard(
    repo_root: Path,
    changed_files: Sequence[str] | None = None,
) -> tuple[bool, dict[str, int], list[str], list[str], list[str]]:
    memory_root = repo_root / "memory"
    if not memory_root.is_dir():
        return False, {}, ["memory root not found; guard not run"], [], []

    policy = load_blocking_policy(repo_root)
    changed_memory_files = [
        item for item in (changed_files or []) if _is_memory_file(item)
    ]
    result = run_guard(
        memory_root,
        repo_root,
        skip_git=False,
        changed_files=changed_memory_files,
        blocking_codes=policy["enabled_codes"],
        override_mode=policy["override_mode"],
    )
    active = filter_active_non_canonical_writer_violations(result["violations"])
    result["active_non_canonical_writer"] = {
        "count": len(active),
        "violations": active,
        "mode": "report_only",
    }
    summary = _summarize_guard(result)
    summary["authority_override_used_current_diff"] = _count_current_diff_violations(
        result,
        changed_files,
        "authority_override_used",
    )
    summary["repo_state_b0_blocker_count"] = _count_blocking_violations(
        result,
        _B0_CODE,
    )
    summary["current_diff_b0_blocker_count"] = _count_current_diff_blocking_violations(
        result,
        changed_files,
        _B0_CODE,
    )
    warnings = []
    background_warnings = []
    for code in (
        "missing_canonical_memory",
        "unbound_memory",
        "test_evidence_provenance_not_found",
        "session_like_non_session_memory_type",
        "non_daily_session_shaped_memory_entry",
        "authority_override_used",
        "authority_override_rejected",
        "test_evidence_artifact_metadata_missing",
        "test_evidence_artifact_metadata_invalid",
        "test_evidence_exit_code_contradicts_claim",
        "test_evidence_linked_commit_mismatch",
        "test_evidence_artifact_not_durable",
    ):
        if not (
            summary.get(code, 0) > 0
            or (
                code == "authority_override_used"
                and summary.get("authority_override_used_current_diff", 0) > 0
            )
        ):
            continue
        if _is_background_warning(result, changed_files, code):
            background_warnings.append(code)
        else:
            warnings.append(code)
    blockers = []
    if summary.get("active_non_canonical_writer", 0) > 0:
        blockers.append("active_non_canonical_writer")
    if policy["error"]:
        # A broken policy file must fail the gate, not degrade to a warning:
        # otherwise corrupting the policy is a silent kill switch.
        warnings.append(policy["error"])
        blockers.append("blocking_policy_error")
    for code in result.get("blocking_violation_codes", []):
        blockers.append(f"memory_authority_blocking:{code}")
    return True, summary, warnings, background_warnings, blockers


def assess_memory_workflow(
    repo: Path,
    *,
    changed_files: Sequence[str] | None = None,
    task_text: str | None = None,
    run_guard_check: bool = False,
    strict_completion_check: bool = False,
) -> MemoryWorkflowDispatchResult:
    repo_root, resolved = _resolve_repo_root(repo)
    changed = (
        sorted({_normalize_changed_file(item) for item in changed_files if item.strip()})
        if changed_files is not None
        else _git_changed_files(repo_root)
    )
    memory_files = [item for item in changed if _is_memory_file(item)]
    protocol_path, writer_path, guard_path = _find_framework_surface(repo_root)

    warnings: list[str] = []
    background_warnings: list[str] = []
    blockers: list[str] = []
    guard_ran = False
    guard_summary: dict[str, int] = {}
    if memory_files and writer_path is None:
        warnings.append("canonical writer not found")
    if memory_files and guard_path is None:
        warnings.append("memory authority guard not found")
    warnings.extend(policy_disable_attestation_warnings(repo_root, changed))
    if run_guard_check:
        (
            guard_ran,
            guard_summary,
            guard_warnings,
            guard_background_warnings,
            guard_blockers,
        ) = _run_authority_guard(
            repo_root,
            changed_files=changed,
        )
        warnings.extend(guard_warnings)
        background_warnings.extend(guard_background_warnings)
        blockers.extend(guard_blockers)
    if memory_files and strict_completion_check and not guard_ran:
        blockers.append("memory_authority_guard_not_run")

    if memory_files:
        return MemoryWorkflowDispatchResult(
            status=MEMORY_REQUIRED,
            repo_root=str(repo_root),
            repo_root_resolved=resolved,
            memory_files_in_diff=memory_files,
            changed_files=changed,
            canonical_writer_required=True,
            memory_protocol_path=protocol_path,
            canonical_writer_path=writer_path,
            authority_guard_path=guard_path,
            recommended_workflow=[
                "Stop editing memory/ files directly.",
                "Use canonical writer for session-derived memory.",
                "Run memory authority guard after memory changes.",
                "Do not claim memory DONE until guard result is reported.",
            ],
            task_classification=TASK_GOVERNED,
            guard_ran=guard_ran,
            guard_summary=guard_summary,
            completion_claim_allowed=guard_ran and not blockers,
            warnings=warnings,
            background_warnings=background_warnings,
            blockers=blockers,
        )

    if _has_memory_keyword(task_text):
        return MemoryWorkflowDispatchResult(
            status=POSSIBLE_MEMORY_TASK,
            repo_root=str(repo_root),
            repo_root_resolved=resolved,
            memory_files_in_diff=[],
            changed_files=changed,
            canonical_writer_required=False,
            memory_protocol_path=protocol_path,
            canonical_writer_path=writer_path,
            authority_guard_path=guard_path,
            recommended_workflow=[
                "If you intend to write repo memory, run the canonical memory workflow before editing memory/.",
            ],
            task_classification=TASK_POSSIBLE,
            guard_ran=guard_ran,
            guard_summary=guard_summary,
            completion_claim_allowed=not blockers,
            warnings=warnings,
            background_warnings=background_warnings,
            blockers=blockers,
        )

    return MemoryWorkflowDispatchResult(
        status=MEMORY_NOT_REQUIRED,
        repo_root=str(repo_root),
        repo_root_resolved=resolved,
        memory_files_in_diff=[],
        changed_files=changed,
        canonical_writer_required=False,
        memory_protocol_path=protocol_path,
        canonical_writer_path=writer_path,
        authority_guard_path=guard_path,
        recommended_workflow=[],
        task_classification=TASK_NOT_MEMORY,
        guard_ran=guard_ran,
        guard_summary=guard_summary,
        completion_claim_allowed=not blockers,
        warnings=warnings,
        background_warnings=background_warnings,
        blockers=blockers,
    )


def format_human(result: MemoryWorkflowDispatchResult) -> str:
    lines = [
        "[memory_workflow]",
        f"status={result.status}",
        f"repo_root={result.repo_root}",
        f"repo_root_resolved={result.repo_root_resolved}",
        f"canonical_writer_required={result.canonical_writer_required}",
        f"task_classification={result.task_classification}",
        f"guard_ran={result.guard_ran}",
        f"completion_claim_allowed={result.completion_claim_allowed}",
        f"memory_protocol_path={result.memory_protocol_path or 'NOT FOUND'}",
        f"canonical_writer_path={result.canonical_writer_path or 'NOT FOUND'}",
        f"authority_guard_path={result.authority_guard_path or 'NOT FOUND'}",
    ]
    if result.memory_files_in_diff:
        lines.append("[memory_files_in_diff]")
        lines.extend(result.memory_files_in_diff)
    if result.guard_summary:
        lines.append("[guard_summary]")
        for key in sorted(result.guard_summary):
            lines.append(f"{key}={result.guard_summary[key]}")
    if result.recommended_workflow:
        lines.append("[recommended_workflow]")
        lines.extend(result.recommended_workflow)
    if result.warnings:
        lines.append("[warnings]")
        lines.extend(result.warnings)
    if result.background_warnings:
        lines.append("[background_warnings]")
        lines.extend(result.background_warnings)
    if result.blockers:
        lines.append("[blockers]")
        lines.extend(result.blockers)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether repo memory work requires canonical workflow dispatch.")
    parser.add_argument("--repo", default=".", type=Path)
    parser.add_argument("--check", action="store_true", help="Run the report-only dispatcher.")
    parser.add_argument("--changed-file", action="append", default=None, help="Override git diff detection; may be repeated.")
    parser.add_argument("--task-text", default=None, help="Optional task text for possible-memory-task advisory detection.")
    parser.add_argument("--run-guard", action="store_true", help="Run memory_authority_guard and summarize warning/blocker signals.")
    parser.add_argument("--fail-on-blocker", action="store_true", help="Exit 2 when selective memory workflow blocker candidates are present.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    result = assess_memory_workflow(
        args.repo,
        changed_files=args.changed_file,
        task_text=args.task_text,
        run_guard_check=args.run_guard,
        strict_completion_check=args.fail_on_blocker,
    )
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(format_human(result))
    return 2 if args.fail_on_blocker and result.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
