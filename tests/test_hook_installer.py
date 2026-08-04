from __future__ import annotations

import subprocess
from pathlib import Path

from governance_tools.hook_install_validator import validate_hook_install
from governance_tools.hook_installer import install_governance_hooks

REPO_ROOT = Path(__file__).resolve().parents[1]


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
    _write(
        root / "runtime_hooks/adapters/copilot/lifecycle.py",
        '"""Thin lifecycle bridge for VS Code and GitHub Copilot hooks."""\n',
    )
    _write(
        root / "governance/copilot-hooks-vscode-template.json",
        '{"version":1,"hooks":{"Stop":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )
    _write(
        root / "governance/copilot-hooks-session-end-template.json",
        '{"version":1,"hooks":{"sessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],"sessionEnd":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )


def _run(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return (completed.stdout or "").strip()


def test_install_governance_hooks_writes_windows_safe_config_without_bom(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    (repo / ".git" / "hooks").mkdir(parents=True)
    _make_framework(framework)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    config = repo / ".git" / "hooks" / "ai-governance-framework-root"
    expected_root = str(framework.resolve()).replace("\\", "/")
    assert config.read_bytes().startswith(expected_root.encode("utf-8"))
    assert b"\r\n" not in config.read_bytes()
    assert not config.read_bytes().startswith(b"\xef\xbb\xbf")
    validation = validate_hook_install(repo)
    assert validation.valid is True
    assert validation.checks["copilot_lifecycle_installed"] is True
    assert (repo / ".github" / "hooks" / "ai-governance-lifecycle.py").is_file()
    assert (repo / ".github" / "hooks" / "ai-governance-vscode.json").is_file()
    assert (repo / ".github" / "hooks" / "ai-governance-copilot.json").is_file()


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


def test_install_governance_hooks_normalizes_shell_hooks_to_lf(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    (repo / ".git" / "hooks").mkdir(parents=True)
    _make_framework(framework)
    for hook_name in ("pre-commit", "pre-push"):
        hook = framework / "scripts" / "hooks" / hook_name
        hook.write_bytes(hook.read_bytes().replace(b"\n", b"\r\n"))

    result = install_governance_hooks(repo, framework, include_copilot=False)

    assert result.ok is True
    for hook_name in ("pre-commit", "pre-push"):
        installed = (repo / ".git" / "hooks" / hook_name).read_bytes()
        assert b"\r\n" not in installed
        assert b"\n" in installed


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
    assert not (repo / ".github" / "hooks").exists()
    assert all(".github" not in changed for changed in result.changed_files)
    assert all(".github" not in installed for installed in result.installed_files)


def test_install_governance_hooks_uses_common_hook_dir_for_linked_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    linked = tmp_path / "linked"
    framework = tmp_path / "framework"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)
    _write(repo / "README.md", "root\n")
    _run(["git", "add", "README.md"], cwd=repo)
    _run(["git", "commit", "-m", "init"], cwd=repo)
    _run(["git", "worktree", "add", "--detach", str(linked), "HEAD"], cwd=repo)
    _make_framework(framework)

    result = install_governance_hooks(linked, framework, include_copilot=False)

    assert result.ok is True
    assert (repo / ".git" / "hooks" / "pre-commit").is_file()
    assert (repo / ".git" / "hooks" / "pre-push").is_file()
    assert (repo / ".git" / "hooks" / "ai-governance-framework-root").is_file()
    assert not (linked / ".git" / "hooks").exists()


def test_managed_hooks_resolve_target_root_from_invocation_worktree_first() -> None:
    for hook_name in ("pre-commit", "pre-push"):
        text = (REPO_ROOT / "scripts" / "hooks" / hook_name).read_text(encoding="utf-8")
        assert 'TARGET_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"' in text


def test_managed_hooks_normalize_windows_framework_paths() -> None:
    for hook_name in ("pre-commit", "pre-push"):
        text = (REPO_ROOT / "scripts" / "hooks" / hook_name).read_text(encoding="utf-8")
        assert 'case "$FRAMEWORK_ROOT" in' in text
        assert 'DRIVE_PATH="${FRAMEWORK_ROOT:2}"' in text
        assert 'FRAMEWORK_ROOT="/mnt/$DRIVE_LOWER/$DRIVE_PATH"' in text
        assert 'FRAMEWORK_PYTHON_ROOT="$FRAMEWORK_ROOT"' in text


def test_shell_installer_deploys_copilot_lifecycle_surface() -> None:
    text = (REPO_ROOT / "scripts" / "install-hooks.sh").read_text(encoding="utf-8")
    assert "runtime_hooks/adapters/copilot/lifecycle.py" in text
    assert "ai-governance-vscode.json" in text
    assert "ai-governance-copilot.json" in text
