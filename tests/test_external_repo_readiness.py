from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date as _date
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
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
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
    _write_lock(target_root, "v1.1.0")

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
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
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
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
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


def test_assess_external_repo_ready_without_hooks() -> None:
    """Hooks are optional — missing hooks must not block readiness_ready."""
    root = _reset_fixture("without_git_hooks_installed")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    # Set up target repo WITHOUT any hooks
    _write(
        target_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n",
    )
    _write(target_root / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(target_root / "AGENTS.md", "# Agents\n")
    _write(target_root / "CHECKLIST.md", "# Checklist\n")
    _write(target_root / "memory" / "02_project_facts.md", "# Project Facts\n\n- target_os: linux\n")
    _write(target_root / "rules/domain/safety.md", "# rule\n")
    _write(target_root / "validators/checker.py", "print('ok')\n")
    _write(
        target_root / "contract.yaml",
        "name: test-no-hooks\ndomain: firmware\nplugin_version: \"1.0.0\"\n"
        "framework_interface_version: \"1\"\nframework_compatible: \">=1.0.0,<2.0.0\"\n"
        "documents:\n  - CHECKLIST.md\nai_behavior_override:\n  - AGENTS.md\nvalidators:\nrule_roots:\n",
    )
    _write_lock(target_root, "v1.0.0-alpha")

    result = assess_external_repo(target_root, framework_root=framework_root)

    assert result.checks["hooks_ready"] is False
    assert result.ready is True, (
        "hooks_ready=False must not block readiness_ready — "
        f"actual ready={result.ready}, errors={result.errors}"
    )
    # hooks warnings are prefixed "hooks (optional):" — label is visible in output
    hooks_warnings = [w for w in result.warnings if w.startswith("hooks")]
    assert hooks_warnings, "expected at least one hooks warning"
    assert all("optional" in w for w in hooks_warnings), (
        f"hooks warnings should include '(optional)': {hooks_warnings}"
    )


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
    assert result.project_facts["memory_schema_status"] == "partial"
    assert result.checks["project_facts_schema_complete"] is False
    assert result.project_facts["sync_direction"] == "external_to_framework"
    assert result.project_facts["artifact_path"].replace("/", "\\").endswith(r"artifacts\external-project-facts\target.json")
    assert result.project_facts["artifact_exists"] is False
    assert result.project_facts["reason"] is None
    assert result.project_facts["remediation_hint"] is None
    assert any("project-facts: intake succeeded with partial memory schema" in item for item in result.warnings)


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


# ── Governance drift integration tests ───────────────────────────────────────

AGENTS_BASE_CONTENT = Path("baselines/repo-min/AGENTS.base.md").read_text(encoding="utf-8")


def _write_valid_baseline_yaml(target_root: Path, agents_base_path: Path) -> None:
    sha = hashlib.sha256(agents_base_path.read_bytes()).hexdigest()
    plan_path = target_root / "PLAN.md"
    contract_path = target_root / "contract.yaml"
    agents_md_path = target_root / "AGENTS.md"
    plan_sha = hashlib.sha256(plan_path.read_bytes()).hexdigest() if plan_path.exists() else "0" * 64
    contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest() if contract_path.exists() else "0" * 64
    agents_md_sha = hashlib.sha256(agents_md_path.read_bytes()).hexdigest() if agents_md_path.exists() else "0" * 64
    baseline = (
        "schema_version: \"1\"\n"
        "baseline_version: 1.0.0\n"
        "source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        "initialized_at: 2026-03-21T00:00:00Z\n"
        "initialized_by: scripts/init-governance.sh\n"
        f"sha256.AGENTS.base.md: {sha}\n"
        f"sha256.PLAN.md: {plan_sha}\n"
        f"sha256.contract.yaml: {contract_sha}\n"
        f"sha256.AGENTS.md: {agents_md_sha}\n"
        "overridable.AGENTS.base.md: protected\n"
        "overridable.PLAN.md: overridable\n"
        "overridable.contract.yaml: overridable\n"
        "overridable.AGENTS.md: overridable\n"
        "contract_required_fields:\n"
        "  - name\n"
        "  - framework_interface_version\n"
        "  - framework_compatible\n"
        "  - domain\n"
        "plan_required_sections:\n"
        "  - \"## Current Phase\"\n"
        "  - \"## Active Sprint\"\n"
        "  - \"## Backlog\"\n"
    )
    gov_dir = target_root / ".governance"
    gov_dir.mkdir(exist_ok=True)
    (gov_dir / "baseline.yaml").write_text(baseline, encoding="utf-8")


def test_governance_drift_field_present_when_no_baseline() -> None:
    root = _reset_fixture("governance_drift_no_baseline")
    target_root = root / "target"
    _write(target_root / ".git" / "HEAD", "ref: refs/heads/main\n")

    result = assess_external_repo(target_root)

    assert result.governance_drift is not None
    assert result.governance_drift["severity"] == "critical"
    assert result.checks["governance_baseline_present"] is False
    assert result.checks["governance_drift_clean"] is False
    # non-blocking — repo may simply not have adopted the baseline yet
    assert result.ready is False  # already False for other reasons, but drift is non-blocking


def test_governance_drift_clean_repo_passes() -> None:
    root = _reset_fixture("governance_drift_clean")
    framework_root = root / "framework"
    target_root = root / "target"

    _make_framework(framework_root)
    _make_target_repo(target_root, framework_root)
    _write_lock(target_root, "v1.0.0-alpha")

    # Write AGENTS.base.md (protected, exact content)
    agents_base = target_root / "AGENTS.base.md"
    agents_base.write_text(AGENTS_BASE_CONTENT, encoding="utf-8")

    # Overwrite PLAN.md with sections the drift checker requires
    _write(
        target_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\nAlpha\n\n## Active Sprint\n- task\n\n## Backlog\n- item\n",
    )

    # Overwrite AGENTS.md with minimal skeleton
    _write(target_root / "AGENTS.md", "# AGENTS.md\n<!-- governance-baseline: overridable -->\n")

    _write_valid_baseline_yaml(target_root, agents_base)

    result = assess_external_repo(target_root)

    assert result.governance_drift is not None
    assert result.checks["governance_baseline_present"] is True
    assert result.governance_drift["severity"] in {"ok", "warning"}  # freshness warning is ok


def test_governance_drift_surfaces_in_format_human() -> None:
    root = _reset_fixture("governance_drift_human_output")
    target_root = root / "target"
    _write(target_root / ".git" / "HEAD", "ref: refs/heads/main\n")

    result = assess_external_repo(target_root)
    rendered = format_human(result)

    assert "[governance_drift]" in rendered
    assert "authoritative" in rendered  # role label present
    assert "severity" in rendered
    # governance_drift must appear before [contract] in output
    drift_pos = rendered.find("[governance_drift]")
    contract_pos = rendered.find("[contract]")
    if contract_pos != -1:
        assert drift_pos < contract_pos, "governance_drift section must appear before [contract]"


def test_governance_drift_surfaces_in_format_json() -> None:
    from governance_tools.external_repo_readiness import format_json

    root = _reset_fixture("governance_drift_json_output")
    target_root = root / "target"
    _write(target_root / ".git" / "HEAD", "ref: refs/heads/main\n")

    result = assess_external_repo(target_root)
    payload = json.loads(format_json(result))

    assert "governance_drift" in payload
    assert payload["governance_drift"]["severity"] == "critical"
