from __future__ import annotations

import json
import subprocess
from datetime import date as _date
from pathlib import Path

from governance_tools.f7_full_update import classify_repo, run_f7_full_update


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
    _write(root / "README.md", "[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)]\n")
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
                "adopted_release": "1.2.0",
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


def test_external_contract_apply_generates_required_f7_surfaces(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    _make_external_contract_repo(repo)

    result = run_f7_full_update(repo_root=repo, framework_root=framework, apply=True)

    assert result.ok is True
    assert result.f7_final_status == "completed"
    assert (repo / "governance" / "framework.lock.json").exists()
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
    assert "governance:key=memory_workflow" in agents_text
    assert "memory/**" in agents_text
    hook_text = (repo / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "MEMORY_WORKFLOW_TOOL" in hook_text
    assert result.stages["framework_lock_commit"] == "verified"
    assert result.stages["memory_workflow_router"] == "verified"
    assert result.stages["memory_workflow_hook_advisory"] == "verified"


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
