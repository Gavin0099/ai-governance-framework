from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.external_repo_version_audit import build_report, format_human


FIXTURE_ROOT = Path("tests/_tmp_external_repo_version_audit")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _repo(root: Path, adopted_release: str | None, compatibility: str = ">=1.0.0,<2.0.0") -> Path:
    repo = root
    _write(repo / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(repo / ".git" / "hooks" / "pre-commit", "# AI Governance Framework\n")
    _write(repo / ".git" / "hooks" / "pre-push", "# AI Governance Framework\n")
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(Path(".").resolve()))
    _write(repo / "PLAN.md", "> **?敺??*: 2026-03-14\n> **Owner**: test\n> **Freshness**: Sprint (7d)\n")
    _write(repo / "AGENTS.md", "# Agents\n")
    _write(repo / "CHECKLIST.md", "# Checklist\n")
    _write(repo / "rules/domain/safety.md", "# rule\n")
    _write(repo / "validators/checker.py", "print('ok')\n")
    _write(
        repo / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
                "plugin_version: \"1.0.0\"",
                "framework_interface_version: \"1\"",
                f"framework_compatible: \"{compatibility}\"",
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
    if adopted_release is not None:
        payload = {
            "framework_repo": "https://github.com/Gavin0099/ai-governance-framework.git",
            "adopted_release": adopted_release,
            "adopted_commit": "abcdef123456",
            "framework_interface_version": "1",
            "framework_compatible": compatibility,
        }
        _write(repo / "governance" / "framework.lock.json", json.dumps(payload, indent=2))
    return repo


def test_build_report_counts_version_states() -> None:
    root = _reset_fixture("state_counts")
    current_repo = _repo(root / "current", "v1.1.0")
    outdated_repo = _repo(root / "outdated", "v0.9.0")
    unknown_repo = _repo(root / "unknown", None)

    report = build_report([current_repo, outdated_repo, unknown_repo])

    assert report["repo_count"] == 3
    assert report["state_counts"]["current"] == 1
    assert report["state_counts"]["outdated"] == 1
    assert report["state_counts"]["unknown"] == 1


def test_format_human_lists_repo_rows() -> None:
    root = _reset_fixture("human_rows")
    current_repo = _repo(root / "current", "v1.1.0")
    report = build_report([current_repo])

    rendered = format_human(report)

    assert "[external_repo_version_audit]" in rendered
    assert "[repos]" in rendered
    assert "state=current" in rendered
    assert "source_ok=True" in rendered
