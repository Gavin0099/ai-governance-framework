from __future__ import annotations

import json
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


def _write_framework_lock(repo: Path, adopted_commit: str) -> None:
    _write(
        repo / "governance" / "framework.lock.json",
        json.dumps({"adopted_commit": adopted_commit}, indent=2) + "\n",
    )


def _commit_path(repo: Path, relpath: str, message: str) -> None:
    _run_git(["add", relpath], repo)
    _run_git(["commit", "-m", message], repo)


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
    assert "[human_readable_adoption_summary]" in rendered
    assert "整體導入狀態：minimal" in rendered
    assert "AI Governance 功能導入狀態：" in rendered
    assert "| 功能 | 狀態 | 這個功能是做什麼 |" in rendered
    assert "AI Governance framework checkout: not full-framework-owned" in rendered
    assert "| 框架本體（Framework checkout） | 未導入 |" in rendered
    assert "| 本 repo 規則（Repo governance instructions） | 未導入 |" in rendered
    assert "| runtime 治理能力（Runtime-capable governance） | 未驗證 |" in rendered
    assert "只有明確回報已可用時才算導入" in rendered
    assert "Validator surface: 未導入" in rendered


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
    assert "Framework version freshness: behind_local_tracking" in rendered
    assert "| 版本新鮮度（Framework version freshness） | 未導入 |" in rendered


def test_lock_consistency_reports_clean_lock_matching_checkout(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "lock_consistent")
    framework = _make_git_framework(repo / "ai-governance-framework")
    framework_head = _run_git(["rev-parse", "HEAD"], framework)
    _write_framework_lock(repo, framework_head)
    _commit_path(repo, "governance/framework.lock.json", "record framework lock")

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)
    payload = summary_to_dict(summary)

    assert summary.lock_consistency.value == "consistent"
    assert "lock_file_dirty=false" in summary.lock_consistency.reasons
    assert "framework_lock_consistency" not in summary.missing_surfaces
    assert "framework lock matches the checked-out framework commit" not in summary.cannot_claim
    assert payload["lock_consistency"]["value"] == "consistent"
    assert "lock_consistency         = consistent" in rendered
    assert "Lock vs checkout consistency" in rendered


def test_lock_consistency_reports_dirty_three_layer_drift(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "lock_dirty")
    framework = _make_git_framework(repo / "ai-governance-framework")
    first_head = _run_git(["rev-parse", "HEAD"], framework)
    _write(framework / "SECOND.txt", "second\n")
    _run_git(["add", "SECOND.txt"], framework)
    _run_git(["commit", "-m", "framework B"], framework)
    framework_head = _run_git(["rev-parse", "HEAD"], framework)

    _write_framework_lock(repo, first_head)
    _commit_path(repo, "governance/framework.lock.json", "record old framework lock")
    dirty_lock_commit = "f" * 40
    _write_framework_lock(repo, dirty_lock_commit)

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)

    assert first_head != framework_head
    assert summary.lock_consistency.value == "inconsistent"
    assert "lock_file_dirty=true" in summary.lock_consistency.reasons
    assert f"lock_adopted_commit={dirty_lock_commit}" in summary.lock_consistency.reasons
    assert f"framework_head={framework_head}" in summary.lock_consistency.reasons
    assert "working-tree lock commit was not found in the local framework checkout" in summary.lock_consistency.reasons
    assert "framework_lock_consistency" in summary.missing_surfaces
    assert "framework lock matches the checked-out framework commit" in summary.cannot_claim
    assert "lock_consistency         = inconsistent" in rendered
    assert "Lock vs checkout consistency" in rendered


def test_repo_owned_framework_pin_freshness_surfaces_stale_local_tracking(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo_owned_stale")
    framework = _make_git_framework_with_remote(
        repo / "additional" / "ai-governance-framework",
        tmp_path / "repo-owned-framework.git",
        behind=True,
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)

    assert summary.framework_topology.value == "repo_owned_framework_path"
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
    rendered = format_human(summary)
    assert "| 領域合約（Domain contract） | 已可用 |" in rendered
    assert "| 自動驗證層（Validator surface） | 已可用 |" in rendered
    assert "| 記憶工作流（Memory workflow） | 未驗證 |" in rendered


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
    assert "| 框架本體（Framework checkout） | 已可用 |" in rendered
    assert "| 本 repo 規則（Repo governance instructions） | 已可用 |" in rendered
    assert "| 本機 commit/push 檢查（Git hooks） | 已可用 |" in rendered
    assert "AI Governance 在可見的靜態表面上看起來已齊備" in rendered


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
    assert "這個 repo 目前看起來尚未由 AI Governance 管理。" in rendered
