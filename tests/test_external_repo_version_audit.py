from __future__ import annotations

import json
from pathlib import Path

from governance_tools.external_repo_version_audit import build_report, format_human


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
            "framework_repo": "https://github.com/GavinWu672/ai-governance-framework",
            "adopted_release": adopted_release,
            "adopted_commit": "abcdef123456",
            "framework_interface_version": "1",
            "framework_compatible": compatibility,
        }
        _write(repo / "governance" / "framework.lock.json", json.dumps(payload, indent=2))
    return repo


def test_build_report_counts_version_states(tmp_path: Path) -> None:
    current_repo = _repo(tmp_path / "current", "v1.0.0-alpha")
    outdated_repo = _repo(tmp_path / "outdated", "v0.9.0")
    unknown_repo = _repo(tmp_path / "unknown", None)

    report = build_report([current_repo, outdated_repo, unknown_repo])

    assert report["repo_count"] == 3
    assert report["state_counts"]["current"] == 1
    assert report["state_counts"]["outdated"] == 1
    assert report["state_counts"]["unknown"] == 1


def test_format_human_lists_repo_rows(tmp_path: Path) -> None:
    current_repo = _repo(tmp_path / "current", "v1.0.0-alpha")
    report = build_report([current_repo])

    rendered = format_human(report)

    assert "[external_repo_version_audit]" in rendered
    assert "[repos]" in rendered
    assert "state=current" in rendered
