from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from pathlib import Path

from governance_tools.external_repo_readiness import ExternalRepoReadiness
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


def _make_hook_valid_framework_root(path: Path) -> Path:
    _make_framework_root(path)
    _write(path / "scripts" / "lib" / "python.sh", "#!/usr/bin/env bash\n")
    _write(path / "scripts" / "run-runtime-governance.sh", "#!/usr/bin/env bash\n")
    _write(path / "governance_tools" / "plan_freshness.py", "# fixture\n")
    _write(path / "governance_tools" / "contract_validator.py", "# fixture\n")
    return path


def _make_git_hook_valid_framework_root(path: Path) -> Path:
    _make_hook_valid_framework_root(path)
    _run_git(["init"], path)
    _run_git(["config", "user.email", "test@example.com"], path)
    _run_git(["config", "user.name", "Test User"], path)
    _run_git(["add", "."], path)
    _run_git(["commit", "-m", "framework"], path)
    return path


def _install_governance_hooks(repo: Path, framework: Path) -> None:
    marker = "# AI Governance Framework\n"
    _write(repo / ".git" / "hooks" / "pre-commit", marker)
    _write(repo / ".git" / "hooks" / "pre-push", marker)
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(framework.resolve()))


def _write_fresh_plan(repo: Path) -> None:
    _write(
        repo / "PLAN.md",
        "# PLAN.md\n\n"
        f"> **最後更新**: {date.today().isoformat()}\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n",
    )


def _patch_ready_readiness(
    monkeypatch,
    repo: Path,
    *,
    drift_clean: bool = True,
    ready: bool = True,
) -> None:
    def fake_assess_external_repo(repo_root: Path, contract_path=None, framework_root=None):
        checks = {
            "git_repo_present": True,
            "plan_present": True,
            "plan_fresh_enough": True,
            "contract_resolved": True,
            "contract_files_complete": True,
            "gitlab_adapter_scope_consistent": True,
            "framework_release_compatible": True,
            "governance_drift_clean": drift_clean,
        }
        return ExternalRepoReadiness(
            ready=ready,
            repo_root=str(repo_root),
            checks=checks,
            contract={"path": str(repo / "contract.yaml")},
            governance_drift={"severity": "ok" if drift_clean else "error", "findings": []},
        )

    monkeypatch.setattr(
        "governance_tools.external_repo_readiness.assess_external_repo",
        fake_assess_external_repo,
    )


def _smoke_payload(
    repo: Path,
    *,
    ok: bool = True,
    generated_at: str = "2026-07-11T00:00:00Z",
) -> dict[str, object]:
    return {
        "result_schema": "external_repo_smoke_result.v0.2",
        "generated_at": generated_at,
        "ok": ok,
        "repo_root": str(repo.resolve()),
        "plan_path": str((repo / "PLAN.md").resolve()),
        "contract_path": str((repo / "contract.yaml").resolve()),
        "framework_worktree_clean": True,
        "framework_worktree_changes": [],
        "rules": ["common"],
        "pre_task_ok": ok,
        "session_start_ok": ok,
        "post_task_ok": None,
        "post_task_cases": [],
        "token_summary": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "warnings": [],
        "errors": [] if ok else ["session_start failed"],
    }


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
    summary_lines = summary.human_readable_adoption_summary
    assert summary_lines[2] == "先看結論："
    assert summary_lines[3].startswith("這份檢查做了什麼：")
    assert summary_lines[4] == "現在能不能用：可使用基本治理指引；完整 framework 尚未導入。"
    assert "尚未證明 repo 內可自行執行 runtime 治理" in summary_lines[5]
    assert summary_lines.index("AI Governance 功能導入狀態：") > 5
    assert "整體導入狀態：minimal" in rendered
    assert "AI Governance 功能導入狀態：" in rendered
    assert "| 功能 | 狀態 | 這個功能是做什麼 |" in rendered
    assert "AI Governance framework checkout: not full-framework-owned" in rendered
    assert "| 框架本體（Framework checkout） | 未導入 |" in rendered
    assert "| 本 repo 規則（Repo governance instructions） | 未導入 |" in rendered
    assert "| runtime 治理能力（Runtime-capable governance） | 未驗證 |" in rendered
    assert "只有明確回報已可用時才算導入" in rendered
    assert "Validator surface: 未導入" in rendered


def test_partial_summary_leads_with_plain_missing_capability(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "partial")
    relpath = "additional/ai-governance-framework"
    framework = _make_git_framework_with_remote(repo / relpath, tmp_path / "framework.git", behind=False)
    _write_gitmodules(repo, relpath)
    _write_repo_specific_agents(repo)
    _write_fresh_plan(repo)
    _write_framework_lock(repo, _run_git(["rev-parse", "HEAD"], framework))

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.user_facing_status.value == "partial"
    assert summary.human_readable_adoption_summary[4] == (
        "現在能不能用：可使用已導入的治理檔案；但不能說這個 repo 已完整導入。"
    )
    assert "尚未宣告 repo 專屬自動檢查" in summary.human_readable_adoption_summary[5]


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
    assert "| 版本新鮮度（Framework version freshness） | 已落後 |" in rendered


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
    assert "版本帳實一致性（Lock vs checkout consistency）" in rendered


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
    assert "| 版本帳實一致性（Lock vs checkout consistency） | 不一致 |" in rendered


def test_lock_consistency_reports_legacy_lock_schema_without_adopted_commit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "legacy_lock")
    framework = _make_git_framework(repo / "ai-governance-framework")
    _write(
        repo / "governance" / "framework.lock.json",
        json.dumps({"framework_baseline_version": "v1.2.0"}, indent=2) + "\n",
    )
    _commit_path(repo, "governance/framework.lock.json", "record legacy framework lock")

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)
    payload = summary_to_dict(summary)

    assert summary.lock_consistency.value == "legacy_lock_schema"
    assert "framework_lock_consistency" in summary.missing_surfaces
    assert "framework lock matches the checked-out framework commit" in summary.cannot_claim
    assert payload["lock_consistency"]["value"] == "legacy_lock_schema"
    assert "legacy_lock_schema: framework lock has framework_baseline_version but no adopted_commit" in (
        " ".join(summary.lock_consistency.reasons)
    )
    assert "lock_consistency         = legacy_lock_schema" in rendered
    assert "| 版本帳實一致性（Lock vs checkout consistency） | 舊版格式 |" in rendered


def test_self_hosting_framework_lock_is_not_consumer_lock_consistency(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "framework_self")
    _make_framework_root(repo)
    _run_git(["checkout", "-b", "main"], repo)
    _run_git(["add", "."], repo)
    _run_git(["commit", "-m", "framework baseline"], repo)
    baseline_head = _run_git(["rev-parse", "HEAD"], repo)
    _write(
        repo / "governance" / "framework.lock.json",
        json.dumps(
            {
                "adopted_commit": baseline_head,
                "_self_reference_note": (
                    "This lock records the framework version used by this repo to evaluate itself. "
                    "It does not prove framework correctness."
                ),
            },
            indent=2,
        )
        + "\n",
    )
    _commit_path(repo, "governance/framework.lock.json", "record self framework lock")
    _write(repo / "NEXT.txt", "next\n")
    _run_git(["add", "NEXT.txt"], repo)
    _run_git(["commit", "-m", "advance framework"], repo)

    summary = build_governance_maturity_summary(repo, framework_root=repo)
    rendered = format_human(summary)

    assert summary.framework_topology.value == "repo_owned_framework_path"
    assert summary.lock_consistency.value == "not_applicable"
    assert "framework_lock_consistency" not in summary.missing_surfaces
    assert "framework lock matches the checked-out framework commit" not in summary.cannot_claim
    assert "self-assessment baseline" in " ".join(summary.lock_consistency.reasons)
    assert "lock_consistency         = not_applicable" in rendered


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


def test_capability_states_distinguish_missing_evidence_from_failed_checks(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "capabilities")
    external_framework = _make_framework_root(tmp_path / "external-framework")

    summary = build_governance_maturity_summary(repo, framework_root=external_framework)
    payload = summary_to_dict(summary)

    assert summary.capability_states["topology"].state == "Detected"
    assert summary.capability_states["runtime_evidence"].state == "Unproven"
    assert summary.capability_states["runtime_evidence"].source == (
        "governance_maturity_summary.runtime_evidence_lookup"
    )
    assert summary.capability_states["hook_installation"].state == "Failed"
    assert summary.capability_states["readiness.plan_present"].state == "Failed"
    assert summary.capability_states["readiness.contract_resolved"].state == "Verified"
    assert "readiness.governance_drift_clean" in summary.capability_states
    assert "readiness.framework_release_compatible" in summary.capability_states
    assert summary.capability_states["readiness.overall"].state == "Failed"
    assert payload["capability_states"]["runtime_evidence"]["state"] == "Unproven"
    assert payload["capability_states"]["runtime_evidence"]["source"] == (
        "governance_maturity_summary.runtime_evidence_lookup"
    )
    assert summary.next_safe_command is None
    assert summary.owner_actions


def test_capability_states_include_verified_hook_and_runtime_evidence(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "verified_capabilities")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(_smoke_payload(repo, ok=True)) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)

    assert summary.capability_states["hook_installation"].state == "Verified"
    assert summary.capability_states["hook_installation"].source == (
        "hook_install_validator.validate_hook_install"
    )
    assert summary.capability_states["runtime_evidence"].state == "Verified"
    assert "external-repo-smoke-result.json" in " ".join(
        summary.capability_states["runtime_evidence"].reasons
    )
    assert "hook_installation: Verified" in rendered
    assert "runtime_evidence: Verified" in rendered


def test_runtime_evidence_failed_receipt_is_failed_not_detected(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "failed_runtime_evidence")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(_smoke_payload(repo, ok=False)) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Failed"
    assert "ok=false" in " ".join(summary.capability_states["runtime_evidence"].reasons)
    assert summary.next_safe_command is None
    assert any("failed runtime smoke" in action for action in summary.owner_actions)


def test_incomplete_ok_runtime_json_is_detected_not_verified(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path / "incomplete_runtime_json")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps({"ok": True, "repo_root": str(repo.resolve())}) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Detected"
    assert "incomplete smoke result shape" in " ".join(
        summary.capability_states["runtime_evidence"].reasons
    )
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command


def test_invalid_typed_runtime_json_is_detected_not_verified(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path / "invalid_typed_runtime_json")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["rules"] = "common"
    payload["pre_task_ok"] = "yes"
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Detected"
    reasons = " ".join(summary.capability_states["runtime_evidence"].reasons)
    assert "rules must be list[str]" in reasons
    assert "pre_task_ok must be bool" in reasons
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command


def test_contradictory_ok_true_runtime_json_is_detected_not_verified(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "contradictory_ok_true_runtime_json")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["pre_task_ok"] = False
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Detected"
    assert "ok=true requires pre_task_ok=true" in " ".join(
        summary.capability_states["runtime_evidence"].reasons
    )
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command


def test_invalid_plan_path_runtime_json_is_detected_not_verified(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "invalid_plan_path_runtime_json")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["plan_path"] = str((tmp_path / "other" / "PLAN.md").resolve())
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Detected"
    assert "plan_path must resolve to target repo PLAN.md" in " ".join(
        summary.capability_states["runtime_evidence"].reasons
    )
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command


def test_contradictory_ok_false_runtime_json_is_detected_not_failed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "contradictory_ok_false_runtime_json")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=False)
    payload["pre_task_ok"] = True
    payload["session_start_ok"] = True
    payload["post_task_ok"] = None
    payload["errors"] = []
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Detected"
    assert "ok=false requires non-empty errors" in " ".join(
        summary.capability_states["runtime_evidence"].reasons
    )
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command


def test_runtime_evidence_mismatched_repo_is_detected_not_verified(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path / "mismatched_runtime_evidence")
    other_repo = tmp_path / "other_repo"
    other_repo.mkdir()
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["repo_root"] = str(other_repo.resolve())
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-repo-smoke-result.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Detected"
    assert "repo_root mismatch" in " ".join(summary.capability_states["runtime_evidence"].reasons)
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command
    assert any("filename-only" in action for action in summary.owner_actions)


def test_latest_attributable_runtime_receipt_wins(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "latest_runtime_evidence")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    old_failed = repo / "artifacts" / "evidence" / "test-results" / "runtime-smoke-old.json"
    new_passed = repo / "artifacts" / "evidence" / "test-results" / "runtime-smoke-new.json"
    _write(
        old_failed,
        json.dumps(_smoke_payload(repo, ok=False, generated_at="2026-07-11T00:00:00Z")) + "\n",
    )
    _write(
        new_passed,
        json.dumps(_smoke_payload(repo, ok=True, generated_at="2026-07-11T00:10:00Z")) + "\n",
    )
    os.utime(old_failed, (1_700_000_100, 1_700_000_100))
    os.utime(new_passed, (1_700_000_000, 1_700_000_000))

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["runtime_evidence"].state == "Verified"
    assert "runtime-smoke-new.json" in " ".join(summary.capability_states["runtime_evidence"].reasons)
    assert "generated_at=2026-07-11T00:10:00Z" in " ".join(summary.capability_states["runtime_evidence"].reasons)
    assert summary.next_safe_command is None


def test_newer_v0_1_receipt_blocks_older_valid_runtime_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "newer_v0_1_runtime_evidence")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    framework_commit = _run_git(["rev-parse", "HEAD"], framework)

    older_valid = _smoke_payload(
        repo,
        ok=True,
        generated_at="2026-07-11T00:00:00Z",
    )
    older_valid["framework_root"] = str(framework.resolve())
    older_valid["framework_commit"] = framework_commit
    newer_v0_1 = _smoke_payload(
        repo,
        ok=True,
        generated_at="2026-07-11T00:10:00Z",
    )
    newer_v0_1["result_schema"] = "external_repo_smoke_result.v0.1"
    newer_v0_1["framework_root"] = str(framework.resolve())
    newer_v0_1["framework_commit"] = framework_commit
    newer_v0_1.pop("framework_worktree_clean")
    newer_v0_1.pop("framework_worktree_changes")

    evidence_dir = repo / "artifacts" / "evidence" / "test-results"
    _write(evidence_dir / "runtime-smoke-old-valid.json", json.dumps(older_valid) + "\n")
    _write(evidence_dir / "runtime-smoke-new-v0-1.json", json.dumps(newer_v0_1) + "\n")

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    runtime_status = summary.capability_states["runtime_evidence"]
    assert runtime_status.state == "Detected"
    assert "runtime-smoke-new-v0-1.json" in " ".join(runtime_status.reasons)
    assert "result_schema must equal 'external_repo_smoke_result.v0.2'" in " ".join(
        runtime_status.reasons
    )
    assert summary.capability_states["external_runtime_execution"].state != "Verified"


def test_newer_dirty_receipt_blocks_older_valid_runtime_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "newer_dirty_runtime_evidence")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    framework_commit = _run_git(["rev-parse", "HEAD"], framework)

    older_valid = _smoke_payload(
        repo,
        ok=True,
        generated_at="2026-07-11T00:00:00Z",
    )
    older_valid["framework_root"] = str(framework.resolve())
    older_valid["framework_commit"] = framework_commit
    newer_dirty = _smoke_payload(
        repo,
        ok=True,
        generated_at="2026-07-11T00:10:00Z",
    )
    newer_dirty["framework_root"] = str(framework.resolve())
    newer_dirty["framework_commit"] = framework_commit
    newer_dirty["framework_worktree_clean"] = False
    newer_dirty["framework_worktree_changes"] = [
        " M governance_tools/external_repo_smoke.py"
    ]

    evidence_dir = repo / "artifacts" / "evidence" / "test-results"
    _write(evidence_dir / "runtime-smoke-old-valid.json", json.dumps(older_valid) + "\n")
    _write(evidence_dir / "runtime-smoke-new-dirty.json", json.dumps(newer_dirty) + "\n")

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    runtime_status = summary.capability_states["runtime_evidence"]
    assert runtime_status.state == "Detected"
    assert "runtime-smoke-new-dirty.json" in " ".join(runtime_status.reasons)
    assert "ok=true requires" in " ".join(runtime_status.reasons)
    assert summary.capability_states["external_runtime_execution"].state != "Verified"


def test_external_runtime_execution_requires_external_prerequisites_and_passing_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state == "Verified"
    assert "does not prove self-contained" in " ".join(status.reasons)
    assert summary.runtime_capable.value == "not_checked"


def test_verified_external_runtime_execution_reconciles_runtime_smoke_non_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_claim_reconciliation")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)
    rendered = format_human(summary)
    serialized = summary_to_dict(summary)

    assert summary.capability_states["external_runtime_execution"].state == "Verified"
    assert "runtime smoke passed" not in summary.cannot_claim
    assert "runtime self-contained governance" in summary.cannot_claim
    assert "hook or CI enforcement" in summary.cannot_claim
    assert "- runtime smoke passed" not in rendered
    assert serialized["capability_states"]["external_runtime_execution"]["state"] == "Verified"
    assert "runtime smoke passed" not in serialized["cannot_claim"]


def test_external_runtime_execution_is_unproven_when_readiness_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_not_ready")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo, ready=False)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["external_runtime_execution"].state == "Unproven"


def test_external_runtime_execution_rejects_evidence_from_a_different_framework(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_wrong_framework")
    framework_a = _make_git_hook_valid_framework_root(tmp_path / "framework_a")
    framework_b = _make_git_hook_valid_framework_root(tmp_path / "framework_b")
    _install_governance_hooks(repo, framework_b)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework_a.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework_a)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework_b)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state == "Unproven"
    assert "does not match current hook root" in " ".join(status.reasons)


def test_external_runtime_execution_rejects_evidence_after_framework_commit_advances(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_stale_commit")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )
    _write(framework / "ADVANCE.txt", "new framework commit\n")
    _run_git(["add", "ADVANCE.txt"], framework)
    _run_git(["commit", "-m", "advance framework"], framework)

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state == "Unproven"
    assert "framework commit does not match" in " ".join(status.reasons)


def test_external_runtime_execution_rejects_receipt_from_dirty_framework(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_dirty_receipt")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    payload["framework_worktree_clean"] = False
    payload["framework_worktree_changes"] = [" M governance_tools/plan_freshness.py"]
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state != "Verified"
    runtime_status = summary.capability_states["runtime_evidence"]
    assert runtime_status.state == "Detected"
    assert "ok=true requires" in " ".join(runtime_status.reasons)


def test_runtime_evidence_rejects_clean_receipt_with_reported_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "runtime_evidence_contradictory_cleanliness")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    payload["framework_worktree_changes"] = [" M governance_tools/plan_freshness.py"]
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    runtime_status = summary.capability_states["runtime_evidence"]
    assert runtime_status.state == "Detected"
    assert "framework_worktree_clean=true requires" in " ".join(runtime_status.reasons)


def test_runtime_evidence_rejects_v0_1_receipt_without_cleanliness_binding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "runtime_evidence_v0_1")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["result_schema"] = "external_repo_smoke_result.v0.1"
    payload.pop("framework_worktree_clean")
    payload.pop("framework_worktree_changes")
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    runtime_status = summary.capability_states["runtime_evidence"]
    assert runtime_status.state == "Detected"
    assert "result_schema must equal 'external_repo_smoke_result.v0.2'" in " ".join(runtime_status.reasons)


def test_external_runtime_execution_rejects_current_dirty_framework(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_current_dirty")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )
    _write(framework / "governance_tools" / "untracked_plugin.py", "ENABLED = True\n")

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state == "Unproven"
    assert "current hook framework worktree is not clean" in " ".join(status.reasons)


def test_external_runtime_execution_rejects_current_tracked_dirty_framework(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_current_tracked_dirty")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )
    _write(framework / "governance_tools" / "plan_freshness.py", "# tracked dirty fixture\n")

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state == "Unproven"
    assert "current hook framework worktree is not clean" in " ".join(status.reasons)


def test_external_runtime_execution_rejects_current_staged_dirty_framework(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "external_runtime_execution_current_staged_dirty")
    framework = _make_git_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)
    payload = _smoke_payload(repo, ok=True)
    payload["framework_root"] = str(framework.resolve())
    payload["framework_commit"] = _run_git(["rev-parse", "HEAD"], framework)
    _write(
        repo / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json",
        json.dumps(payload) + "\n",
    )
    _write(framework / "governance_tools" / "plan_freshness.py", "# staged dirty fixture\n")
    _run_git(["add", "governance_tools/plan_freshness.py"], framework)

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    status = summary.capability_states["external_runtime_execution"]
    assert status.state == "Unproven"
    assert "current hook framework worktree is not clean" in " ".join(status.reasons)


def test_next_safe_command_runs_runtime_smoke_when_static_prerequisites_are_present(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "runtime_next_command")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _patch_ready_readiness(monkeypatch, repo)

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["readiness.plan_present"].state == "Verified"
    assert summary.capability_states["readiness.contract_resolved"].state == "Verified"
    assert summary.capability_states["hook_installation"].state == "Verified"
    assert summary.capability_states["runtime_evidence"].state == "Unproven"
    assert summary.next_safe_command is not None
    assert "external_repo_smoke.py" in summary.next_safe_command
    assert "external_repo_readiness.py" not in summary.next_safe_command
    assert f'--repo "{repo.resolve()}"' in summary.next_safe_command


def test_owner_action_names_readiness_failure_before_runtime_smoke(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "owner_action_readiness")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["readiness.plan_present"].state == "Failed"
    assert summary.capability_states["hook_installation"].state == "Verified"
    assert summary.next_safe_command is None
    assert any("PLAN.md" in action for action in summary.owner_actions)


def test_hook_failure_requires_owner_action_not_diagnostic_next_command(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "hook_owner_action")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _write_fresh_plan(repo)

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["readiness.plan_present"].state == "Verified"
    assert summary.capability_states["readiness.contract_resolved"].state == "Verified"
    assert summary.capability_states["hook_installation"].state == "Failed"
    assert summary.next_safe_command is None
    assert any("hook installation" in action for action in summary.owner_actions)


def test_critical_plan_blocks_runtime_smoke_command(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "critical_plan")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write(
        repo / "PLAN.md",
        "# PLAN.md\n\n"
        "> **最後更新**: 2020-01-01\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["readiness.plan_present"].state == "Verified"
    assert summary.capability_states["readiness.plan_fresh_enough"].state == "Failed"
    assert summary.capability_states["readiness.overall"].state == "Failed"
    assert summary.next_safe_command is None
    assert any("PLAN.md" in action for action in summary.owner_actions)


def test_incomplete_contract_blocks_runtime_smoke_command(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "incomplete_contract")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)
    _write(
        repo / "contract.yaml",
        "name: incomplete-contract\n"
        "documents:\n"
        "  - missing.md\n",
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["readiness.contract_resolved"].state == "Verified"
    assert summary.capability_states["readiness.contract_files_complete"].state == "Failed"
    assert summary.capability_states["readiness.overall"].state == "Failed"
    assert summary.next_safe_command is None
    assert any("missing contract" in action for action in summary.owner_actions)


def test_governance_drift_failure_blocks_runtime_smoke_even_when_readiness_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path / "drift_failed")
    framework = _make_hook_valid_framework_root(tmp_path / "framework")
    _install_governance_hooks(repo, framework)
    _write_fresh_plan(repo)

    def fake_assess_external_repo(repo_root: Path, contract_path=None, framework_root=None):
        checks = {
            "git_repo_present": True,
            "plan_present": True,
            "plan_fresh_enough": True,
            "contract_resolved": True,
            "contract_files_complete": True,
            "gitlab_adapter_scope_consistent": True,
            "framework_release_compatible": True,
            "governance_drift_clean": False,
        }
        return ExternalRepoReadiness(
            ready=True,
            repo_root=str(repo_root),
            checks=checks,
            contract={"path": str(repo / "contract.yaml")},
            governance_drift={"severity": "error", "findings": [{"check": "drift", "severity": "error"}]},
        )

    monkeypatch.setattr(
        "governance_tools.external_repo_readiness.assess_external_repo",
        fake_assess_external_repo,
    )

    summary = build_governance_maturity_summary(repo, framework_root=framework)

    assert summary.capability_states["readiness.overall"].state == "Verified"
    assert summary.capability_states["readiness.governance_drift_clean"].state == "Failed"
    assert summary.next_safe_command is None
    assert any("governance drift" in action for action in summary.owner_actions)
