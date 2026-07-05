#!/usr/bin/env python3
"""CI-only selective memory workflow blocker.

This check blocks current-diff memory writer violations and policy-backed memory
authority blockers. Historical warning-only debt remains warning-only and local
hooks remain advisory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

from governance_tools.memory_authority_guard import (
    filter_active_non_canonical_writer_violations,
    load_blocking_policy,
    run_guard,
)
from governance_tools.memory_policy_attestation import (
    policy_disable_attestation_warnings,
)


_B0_CODE = "session_like_non_session_memory_type"
_BLOCKING_POLICY_RELPATH = "governance/memory_blocking_policy.json"


@dataclass
class CiMemoryWorkflowCheckResult:
    repo_root: str
    mode: str
    changed_files: list[str]
    changed_memory_files: list[str]
    active_non_canonical_writer_count: int
    current_diff_active_non_canonical_writer_count: int
    repo_state_b0_blocker_count: int = 0
    current_diff_b0_blocker_count: int = 0
    blockers: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    clean: bool = True


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
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _normalize(path_text: str) -> str:
    return path_text.strip().replace("\\", "/").lstrip("./")


def _changed_files_from_refs(repo: Path, base_ref: str, head_ref: str) -> list[str]:
    code, stdout, stderr = _run_git(repo, ["diff", "--name-only", f"{base_ref}..{head_ref}"])
    if code != 0:
        raise RuntimeError(f"git diff failed for {base_ref}..{head_ref}: {stderr}")
    return sorted({_normalize(line) for line in stdout.splitlines() if _normalize(line)})


def _is_memory_file(path_text: str) -> bool:
    normalized = _normalize(path_text)
    return normalized == "memory" or normalized.startswith("memory/")


def _violation_memory_path(violation: dict) -> str | None:
    filename = str(violation.get("file") or "").strip().replace("\\", "/")
    if not filename:
        return None
    if filename.startswith("memory/"):
        return filename
    return f"memory/{filename}"


def check(
    project_root: Path,
    *,
    changed_files: Sequence[str],
    active_from: str = "2026-06-02",
) -> CiMemoryWorkflowCheckResult:
    repo_root = project_root.resolve()
    normalized_changed = sorted({_normalize(item) for item in changed_files if _normalize(item)})
    changed_memory_files = [item for item in normalized_changed if _is_memory_file(item)]

    policy = load_blocking_policy(repo_root)
    guard_result = run_guard(
        repo_root / "memory",
        repo_root,
        skip_git=True,
        changed_files=changed_memory_files,
        blocking_codes=policy["enabled_codes"],
        override_mode=policy["override_mode"],
    )
    active = filter_active_non_canonical_writer_violations(
        guard_result["violations"],
        active_from=active_from,
    )
    changed_memory_set = set(changed_memory_files)
    current_diff_active = [
        violation
        for violation in active
        if _violation_memory_path(violation) in changed_memory_set
    ]
    current_diff_authority_overrides = [
        violation
        for violation in guard_result["violations"]
        if violation.get("code") == "authority_override_used"
        and _violation_memory_path(violation) in changed_memory_set
    ]
    repo_state_b0_blockers = [
        violation
        for violation in guard_result["violations"]
        if violation.get("code") == _B0_CODE
        and violation.get("enforcement") == "block"
    ]
    current_diff_b0_blockers = [
        violation
        for violation in repo_state_b0_blockers
        if _violation_memory_path(violation) in changed_memory_set
    ]

    warnings = []
    counts = guard_result.get("violation_counts_by_code") or {}
    for code in (
        "missing_canonical_memory",
        "unbound_memory",
        "non_canonical_writer",
        "session_like_non_session_memory_type",
        "non_daily_session_shaped_memory_entry",
        "authority_override_rejected",
        "test_evidence_artifact_metadata_missing",
        "test_evidence_artifact_metadata_invalid",
        "test_evidence_exit_code_contradicts_claim",
        "test_evidence_linked_commit_mismatch",
    ):
        count = int(counts.get(code) or 0)
        if count:
            warnings.append(f"{code}={count}")
    if current_diff_authority_overrides:
        warnings.append(
            f"authority_override_used={len(current_diff_authority_overrides)}"
        )

    if policy["error"]:
        warnings.append(policy["error"])
    warnings.extend(policy_disable_attestation_warnings(repo_root, normalized_changed))

    blockers = [
        {
            "code": "active_non_canonical_writer",
            "file": _violation_memory_path(violation),
            "reason": violation.get("reason", ""),
        }
        for violation in current_diff_active
    ]
    blockers.extend(
        {
            "code": f"memory_authority_blocking:{violation['code']}",
            "file": _violation_memory_path(violation),
            "reason": violation.get("reason", ""),
        }
        for violation in guard_result["violations"]
        if violation.get("enforcement") == "block"
    )
    if policy["error"]:
        # A broken policy file must fail the gate, not degrade to a warning:
        # otherwise corrupting the policy is a silent kill switch.
        blockers.append({
            "code": "blocking_policy_error",
            "file": _BLOCKING_POLICY_RELPATH,
            "reason": policy["error"],
        })

    return CiMemoryWorkflowCheckResult(
        repo_root=str(repo_root),
        mode="ci_selective_current_diff",
        changed_files=normalized_changed,
        changed_memory_files=changed_memory_files,
        active_non_canonical_writer_count=len(active),
        current_diff_active_non_canonical_writer_count=len(current_diff_active),
        repo_state_b0_blocker_count=len(repo_state_b0_blockers),
        current_diff_b0_blocker_count=len(current_diff_b0_blockers),
        blockers=blockers,
        warnings=warnings,
        clean=not blockers,
    )


def format_human(result: CiMemoryWorkflowCheckResult) -> str:
    lines = [
        "[ci_memory_workflow_check]",
        f"mode={result.mode}",
        f"repo_root={result.repo_root}",
        f"changed_files={len(result.changed_files)}",
        f"changed_memory_files={len(result.changed_memory_files)}",
        f"active_non_canonical_writer_count={result.active_non_canonical_writer_count}",
        "current_diff_active_non_canonical_writer_count="
        f"{result.current_diff_active_non_canonical_writer_count}",
        f"repo_state_b0_blocker_count={result.repo_state_b0_blocker_count}",
        f"current_diff_b0_blocker_count={result.current_diff_b0_blocker_count}",
        f"clean={result.clean}",
    ]
    if result.changed_memory_files:
        lines.append("[changed_memory_files]")
        lines.extend(result.changed_memory_files)
    if result.warnings:
        lines.append("[warnings]")
        lines.extend(result.warnings)
    if result.blockers:
        lines.append("[blockers]")
        for blocker in result.blockers:
            lines.append(f"{blocker['code']}: {blocker['file']} -- {blocker['reason']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CI-only blocker for current-diff memory workflow violations."
    )
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--changed-file", action="append", default=None)
    parser.add_argument("--active-from", default="2026-06-02")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    if args.changed_file is not None:
        changed_files = args.changed_file
    elif args.base_ref:
        changed_files = _changed_files_from_refs(project_root, args.base_ref, args.head_ref)
    else:
        raise SystemExit("error: provide --base-ref/--head-ref or at least one --changed-file")

    result = check(project_root, changed_files=changed_files, active_from=args.active_from)
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(format_human(result))
    return 0 if result.clean else 2


if __name__ == "__main__":
    raise SystemExit(main())
