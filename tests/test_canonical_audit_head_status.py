"""
Regression tests for issue #219 (part A).

_get_repo_head() returned "" for every failure, so the canonical audit log's
linked_head_commit could not distinguish "not a git repo", "git failed" and
"git timed out" from each other.  The audit entry now carries
linked_head_commit_status (and a short detail for non-ok states).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from governance_tools import session_end_hook as hook


@pytest.fixture(autouse=True)
def _isolate_git_discovery(tmp_path, monkeypatch):
    # tmp_path may live inside this repository's checkout (short --basetemp);
    # stop git from walking up into it, or "not a git repo" would find our repo.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo_with_commit(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "seed")
    return root


def _audit_entries(root: Path) -> list[dict]:
    path = root / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(root: Path) -> None:
    hook._append_canonical_audit_log(
        root, session_id="session-a", artifact_state="ok", canonical_path_audit={},
        gate_blocked=False, policy_source="builtin", policy_path=None,
        fallback_used=True, repo_policy_present=False,
    )


def test_resolves_head_in_a_repo(tmp_path):
    repo = _repo_with_commit(tmp_path / "repo")
    head, status, detail = hook._resolve_repo_head(repo)
    assert (head, status, detail) == (_git(repo, "rev-parse", "HEAD"), hook.HEAD_STATUS_OK, "")
    assert hook._get_repo_head(repo) == head  # compatibility wrapper


def test_not_a_git_repo(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    head, status, detail = hook._resolve_repo_head(plain)
    assert head == ""
    assert status == hook.HEAD_STATUS_NOT_A_GIT_REPO
    assert detail  # git's own first stderr line, whatever the locale


def test_repo_without_commits_is_a_git_error_not_a_missing_repo(tmp_path):
    repo = tmp_path / "unborn"
    repo.mkdir()
    _git(repo, "init", "-q")
    head, status, _ = hook._resolve_repo_head(repo)
    assert (head, status) == ("", hook.HEAD_STATUS_GIT_ERROR)


def test_git_missing_is_reported(tmp_path, monkeypatch):
    def _missing(*_a, **_k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(hook.subprocess, "run", _missing)
    head, status, detail = hook._resolve_repo_head(tmp_path)
    assert (head, status) == ("", hook.HEAD_STATUS_GIT_UNAVAILABLE)
    assert "git" in detail


def test_git_timeout_is_reported(tmp_path, monkeypatch):
    def _slow(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr(hook.subprocess, "run", _slow)
    assert hook._resolve_repo_head(tmp_path)[:2] == ("", hook.HEAD_STATUS_TIMEOUT)


def test_unexpected_error_never_raises(tmp_path, monkeypatch):
    def _boom(*_a, **_k):
        raise PermissionError("denied")

    monkeypatch.setattr(hook.subprocess, "run", _boom)
    head, status, detail = hook._resolve_repo_head(tmp_path)
    assert (head, status) == ("", hook.HEAD_STATUS_GIT_ERROR)
    assert "PermissionError" in detail


def test_audit_entry_records_status_for_non_git_root(tmp_path):
    """Issue #219 repro: the entry used to say only linked_head_commit=''."""
    plain = tmp_path / "plain"
    plain.mkdir()
    _append(plain)
    entry = _audit_entries(plain)[-1]
    assert entry["linked_head_commit"] == ""
    assert entry["linked_head_commit_status"] == hook.HEAD_STATUS_NOT_A_GIT_REPO
    assert entry["linked_head_commit_detail"]


def test_audit_entry_ok_has_no_detail(tmp_path):
    repo = _repo_with_commit(tmp_path / "repo")
    _append(repo)
    entry = _audit_entries(repo)[-1]
    assert entry["linked_head_commit"] == _git(repo, "rev-parse", "HEAD")
    assert entry["linked_head_commit_status"] == hook.HEAD_STATUS_OK
    assert "linked_head_commit_detail" not in entry


def test_session_end_hook_cli_path_on_non_git_root(tmp_path):
    """The exact command from the issue: session_end_hook on a non-git root."""
    plain = tmp_path / "plain"
    plain.mkdir()
    hook.run_session_end_hook(plain)
    entry = _audit_entries(plain)[-1]
    assert entry["linked_head_commit"] == ""
    assert entry["linked_head_commit_status"] == hook.HEAD_STATUS_NOT_A_GIT_REPO
