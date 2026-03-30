from __future__ import annotations

import json
import shutil
from datetime import date as _date
from pathlib import Path

from governance_tools.external_repo_onboarding_report import (
    build_onboarding_report,
    format_human,
    write_report_bundle,
)


FIXTURE_ROOT = Path("tests/_tmp_external_repo_onboarding_report")


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


def _make_contract_repo(repo_root: Path, framework_root: Path) -> None:
    hook_dir = repo_root / ".git" / "hooks"
    _make_framework(framework_root)
    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(hook_dir / "ai-governance-framework-root", str(framework_root))
    _write(
        repo_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(repo_root / "AGENTS.md", "# Agents\n")
    _write(repo_root / "CHECKLIST.md", "# Checklist\n")
    _write(repo_root / "memory" / "02_project_facts.md", "# Project Facts\n\n- target_os: windows\n")
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


def test_build_onboarding_report_combines_readiness_and_smoke() -> None:
    root = _reset_fixture("combined_report")
    framework_root = root / "framework"
    repo_root = root / "target"

    _make_contract_repo(repo_root, framework_root)

    report = build_onboarding_report(repo_root)

    assert report.ok is True
    assert report.readiness["ready"] is True
    assert report.smoke["ok"] is True
    assert report.smoke["rules"] == ["common", "firmware"]
    assert report.readiness["project_facts"]["status"] == "available"
    assert report.readiness["project_facts"]["source_filename"] == "02_project_facts.md"
    assert report.readiness["project_facts"]["artifact_path"].replace("/", "\\").endswith(r"artifacts\external-project-facts\target.json")


def test_format_human_surfaces_readiness_and_smoke_sections() -> None:
    root = _reset_fixture("human_output")
    repo_root = root / "target"
    _write(repo_root / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(repo_root / "memory" / "02_project_facts.md", "# Project Facts\n\n- target_os: windows\n")

    report = build_onboarding_report(repo_root)
    rendered = format_human(report)

    assert "External Repo Onboarding Report" in rendered
    assert "project_facts      = status=available" in rendered
    assert "[readiness]" in rendered
    assert "[project_facts]" in rendered
    assert "status" in rendered
    assert "artifact_path" in rendered
    assert "artifact_drift" in rendered
    assert "remediation_hint" in rendered
    assert "[smoke]" in rendered
    assert "errors:" in rendered


def test_write_report_bundle_creates_latest_history_and_index() -> None:
    root = _reset_fixture("bundle_output")
    framework_root = root / "framework"
    repo_root = root / "target"

    _make_contract_repo(repo_root, framework_root)

    report = build_onboarding_report(repo_root)
    bundle = write_report_bundle(report, repo_root / "memory" / "governance_onboarding")

    assert Path(bundle["latest_json"]).is_file()
    assert Path(bundle["latest_txt"]).is_file()
    assert Path(bundle["history_json"]).is_file()
    assert Path(bundle["history_txt"]).is_file()
    assert Path(bundle["index_txt"]).is_file()

    latest_payload = json.loads(Path(bundle["latest_json"]).read_text(encoding="utf-8"))
    assert latest_payload["ok"] is True
    assert latest_payload["readiness"]["project_facts"]["source_filename"] == "02_project_facts.md"
    assert latest_payload["readiness"]["project_facts"]["artifact_path"].replace("/", "\\").endswith(r"artifacts\external-project-facts\target.json")
    index_text = Path(bundle["index_txt"]).read_text(encoding="utf-8")
    assert "[external_repo_onboarding_index]" in index_text
    assert "ok=True" in index_text
