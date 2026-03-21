from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.external_repo_readiness import assess_external_repo, format_human


FIXTURE_ROOT = Path("tests/_tmp_external_repo_readiness")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework(framework_root: Path) -> None:
    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")


def _make_target_repo(target_root: Path, framework_root: Path) -> None:
    hook_dir = target_root / ".git" / "hooks"
    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(hook_dir / "ai-governance-framework-root", str(framework_root))
    _write(
        target_root / "PLAN.md",
        "> **最後更新**: 2026-03-14\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
    )
    _write(target_root / "AGENTS.md", "# Agents\n")
    _write(target_root / "CHECKLIST.md", "# Checklist\n")
    _write(target_root / "memory" / "02_project_facts.md", "# Project Facts\n\n- target_os: windows\n")
    _write(target_root / "rules/domain/safety.md", "# rule\n")
    _write(target_root / "validators/checker.py", "print('ok')\n")
    _write(
        target_root / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
                "plugin_version: \"1.0.0\"",
                "framework_interface_version: \"1\"",
                "framework_compatible: \">=1.0.0,<2.0.0\"",
                "documents:",
                "  - CHECKLIST.md",
                "ai_behavior_override:",
                "  - AGENTS.md",
                "rule_roots:",
                "  - rules",
                "validators:",
                "  - validators/checker.py",
            ]
        ),
    )


def _write_lock(target_root: Path, adopted_release: str, compatibility: str = ">=1.0.0,<2.0.0") -> None:
    payload = {
        "framework_repo": "https://github.com/GavinWu672/ai-governance-framework",
        "adopted_release": adopted_release,
        "adopted_commit": "abcdef123456",
        "framework_interface_version": "1",
        "framework_compatible": compatibility,
    }
    _write(target_root / "governance" / "framework.lock.json", json.dumps(payload, indent=2))


def test_assess_external_repo_returns_ready_for_complete_repo() -> None:
    root = _reset_fixture("complete_repo")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v1.0.0-alpha")

    result = assess_external_repo(target_root)

    assert result.ready is True
    assert result.checks["hooks_ready"] is True
    assert result.checks["contract_resolved"] is True
    assert result.checks["framework_version_current"] is True
    assert result.framework_version["state"] == "current"
    assert result.contract["name"] == "sample-contract"


def test_assess_external_repo_reports_missing_contract_and_hooks() -> None:
    root = _reset_fixture("missing_contract_and_hooks")
    target_root = root / "target"
    _write(target_root / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(
        target_root / "PLAN.md",
        "> **最後更新**: 2026-03-14\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
    )

    result = assess_external_repo(target_root)

    assert result.ready is False
    assert result.checks["hooks_ready"] is False
    assert result.checks["contract_resolved"] is False
    assert result.framework_version["state"] == "unknown"
    assert any("contract.yaml not resolved" in item for item in result.warnings)


def test_assess_external_repo_can_use_explicit_framework_root() -> None:
    root = _reset_fixture("explicit_framework_root")
    framework_root = root / "framework"
    target_root = root / "target"
    hook_dir = target_root / ".git" / "hooks"

    _make_framework(framework_root)
    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(
        target_root / "PLAN.md",
        "> **最後更新**: 2026-03-14\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
    )

    result = assess_external_repo(target_root, framework_root=framework_root)

    assert result.checks["hooks_ready"] is True
    assert result.hooks["framework_root"] == str(framework_root.resolve())
    assert any("using explicit framework root" in item for item in result.warnings)


def test_assess_external_repo_marks_outdated_without_failing_readiness() -> None:
    root = _reset_fixture("outdated_but_compatible")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v0.9.0")

    result = assess_external_repo(target_root)

    assert result.ready is True
    assert result.framework_version["state"] == "outdated"
    assert result.checks["framework_release_compatible"] is True
    assert result.checks["framework_version_current"] is False


def test_assess_external_repo_fails_when_current_release_is_incompatible() -> None:
    root = _reset_fixture("incompatible_release")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v0.9.0", compatibility="<1.0.0")

    result = assess_external_repo(target_root)

    assert result.ready is False
    assert result.framework_version["state"] == "incompatible"
    assert result.checks["framework_release_compatible"] is False
    assert any("outside declared compatibility range" in item for item in result.errors)


def test_format_human_surfaces_framework_version_section() -> None:
    root = _reset_fixture("human_output")
    target_root = root / "target"
    _write(target_root / ".git" / "HEAD", "ref: refs/heads/main\n")

    result = assess_external_repo(target_root)
    rendered = format_human(result)

    assert "External Repo Readiness" in rendered
    assert "project_facts      = status=missing" in rendered
    assert "[checks]" in rendered
    assert "[framework_version]" in rendered
    assert "warnings:" in rendered


def test_assess_external_repo_surfaces_project_facts_intake() -> None:
    root = _reset_fixture("project_facts_intake")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v1.0.0-alpha")

    result = assess_external_repo(target_root)

    assert result.checks["project_facts_present"] is True
    assert result.checks["project_facts_intakeable"] is True
    assert result.project_facts["status"] == "available"
    assert result.project_facts["source_filename"] == "02_project_facts.md"
    assert result.project_facts["sync_direction"] == "external_to_framework"
    assert result.project_facts["artifact_path"].replace("/", "\\").endswith(r"artifacts\external-project-facts\target.json")
    assert result.project_facts["artifact_exists"] is False
    assert result.project_facts["reason"] is None
    assert result.project_facts["remediation_hint"] is None


def test_assess_external_repo_detects_project_facts_artifact_drift() -> None:
    root = _reset_fixture("project_facts_drift")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v1.0.0-alpha")
    artifact = Path("artifacts") / "external-project-facts" / "target.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({"fact_source": {"content_sha256": "stale-sha"}}, indent=2), encoding="utf-8")

    result = assess_external_repo(target_root)

    assert result.checks["project_facts_drift_free"] is False
    assert result.project_facts["status"] == "drifted"
    assert result.project_facts["artifact_exists"] is True
    assert result.project_facts["artifact_drift"] is True
    assert result.project_facts["remediation_hint"].startswith("python governance_tools/external_project_facts_intake.py --repo")
    assert any("project-facts: intake artifact drift detected" in item for item in result.warnings)
    artifact.unlink()


def test_assess_external_repo_classifies_missing_project_facts() -> None:
    root = _reset_fixture("missing_project_facts")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v1.0.0-alpha")
    (target_root / "memory" / "02_project_facts.md").unlink()

    result = assess_external_repo(target_root)

    assert result.checks["project_facts_present"] is False
    assert result.checks["project_facts_intakeable"] is False
    assert result.project_facts["status"] == "missing"
    assert result.project_facts["available"] is False
    assert "No external project facts found under" in result.project_facts["reason"]
    assert result.project_facts["remediation_hint"].startswith("python governance_tools/external_project_facts_intake.py --repo")
