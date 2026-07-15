from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from governance_tools.hook_installer import install_governance_hooks


REPO_ROOT = Path(__file__).resolve().parents[1]
ZERO_OID = "0" * 40


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return (completed.stdout or "").strip()


def _git_bash() -> Path:
    candidates: list[Path] = []
    if os.name == "nt":
        candidates.extend(
            [
                Path("C:/Program Files/Git/bin/bash.exe"),
                Path("C:/Program Files/Git/usr/bin/bash.exe"),
            ]
        )
    discovered = shutil.which("bash")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    pytest.skip("Git Bash/bash is required for managed hook execution tests")


def _make_consumer(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "consumer"
    framework = tmp_path / "framework"
    repo.mkdir()
    _run_git(repo, "init")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test User")
    _write(repo / "README.md", "baseline\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-m", "baseline")

    for hook_name in ("pre-commit", "pre-push"):
        source = REPO_ROOT / "scripts" / "hooks" / hook_name
        _write(
            framework / "scripts" / "hooks" / hook_name,
            source.read_text(encoding="utf-8"),
        )
    _write(
        framework / "scripts" / "lib" / "python.sh",
        "set_python_cmd() { PYTHON_CMD=(python); return 0; }\n",
    )

    result = install_governance_hooks(
        repo,
        framework,
        include_copilot=False,
    )
    assert result.ok is True
    return repo, framework


def _run_pre_push(repo: Path, update_line: str) -> subprocess.CompletedProcess[str]:
    hook = repo / ".git" / "hooks" / "pre-push"
    return subprocess.run(
        [str(_git_bash()), "--login", hook.as_posix(), "origin", "unused"],
        cwd=repo,
        input=update_line,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_memory_policy_authority_stays_in_ci_with_advisory_pre_commit() -> None:
    pre_commit = (REPO_ROOT / "scripts" / "hooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    pre_push = (REPO_ROOT / "scripts" / "hooks" / "pre-push").read_text(
        encoding="utf-8"
    )
    workflow = (REPO_ROOT / ".github" / "workflows" / "governance.yml").read_text(
        encoding="utf-8"
    )

    assert "python -m governance_tools.ci_memory_workflow_check" in workflow
    assert (
        '"$MEMORY_WORKFLOW_TOOL" --repo "$TARGET_REPO_ROOT" --check '
        "--run-guard --format json"
    ) in pre_commit
    assert "pre-commit advisory only; commit is not blocked" in pre_commit

    forbidden_pre_push_tokens = (
        "TODAY_MEMORY_PATH",
        "MEMORY_UPDATED_IN_PUSH",
        "memory_freshness_guard.py",
        "daily_memory_guard.py",
        "blocked: missing required memory file",
        "blocked: push does not include",
    )
    for token in forbidden_pre_push_tokens:
        assert token not in pre_push


def test_git_bash_branch_deletion_is_not_blocked_by_memory_policy(
    tmp_path: Path,
) -> None:
    repo, _framework = _make_consumer(tmp_path)
    remote_head = _run_git(repo, "rev-parse", "HEAD")

    completed = _run_pre_push(
        repo,
        f"refs/heads/topic {ZERO_OID} refs/heads/topic {remote_head}\n",
    )

    assert completed.returncode == 0, completed.stdout
    assert "[governance] blocked:" not in completed.stdout


def test_git_bash_product_push_does_not_require_future_post_push_memory(
    tmp_path: Path,
) -> None:
    repo, _framework = _make_consumer(tmp_path)
    remote_head = _run_git(repo, "rev-parse", "HEAD")
    _write(repo / "product.txt", "product-only change\n")
    _run_git(repo, "add", "product.txt")
    # This fixture targets pre-push behavior. Avoid invoking the independently
    # covered pre-commit hook while constructing the outgoing product commit.
    _run_git(repo, "commit", "--no-verify", "-m", "product change")
    local_head = _run_git(repo, "rev-parse", "HEAD")

    assert not (repo / "memory").exists()
    completed = _run_pre_push(
        repo,
        f"refs/heads/main {local_head} refs/heads/main {remote_head}\n",
    )

    assert completed.returncode == 0, completed.stdout
    assert "[governance] blocked:" not in completed.stdout
