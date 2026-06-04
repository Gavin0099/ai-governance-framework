from __future__ import annotations

import subprocess
from pathlib import Path

from governance_tools.external_governance_submodule_updater import (
    _git_env,
    update_governance_submodule,
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_env(),
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git -C {repo} {' '.join(args)} failed\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed.stdout.strip()


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")


def _make_fixture(tmp_path: Path) -> tuple[Path, Path, str, str]:
    framework = tmp_path / "framework"
    consumer = tmp_path / "consumer"

    _init_repo(framework)
    (framework / "README.md").write_text("v1\n", encoding="utf-8")
    old_head = _commit_all(framework, "framework v1")
    (framework / "README.md").write_text("v2\n", encoding="utf-8")
    new_head = _commit_all(framework, "framework v2")

    _init_repo(consumer)
    _git(
        consumer,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(framework),
        "ai-governance-framework",
    )
    _git(consumer / "ai-governance-framework", "checkout", old_head)
    _commit_all(consumer, "pin old framework")

    return consumer, framework, old_head, new_head


def test_dry_run_does_not_change_submodule_or_stage_files(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    (consumer / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.mode == "dry_run"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.after_head == old_head
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_apply_stage_updates_only_submodule_pointer(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    (consumer / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is True
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.after_head == new_head
    assert result.staged_files == ["ai-governance-framework"]
    assert _git(consumer, "diff", "--cached", "--name-only") == "ai-governance-framework"
    assert "?? unrelated.txt" in _git(consumer, "status", "--short")


def test_refuses_when_nested_submodule_is_dirty(tmp_path: Path) -> None:
    consumer, _framework, _old_head, _new_head = _make_fixture(tmp_path)
    nested = consumer / "ai-governance-framework"
    (nested / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is False
    assert "nested submodule checkout is dirty" in result.errors[0]
    assert _git(consumer, "diff", "--cached", "--name-only") == ""
