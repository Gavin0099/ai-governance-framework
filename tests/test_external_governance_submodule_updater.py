from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from governance_tools.external_governance_submodule_updater import (
    _git_env,
    _run_git,
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


def _write_framework_baseline(framework: Path) -> None:
    baseline = framework / "baselines" / "repo-min"
    baseline.mkdir(parents=True, exist_ok=True)
    (baseline / "AGENTS.base.md").write_text(
        "# AGENTS.base.md\n<!-- governance-baseline: protected -->\n",
        encoding="utf-8",
    )
    (baseline / "AGENTS.md").write_text(
        "# AGENTS.md\n\n"
        "## AI Governance Update Intent Rule\n\n"
        "intent rule\n\n"
        "### F-7 Full Update Semantics\n\n"
        "F-7 is the AI Governance Full Update workflow.\n\n"
        "## Repo-Specific Risk Levels\n\n"
        "N/A\n",
        encoding="utf-8",
    )


def test_run_git_uses_utf8_replacement_decode_and_handles_none_streams(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=None, stderr=None)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = _run_git(tmp_path, ["commit", "-m", "message"])

    kwargs = captured["kwargs"]
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.returncode == 0


def _make_fixture(tmp_path: Path) -> tuple[Path, Path, str, str]:
    framework = tmp_path / "framework"
    consumer = tmp_path / "consumer"

    _init_repo(framework)
    (framework / "README.md").write_text("v1\n", encoding="utf-8")
    _write_framework_baseline(framework)
    old_head = _commit_all(framework, "framework v1")
    (framework / "README.md").write_text("v2\n", encoding="utf-8")
    _write_framework_baseline(framework)
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


def _make_already_current_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    framework = tmp_path / "framework"
    consumer = tmp_path / "consumer"

    _init_repo(framework)
    (framework / "README.md").write_text("v1\n", encoding="utf-8")
    _write_framework_baseline(framework)
    target_head = _commit_all(framework, "framework v1")

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
    _commit_all(consumer, "pin current framework")

    return consumer, framework, target_head


def _make_divergent_fixture(tmp_path: Path) -> tuple[Path, Path, str, str]:
    framework = tmp_path / "framework"
    consumer = tmp_path / "consumer"

    _init_repo(framework)
    (framework / "README.md").write_text("v1\n", encoding="utf-8")
    _write_framework_baseline(framework)
    base_head = _commit_all(framework, "framework v1")
    _git(framework, "checkout", "-b", "side", base_head)
    (framework / "SIDE.md").write_text("side\n", encoding="utf-8")
    _write_framework_baseline(framework)
    side_head = _commit_all(framework, "framework side")
    _git(framework, "checkout", "main")
    (framework / "README.md").write_text("v2\n", encoding="utf-8")
    _write_framework_baseline(framework)
    target_head = _commit_all(framework, "framework v2")

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
    _git(consumer / "ai-governance-framework", "checkout", side_head)
    _commit_all(consumer, "pin divergent framework")

    return consumer, framework, side_head, target_head


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
    assert result.update_mode == "dry_run"
    assert result.fast_forward is True
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.after_head == old_head
    assert result.full_update_stage_report["final_status"] == "not_verified"
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_dry_run_refuses_uninitialized_submodule_checkout(tmp_path: Path) -> None:
    consumer, _framework, _old_head, _new_head = _make_fixture(tmp_path)
    _git(consumer, "submodule", "deinit", "-f", "--", "ai-governance-framework")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is False
    assert result.update_mode == "failed"
    assert result.before_head == ""
    assert result.after_head == ""
    assert result.target_head == ""
    assert result.full_update_stage_report["final_status"] == "blocked"
    assert "submodule path is not an initialized git checkout" in result.errors[0]
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
    assert result.update_mode == "fast_forward"
    assert result.fast_forward is True
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.after_head == new_head
    assert result.full_update_stage_report["framework_pointer"] == "updated"
    assert result.full_update_stage_report["repo_local_instruction"] == "updated"
    assert result.full_update_stage_report["memory_writer_coverage"] == "missing"
    assert result.full_update_stage_report["hook_validator_enforcement"] == "missing"
    assert result.full_update_stage_report["final_status"] == "partially_updated"
    assert result.staged_files == [
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
    ]
    assert _git(consumer, "diff", "--cached", "--name-only").splitlines() == [
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
    ]
    assert "F-7 Full Update Semantics" in (consumer / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "?? unrelated.txt" in _git(consumer, "status", "--short")


def test_apply_commit_noops_when_submodule_already_points_at_target(
    tmp_path: Path,
) -> None:
    consumer, _framework, target_head = _make_already_current_fixture(tmp_path)
    before_consumer_head = _git(consumer, "rev-parse", "HEAD")
    (consumer / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
        commit=True,
    )

    assert result.ok is True
    assert result.update_mode == "already_current"
    assert result.fast_forward is True
    assert result.before_head == target_head
    assert result.target_head == target_head
    assert result.after_head == target_head
    assert result.full_update_stage_report["framework_pointer"] == "already_current"
    assert result.full_update_stage_report["repo_local_instruction"] == "updated"
    assert result.full_update_stage_report["final_status"] == "partially_updated"
    assert result.staged_files == ["AGENTS.base.md", "AGENTS.md"]
    assert result.committed is True
    assert result.commit_hash is not None
    assert _git(consumer, "rev-parse", "HEAD") != before_consumer_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""
    assert "?? unrelated.txt" in _git(consumer, "status", "--short")


def test_refuses_when_nested_submodule_has_tracked_changes(tmp_path: Path) -> None:
    consumer, _framework, _old_head, _new_head = _make_fixture(tmp_path)
    nested = consumer / "ai-governance-framework"
    # Modify a tracked file — this should block the update.
    (nested / "README.md").write_text("local modification\n", encoding="utf-8")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is False
    assert result.update_mode == "failed"
    assert result.full_update_stage_report["final_status"] == "blocked"
    assert "nested submodule checkout has tracked-file changes" in result.errors[0]
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_allows_untracked_files_in_nested_submodule(tmp_path: Path) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    nested = consumer / "ai-governance-framework"
    # Untracked files (e.g. runtime artifacts, DB files) must not block update.
    (nested / "runtime.db").write_text("untracked\n", encoding="utf-8")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
        commit=True,
    )

    assert result.ok is True
    assert result.after_head == new_head
    assert result.full_update_stage_report["repo_local_instruction"] == "updated"


def test_non_fast_forward_update_refuses_without_explicit_checkout(
    tmp_path: Path,
) -> None:
    consumer, _framework, side_head, _target_head = _make_divergent_fixture(tmp_path)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is False
    assert result.update_mode == "failed"
    assert result.fast_forward is None
    assert result.full_update_stage_report["final_status"] == "blocked"
    assert "merge --ff-only" in result.errors[0]
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == side_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_non_fast_forward_update_checkout_runs_only_when_explicitly_allowed(
    tmp_path: Path,
) -> None:
    consumer, _framework, side_head, target_head = _make_divergent_fixture(tmp_path)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
        allow_detached_target_checkout=True,
    )

    assert result.ok is True
    assert result.before_head == side_head
    assert result.target_head == target_head
    assert result.after_head == target_head
    assert result.update_mode == "detached_target_checkout"
    assert result.fast_forward is False
    assert result.full_update_stage_report["framework_pointer"] == "updated"
    assert result.full_update_stage_report["repo_local_instruction"] == "updated"
    assert result.staged_files == [
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
    ]
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == target_head
    assert _git(consumer, "diff", "--cached", "--name-only").splitlines() == [
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
    ]
