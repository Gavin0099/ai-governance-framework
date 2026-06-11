from __future__ import annotations

from pathlib import Path

from governance_tools.hook_install_validator import validate_hook_install
from governance_tools.hook_installer import install_governance_hooks


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework(root: Path) -> None:
    _write(root / "scripts" / "hooks" / "pre-commit", "#!/usr/bin/env bash\n# AI Governance Framework\n")
    _write(root / "scripts" / "hooks" / "pre-push", "#!/usr/bin/env bash\n# AI Governance Framework\n")
    _write(root / "scripts/lib/python.sh", "")
    _write(root / "scripts/run-runtime-governance.sh", "")
    _write(root / "governance_tools/plan_freshness.py", "")
    _write(root / "governance_tools/contract_validator.py", "")
    _write(
        root / "governance/copilot-instructions-template.md",
        "# Copilot Workspace Instructions\n<!-- AI Governance Framework: copilot-instructions v1.0 -->\n",
    )


def test_install_governance_hooks_writes_windows_safe_config_without_bom(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    (repo / ".git" / "hooks").mkdir(parents=True)
    _make_framework(framework)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    config = repo / ".git" / "hooks" / "ai-governance-framework-root"
    assert config.read_bytes().startswith(str(framework.resolve()).encode("utf-8"))
    assert not config.read_bytes().startswith(b"\xef\xbb\xbf")
    assert validate_hook_install(repo).valid is True


def test_install_governance_hooks_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    (repo / ".git" / "hooks").mkdir(parents=True)
    _make_framework(framework)

    first = install_governance_hooks(repo, framework)
    second = install_governance_hooks(repo, framework)

    assert first.ok is True
    assert second.ok is True
    assert second.changed_files == []


def test_install_governance_hooks_backs_up_unmanaged_hook(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _write(repo / ".git" / "hooks" / "pre-push", "# custom hook\n")
    _make_framework(framework)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    assert any(Path(item).name.startswith("pre-push.bak.") for item in result.backups)


def test_install_governance_hooks_hooks_only_does_not_touch_copilot(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    (repo / ".git" / "hooks").mkdir(parents=True)
    _make_framework(framework)

    result = install_governance_hooks(repo, framework, include_copilot=False)

    assert result.ok is True
    assert (repo / ".git" / "hooks" / "pre-commit").exists()
    assert (repo / ".git" / "hooks" / "pre-push").exists()
    assert (repo / ".git" / "hooks" / "ai-governance-framework-root").exists()
    assert not (repo / ".github" / "copilot-instructions.md").exists()
    assert all(".github" not in changed for changed in result.changed_files)
    assert all(".github" not in installed for installed in result.installed_files)
