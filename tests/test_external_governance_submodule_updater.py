from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

import governance_tools.external_governance_submodule_updater as updater_module
from governance_tools.external_governance_submodule_updater import (
    SUBMODULE_APPLY_MUTATION_ALLOWLIST,
    UpdateResult,
    _build_full_update_stage_report,
    _check_existing_memory_normalization,
    _git_env,
    _refresh_repo_local_instructions,
    _run_git,
    _submodule_apply_mutation_allowlist,
    format_human,
    main,
    update_governance_submodule,
)
from governance_tools.update_receipt import RECEIPT_RELATIVE_PATH


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


def test_gate_path_inventories_preserve_tabs_newlines_and_spaces(monkeypatch) -> None:
    outputs = iter(
        (
            " staged\tfile\nname.py\0second file.py\0",
            (
                "100644 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 0\tregular.txt\0"
                "160000 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 0\t"
                " sibling\tmodule\nname\0"
            ),
        )
    )
    calls: list[tuple[tuple[str, ...], bool]] = []

    def fake_run_git(_repo, args, *, preserve_stdout=False, **_kwargs):
        calls.append((tuple(args), preserve_stdout))
        return SimpleNamespace(stdout=next(outputs))

    monkeypatch.setattr(updater_module, "_run_git", fake_run_git)

    assert updater_module._staged_files(Path("repo")) == [
        " staged\tfile\nname.py",
        "second file.py",
    ]
    assert updater_module._parse_name_status(
        "M\0 tracked\tfile\nname.py\0A\0second file.py\0",
        scope="worktree",
    ) == [
        ("worktree:M", " tracked\tfile\nname.py"),
        ("worktree:A", "second file.py"),
    ]
    assert updater_module._tracked_gitlinks(Path("repo")) == [
        (
            " sibling\tmodule\nname",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
    ]
    assert all(preserve_stdout for _args, preserve_stdout in calls)
    assert all("-z" in args for args, _preserve_stdout in calls)


def test_parent_dirty_status_uses_nul_safe_callers(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], bool]] = []

    def fake_run_git(_repo, args, *, preserve_stdout=False, **_kwargs):
        call = tuple(args)
        calls.append((call, preserve_stdout))
        if "ls-files" in call:
            stdout = " untracked\tfile\nname.py\0"
        elif "--cached" in call:
            stdout = "M\0 index\tfile\nname.py\0"
        else:
            stdout = "M\0 worktree\tfile\nname.py\0"
        return SimpleNamespace(stdout=stdout)

    monkeypatch.setattr(updater_module, "_run_git", fake_run_git)
    monkeypatch.setattr(updater_module, "_tracked_gitlinks", lambda _repo: [])

    assert updater_module._parent_dirty_status(Path("repo")) == {
        " index\tfile\nname.py": ("index:M",),
        " worktree\tfile\nname.py": ("worktree:M",),
        " untracked\tfile\nname.py": ("untracked:??",),
    }
    assert len(calls) == 3
    assert all(preserve_stdout for _args, preserve_stdout in calls)
    assert all("-z" in args for args, _preserve_stdout in calls)


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
    hook_dir = framework / "scripts" / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / "pre-commit").write_text(
        "#!/usr/bin/env bash\n"
        "# pre-commit hook — AI Governance Framework\n"
        'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"\n'
        '"$MEMORY_WORKFLOW_TOOL" --repo "$TARGET_REPO_ROOT" --check --format json || true\n',
        encoding="utf-8",
    )
    (hook_dir / "pre-push").write_text(
        "#!/usr/bin/env bash\n# pre-push hook - AI Governance Framework\n",
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
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_main_human_output_is_safe_for_ascii_console(tmp_path: Path, monkeypatch) -> None:
    class AsciiOnlyStdout:
        encoding = "ascii"

        def __init__(self) -> None:
            self.parts: list[str] = []

        def write(self, text: str) -> int:
            text.encode(self.encoding, errors="strict")
            self.parts.append(text)
            return len(text)

    result = UpdateResult(
        ok=True,
        mode="dry_run",
        update_mode="dry_run",
        fast_forward=True,
        repo=str(tmp_path),
        submodule_path="ai-governance-framework",
        before_head="old",
        target_head="new",
        after_head="old",
        staged_files=[],
        committed=False,
        commit_hash=None,
        message="\u66f4\u65b0\u5b8c\u6210\uff1a\u4e2d\u6587\u8868\u683c",
        errors=[],
        full_update_stage_report={
            "governance_maturity_summary": {
                "human_readable_adoption_summary": [
                    "[human_readable_adoption_summary]",
                    "| \u529f\u80fd | \u72c0\u614b | \u9019\u500b\u529f\u80fd\u662f\u505a\u4ec0\u9ebc |",
                ],
            }
        },
        target_source="fresh_remote_ls_remote",
    )
    stdout = AsciiOnlyStdout()
    monkeypatch.setattr(
        "governance_tools.external_governance_submodule_updater.update_governance_submodule",
        lambda **_kwargs: result,
    )
    monkeypatch.setattr("sys.stdout", stdout)

    assert main(["--repo", str(tmp_path)]) == 0
    rendered = "".join(stdout.parts)
    assert "[human_readable_adoption_summary]" in rendered
    assert "??" in rendered


def _make_fixture(
    tmp_path: Path,
    *,
    submodule_path: str = "ai-governance-framework",
    gitmodules_url: str | None = None,
) -> tuple[Path, Path, str, str]:
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
        submodule_path,
    )
    if gitmodules_url is not None:
        _git(
            consumer,
            "config",
            "--file",
            ".gitmodules",
            f"submodule.{submodule_path}.url",
            gitmodules_url,
        )
    _git(consumer / submodule_path, "checkout", old_head)
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


def _make_remote_ahead_without_local_object_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, str, str]:
    framework = tmp_path / "framework"
    consumer = tmp_path / "consumer"

    _init_repo(framework)
    (framework / "README.md").write_text("v1\n", encoding="utf-8")
    _write_framework_baseline(framework)
    old_head = _commit_all(framework, "framework v1")

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

    (framework / "README.md").write_text("v2\n", encoding="utf-8")
    _write_framework_baseline(framework)
    new_head = _commit_all(framework, "framework v2")

    return consumer, framework, old_head, new_head


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
    assert result.target_source == "fresh_remote_ls_remote"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.after_head == old_head
    assert result.update_receipt["status"] == "not_written"
    assert not (consumer / RECEIPT_RELATIVE_PATH).exists()
    assert result.full_update_stage_report["final_status"] == "not_verified"
    assert (
        result.full_update_stage_report["final_status_scope"]
        == "full_update_completion"
    )
    assert result.full_update_stage_report["governance_maturity_summary"]["report_only"] is True
    assert result.final_report_requirement["status"] == "required"
    assert "table rows as a table" in result.final_report_requirement["instruction"]
    assert "[human_readable_adoption_summary]" in (
        result.final_report_requirement["human_readable_adoption_summary"]
    )
    payload = asdict(result)
    assert "final_report_requirement" in asdict(result)
    assert payload["final_report_table_required"]["status"] == "required"
    assert payload["final_report_table_required"]["must_relay_as"] == "table_rows_verbatim"
    assert "[human_readable_adoption_summary]" in (
        payload["final_report_table_required"]["table_rows"]
    )
    envelope = payload["ai_governance_update_result"]
    assert envelope["report_only"] is True
    assert envelope["framework_update_status"] == {
        "value": "update_available",
        "source": "updater",
    }
    assert envelope["operation_execution"] == {
        "status": "passed",
        "mode": "dry_run",
        "framework_update_applied": False,
        "meaning": "dry-run checks passed; no update was applied",
    }
    assert envelope["governance_maturity_summary"]["value"] == "present"
    assert envelope["human_readable_adoption_summary"]["value"] == "reported"
    assert envelope["final_report_requirement"]["value"] == "present"
    rendered = format_human(result)
    assert "full_update_stage_report:" in rendered
    assert "[ai_governance_update_result]" in rendered
    assert "framework_update_status=update_available" in rendered
    assert "operation_execution_status=passed" in rendered
    assert "operation_mode=dry_run" in rendered
    assert "framework_update_applied=false" in rendered
    assert "- final_status_scope=full_update_completion" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "[final_report_requirement]" in rendered
    assert "table rows as a table" in rendered
    assert "AI Governance 功能導入狀態：" in rendered
    assert "| 功能 | 狀態 | 這個功能是做什麼 |" in rendered
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_stage_report_downgrades_completed_when_lock_consistency_is_inconsistent() -> None:
    report = _build_full_update_stage_report(
        framework_pointer="updated",
        repo_local_instruction="updated",
        memory_writer_coverage="verified",
        hook_validator_enforcement="verified",
        existing_memory_normalization="completed",
        governance_maturity_summary={
            "report_only": True,
            "lock_consistency": {"value": "inconsistent"},
            "human_readable_adoption_summary": ["[human_readable_adoption_summary]"],
        },
    )

    assert report["final_status"] == "partially_updated"


def test_dry_run_uses_fresh_remote_before_stale_local_tracking(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    submodule = consumer / "ai-governance-framework"
    _git(submodule, "update-ref", "refs/remotes/origin/main", old_head)

    result = update_governance_submodule(
        repo=consumer,
        target_ref="origin/main",
        fetch_remote="origin",
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.mode == "dry_run"
    assert result.update_mode == "dry_run"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.target_source == "fresh_remote_ls_remote"
    assert result.after_head == old_head
    assert _git(submodule, "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_dry_run_reports_local_tracking_fallback_when_remote_unavailable(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    submodule = consumer / "ai-governance-framework"
    _git(submodule, "update-ref", "refs/remotes/origin/main", new_head)
    _git(submodule, "remote", "set-url", "origin", "https://example.invalid/nope.git")

    result = update_governance_submodule(
        repo=consumer,
        target_ref="origin/main",
        fetch_remote="origin",
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.mode == "dry_run"
    assert result.update_mode == "dry_run"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.target_source == "local_tracking_ref_fallback"
    assert result.full_update_stage_report["framework_pointer"] == "not_verified"
    assert result.full_update_stage_report["target_fresh_upstream_verified"] is False
    assert result.full_update_stage_report["details"]["target_resolution"]["target_source"] == (
        "local_tracking_ref_fallback"
    )
    assert (
        result.full_update_stage_report["details"]["target_resolution"][
            "target_fresh_upstream_verified"
        ]
        is False
    )
    assert _git(submodule, "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_dry_run_fallback_uses_fetch_remote_tracking_ref_by_default(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    submodule = consumer / "ai-governance-framework"
    _git(submodule, "update-ref", "refs/remotes/gitlab/main", new_head)

    result = update_governance_submodule(
        repo=consumer,
        fetch_remote="gitlab",
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.target_source == "local_tracking_ref_fallback"
    assert result.full_update_stage_report["details"]["target_resolution"]["target_ref"] == (
        "gitlab/main"
    )


def test_dry_run_explicit_target_ref_overrides_fetch_remote_tracking_ref(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    submodule = consumer / "ai-governance-framework"
    _git(submodule, "update-ref", "refs/remotes/origin/main", old_head)
    _git(submodule, "update-ref", "refs/remotes/gitlab/main", new_head)

    result = update_governance_submodule(
        repo=consumer,
        target_ref="origin/main",
        fetch_remote="gitlab",
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.target_head == old_head
    assert result.target_source == "local_tracking_ref_fallback"
    assert result.full_update_stage_report["details"]["target_resolution"]["target_ref"] == (
        "origin/main"
    )


def test_refresh_repo_local_instructions_replaces_custom_risk_heading_section(tmp_path: Path) -> None:
    consumer, framework, _old_head, _new_head = _make_fixture(tmp_path)
    agents = consumer / "AGENTS.md"
    agents.write_text(
        "# CFU\n\n"
        "## AI Governance Update Intent Rule\n\n"
        "stale intent\n\n"
        "## CFU Risk Levels\n\n"
        "firmware-specific risks\n",
        encoding="utf-8",
    )

    first = _refresh_repo_local_instructions(consumer, framework)
    second = _refresh_repo_local_instructions(consumer, framework)
    refreshed = agents.read_text(encoding="utf-8")

    assert first["status"] == "updated"
    assert second["status"] == "already_current"
    assert refreshed.count("## AI Governance Update Intent Rule") == 1
    assert refreshed.count("## CFU Risk Levels") == 1
    assert "intent rule" in refreshed
    assert "firmware-specific risks" in refreshed


def test_refresh_repo_local_instructions_blocks_without_risk_heading(tmp_path: Path) -> None:
    consumer, framework, _old_head, _new_head = _make_fixture(tmp_path)
    agents = consumer / "AGENTS.md"
    original = (
        "# CFU\n\n"
        "## AI Governance Update Intent Rule\n\n"
        "stale intent\n\n"
        "## Custom Controls\n\n"
        "consumer-specific controls\n\n"
        "<!-- governance:key=memory_workflow -->\n"
    )
    agents.write_text(original, encoding="utf-8")

    result = _refresh_repo_local_instructions(consumer, framework)

    assert result["status"] == "blocked"
    assert any(
        "cannot safely refresh existing AI Governance update section" in error
        for error in result["errors"]
    )
    assert agents.read_text(encoding="utf-8") == original


def test_dry_run_local_tracking_fallback_cannot_claim_already_current(
    tmp_path: Path,
) -> None:
    consumer, _framework, target_head = _make_already_current_fixture(tmp_path)
    submodule = consumer / "ai-governance-framework"
    _git(submodule, "remote", "set-url", "origin", "https://example.invalid/nope.git")

    result = update_governance_submodule(
        repo=consumer,
        target_ref="origin/main",
        fetch_remote="origin",
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.before_head == target_head
    assert result.target_head == target_head
    assert result.target_source == "local_tracking_ref_fallback"
    assert result.full_update_stage_report["framework_pointer"] == "not_verified"
    assert result.full_update_stage_report["final_status"] == "not_verified"
    assert result.full_update_stage_report["target_fresh_upstream_verified"] is False
    assert "already_current/updated must not be claimed" in (
        result.full_update_stage_report["target_claim_boundary"]
    )
    rendered = format_human(result)
    assert "target_source=local_tracking_ref_fallback" in rendered
    assert "target_fresh_upstream_verified=False" in rendered
    assert "already_current/updated must not be claimed" in rendered
    assert _git(submodule, "rev-parse", "HEAD") == target_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_dry_run_reports_unknown_fast_forward_when_fresh_target_not_local(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, new_head = _make_remote_ahead_without_local_object_fixture(
        tmp_path
    )

    result = update_governance_submodule(
        repo=consumer,
        target_ref="origin/main",
        fetch_remote="origin",
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.mode == "dry_run"
    assert result.update_mode == "dry_run"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.target_source == "fresh_remote_ls_remote"
    assert result.fast_forward is None
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_default_path_autodetects_dot_prefixed_governance_submodule(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(
        tmp_path,
        submodule_path=".ai-governance-framework",
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.submodule_path == ".ai-governance-framework"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert _git(consumer / ".ai-governance-framework", "rev-parse", "HEAD") == old_head


def test_default_path_autodetects_gitmodules_governance_url_with_custom_path(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(
        tmp_path,
        submodule_path="external/ai-governance-framework",
        gitmodules_url="https://github.com/Gavin0099/ai-governance-framework.git",
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=True,
    )

    assert result.ok is True
    assert result.submodule_path == "external/ai-governance-framework"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert (
        _git(consumer / "external/ai-governance-framework", "rev-parse", "HEAD")
        == old_head
    )


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
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "failed",
        "mode": "dry_run",
        "framework_update_applied": False,
        "meaning": "dry-run checks failed; no update was applied",
    }
    assert "submodule path is not an initialized git checkout" in result.errors[0]
    assert _git(consumer, "diff", "--cached", "--name-only") == ""


def test_existing_memory_normalization_uses_active_guard_result(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "memory").mkdir(parents=True)
    (repo / "memory" / "2026-06-11.md").write_text("historical memory\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                '{"ok": true, "active_non_canonical_writer": '
                '{"count": 0, "violations": []}}'
            ),
            stderr="",
        )

    monkeypatch.setattr(
        "governance_tools.external_governance_submodule_updater.subprocess.run",
        fake_run,
    )

    assert _check_existing_memory_normalization(repo) == "verified"


def test_existing_memory_normalization_flags_active_guard_violations(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "memory").mkdir(parents=True)
    (repo / "memory" / "2026-06-11.md").write_text("active violation\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout='{"ok": true, "active_non_canonical_writer": {"count": 1}}',
            stderr="",
        )

    monkeypatch.setattr(
        "governance_tools.external_governance_submodule_updater.subprocess.run",
        fake_run,
    )

    assert _check_existing_memory_normalization(repo) == "needed"


def test_existing_memory_normalization_is_cwd_independent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    memory_dir = repo / "memory"
    memory_dir.mkdir()
    (memory_dir / "2026-04-30.md").write_text("# Historical memory\n", encoding="utf-8")
    _commit_all(repo, "test: add historical memory")

    launch_dir = tmp_path / "launch"
    launch_dir.mkdir()
    monkeypatch.chdir(launch_dir)

    assert _check_existing_memory_normalization(repo) == "verified"


def test_apply_stage_updates_only_submodule_pointer(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    (consumer / "unrelated.txt").write_text("dirty\n", encoding="utf-8")
    unrelated_before = (consumer / "unrelated.txt").read_bytes()
    unrelated_status_before = _git(consumer, "status", "--short", "--", "unrelated.txt")
    (consumer / "governance" / "framework.lock.json").parent.mkdir(parents=True)
    (consumer / "governance" / "framework.lock.json").write_text(
        json.dumps({"adopted_commit": old_head}, indent=2) + "\n",
        encoding="utf-8",
    )
    _git(consumer, "add", "governance/framework.lock.json")
    _git(consumer, "commit", "-m", "test: add framework lock")
    _git(consumer / "ai-governance-framework", "update-ref", "refs/remotes/origin/main", old_head)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is True
    assert result.update_mode == "fast_forward"
    assert result.fast_forward is True
    assert result.target_source == "fresh_remote_fetch_head"
    assert result.before_head == old_head
    assert result.target_head == new_head
    assert result.after_head == new_head
    assert result.full_update_stage_report["framework_pointer"] == "updated"
    assert result.full_update_stage_report["repo_local_instruction"] == "updated"
    assert result.full_update_stage_report["memory_writer_coverage"] == "verified"
    assert result.full_update_stage_report["hook_validator_enforcement"] == "updated"
    # The lock is staged but intentionally not committed by this test, so the
    # maturity summary correctly keeps the overall F-7 state partial.
    assert result.full_update_stage_report["final_status"] == "partially_updated"
    assert result.full_update_stage_report["governance_maturity_summary"]["report_only"] is True
    payload = asdict(result)
    assert payload["final_report_table_required"]["status"] == "required"
    assert payload["final_report_table_required"]["must_relay_as"] == "table_rows_verbatim"
    assert "[human_readable_adoption_summary]" in (
        payload["final_report_table_required"]["table_rows"]
    )
    assert payload["ai_governance_update_result"]["framework_update_status"] == {
        "value": "updated",
        "source": "updater",
    }
    assert payload["ai_governance_update_result"]["operation_execution"] == {
        "status": "passed",
        "mode": "apply",
        "framework_update_applied": True,
        "meaning": "apply completed and updated the framework checkout",
    }
    assert (
        payload["ai_governance_update_result"]["lock_consistency"]["value"]
        == payload["full_update_stage_report"]["governance_maturity_summary"][
            "lock_consistency"
        ]["value"]
    )
    rendered = format_human(result)
    assert "full_update_stage_report:" in rendered
    assert "[ai_governance_update_result]" in rendered
    assert "framework_update_status=updated" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "AI Governance 功能導入狀態：" in rendered
    assert "| 功能 | 狀態 | 這個功能是做什麼 |" in rendered
    assert "update_receipt_status=written" in rendered
    assert "update_receipt_path=governance/.update-receipt.json" in rendered
    assert result.staged_files == [
        ".gitignore",
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
        "governance/.update-receipt.json",
        "governance/framework.lock.json",
    ]
    assert _git(consumer, "diff", "--cached", "--name-only").splitlines() == [
        ".gitignore",
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
        "governance/.update-receipt.json",
        "governance/framework.lock.json",
    ]
    receipt = json.loads((consumer / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert result.update_receipt["status"] == "written"
    assert result.update_receipt["staged"] is True
    assert receipt["receipt_type"] == "ai_governance_update"
    assert receipt["tool"] == "external_governance_submodule_updater"
    assert receipt["framework_before"] == old_head
    assert receipt["framework_after"] == new_head
    assert receipt["update_status"] == "updated"
    assert receipt["lock_adopted_commit"] == new_head
    assert receipt["lock_matches_checkout"] is True
    lock = json.loads(
        (consumer / "governance" / "framework.lock.json").read_text(encoding="utf-8")
    )
    assert lock["adopted_commit"] == new_head
    assert lock["updated_at"]
    assert "full governance adoption" in receipt["not_claimed"]
    assert "F-7 Full Update Semantics" in (consumer / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "governance:key=memory_workflow" in (consumer / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "MEMORY_WORKFLOW_TOOL" in (
        consumer / ".git" / "hooks" / "pre-commit"
    ).read_text(encoding="utf-8")
    assert (consumer / "unrelated.txt").read_bytes() == unrelated_before
    assert _git(consumer, "status", "--short", "--", "unrelated.txt") == (
        unrelated_status_before
    )


def test_apply_blocks_non_allowlisted_dirty_content_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    product = consumer / "Source" / "product.cpp"
    product.parent.mkdir()
    product.write_text("user work\n", encoding="utf-8")
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_mutate_product(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        product.write_text("unexpected updater mutation\n", encoding="utf-8")
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_mutate_product,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        for error in result.errors
    )
    assert any("Source/product.cpp" in error for error in result.errors)
    assert result.update_receipt["status"] == "written"
    assert (consumer / RECEIPT_RELATIVE_PATH).exists()
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "failed",
        "mode": "apply",
        "framework_update_applied": True,
        "meaning": (
            "apply failed after framework and governance mutations were observed; "
            "inspect and reconcile the working tree"
        ),
    }


def test_apply_allows_unchanged_untracked_artifact_to_become_ignored(
    tmp_path: Path,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    artifact = consumer / "artifacts" / "runtime" / "existing.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"state":"user-owned"}\n', encoding="utf-8")
    before = artifact.read_bytes()
    assert _git(consumer, "status", "--short", "--", artifact) == (
        "?? artifacts/runtime/existing.json"
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is True
    assert result.after_head == new_head
    assert artifact.read_bytes() == before
    assert _git(consumer, "check-ignore", "artifacts/runtime/existing.json") == (
        "artifacts/runtime/existing.json"
    )


def test_apply_blocks_content_mutation_after_untracked_artifact_becomes_ignored(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    artifact = consumer / "artifacts" / "runtime" / "existing.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"state":"user-owned"}\n', encoding="utf-8")
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_mutate_artifact(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        artifact.write_text('{"state":"mutated"}\n', encoding="utf-8")
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_mutate_artifact,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "artifacts/runtime/existing.json" in error
        for error in result.errors
    )


def test_apply_blocks_deletion_after_untracked_artifact_becomes_ignored(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    artifact = consumer / "artifacts" / "runtime" / "existing.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"state":"user-owned"}\n', encoding="utf-8")
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_delete_artifact(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        artifact.unlink()
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_delete_artifact,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "artifacts/runtime/existing.json" in error
        for error in result.errors
    )


def test_apply_blocks_new_non_allowlisted_dirty_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    product = consumer / "Source" / "new-product.cpp"
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_create_product(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        product.parent.mkdir(parents=True)
        product.write_text("unexpected updater output\n", encoding="utf-8")
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_create_product,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "Source/new-product.cpp" in error
        for error in result.errors
    )


def test_apply_blocks_new_path_ignored_by_managed_hygiene(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    artifact = consumer / "artifacts" / "runtime" / "late-created.json"
    original_ensure_gitignore_hygiene = updater_module._ensure_gitignore_hygiene

    def ensure_hygiene_then_create_ignored_artifact(repo: Path):
        report = original_ensure_gitignore_hygiene(repo)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text('{"state":"unexpected"}\n', encoding="utf-8")
        return report

    monkeypatch.setattr(
        updater_module,
        "_ensure_gitignore_hygiene",
        ensure_hygiene_then_create_ignored_artifact,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert artifact.exists()
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "artifacts/runtime/late-created.json" in error
        for error in result.errors
    )


def test_apply_blocks_ignore_transition_from_git_info_exclude(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    product = consumer / "Source" / "product.cpp"
    product.parent.mkdir(parents=True)
    product.write_text("user work\n", encoding="utf-8")
    before = product.read_bytes()
    exclude = consumer / ".git" / "info" / "exclude"
    original_ensure_gitignore_hygiene = updater_module._ensure_gitignore_hygiene

    def ensure_hygiene_then_change_exclude(repo: Path):
        report = original_ensure_gitignore_hygiene(repo)
        existing = exclude.read_text(encoding="utf-8")
        exclude.write_text(existing + "\n/Source/product.cpp\n", encoding="utf-8")
        return report

    monkeypatch.setattr(
        updater_module,
        "_ensure_gitignore_hygiene",
        ensure_hygiene_then_change_exclude,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert product.read_bytes() == before
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "Source/product.cpp" in error
        for error in result.errors
    )


def test_apply_blocks_untracked_path_becoming_staged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    product = consumer / "Source" / "product.cpp"
    product.parent.mkdir(parents=True)
    product.write_text("user work\n", encoding="utf-8")
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_stage_product(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        _git(consumer, "add", "Source/product.cpp")
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_stage_product,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "Source/product.cpp" in error
        for error in result.errors
    )


def test_managed_gitignore_matches_treats_not_ignored_as_empty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    updater_module._ensure_gitignore_hygiene(repo)

    assert updater_module._managed_gitignore_matches(
        repo,
        ["Source/product.cpp"],
    ) == frozenset()


def test_managed_gitignore_matches_fails_closed_on_git_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    updater_module._ensure_gitignore_hygiene(repo)

    monkeypatch.setattr(
        updater_module,
        "_run_git",
        lambda *_args, **_kwargs: updater_module.CommandResult(
            command=["git", "check-ignore"],
            returncode=2,
            stdout="",
            stderr="simulated check-ignore failure",
        ),
    )

    with pytest.raises(
        updater_module.SubmoduleUpdateError,
        match="cannot inspect ignore authority",
    ):
        updater_module._managed_gitignore_matches(repo, ["artifacts/runtime/x.json"])


@pytest.mark.parametrize(
    "malformed_stdout",
    [
        ".gitignore\0not-four-fields\0",
        ".gitignore\01\0artifacts/runtime/\0artifacts/runtime/x.json",
    ],
)
def test_managed_gitignore_matches_fails_closed_on_malformed_nul_output(
    tmp_path: Path,
    monkeypatch,
    malformed_stdout: str,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    updater_module._ensure_gitignore_hygiene(repo)

    monkeypatch.setattr(
        updater_module,
        "_run_git",
        lambda *_args, **_kwargs: updater_module.CommandResult(
            command=["git", "check-ignore"],
            returncode=0,
            stdout=malformed_stdout,
            stderr="",
        ),
    )

    with pytest.raises(
        updater_module.SubmoduleUpdateError,
        match="NUL-delimited",
    ):
        updater_module._managed_gitignore_matches(repo, ["artifacts/runtime/x.json"])


def test_apply_blocks_new_ignored_path_with_leading_space(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    (consumer / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    _git(consumer, "add", ".gitignore")
    _git(consumer, "commit", "-m", "test: add user pyc ignore")
    (consumer / "x.pyc").write_bytes(b"existing ignored\n")
    late_path = consumer / " x.pyc"
    original_ensure_gitignore_hygiene = updater_module._ensure_gitignore_hygiene

    def ensure_hygiene_then_create_leading_space_path(repo: Path):
        report = original_ensure_gitignore_hygiene(repo)
        late_path.write_bytes(b"late ignored\n")
        return report

    monkeypatch.setattr(
        updater_module,
        "_ensure_gitignore_hygiene",
        ensure_hygiene_then_create_leading_space_path,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert late_path.exists()
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and " x.pyc" in error
        for error in result.errors
    )


def test_apply_allows_initial_leading_space_path_to_become_ignored(
    tmp_path: Path,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    artifact = consumer / " x.pyc"
    artifact.write_bytes(b"initial user artifact\n")
    before = artifact.read_bytes()

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is True
    assert result.after_head == new_head
    assert artifact.read_bytes() == before
    assert _git(consumer, "check-ignore", "--quiet", "--", " x.pyc") == ""


def test_apply_blocks_transition_when_managed_gitignore_block_is_corrupted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    artifact = consumer / "x.pyc"
    artifact.write_bytes(b"initial user artifact\n")
    original_ensure_gitignore_hygiene = updater_module._ensure_gitignore_hygiene

    def ensure_hygiene_then_corrupt_managed_block(repo: Path):
        report = original_ensure_gitignore_hygiene(repo)
        gitignore = repo / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        gitignore.write_text(
            text.replace(
                "# <<< ai-governance hygiene (managed) <<<",
                "BROKEN-EXTRA-LINE\n# <<< ai-governance hygiene (managed) <<<",
            ),
            encoding="utf-8",
        )
        return report

    monkeypatch.setattr(
        updater_module,
        "_ensure_gitignore_hygiene",
        ensure_hygiene_then_corrupt_managed_block,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "x.pyc" in error
        for error in result.errors
    )


def test_post_commit_boundary_failure_reports_commit_and_applied_pointer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    product = consumer / "Source" / "product.cpp"
    product.parent.mkdir()
    product.write_text("user work\n", encoding="utf-8")
    original_run_git = updater_module._run_git

    def run_git_then_mutate_after_commit(repo, args, *positional, **kwargs):
        result = original_run_git(repo, args, *positional, **kwargs)
        if Path(repo).resolve() == consumer.resolve() and args[:2] == ["commit", "-m"]:
            product.write_text("unexpected post-commit mutation\n", encoding="utf-8")
        return result

    monkeypatch.setattr(updater_module, "_run_git", run_git_then_mutate_after_commit)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
        commit=True,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert result.committed is True
    assert result.commit_hash == _git(consumer, "rev-parse", "HEAD")
    assert result.update_receipt["status"] == "written"
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        for error in result.errors
    )
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "failed",
        "mode": "apply",
        "framework_update_applied": True,
        "meaning": (
            "apply failed after framework and governance mutations were observed; "
            "inspect and reconcile the working tree"
        ),
    }


def test_apply_blocks_dirty_sibling_submodule_content_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    sibling_origin = tmp_path / "sibling-product-origin"
    _init_repo(sibling_origin)
    (sibling_origin / "README.md").write_text("sibling product\n", encoding="utf-8")
    _commit_all(sibling_origin, "test: add sibling product")
    _git(
        consumer,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(sibling_origin),
        "sibling-product",
    )
    _commit_all(consumer, "test: add sibling product submodule")
    sibling_artifact = consumer / "sibling-product" / "runtime.db"
    sibling_artifact.write_text("user sibling work\n", encoding="utf-8")
    assert "sibling-product" in _git(consumer, "status", "--short")
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_mutate_sibling(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        sibling_artifact.write_text(
            "unexpected sibling mutation\n",
            encoding="utf-8",
        )
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_mutate_sibling,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "sibling-product" in error
        for error in result.errors
    )
    assert result.ai_governance_update_result["operation_execution"][
        "framework_update_applied"
    ] is True


def test_apply_blocks_leading_space_sibling_submodule_content_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    sibling_origin = tmp_path / "sibling-product-origin"
    _init_repo(sibling_origin)
    (sibling_origin / "README.md").write_text("sibling product\n", encoding="utf-8")
    _commit_all(sibling_origin, "test: add sibling product")
    _git(
        consumer,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(sibling_origin),
        "sibling-product",
    )
    _commit_all(consumer, "test: add sibling product submodule")
    sibling_artifact = consumer / "sibling-product" / " runtime.db"
    sibling_artifact.write_text("user sibling work\n", encoding="utf-8")
    assert "sibling-product" in _git(consumer, "status", "--short")
    original_write_update_receipt = updater_module.write_update_receipt

    def write_receipt_then_mutate_sibling(*args, **kwargs):
        receipt = original_write_update_receipt(*args, **kwargs)
        sibling_artifact.write_text(
            "unexpected sibling mutation\n",
            encoding="utf-8",
        )
        return receipt

    monkeypatch.setattr(
        updater_module,
        "write_update_receipt",
        write_receipt_then_mutate_sibling,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.after_head == new_head
    assert any(
        "parent dirty snapshot changed outside the F-7 apply allowlist" in error
        and "sibling-product" in error
        for error in result.errors
    )
    assert result.ai_governance_update_result["operation_execution"][
        "framework_update_applied"
    ] is True


def test_apply_blocks_preexisting_dirty_governance_overlap_before_mutation(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    agents = consumer / "AGENTS.md"
    agents.write_text("# unknown local governance work\n", encoding="utf-8")
    before = agents.read_bytes()

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert "pre-existing dirty files overlapping" in result.errors[0]
    assert "AGENTS.md" in result.errors[0]
    assert agents.read_bytes() == before
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert not (consumer / RECEIPT_RELATIVE_PATH).exists()


def test_apply_blocks_preexisting_unmanaged_hook_before_mutation(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    hook = consumer / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/usr/bin/env bash\necho user hook\n", encoding="utf-8")
    before = hook.read_bytes()

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert ".git/hooks/pre-commit" in result.errors[0]
    assert hook.read_bytes() == before
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert not (consumer / RECEIPT_RELATIVE_PATH).exists()
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "failed",
        "mode": "apply",
        "framework_update_applied": False,
        "meaning": (
            "apply did not complete; inspect the working tree before retrying"
        ),
    }


def test_apply_allows_pinned_managed_hooks_to_upgrade(tmp_path: Path) -> None:
    consumer, _framework, _old_head, new_head = _make_fixture(tmp_path)
    nested = (consumer / "ai-governance-framework").resolve()
    hook_dir = consumer / ".git" / "hooks"
    for hook_name in ("pre-commit", "pre-push"):
        (hook_dir / hook_name).write_bytes(
            (nested / "scripts" / "hooks" / hook_name).read_bytes()
        )
    (hook_dir / "ai-governance-framework-root").write_text(
        f"{nested}\n",
        encoding="utf-8",
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is True
    assert result.after_head == new_head
    for hook_name in ("pre-commit", "pre-push"):
        assert (hook_dir / hook_name).read_bytes() == (
            nested / "scripts" / "hooks" / hook_name
        ).read_bytes()


def test_linked_worktree_blocks_unknown_common_hook_before_mutation(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    linked = tmp_path / "linked-consumer"
    _git(consumer, "worktree", "add", "-b", "linked-boundary-test", str(linked))
    _git(
        linked,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "update",
        "--init",
        "ai-governance-framework",
    )
    common_hook = consumer / ".git" / "hooks" / "pre-push"
    common_hook.write_text("#!/usr/bin/env bash\necho shared user hook\n", encoding="utf-8")
    before = common_hook.read_bytes()

    result = update_governance_submodule(
        repo=linked,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert ".git/hooks/pre-push" in result.errors[0]
    assert common_hook.read_bytes() == before
    assert _git(linked / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert not (linked / RECEIPT_RELATIVE_PATH).exists()


def test_linked_worktree_apply_blocks_shared_hook_config_authority(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    linked = tmp_path / "linked-consumer"
    _git(consumer, "worktree", "add", "-b", "linked-authority-test", str(linked))
    _git(
        linked,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "update",
        "--init",
        "ai-governance-framework",
    )

    result = update_governance_submodule(
        repo=linked,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert "linked worktree is blocked" in result.errors[0]
    assert "cross-worktree config drift" in result.errors[0]
    assert _git(linked / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert not (linked / RECEIPT_RELATIVE_PATH).exists()


def test_post_pointer_permission_error_returns_failure_envelope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)

    def deny_instruction_refresh(*_args, **_kwargs):
        raise PermissionError("simulated permission denial")

    monkeypatch.setattr(
        updater_module,
        "_refresh_repo_local_instructions",
        deny_instruction_refresh,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.before_head == old_head
    assert result.after_head == new_head
    assert result.update_receipt["status"] == "not_written"
    assert result.committed is False
    assert any(
        "PermissionError: simulated permission denial" in error
        for error in result.errors
    )
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "failed",
        "mode": "apply",
        "framework_update_applied": True,
        "meaning": (
            "apply failed after the framework checkout changed; inspect and reconcile "
            "the working tree"
        ),
    }


def test_repeated_post_pointer_boundary_permission_error_returns_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)

    def deny_boundary_recheck(*_args, **_kwargs):
        raise PermissionError("simulated boundary permission denial")

    monkeypatch.setattr(
        updater_module,
        "_verify_parent_dirty_snapshot_unchanged",
        deny_boundary_recheck,
    )

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert result.before_head == old_head
    assert result.after_head == new_head
    assert result.update_receipt["status"] == "written"
    assert result.committed is False
    assert result.errors == [
        "PermissionError: simulated boundary permission denial"
    ]
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "failed",
        "mode": "apply",
        "framework_update_applied": True,
        "meaning": (
            "apply failed after framework and governance mutations were observed; "
            "inspect and reconcile the working tree"
        ),
    }


def test_apply_blocks_broken_hook_symlink_before_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    hook = consumer / ".git" / "hooks" / "pre-commit"
    original_lstat = Path.lstat

    def report_broken_symlink(path: Path):
        if path == hook:
            return SimpleNamespace(st_mode=0o120777)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", report_broken_symlink)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert ".git/hooks/pre-commit" in result.errors[0]
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert not (consumer / RECEIPT_RELATIVE_PATH).exists()


def test_apply_blocks_matching_hook_symlink_before_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    nested = (consumer / "ai-governance-framework").resolve()
    hook = consumer / ".git" / "hooks" / "pre-push"
    hook.write_bytes((nested / "scripts" / "hooks" / "pre-push").read_bytes())
    before = hook.read_bytes()
    original_lstat = Path.lstat

    def report_matching_symlink(path: Path):
        if path == hook:
            return SimpleNamespace(st_mode=0o120777)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", report_matching_symlink)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=False,
    )

    assert result.ok is False
    assert ".git/hooks/pre-push" in result.errors[0]
    assert hook.read_bytes() == before
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert not (consumer / RECEIPT_RELATIVE_PATH).exists()


def test_submodule_apply_allowlist_is_fixed_and_includes_managed_hooks() -> None:
    allowlist = _submodule_apply_mutation_allowlist("vendor/governance")

    assert allowlist == frozenset(
        {
            *SUBMODULE_APPLY_MUTATION_ALLOWLIST,
            "vendor/governance",
        }
    )
    assert {
        ".git/hooks/ai-governance-framework-root",
        ".git/hooks/pre-commit",
        ".git/hooks/pre-push",
    } <= allowlist


def test_apply_does_not_complete_when_hook_advisory_source_missing(tmp_path: Path) -> None:
    consumer, framework, _old_head, _new_head = _make_fixture(tmp_path)
    (framework / "scripts" / "hooks" / "pre-commit").unlink()
    missing_hook_head = _commit_all(framework, "framework without memory hook")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is True
    assert result.target_head == missing_hook_head
    assert result.full_update_stage_report["memory_writer_coverage"] == "verified"
    assert result.full_update_stage_report["hook_validator_enforcement"] == "missing"
    assert result.full_update_stage_report["final_status"] == "partially_updated"
    assert (
        "missing source hook"
        in result.full_update_stage_report["details"]["hook_validator_enforcement"][
            "errors"
        ][0]
    )


def test_apply_commit_recomputes_lock_consistency_after_commit(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    lock_path = consumer / "governance" / "framework.lock.json"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(
        json.dumps({"adopted_commit": old_head}, indent=2) + "\n",
        encoding="utf-8",
    )
    _commit_all(consumer, "add consumer lock")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
        commit=True,
    )

    assert result.ok is True
    assert result.committed is True
    assert result.full_update_stage_report["final_status"] == "full_update_completed"
    assert (
        result.full_update_stage_report["governance_maturity_summary"]["lock_consistency"][
            "value"
        ]
        == "consistent"
    )
    assert json.loads(lock_path.read_text(encoding="utf-8"))["adopted_commit"] == new_head
    assert _git(consumer, "status", "--short") == ""


def test_invalid_existing_lock_remains_partial_and_receipt_does_not_claim_match(
    tmp_path: Path,
) -> None:
    consumer, _framework, _old_head, _new_head = _make_fixture(tmp_path)
    lock_path = consumer / "governance" / "framework.lock.json"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("not valid json\n", encoding="utf-8")
    _commit_all(consumer, "add invalid consumer lock")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    receipt = json.loads((consumer / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert result.ok is True
    assert result.full_update_stage_report["final_status"] == "partially_updated"
    assert result.full_update_stage_report["details"]["framework_lock"]["status"] == "invalid"
    assert receipt["lock_adopted_commit"] is None
    assert receipt["lock_matches_checkout"] is False
    assert lock_path.read_text(encoding="utf-8") == "not valid json\n"


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
    assert result.ai_governance_update_result["operation_execution"] == {
        "status": "passed",
        "mode": "apply",
        "framework_update_applied": False,
        "meaning": "apply completed; the framework checkout was already current",
    }
    assert result.before_head == target_head
    assert result.target_head == target_head
    assert result.after_head == target_head
    assert result.full_update_stage_report["framework_pointer"] == "already_current"
    assert result.full_update_stage_report["repo_local_instruction"] == "updated"
    assert result.full_update_stage_report["memory_writer_coverage"] == "verified"
    assert result.full_update_stage_report["hook_validator_enforcement"] == "updated"
    assert result.full_update_stage_report["final_status"] == "full_update_completed"
    assert result.full_update_stage_report["governance_maturity_summary"]["report_only"] is True
    rendered = format_human(result)
    assert "full_update_stage_report:" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "AI Governance 功能導入狀態：" in rendered
    assert "| 功能 | 狀態 | 這個功能是做什麼 |" in rendered
    assert result.staged_files == [
        ".gitignore",
        "AGENTS.base.md",
        "AGENTS.md",
        "governance/.update-receipt.json",
    ]
    receipt = json.loads((consumer / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert result.update_receipt["status"] == "written"
    assert result.update_receipt["staged"] is True
    assert receipt["framework_before"] == target_head
    assert receipt["framework_after"] == target_head
    assert receipt["update_status"] == "already_current"
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


def test_apply_refuses_preexisting_staged_files_before_mutation_and_reports_summary(
    tmp_path: Path,
) -> None:
    consumer, _framework, old_head, _new_head = _make_fixture(tmp_path)
    (consumer / "unrelated.txt").write_text("staged user work\n", encoding="utf-8")
    _git(consumer, "add", "unrelated.txt")

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is False
    assert result.mode == "apply"
    assert result.update_mode == "failed"
    assert result.full_update_stage_report["final_status"] == "blocked"
    assert result.full_update_stage_report["governance_maturity_summary"][
        "report_only"
    ] is True
    assert "pre-existing staged files" in result.errors[0]
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == old_head
    assert _git(consumer, "diff", "--cached", "--name-only") == "unrelated.txt"


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
    consumer, _framework, side_head, target_head = _make_divergent_fixture(tmp_path)

    result = update_governance_submodule(
        repo=consumer,
        fetch_ref="main",
        dry_run=False,
        stage=True,
    )

    assert result.ok is False
    assert result.update_mode == "failed"
    assert result.fast_forward is None
    assert result.target_head == target_head
    assert result.target_source == "fresh_remote_fetch_head"
    assert result.full_update_stage_report["details"]["target_resolution"]["target_source"] == (
        "fresh_remote_fetch_head"
    )
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
    assert result.full_update_stage_report["memory_writer_coverage"] == "verified"
    assert result.full_update_stage_report["hook_validator_enforcement"] == "updated"
    assert result.staged_files == [
        ".gitignore",
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
        "governance/.update-receipt.json",
    ]
    receipt = json.loads((consumer / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert receipt["framework_before"] == side_head
    assert receipt["framework_after"] == target_head
    assert result.update_receipt["staged"] is True
    assert _git(consumer / "ai-governance-framework", "rev-parse", "HEAD") == target_head
    assert _git(consumer, "diff", "--cached", "--name-only").splitlines() == [
        ".gitignore",
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
        "governance/.update-receipt.json",
    ]
