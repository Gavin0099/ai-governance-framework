#!/usr/bin/env python3
"""Shared Git provenance rules for canonical memory producers and readers.

Claim ceiling:
- ``bound`` means that the named commit resolves to a commit object in the
  local repository.
- It does not mean that the commit was pushed or that memory prose is true.
- Mixed-scope findings are report-only observations.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):  # pragma: no cover - direct-script fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.evidence_roots import (
    EvidenceRootPolicy,
    find_evidence_tokens,
    load_evidence_root_policy,
    normalize_token,
    policy_from_values,
)

REAL_COMMIT_RE = re.compile(r"^[a-f0-9]{5,40}$", re.IGNORECASE)
UNBOUND_COMMIT_TOKENS = frozenset(
    {"", "UNCOMMITTED", "WORKTREE", "PENDING", "LOCAL-UNCOMMITTED"}
)
MIXED_SCOPE_CODE = "mixed_scope_memory_binding"
CANONICAL_WRITER = "governance_tools.memory_record"

_FIELD_RE = re.compile(r"^\s{0,4}(?P<key>[a-z_]+):\s*(?P<value>.*)$")


def _run_git(
    project_root: Path,
    args: Sequence[str],
    *,
    input_text: str | None = None,
) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), *args],
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover - defensive environment fallback
        return 1, "", str(exc)
    return (
        completed.returncode,
        (completed.stdout or "").strip(),
        (completed.stderr or "").strip(),
    )


def is_git_worktree(project_root: Path) -> bool:
    code, stdout, _stderr = _run_git(
        project_root, ["rev-parse", "--is-inside-work-tree"]
    )
    return code == 0 and stdout == "true"


def is_unbound_commit_token(commit: str | None) -> bool:
    return (commit or "").strip().upper() in UNBOUND_COMMIT_TOKENS


def git_commit_exists(project_root: Path, commit_hash: str) -> bool:
    candidate = commit_hash.strip()
    if not REAL_COMMIT_RE.fullmatch(candidate) or not is_git_worktree(project_root):
        return False
    code, _stdout, _stderr = _run_git(
        project_root, ["cat-file", "-e", f"{candidate}^{{commit}}"]
    )
    return code == 0


def git_commits_exist(
    project_root: Path, commit_hashes: Sequence[str]
) -> dict[str, bool]:
    unique_hashes = sorted(
        {
            commit_hash.strip().lower()
            for commit_hash in commit_hashes
            if REAL_COMMIT_RE.fullmatch(commit_hash.strip())
        }
    )
    if not unique_hashes:
        return {}
    if not is_git_worktree(project_root):
        return {commit_hash: False for commit_hash in unique_hashes}

    query = "".join(f"{commit_hash}^{{commit}}\n" for commit_hash in unique_hashes)
    code, stdout, _stderr = _run_git(
        project_root, ["cat-file", "--batch-check"], input_text=query
    )
    if code != 0:
        return {
            commit_hash: git_commit_exists(project_root, commit_hash)
            for commit_hash in unique_hashes
        }

    results: dict[str, bool] = {}
    for commit_hash, line in zip(unique_hashes, stdout.splitlines()):
        parts = line.split()
        results[commit_hash] = len(parts) >= 2 and parts[1] == "commit"
    for commit_hash in unique_hashes:
        results.setdefault(commit_hash, False)
    return results


def resolve_memory_binding(
    project_root: Path,
    commit: str | None,
    session_id: str | None = None,
    *,
    allow_session_fallback: bool,
) -> str:
    """Resolve producer-side binding without treating hash-shaped text as proof."""
    candidate = (commit or "").strip()
    if git_commit_exists(project_root, candidate):
        return "bound"
    if allow_session_fallback and (session_id or "").strip():
        return "bound_session_id"
    return "unbound"


def _normalize_path(path_text: str) -> str:
    return path_text.strip().replace("\\", "/").lstrip("./")


def _is_memory_path(path_text: str) -> bool:
    normalized = _normalize_path(path_text)
    return normalized == "memory" or normalized.startswith("memory/")


def _added_canonical_entries(patch: str) -> list[dict[str, str]]:
    added_lines = [
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in added_lines:
        if line.startswith("- memory_type:"):
            if current is not None:
                entries.append(current)
            current = {"memory_type": line.split(":", 1)[1].strip()}
            continue
        if current is None:
            continue
        match = _FIELD_RE.match(line)
        if match:
            current[match.group("key")] = match.group("value").strip()
    if current is not None:
        entries.append(current)
    return [
        entry
        for entry in entries
        if entry.get("writer") == CANONICAL_WRITER
        and entry.get("memory_type") == "session-derived"
    ]


def _entry_artifact_refs(
    entries: Sequence[dict[str, str]], policy: EvidenceRootPolicy
) -> set[str]:
    refs: set[str] = set()
    for entry in entries:
        for token in find_evidence_tokens(entry.get("test_evidence", ""), policy):
            refs.add(_normalize_path(normalize_token(token)))
    return refs


def _companion_patterns(policy: EvidenceRootPolicy) -> list[re.Pattern[str]]:
    """Closeout companion shapes, anchored under each declared evidence root."""
    patterns: list[re.Pattern[str]] = []
    for root in policy.roots:
        escaped = re.escape(root)
        patterns.append(
            re.compile(rf"{escaped}/evidence/test-results/receipt-[^/]+\.(json|txt)")
        )
        patterns.append(
            re.compile(rf"{escaped}/runtime/(closeouts|verdicts)/[^/]+\.json")
        )
    return patterns


def _is_closeout_companion_path(
    path_text: str,
    *,
    plan_updated: bool,
    cited_artifacts: set[str],
    companion_patterns: Sequence[re.Pattern[str]] | None = None,
) -> bool:
    if companion_patterns is None:
        companion_patterns = _companion_patterns(policy_from_values(None))
    normalized = _normalize_path(path_text)
    if _is_memory_path(normalized):
        return True
    if normalized == "PLAN.md":
        return plan_updated
    if normalized in cited_artifacts:
        return True
    return any(pattern.fullmatch(normalized) for pattern in companion_patterns)


def _finding_for_scope(
    project_root: Path,
    *,
    scope_ref: str,
    changed_paths: Sequence[str],
    memory_patch: str,
) -> dict | None:
    entries = _added_canonical_entries(memory_patch)
    bound_commits = sorted(
        {
            entry.get("commit_hash") or entry.get("commit") or ""
            for entry in entries
            if entry.get("memory_binding") == "bound"
        }
    )
    bound_commits = [
        commit_hash
        for commit_hash in bound_commits
        if git_commit_exists(project_root, commit_hash)
    ]
    if not bound_commits:
        return None

    plan_updated = any(
        entry.get("plan_reconciliation") == "updated" for entry in entries
    )
    policy = load_evidence_root_policy(project_root)
    cited_artifacts = _entry_artifact_refs(entries, policy)
    companion_patterns = _companion_patterns(policy)
    disallowed_paths = sorted(
        {
            _normalize_path(path)
            for path in changed_paths
            if not _is_closeout_companion_path(
                path,
                plan_updated=plan_updated,
                cited_artifacts=cited_artifacts,
                companion_patterns=companion_patterns,
            )
        }
    )
    if not disallowed_paths:
        return None

    return {
        "code": MIXED_SCOPE_CODE,
        "enforcement": "report_only",
        "scope_ref": scope_ref,
        "bound_commits": bound_commits,
        "disallowed_paths": disallowed_paths,
        "reason": (
            "canonical memory in this scope binds an earlier local commit while "
            "the same scope also changes non-closeout paths"
        ),
    }


def detect_staged_mixed_scope_memory_bindings(project_root: Path) -> list[dict]:
    """Inspect only the staged scope; unrelated working-tree dirt is ignored."""
    if not is_git_worktree(project_root):
        return []
    code, stdout, _stderr = _run_git(
        project_root, ["diff", "--cached", "--name-only"]
    )
    if code != 0:
        return []
    changed_paths = [
        _normalize_path(line) for line in stdout.splitlines() if line.strip()
    ]
    memory_paths = [path for path in changed_paths if _is_memory_path(path)]
    if not memory_paths:
        return []
    code, patch, _stderr = _run_git(
        project_root, ["diff", "--cached", "--unified=0", "--", *memory_paths]
    )
    if code != 0:
        return []
    finding = _finding_for_scope(
        project_root,
        scope_ref="INDEX",
        changed_paths=changed_paths,
        memory_patch=patch,
    )
    return [finding] if finding else []


def _commit_changed_paths(project_root: Path, commit: str) -> list[str]:
    code, parent, _stderr = _run_git(project_root, ["rev-parse", f"{commit}^1"])
    if code == 0 and parent:
        args = ["diff", "--name-only", parent, commit]
    else:
        args = ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit]
    code, stdout, _stderr = _run_git(project_root, args)
    if code != 0:
        return []
    return [_normalize_path(line) for line in stdout.splitlines() if line.strip()]


def _commit_memory_patch(
    project_root: Path, commit: str, memory_paths: Sequence[str]
) -> str:
    code, parent, _stderr = _run_git(project_root, ["rev-parse", f"{commit}^1"])
    if code == 0 and parent:
        args = ["diff", "--unified=0", parent, commit, "--", *memory_paths]
    else:
        args = ["show", "--format=", "--unified=0", commit, "--", *memory_paths]
    code, stdout, _stderr = _run_git(project_root, args)
    return stdout if code == 0 else ""


def detect_commit_range_mixed_scope_memory_bindings(
    project_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
) -> list[dict]:
    """Inspect each commit independently so a legal two-commit flow stays clean."""
    if not is_git_worktree(project_root):
        return []
    code, stdout, _stderr = _run_git(
        project_root, ["rev-list", "--reverse", f"{base_ref}..{head_ref}"]
    )
    if code != 0:
        return []

    findings: list[dict] = []
    for commit in [line.strip() for line in stdout.splitlines() if line.strip()]:
        changed_paths = _commit_changed_paths(project_root, commit)
        memory_paths = [path for path in changed_paths if _is_memory_path(path)]
        if not memory_paths:
            continue
        finding = _finding_for_scope(
            project_root,
            scope_ref=commit,
            changed_paths=changed_paths,
            memory_patch=_commit_memory_patch(project_root, commit, memory_paths),
        )
        if finding:
            findings.append(finding)
    return findings
