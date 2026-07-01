from __future__ import annotations

import subprocess
from pathlib import Path

from governance_tools.governance_maturity_summary import (
    build_governance_maturity_summary,
    format_human,
    summary_to_dict,
)


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


def _make_git_framework_with_remote(path: Path, remote: Path, *, behind: bool) -> Path:
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
    return path


def _write_gitmodules(repo: Path, relpath: str) -> None:
    _write(
        repo / ".gitmodules",
        "[submodule \"ai-governance-framework\"]\n"
        f"\tpath = {relpath}\n"
        "\turl = https://example.invalid/ai-governance-framework.git\n",
    )


def _write_repo_specific_agents(repo: Path) -> None:
    _write(
        repo / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "## Repo-Specific Risk Levels",
                "<!-- governance:key=risk_levels -->",
                "- HIGH: changes under src/provider_adapter.py alter provider routing",
                "",
                "## Must-Test Paths",
                "<!-- governance:key=must_test_paths -->",
                "- `python -m pytest tests/test_provider_adapter.py`",
            ]
        ),
    )


def test_copy_based_summary_is_report_only_and_does_not_claim_runtime_governance(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "copy")
    external_framework = _make_framework_root(tmp_path / "external-framework")

    summary = build_governance_maturity_summary(repo, framework_root=external_framework)
    payload = summary_to_dict(summary)
    rendered = format_human(summary)

    assert summary.report_only is True
    assert summary.user_facing_status.value == "minimal"
    assert summary.framework_topology.value == "copy_based"
    assert summary.framework_pin_freshness.value == "not_applicable"
    assert summary.claim_ceiling.value == "governance_assisted"
    assert "runtime_self_contained_governance" in summary.missing_surfaces
    assert "runtime self-contained governance" in summary.cannot_claim
    assert payload["report_only"] is True
    assert payload["user_facing_status"]["value"] == "minimal"
    assert "claim_boundary" in rendered
    assert "user_facing_status       = minimal" in rendered
    assert "Basic governance guidance is present" in rendered


def test_framework_pin_freshness_surfaces_stale_local_tracking_without_fetch(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "stale")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework_with_remote(repo / relpath, tmp_path / "framework.git", behind=True)

    summary = build_governance_maturity_summary(repo)
    rendered = format_human(summary)

    assert summary.framework_topology.value == "submodule_consumer"
    assert summary.framework_pin_freshness.value == "behind_local_tracking"
    assert "framework_pin_freshness" in summary.missing_surfaces
    assert "framework pin freshness" in summary.cannot_claim
    assert "framework_pin_freshness  = behind_local_tracking" in rendered


def test_repo_specific_rules_domain_contract_and_validator_surface_are_derived(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "domain")
    framework = _make_framework_root(repo / "additional" / "ai-governance-framework")
    _write_repo_specific_agents(repo)
    _write(repo / "validators" / "check_contract.py", "print('ok')\n")
    _write(
        repo / "contract.yaml",
        "\n".join(
            [
                "name: domain-test",
                "validators:",
                "  - validators/check_contract.py",
            ]
        )
        + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.user_facing_status.value == "partial"
    assert summary.framework_topology.value == "repo_owned_framework_path"
    assert summary.repo_specific_rules_present.value is True
    assert summary.agents_calibration.value == "repo_specific_minimal"
    assert summary.domain_contract_present.value is True
    assert summary.validator_surface_present.value is True
    assert summary.memory_workflow_surface.value == "not_checked"
    assert "repo_specific_agents_rules" not in summary.missing_surfaces
    assert "Some governance surfaces are present" in " ".join(summary.user_facing_status.reasons)


def test_external_hook_root_is_reported_as_signal_conflict_not_blocker(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "external_hook")
    relpath = "additional/ai-governance-framework"
    _write_gitmodules(repo, relpath)
    _make_git_framework(repo / relpath)
    external_framework = _make_framework_root(tmp_path / "external-framework")
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(external_framework.resolve()))

    summary = build_governance_maturity_summary(repo)

    assert summary.user_facing_status.value == "partial"
    assert summary.framework_topology.value == "submodule_consumer"
    assert summary.hook_config_framework_root.value == "external"
    assert "repo_owned_hook_execution" in summary.missing_surfaces
    assert summary.signal_conflicts
    assert summary.signal_conflicts[0].field == "hooks"
    assert summary.signal_conflicts[0].action == "manual_review_required"
    assert "Some governance signals conflict" in " ".join(summary.user_facing_status.reasons)


def test_full_candidate_status_is_visible_but_not_runtime_claim(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "full_candidate")
    relpath = "additional/ai-governance-framework"
    framework = _make_git_framework_with_remote(repo / relpath, tmp_path / "framework-current.git", behind=False)
    _write_gitmodules(repo, relpath)
    _write_repo_specific_agents(repo)
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(framework.resolve()))
    _write(repo / "validators" / "check_contract.py", "print('ok')\n")
    _write(
        repo / "contract.yaml",
        "\n".join(
            [
                "name: full-candidate-test",
                "validators:",
                "  - validators/check_contract.py",
            ]
        )
        + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)

    assert summary.user_facing_status.value == "full_candidate"
    assert "runtime enforcement and semantic correctness are not proven" in " ".join(
        summary.user_facing_status.reasons
    )
    assert "runtime self-contained governance" in summary.cannot_claim
    assert "user_facing_status       = full_candidate" in rendered


def test_unknown_adoption_without_repo_rules_is_user_facing_not_governed(tmp_path: Path) -> None:
    repo = tmp_path / "not_governed" / "repo"
    repo.mkdir(parents=True)
    _run_git(["init"], repo)
    _run_git(["config", "user.email", "test@example.com"], repo)
    _run_git(["config", "user.name", "Test User"], repo)

    summary = build_governance_maturity_summary(repo)
    rendered = format_human(summary)

    assert summary.framework_topology.value == "unknown"
    assert summary.user_facing_status.value == "not_governed"
    assert "No repo-specific governance surfaces were detected" in " ".join(
        summary.user_facing_status.reasons
    )
    assert "user_facing_status       = not_governed" in rendered
