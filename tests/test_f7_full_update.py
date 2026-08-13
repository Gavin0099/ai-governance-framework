from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import date as _date
from pathlib import Path

from governance_tools.external_governance_submodule_updater import UpdateResult
from governance_tools.f7_full_update import (
    _ensure_agents_keyed_sections,
    classify_repo,
    format_human,
    run_f7_full_update,
)
from governance_tools.update_receipt import RECEIPT_RELATIVE_PATH


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")


def _make_framework(root: Path) -> None:
    _init_repo(root)
    _write(root / "README.md", "[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)]\n")
    _write(
        root / "scripts" / "hooks" / "pre-commit",
        "#!/usr/bin/env bash\n"
        "# AI Governance Framework\n"
        'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"\n'
        '"$MEMORY_WORKFLOW_TOOL" --repo "$TARGET_REPO_ROOT" --check --format json || true\n',
    )
    _write(root / "scripts" / "hooks" / "pre-push", "#!/usr/bin/env bash\n# AI Governance Framework\n")
    _write(root / "scripts/lib/python.sh", "")
    _write(root / "scripts/run-runtime-governance.sh", "")
    _write(root / "governance_tools/plan_freshness.py", "")
    _write(root / "governance_tools/contract_validator.py", "")
    _write(root / "governance_tools/memory_workflow.py", "")
    _write(
        root / "governance/copilot-instructions-template.md",
        "# Copilot Workspace Instructions\n<!-- AI Governance Framework: copilot-instructions v1.0 -->\n",
    )
    _write(root / "governance/framework.lock.json", "{}\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "seed framework")
    head = _git(root, "rev-parse", "HEAD")
    _write(
        root / "governance/framework.lock.json",
        json.dumps(
            {
                "framework_repo": "https://github.com/Gavin0099/ai-governance-framework.git",
                "adopted_release": "1.3.0",
                "adopted_commit": "stale-template-commit",
                "framework_interface_version": "1",
                "framework_compatible": ">=1.0.0,<2.0.0",
            },
            indent=2,
        ),
    )


def _make_external_contract_repo(repo: Path) -> None:
    _init_repo(repo)
    _write(
        repo / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
    )
    _write(repo / "AGENTS.md", "# Contract Agent Rules\n\n- Read contract.yaml first.\n- Preserve this domain rule.\n")
    _write(repo / "CHECKLIST.md", "# Checklist\n")
    _write(repo / "memory" / "02_project_facts.md", "# Project Facts\n\n- target_os: windows\n- language: markdown\n- runtime: none\n- test_command: python -m pytest\n")
    _write(repo / "rules/domain/safety.md", "# Rule\n")
    _write(repo / "validators/checker.py", "print('ok')\n")
    _write(
        repo / "contract.yaml",
        "name: sample-contract\n"
        "domain: rtl\n"
        "plugin_version: \"1.0.0\"\n"
        "framework_interface_version: \"1\"\n"
        "framework_compatible: \">=1.0.0,<2.0.0\"\n"
        "documents:\n  - CHECKLIST.md\n"
        "ai_behavior_override:\n  - AGENTS.md\n"
        "rule_roots:\n  - rules\n"
        "validators:\n  - validators/checker.py\n",
    )


def test_classify_repo_detects_external_contract_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _make_external_contract_repo(repo)

    assert classify_repo(repo) == "external_contract_repo"


def test_classify_repo_prefers_gitmodules_submodule_when_status_helper_fails(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    _make_external_contract_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
    )
    (repo / "ai-governance-framework").mkdir()

    import governance_tools.f7_full_update as f7

    original_git = f7._git

    def fake_git(repo_root: Path, args):
        if list(args)[:2] == ["submodule", "status"]:
            return 1, "", "git-submodule helper failed"
        return original_git(repo_root, args)

    monkeypatch.setattr(f7, "_git", fake_git)

    assert classify_repo(repo) == "submodule_consumer"


def test_ready_true_but_f7_partially_updated_when_hooks_and_lock_missing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)

    assert result.repo_role == "external_contract_repo"
    assert result.details["readiness_ready"] is True
    assert result.f7_final_status == "partially_updated"
    assert result.details["strict_external_f7_completed"] is False
    assert result.stages["memory_workflow_router"] == "not_verified"
    assert result.stages["memory_workflow_hook_advisory"] == "not_verified"
    assert result.stages["framework_lock_commit"] == "not_verified"


def test_external_contract_cannot_complete_without_memory_workflow_rollout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _write(
        repo / "governance" / "RESPONSE_ENVELOPE_CONTRACT.md",
        "# Response Envelope Contract v0.7\n"
        "> v0.6 historical release note\n",
    )
    _write(
        repo / "AGENTS.md",
        "<!-- governance-baseline: overridable -->\n"
        "<!-- baseline_version: 1.0.0 -->\n"
        + (repo / "AGENTS.md").read_text(encoding="utf-8"),
    )
    _write(repo / "governance" / "framework.lock.json", (framework / "governance" / "framework.lock.json").read_text(encoding="utf-8"))
    _write(repo / ".git" / "hooks" / "pre-commit", "#!/usr/bin/env bash\n# AI Governance Framework\n")
    _write(repo / ".git" / "hooks" / "pre-push", "#!/usr/bin/env bash\n# AI Governance Framework\n")
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(framework))
    _write(
        repo / ".github" / "copilot-instructions.md",
        "# Copilot Workspace Instructions\n<!-- AI Governance Framework: copilot-instructions v1.0 -->\n",
    )

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)

    assert result.details["readiness_ready"] is True
    assert result.details["memory_workflow_router_present"] is False
    assert result.details["memory_workflow_hook_advisory_present"] is False
    assert result.f7_final_status == "partially_updated"
    assert result.details["strict_external_f7_completed"] is False
    assert result.details["framework_version_diagnostics"]["adopted_release_current"] is True
    assert result.details["framework_version_diagnostics"]["adopted_commit_current"] is False
    assert "F-7 completion also requires adopted_commit_current" in result.details["framework_version_diagnostics"]["note"]
    assert result.details["agents_baseline_diagnostics"]["baseline_version"] == "1.0.0"
    assert result.details["agents_baseline_diagnostics"]["baseline_version_is_framework_release"] is False
    assert any("release-current is not F-7 completion" in warning for warning in result.warnings)
    assert "governance_maturity_summary" in result.stages
    summary = result.stages["governance_maturity_summary"]
    assert summary["report_only"] is True
    assert summary["runtime_capable"]["value"] == "not_checked"
    rendered = format_human(result)
    assert "[human_readable_update_summary]" in rendered
    assert "F-7 full update workflow means the complete AI Governance update flow" in rendered
    assert "[governance_maturity_summary]" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "runtime_capable=not_checked" in rendered


def test_f7_submodule_backend_surfaces_governance_maturity_summary(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _init_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
    )
    _write(repo / "ai-governance-framework" / "README.md", "partial framework checkout\n")

    import governance_tools.f7_full_update as f7

    def fake_update(**_kwargs):
        return UpdateResult(
            ok=True,
            mode="dry_run",
            update_mode="dry_run",
            fast_forward=True,
            repo=str(repo),
            submodule_path="ai-governance-framework",
            before_head="a" * 40,
            target_head="a" * 40,
            after_head="a" * 40,
            staged_files=[],
            committed=False,
            commit_hash=None,
            message="dry run complete",
            errors=[],
            full_update_stage_report={"final_status": "already_current", "framework_pointer": "already_current"},
        )

    monkeypatch.setattr(f7, "update_governance_submodule", fake_update)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)

    assert result.repo_role == "submodule_consumer"
    assert result.f7_final_status == "already_current"
    assert "governance_maturity_summary" in result.stages
    assert result.stages["governance_maturity_summary"]["report_only"] is True
    assert result.stages["governance_maturity_summary"]["runtime_capable"]["value"] == "not_checked"
    assert result.final_report_requirement["status"] == "required"
    assert "table rows as a table" in result.final_report_requirement["instruction"]
    assert "[human_readable_adoption_summary]" in (
        result.final_report_requirement["human_readable_adoption_summary"]
    )
    payload = asdict(result)
    assert "final_report_requirement" in payload
    assert payload["final_report_table_required"]["status"] == "required"
    assert payload["final_report_table_required"]["update_report_complete"] is True
    assert payload["final_report_table_required"]["completion_claim_allowed"] is True
    assert payload["final_report_table_required"]["must_relay_as"] == "table_rows_verbatim"
    assert "[human_readable_adoption_summary]" in (
        payload["final_report_table_required"]["table_rows"]
    )
    envelope = payload["ai_governance_update_result"]
    assert envelope["report_only"] is True
    assert envelope["framework_update_status"] == {
        "value": "already_current",
        "source": "f7_full_update",
    }
    assert envelope["governance_maturity_summary"]["value"] == "present"
    assert envelope["human_readable_adoption_summary"]["value"] == "reported"
    assert envelope["final_report_requirement"]["value"] == "present"
    assert envelope["update_report_complete"] is True
    assert envelope["completion_claim_allowed"] is True
    rendered = format_human(result)
    assert "[governance_maturity_summary]" in rendered
    assert "[ai_governance_update_result]" in rendered
    assert "framework_update_status=already_current" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "[final_report_requirement]" in rendered
    assert "table rows as a table" in rendered
    assert "整體導入狀態：" in rendered
    assert "AI Governance 功能導入狀態：" in rendered


def test_f7_submodule_staged_blocker_still_relays_adoption_table(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _init_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
    )
    _write(repo / "ai-governance-framework" / "README.md", "partial framework checkout\n")
    _git(repo, "add", ".gitmodules")

    import governance_tools.f7_full_update as f7

    called: dict[str, object] = {}

    def fake_update(**kwargs):
        called.update(kwargs)
        return UpdateResult(
            ok=False,
            mode="dry_run",
            update_mode="failed",
            fast_forward=None,
            repo=str(repo),
            submodule_path="ai-governance-framework",
            before_head="a" * 40,
            target_head="",
            after_head="a" * 40,
            staged_files=[],
            committed=False,
            commit_hash=None,
            message="submodule pointer update failed",
            errors=["consuming repo has pre-existing staged files; refusing to mix scopes"],
            full_update_stage_report={
                "final_status": "blocked",
                "framework_pointer": "blocked",
            },
        )

    monkeypatch.setattr(f7, "update_governance_submodule", fake_update)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)

    assert called["dry_run"] is True
    assert result.repo_role == "submodule_consumer"
    assert result.f7_final_status == "blocked"
    assert result.errors == [
        "consuming repo has pre-existing staged files; refusing to mix scopes"
    ]
    assert result.stages["governance_maturity_summary"]["report_only"] is True
    assert result.final_report_requirement["status"] == "required"
    assert result.final_report_table_required["status"] == "required"
    assert result.final_report_table_required["table_rows"]
    assert result.final_report_table_required["update_report_complete"] is True
    assert result.final_report_table_required["completion_claim_allowed"] is True
    assert result.ai_governance_update_result["human_readable_adoption_summary"][
        "value"
    ] == "reported"
    assert result.ai_governance_update_result["update_report_complete"] is True
    assert result.ai_governance_update_result["completion_claim_allowed"] is True
    rendered = format_human(result)
    assert "[human_readable_adoption_summary]" in rendered


def test_f7_orchestrator_staged_blocker_still_relays_adoption_table(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _git(repo, "add", "contract.yaml")

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)

    assert result.repo_role == "external_contract_repo"
    assert result.f7_final_status == "blocked"
    assert result.final_report_table_required["status"] == "required"
    assert result.final_report_table_required["table_rows"]
    assert result.ai_governance_update_result["update_report_complete"] is True
    assert result.ai_governance_update_result["completion_claim_allowed"] is True
    rendered = format_human(result)
    assert "[human_readable_adoption_summary]" in rendered
    assert "framework_update_status=blocked" in rendered


def test_f7_submodule_backend_surfaces_target_freshness_downgrade(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _init_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
    )
    _write(repo / "ai-governance-framework" / "README.md", "partial framework checkout\n")

    import governance_tools.f7_full_update as f7

    def fake_update(**_kwargs):
        return UpdateResult(
            ok=True,
            mode="dry_run",
            update_mode="dry_run",
            fast_forward=True,
            repo=str(repo),
            submodule_path="ai-governance-framework",
            before_head="a" * 40,
            target_head="a" * 40,
            after_head="a" * 40,
            staged_files=[],
            committed=False,
            commit_hash=None,
            message="dry run complete",
            errors=[],
            full_update_stage_report={
                "framework_pointer": "not_verified",
                "target_source": "local_tracking_ref_fallback",
                "target_fresh_upstream_verified": False,
                "target_claim_boundary": (
                    "target resolved from local tracking fallback; upstream freshness "
                    "was not verified, so already_current/updated must not be claimed"
                ),
                "final_status": "not_verified",
            },
        )

    monkeypatch.setattr(f7, "update_governance_submodule", fake_update)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)
    rendered = format_human(result)

    assert result.repo_role == "submodule_consumer"
    assert result.f7_final_status == "not_verified"
    assert result.stages["framework_pointer"] == "not_verified"
    assert result.stages["target_source"] == "local_tracking_ref_fallback"
    assert result.stages["target_fresh_upstream_verified"] is False
    assert "target_source=local_tracking_ref_fallback" in rendered
    assert "target_fresh_upstream_verified=False" in rendered
    assert "already_current/updated must not be claimed" in rendered


def test_f7_submodule_backend_preserves_fresh_update_available_status(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _init_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
    )
    _write(repo / "ai-governance-framework" / "README.md", "partial framework checkout\n")
    _git(repo, "add", ".gitmodules")

    import governance_tools.f7_full_update as f7

    def fake_update(**_kwargs):
        return UpdateResult(
            ok=True,
            mode="dry_run",
            update_mode="dry_run",
            fast_forward=True,
            repo=str(repo),
            submodule_path="ai-governance-framework",
            before_head="a" * 40,
            target_head="b" * 40,
            after_head="a" * 40,
            staged_files=[],
            committed=False,
            commit_hash=None,
            message="dry run complete",
            errors=[],
            full_update_stage_report={
                "framework_pointer": "not_verified",
                "target_source": "fresh_remote_ls_remote",
                "target_fresh_upstream_verified": True,
                "target_claim_boundary": (
                    "fresh upstream target verified; already_current/updated claims "
                    "are allowed"
                ),
                "final_status": "not_verified",
            },
            target_source="fresh_remote_ls_remote",
        )

    monkeypatch.setattr(f7, "update_governance_submodule", fake_update)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)
    rendered = format_human(result)

    assert result.repo_role == "submodule_consumer"
    assert result.f7_final_status == "not_verified"
    assert result.stages["framework_pointer"] == "not_verified"
    assert result.ai_governance_update_result["framework_update_status"] == {
        "value": "update_available",
        "source": "f7_full_update",
    }
    assert "framework_update_status=update_available" in rendered


def test_f7_submodule_backend_downgrades_completed_when_lock_consistency_is_inconsistent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _init_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
    )
    _write(repo / "ai-governance-framework" / "README.md", "partial framework checkout\n")

    import governance_tools.f7_full_update as f7

    def fake_update(**_kwargs):
        return UpdateResult(
            ok=True,
            mode="apply",
            update_mode="fast_forward",
            fast_forward=True,
            repo=str(repo),
            submodule_path="ai-governance-framework",
            before_head="a" * 40,
            target_head="b" * 40,
            after_head="b" * 40,
            staged_files=["ai-governance-framework"],
            committed=False,
            commit_hash=None,
            message="submodule pointer update complete",
            errors=[],
            update_receipt={
                "status": "written",
                "path": RECEIPT_RELATIVE_PATH,
                "staged": False,
            },
            full_update_stage_report={
                "framework_pointer": "updated",
                "repo_local_instruction": "updated",
                "memory_writer_coverage": "verified",
                "hook_validator_enforcement": "verified",
                "existing_memory_normalization": "completed",
                "final_status": "full_update_completed",
            },
        )

    monkeypatch.setattr(f7, "update_governance_submodule", fake_update)
    monkeypatch.setattr(
        f7,
        "_governance_maturity_stage",
        lambda *_args, **_kwargs: {
            "report_only": True,
            "lock_consistency": {"value": "inconsistent"},
            "human_readable_adoption_summary": ["[human_readable_adoption_summary]"],
        },
    )

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)
    rendered = format_human(result)

    assert result.repo_role == "submodule_consumer"
    assert result.stages["governance_maturity_summary"]["lock_consistency"]["value"] == "inconsistent"
    assert result.f7_final_status == "partially_updated"
    assert result.update_receipt["status"] == "written"
    assert RECEIPT_RELATIVE_PATH in result.changed_files
    assert "Current result: partially_updated." in rendered


def test_f7_maturity_summary_failure_is_report_only(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)

    import governance_tools.f7_full_update as f7

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(f7, "build_governance_maturity_summary", boom)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)
    rendered = format_human(result)

    assert result.ok is True
    assert result.f7_final_status == "partially_updated"
    assert result.stages["governance_maturity_summary"]["status"] == "not_available"
    assert "RuntimeError: boom" in result.stages["governance_maturity_summary"]["reason"]
    envelope = result.ai_governance_update_result
    assert envelope["governance_maturity_summary"]["value"] == "not_available"
    assert "RuntimeError: boom" in envelope["governance_maturity_summary"]["reason"]
    assert envelope["human_readable_adoption_summary"]["value"] == "not_reported"
    assert envelope["update_report_complete"] is False
    assert envelope["completion_claim_allowed"] is False
    assert "complete AI Governance update report" in envelope["cannot_claim"]
    assert "status=not_available" in rendered
    assert "[ai_governance_update_result]" in rendered
    assert "governance_maturity_summary=not_available" in rendered
    assert "RuntimeError: boom" in rendered
    assert "update_report_complete=false" in rendered
    assert "completion_claim_allowed=false" in rendered


def test_external_contract_remediation_plan_excludes_product_and_generated_dirty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _write(repo / "Source" / "product.cpp", "dirty product\n")
    _write(repo / "artifacts" / "runtime" / "receipt.json", "{}\n")
    _write(repo / "governance" / "framework.lock.json", "{}\n")

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=False)
    plan = result.details["remediation_plan"]

    assert plan["mode"] == "read_only_plan"
    assert plan["strategy"] == "clean_worktree_recommended"
    assert any(item.startswith("?? Source/") for item in plan["excluded_dirty_scopes"]["product_build_or_submodule"])
    assert any(item.startswith("?? artifacts/") for item in plan["excluded_dirty_scopes"]["generated_or_local_runtime"])
    assert any(item.startswith("?? governance/") for item in plan["allowlisted_dirty"])
    assert any("clean worktree" in warning for warning in result.warnings)


def test_external_contract_apply_generates_required_f7_surfaces(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    assert result.ok is True
    assert result.f7_final_status == "completed"
    assert (repo / "governance" / "framework.lock.json").exists()
    assert (repo / RECEIPT_RELATIVE_PATH).exists()
    lock = json.loads((repo / "governance" / "framework.lock.json").read_text(encoding="utf-8"))
    assert lock["adopted_commit"] == _git(framework, "rev-parse", "HEAD")
    assert lock["adopted_commit"] != "stale-template-commit"
    assert (repo / ".git" / "hooks" / "pre-commit").exists()
    assert (repo / ".git" / "hooks" / "pre-push").exists()
    assert (repo / ".github" / "copilot-instructions.md").exists()
    assert not (repo / ".git" / "hooks" / "ai-governance-framework-root").read_bytes().startswith(b"\xef\xbb\xbf")
    agents_text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "Preserve this domain rule." in agents_text
    assert "governance:key=f7_update_boundary" in agents_text
    assert "--format human" in agents_text
    assert "[human_readable_adoption_summary]" in agents_text
    assert "table rows as a table, not a prose summary" in agents_text
    assert "user-facing adoption status" in agents_text
    assert "expanded-report exception to the compact three-line default" in agents_text
    assert "Response envelope contract version: v0.7" in agents_text
    assert "full_evidence_request" in agents_text
    assert "owner_decision_required" in agents_text
    assert "failed_or_partial" in agents_text
    assert "update_report_complete=false" in agents_text
    assert "completion_claim_allowed=false" in agents_text
    assert "happy-path-only tests" in agents_text
    assert "expected values must come from a spec/invariant/fixture" in agents_text
    assert "mock-only assertions are weak evidence" in agents_text
    assert "domain validators need pass/fail fixtures" in agents_text
    assert "`test_signal_quality_audit` output is report-only reviewer evidence" in agents_text
    assert "--format json` from the framework environment" not in agents_text
    assert "governance:key=memory_workflow" in agents_text
    assert "memory/**" in agents_text
    assert result.final_report_requirement["status"] == "required"
    assert result.final_report_table_required["update_report_complete"] is True
    assert result.final_report_table_required["completion_claim_allowed"] is True
    assert result.ai_governance_update_result["update_report_complete"] is True
    assert result.ai_governance_update_result["completion_claim_allowed"] is True
    assert "table rows as a table" in result.final_report_requirement["instruction"]
    assert "[human_readable_adoption_summary]" in (
        result.final_report_requirement["human_readable_adoption_summary"]
    )
    payload = asdict(result)
    receipt = json.loads((repo / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert result.update_receipt["status"] == "written"
    assert result.update_receipt["staged"] is False
    assert RECEIPT_RELATIVE_PATH in result.changed_files
    assert receipt["receipt_type"] == "ai_governance_update"
    assert receipt["tool"] == "f7_full_update"
    assert receipt["framework_before"] is None
    assert receipt["framework_after"] == _git(framework, "rev-parse", "HEAD")
    assert receipt["lock_adopted_commit"] == _git(framework, "rev-parse", "HEAD")
    assert receipt["lock_matches_checkout"] is True
    assert receipt["update_status"] == "updated"
    assert "hook/CI enforcement" in receipt["not_claimed"]
    assert "final_report_requirement" in payload
    assert payload["update_receipt"]["status"] == "written"
    assert payload["final_report_table_required"]["status"] == "required"
    assert payload["final_report_table_required"]["must_relay_as"] == "table_rows_verbatim"
    assert "[human_readable_adoption_summary]" in (
        payload["final_report_table_required"]["table_rows"]
    )
    assert payload["ai_governance_update_result"]["framework_update_status"] == {
        "value": "updated",
        "source": "f7_full_update",
    }
    assert (
        payload["ai_governance_update_result"]["lock_consistency"]["value"]
        == payload["stages"]["governance_maturity_summary"]["lock_consistency"]["value"]
    )
    hook_text = (repo / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "MEMORY_WORKFLOW_TOOL" in hook_text
    assert result.stages["framework_lock_commit"] == "verified"
    assert result.stages["memory_workflow_router"] == "verified"
    assert result.stages["memory_workflow_hook_advisory"] == "verified"
    rendered = format_human(result)
    assert "Update receipt status: written." in rendered
    assert "Update receipt path: governance/.update-receipt.json." in rendered
    assert "[ai_governance_update_result]" in rendered
    assert "framework_update_status=updated" in rendered


def test_external_contract_apply_refreshes_existing_f7_update_boundary_block(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _write(
        repo / "AGENTS.md",
        "# Contract Agent Rules\n\n"
        "- Preserve this domain rule.\n\n"
        "<!-- governance:key=f7_update_boundary -->\n"
        "- F-7 updates must preserve existing repo-specific AGENTS.md rules.\n"
        "- Validate F-7 state with `python -X utf8 -m governance_tools.f7_full_update --repo . --format json` from the framework environment.\n"
        "- Required external contract surfaces: contract.yaml, governance/framework.lock.json, .git/hooks/pre-commit, .git/hooks/pre-push, .github/copilot-instructions.md.\n"
        "\n"
        "- Validate F-7 state with `python -X utf8 E:\\BackUp\\Git_EE\\ai-governance-framework\\governance_tools\\f7_full_update.py --repo E:\\BackUp\\Git_EE\\Enumd-private-vault --format json`.\n"
        "\n"
        "## Repo-Specific Notes\n"
        "- Keep this section.\n",
    )

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    agents_text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert result.ok is True
    assert result.f7_final_status == "completed"
    assert result.stages["agents_calibration"] == "updated_preserved_repo_rules"
    assert "Preserve this domain rule." in agents_text
    assert "## Repo-Specific Notes" in agents_text
    assert "Keep this section." in agents_text
    assert "--format human" in agents_text
    assert "[human_readable_adoption_summary]" in agents_text
    assert "table rows as a table, not a prose summary" in agents_text
    assert "user-facing adoption status" in agents_text
    assert "expanded-report exception to the compact three-line default" in agents_text
    assert "Response envelope contract version: v0.7" in agents_text
    assert "full_evidence_request" in agents_text
    assert "owner_decision_required" in agents_text
    assert "failed_or_partial" in agents_text
    assert "update_report_complete=false" in agents_text
    assert "completion_claim_allowed=false" in agents_text
    assert "happy-path-only tests" in agents_text
    assert "expected values must come from a spec/invariant/fixture" in agents_text
    assert "mock-only assertions are weak evidence" in agents_text
    assert "domain validators need pass/fail fixtures" in agents_text
    assert "`test_signal_quality_audit` output is report-only reviewer evidence" in agents_text
    assert "f7_full_update.py --repo E:\\BackUp\\Git_EE\\Enumd-private-vault --format json" in agents_text
    assert "--format json` from the framework environment" not in agents_text


def test_external_contract_apply_marks_legacy_response_envelope_conflict(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _write(
        repo / "AGENTS.md",
        "# Contract Agent Rules\n\n"
        "<!-- Response envelope contract: v0.1 -->\n"
        "- Keep the existing domain rules.\n",
    )

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    agents_text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert result.ok is True
    assert result.f7_final_status == "partially_updated"
    assert result.stages["response_envelope_surface"] == "conflict"
    assert result.details["response_envelope_conflicts"] == ["AGENTS.md: v0.1"]
    assert "Response envelope contract: v0.1" in agents_text
    assert "Response envelope contract version: v0.7" in agents_text
    assert "full_evidence_request" in agents_text
    assert any("response envelope contract versions conflict" in warning for warning in result.warnings)


def test_external_contract_apply_preserves_repo_specific_f7_json_guidance_outside_boundary(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _write(
        repo / "AGENTS.md",
        "# Contract Agent Rules\n\n"
        "- Preserve this domain rule.\n\n"
        "## Memory Workflow Router\n"
        "- Validate F-7 state with `python -X utf8 -m governance_tools.f7_full_update --repo . --format json` before reporting update status.\n"
        "- Validate F-7 state with `python -X utf8 -m governance_tools.f7_full_update --repo . --format json` from the framework environment.\n"
        "- Keep memory workflow json checks for `memory/**` with `python -m governance_tools.memory_workflow --check --repo . --format json`.\n"
        "\n"
        "## Repo-Specific Notes\n"
        "- Keep this section.\n",
    )

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    agents_text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert result.ok is True
    assert result.f7_final_status == "completed"
    assert "--format human" in agents_text
    assert "[human_readable_adoption_summary]" in agents_text
    assert "table rows as a table, not a prose summary" in agents_text
    assert "happy-path-only tests" in agents_text
    assert "expected values must come from a spec/invariant/fixture" in agents_text
    assert "mock-only assertions are weak evidence" in agents_text
    assert "domain validators need pass/fail fixtures" in agents_text
    assert "`test_signal_quality_audit` output is report-only reviewer evidence" in agents_text
    assert "f7_full_update --repo . --format json` before reporting update status" in agents_text
    assert "--format json` from the framework environment" not in agents_text
    assert "memory_workflow --check --repo . --format json" in agents_text
    assert "## Memory Workflow Router" in agents_text
    assert "## Repo-Specific Notes" in agents_text
    assert "Keep this section." in agents_text


def test_external_contract_linked_worktree_uses_common_hooks_for_memory_workflow_advisory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    linked = tmp_path / "linked"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    _write(repo / "governance" / "framework.lock.json", (framework / "governance" / "framework.lock.json").read_text(encoding="utf-8"))
    _write(
        repo / "AGENTS.md",
        (repo / "AGENTS.md").read_text(encoding="utf-8")
        + "\n<!-- governance:key=memory_workflow -->\n"
        + "- Before claiming completion for any change touching `memory/**`, run `python -m governance_tools.memory_workflow --check --repo .`.\n",
    )
    _write(
        repo / ".github" / "copilot-instructions.md",
        "# Copilot Workspace Instructions\n<!-- AI Governance Framework: copilot-instructions v1.0 -->\n",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed external contract")
    _git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    _write(
        repo / ".git" / "hooks" / "pre-commit",
        "#!/usr/bin/env bash\n"
        "# AI Governance Framework\n"
        'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"\n'
        '"$MEMORY_WORKFLOW_TOOL" --repo "$TARGET_REPO_ROOT" --check --format json || true\n',
    )
    _write(repo / ".git" / "hooks" / "pre-push", "#!/usr/bin/env bash\n# AI Governance Framework\n")
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(framework))

    result = run_f7_full_update(repo_root=linked, framework_root=framework, apply=False)

    assert result.repo_role == "external_contract_repo"
    assert result.stages["memory_workflow_hook_advisory"] == "verified"
    assert result.details["memory_workflow_hook_advisory_present"] is True


def test_f7_partial_hook_install_failure_is_blocked_not_updated(tmp_path: Path) -> None:
    """A partial install must not report `updated` next to an overall blocked status."""
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    # Framework-marked instructions that match no shipped template: the installer
    # cannot prove they are unedited, so it refuses to migrate them.
    edited_legacy = (
        "# Copilot Workspace Instructions\n"
        "<!-- AI Governance Framework: copilot-instructions v1.0 -->\n"
        "old framework rules\n"
        "\n## House rule\n\nNever touch vendor/.\n"
    )
    instructions = repo / ".github" / "copilot-instructions.md"
    _write(instructions, edited_legacy)
    before = instructions.read_bytes()

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    # Git hooks really were written, so this is a partial install, not a no-op.
    assert (repo / ".git" / "hooks" / "pre-commit").is_file()
    assert any("pre-commit" in path for path in result.changed_files)

    assert result.stages["hook_validator_enforcement"] == "blocked"
    assert result.f7_final_status == "blocked"
    assert result.ok is False
    assert any("edited after install" in error for error in result.errors)

    # The consumer's instructions are untouched — their rule is still where Copilot reads it.
    assert instructions.read_bytes() == before
    assert "Never touch vendor/." in instructions.read_text(encoding="utf-8")

    human = format_human(result)
    assert "hook_validator_enforcement" in human
    assert "updated" not in human.split("hook_validator_enforcement")[1].split("\n")[0]


def test_f7_surfaces_backup_inventory_when_install_replaces_content(tmp_path: Path) -> None:
    """Backups are the only record of replaced content, so they must reach the report."""
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)
    instructions = repo / ".github" / "copilot-instructions.md"
    _write(instructions, "# House rules\n\nNever touch vendor/.\n")

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    backup_warnings = [w for w in result.warnings if "kept a backup at" in w]
    assert backup_warnings, result.warnings
    assert any("copilot-instructions.md.bak." in w for w in backup_warnings)

    human = format_human(result)
    assert "kept a backup at" in human
    payload = json.dumps(asdict(result), ensure_ascii=False)
    assert "copilot-instructions.md.bak." in payload

    # The consumer content survived the install that produced the backup.
    assert "Never touch vendor/." in instructions.read_text(encoding="utf-8")


def test_submodule_consumer_receives_instruction_surfaces(tmp_path: Path) -> None:
    """F-7 claims to refresh repo-local governance instructions.

    For a submodule consumer it did not: install_governance_hooks was only
    reachable from the external-contract backend, so the files every agent reads
    at session start were never deployed for this repo role.
    """
    repo = tmp_path / "consumer"
    framework = repo / "ai-governance-framework"
    _init_repo(repo)
    _write(repo / "AGENTS.md", "# AGENTS\n\nHouse rules.\n")
    _write(
        repo / ".gitmodules",
        '[submodule "ai-governance-framework"]\n'
        "\tpath = ai-governance-framework\n"
        "\turl = https://example.invalid/ai-governance-framework.git\n",
    )
    _make_framework(framework)
    _write(
        framework / "governance" / "agent-contract-template.md",
        "<!-- AI Governance Framework: agent-contract BEGIN -->\n"
        "contract rules\n"
        "<!-- AI Governance Framework: agent-contract END -->\n",
    )

    result = run_f7_full_update(
        repo_root=repo,
        framework_root=framework,
        apply=True,
        submodule_path="ai-governance-framework",
    )

    for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        text = (repo / name).read_text(encoding="utf-8")
        assert "agent-contract BEGIN" in text, name
    assert "House rules." in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert result.stages.get("hook_validator_enforcement") in {"updated", "verified", "blocked"}


def test_memory_workflow_block_installs_even_when_the_word_appears(tmp_path: Path) -> None:
    """The guard also required the bare word to be absent.

    Any repo that merely mentioned `memory_workflow` — in a router, a command
    example, a note — never received the block at all, permanently.
    """
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _write(repo / "AGENTS.md", "# AGENTS\n\nSee memory_workflow docs.\n")

    first, _, _ = _ensure_agents_keyed_sections(repo)
    text = (repo / "AGENTS.md").read_text(encoding="utf-8")

    assert text.count("governance:key=memory_workflow") == 1
    assert first != "verified"


def test_agents_refresh_stays_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _write(repo / "AGENTS.md", "# AGENTS\n\nHouse rules.\n")

    for _ in range(3):
        _ensure_agents_keyed_sections(repo)

    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count("governance:key=memory_workflow") == 1
    assert text.count("governance:key=f7_update_boundary") == 1


def test_f7_accepts_a_non_origin_framework_remote() -> None:
    """A consumer whose authoritative remote is not `origin` had no way to say so.

    The target always resolved to origin/main, so a repo with a stale mirror on
    origin failed ff-only against a months-old commit with no flag to correct it.
    """
    import inspect
    from governance_tools.f7_full_update import run_f7_full_update as run

    params = inspect.signature(run).parameters
    assert {"target_ref", "fetch_remote", "fetch_ref"} <= set(params)
    assert params["fetch_remote"].default == "origin"
    assert params["fetch_ref"].default == "main"
