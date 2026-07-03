from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from governance_tools.external_governance_submodule_updater import (
    UpdateResult,
    _build_full_update_stage_report,
    _check_existing_memory_normalization,
    _git_env,
    _run_git,
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
    rendered = format_human(result)
    assert "full_update_stage_report:" in rendered
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


def test_apply_stage_updates_only_submodule_pointer(tmp_path: Path) -> None:
    consumer, _framework, old_head, new_head = _make_fixture(tmp_path)
    (consumer / "unrelated.txt").write_text("dirty\n", encoding="utf-8")
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
    assert result.full_update_stage_report["final_status"] == "full_update_completed"
    assert result.full_update_stage_report["governance_maturity_summary"]["report_only"] is True
    payload = asdict(result)
    assert payload["final_report_table_required"]["status"] == "required"
    assert payload["final_report_table_required"]["must_relay_as"] == "table_rows_verbatim"
    assert "[human_readable_adoption_summary]" in (
        payload["final_report_table_required"]["table_rows"]
    )
    rendered = format_human(result)
    assert "full_update_stage_report:" in rendered
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
    ]
    assert _git(consumer, "diff", "--cached", "--name-only").splitlines() == [
        ".gitignore",
        "AGENTS.base.md",
        "AGENTS.md",
        "ai-governance-framework",
        "governance/.update-receipt.json",
    ]
    receipt = json.loads((consumer / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert result.update_receipt["status"] == "written"
    assert result.update_receipt["staged"] is True
    assert receipt["receipt_type"] == "ai_governance_update"
    assert receipt["tool"] == "external_governance_submodule_updater"
    assert receipt["framework_before"] == old_head
    assert receipt["framework_after"] == new_head
    assert receipt["update_status"] == "updated"
    assert receipt["lock_adopted_commit"] is None
    assert receipt["lock_matches_checkout"] is False
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
    assert "?? unrelated.txt" in _git(consumer, "status", "--short")


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
