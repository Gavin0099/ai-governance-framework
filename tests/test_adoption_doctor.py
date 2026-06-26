from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools import adoption_doctor
from governance_tools.adoption_doctor import format_human, inspect_adoption, main


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_git(args: list[str], cwd: Path) -> str:
    cwd.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip()


def _make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir(parents=True)
    _run_git(["init"], repo)
    _run_git(["config", "user.email", "test@example.com"], repo)
    _run_git(["config", "user.name", "Test User"], repo)
    _write(repo / ".governance" / "baseline.yaml", "schema_version: '1'\n")
    _write(repo / "contract.yaml", "name: test\n")
    return repo


def _make_framework_root(path: Path) -> Path:
    _write(path / "governance_tools" / "__init__.py", "")
    _write(path / "runtime_hooks" / "__init__.py", "")
    _write(path / "governance" / "runtime_injection_snapshot.v0.yaml", "version: 0\n")
    return path


def _make_git_framework(path: Path) -> Path:
    _make_framework_root(path)
    _run_git(["init"], path)
    _run_git(["config", "user.email", "test@example.com"], path)
    _run_git(["config", "user.name", "Test User"], path)
    _run_git(["checkout", "-b", "main"], path)
    _run_git(["add", "."], path)
    _run_git(["commit", "-m", "framework A"], path)
    return path


def _make_git_framework_with_remote(path: Path, remote: Path, *, behind: bool) -> tuple[Path, str]:
    _make_git_framework(path)
    first_commit = _run_git(["rev-parse", "HEAD"], path)
    _run_git(["init", "--bare"], remote)
    _run_git(["remote", "add", "origin", str(remote.resolve())], path)
    _run_git(["push", "-u", "origin", "main"], path)
    if behind:
        _write(path / "SECOND.txt", "second\n")
        _run_git(["add", "SECOND.txt"], path)
        _run_git(["commit", "-m", "framework B"], path)
        _run_git(["push", "origin", "main"], path)
        _run_git(["fetch", "origin", "main"], path)
        _run_git(["checkout", first_commit], path)
    return path, first_commit


def _write_gitmodules(repo: Path, relpath: str) -> None:
    _write(
        repo / ".gitmodules",
        "[submodule \"ai-governance-framework\"]\n"
        f"\tpath = {relpath}\n"
        "\turl = https://example.invalid/ai-governance-framework.git\n",
    )


def test_copy_based_repo_with_external_framework_root_reports_audit_only(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "copy")
    external_framework = _make_framework_root(tmp_path / "external-framework")

    report = inspect_adoption(repo, framework_root=external_framework)

    assert report.adoption_class.value == "copy_based"
    assert report.self_contained.value == "no"
    assert report.runtime_capable.value == "not_checked"
    assert report.external_framework_dependency.value == "observed"
    assert report.submodule_pin.value == "not_applicable"
    assert any(f.code == "copy_based_audit_surface" for f in report.findings)
    assert any(f.code == "external_framework_dependency" for f in report.findings)


def test_repo_owned_framework_path_without_submodule_proof_is_not_submodule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo_owned")
    framework = _make_framework_root(repo / "additional" / "ai-governance-framework")

    report = inspect_adoption(repo, framework_root=framework)

    assert report.adoption_class.value == "repo_owned_framework_path"
    assert report.framework_submodule.value == "not_applicable"
    assert report.self_contained.value == "yes"
    assert report.runtime_capable.value == "not_checked"
    assert "runtime smoke passed" in " ".join(report.self_contained.reasons)


def test_submodule_consumer_with_initialized_framework_checkout(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "submodule")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework(repo / relpath)

    report = inspect_adoption(repo)

    assert report.adoption_class.value == "submodule_consumer"
    assert report.framework_submodule.value == "initialized"
    assert report.self_contained.value == "yes"
    assert report.runtime_capable.value == "not_checked"


def test_external_hook_config_is_reported_with_repo_owned_submodule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "external_hook")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework(repo / relpath)
    external_framework = _make_framework_root(tmp_path / "external-framework")
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(external_framework.resolve()))

    report = inspect_adoption(repo)
    rendered = format_human(report)
    payload = json.loads(adoption_doctor.format_json(report))

    assert report.adoption_class.value == "submodule_consumer"
    assert report.self_contained.value == "yes"
    assert report.hook_config_framework_root.value == "external"
    assert payload["hook_config_framework_root"]["value"] == "external"
    assert "[hook_config_framework_root]" in rendered
    assert any(f.code == "external_hook_framework_root" for f in report.findings)


def test_partial_or_uninitialized_submodule_is_reported_without_self_contained_claim(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "partial")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _write(repo / relpath / "README.md", "partial checkout\n")

    report = inspect_adoption(repo)

    assert report.adoption_class.value == "unknown"
    assert report.framework_submodule.value == "partial_or_uninitialized"
    assert report.self_contained.value == "no"
    assert report.submodule_pin.value == "unknown"
    assert any(f.code == "submodule_not_initialized" for f in report.findings)
    assert any(f.code == "pin_status_unknown" for f in report.findings)


def test_root_level_leftover_runtime_hooks_is_warning_for_consumer_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "leftover")
    framework = _make_framework_root(repo / "additional" / "ai-governance-framework")
    _write(repo / "runtime_hooks" / "core.py", "# leftover\n")

    report = inspect_adoption(repo, framework_root=framework)

    assert report.root_level_leftover_runtime_hooks.value == "present"
    assert any(f.code == "root_level_runtime_hooks" for f in report.findings)


def test_stale_pin_uses_local_tracking_and_remains_report_only(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "stale")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework_with_remote(repo / relpath, tmp_path / "framework.git", behind=True)

    report = inspect_adoption(repo)

    assert report.submodule_pin.value == "behind_local_tracking"
    assert report.submodule_pin.remote_tracking_ref == "origin/main"
    assert report.submodule_pin.remote_tracking_freshness in {"observed", "unknown"}
    assert any(f.code == "pin_behind_local_tracking" for f in report.findings)
    assert all(f.severity != "blocking" for f in report.findings)


def test_current_pin_is_not_rendered_as_unqualified_current(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "current")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework_with_remote(repo / relpath, tmp_path / "current-framework.git", behind=False)

    report = inspect_adoption(repo)
    rendered = format_human(report)
    payload = json.loads(adoption_doctor.format_json(report))

    assert report.submodule_pin.value == "current_vs_local_tracking"
    assert payload["submodule_pin"]["value"] == "current_vs_local_tracking"
    assert "state             = current_vs_local_tracking" in rendered
    assert "state             = current\n" not in rendered
    assert "true current remote head" in rendered


def test_doctor_does_not_fetch_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "no_fetch")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework_with_remote(repo / relpath, tmp_path / "no-fetch-framework.git", behind=True)
    real_run = adoption_doctor.subprocess.run
    commands: list[list[str]] = []

    def spy_run(command: list[str], *args: object, **kwargs: object):
        commands.append(command)
        assert "fetch" not in command
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(adoption_doctor.subprocess, "run", spy_run)

    report = inspect_adoption(repo)

    assert report.submodule_pin.value == "behind_local_tracking"
    assert not any("fetch" in command for command in commands)


def test_cli_returns_zero_when_findings_exist(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "cli")
    external_framework = _make_framework_root(tmp_path / "cli-framework")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "adoption_doctor.py",
            "--repo",
            str(repo),
            "--framework-root",
            str(external_framework),
            "--format",
            "json",
        ],
    )

    rc = main()
    output = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert output["report_only"] is True
    assert output["findings"]
    assert output["adoption_class"]["value"] == "copy_based"


def test_human_output_contains_report_only_claim_boundary(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "human")
    external_framework = _make_framework_root(tmp_path / "human-framework")

    rendered = format_human(inspect_adoption(repo, framework_root=external_framework))

    assert "report_only       = true" in rendered
    assert "does not install, update, delete, fetch, stage, rewrite, or enforce anything" in rendered
