from __future__ import annotations

from pathlib import Path

from governance_tools.external_repo_onboarding_report import build_onboarding_report, format_human


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework(framework_root: Path) -> None:
    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")


def test_build_onboarding_report_combines_readiness_and_smoke(tmp_path: Path) -> None:
    framework_root = tmp_path / "framework"
    repo_root = tmp_path / "target"
    hook_dir = repo_root / ".git" / "hooks"

    _make_framework(framework_root)
    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(hook_dir / "ai-governance-framework-root", str(framework_root))
    _write(
        repo_root / "PLAN.md",
        "> **最後更新**: 2026-03-15\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(repo_root / "AGENTS.md", "# Agents\n")
    _write(repo_root / "CHECKLIST.md", "# Checklist\n")
    _write(repo_root / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(repo_root / "validators" / "check.py", "def x():\n    return True\n")
    _write(
        repo_root / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
                "documents:",
                "  - CHECKLIST.md",
                "ai_behavior_override:",
                "  - AGENTS.md",
                "rule_roots:",
                "  - rules",
                "validators:",
                "  - validators/check.py",
            ]
        ),
    )

    report = build_onboarding_report(repo_root)

    assert report.ok is True
    assert report.readiness["ready"] is True
    assert report.smoke["ok"] is True
    assert report.smoke["rules"] == ["common", "firmware"]


def test_format_human_surfaces_readiness_and_smoke_sections(tmp_path: Path) -> None:
    repo_root = tmp_path / "target"
    _write(repo_root / ".git" / "HEAD", "ref: refs/heads/main\n")

    report = build_onboarding_report(repo_root)
    rendered = format_human(report)

    assert "External Repo Onboarding Report" in rendered
    assert "[readiness]" in rendered
    assert "[smoke]" in rendered
    assert "errors:" in rendered
