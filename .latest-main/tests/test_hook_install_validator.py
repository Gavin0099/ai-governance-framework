from __future__ import annotations

import shutil
from pathlib import Path

from governance_tools.hook_install_validator import format_human, validate_hook_install


FIXTURE_ROOT = Path("tests/_tmp_hook_install_validator")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_validate_hook_install_accepts_framework_backed_external_repo() -> None:
    root = _reset_fixture("framework_backed_repo")
    repo_root = root / "target"
    hook_dir = repo_root / ".git" / "hooks"
    framework_root = root / "framework"

    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(hook_dir / "ai-governance-framework-root", str(framework_root))

    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.framework_root == str(framework_root.resolve())
    assert result.checks["pre_commit_installed"] is True
    assert result.checks["pre_push_installed"] is True
    assert result.checks["framework_file:scripts/lib/python.sh"] is True


def test_validate_hook_install_reports_missing_framework_config() -> None:
    root = _reset_fixture("missing_framework_config")
    repo_root = root / "target"
    hook_dir = repo_root / ".git" / "hooks"

    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")

    result = validate_hook_install(repo_root)

    assert result.valid is False
    assert result.framework_root == str(repo_root.resolve())
    assert result.checks["framework_root_config_present"] is False
    assert any("ai-governance-framework-root" in warning for warning in result.warnings)


def test_validate_hook_install_accepts_explicit_framework_root_without_config() -> None:
    root = _reset_fixture("explicit_framework_root")
    repo_root = root / "target"
    hook_dir = repo_root / ".git" / "hooks"
    framework_root = root / "framework"

    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")

    result = validate_hook_install(repo_root, framework_root=framework_root)

    assert result.valid is True
    assert result.framework_root == str(framework_root.resolve())
    assert result.checks["framework_root_config_present"] is False
    assert any("using explicit framework root" in warning for warning in result.warnings)


def test_validate_hook_install_accepts_git_bash_framework_root_config() -> None:
    root = _reset_fixture("git_bash_framework_root")
    repo_root = root / "target"
    hook_dir = repo_root / ".git" / "hooks"
    framework_root = root / "framework"

    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    git_bash_path = framework_root.resolve().as_posix()
    if len(git_bash_path) >= 3 and git_bash_path[1:3] == ":/":
        git_bash_path = f"/{git_bash_path[0].lower()}/{git_bash_path[3:]}"
    _write(hook_dir / "ai-governance-framework-root", git_bash_path)

    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.framework_root == str(framework_root.resolve())
    assert result.checks["framework_root_exists"] is True


def test_validate_hook_install_accepts_self_hosted_framework_repo() -> None:
    root = _reset_fixture("self_hosted_repo")
    repo_root = root / "framework"
    hook_dir = repo_root / ".git" / "hooks"

    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(repo_root / "scripts/lib/python.sh", "")
    _write(repo_root / "scripts/run-runtime-governance.sh", "")
    _write(repo_root / "governance_tools/plan_freshness.py", "")
    _write(repo_root / "governance_tools/contract_validator.py", "")

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.framework_root == str(repo_root.resolve())
    assert result.checks["framework_root_config_present"] is False


def test_format_human_includes_framework_root_and_errors() -> None:
    root = _reset_fixture("human_output")
    repo_root = root / "target"
    hook_dir = repo_root / ".git" / "hooks"
    _write(hook_dir / "pre-commit", "not ours\n")

    result = validate_hook_install(repo_root)
    rendered = format_human(result)

    assert "framework_root" in rendered
    assert "errors:" in rendered
    assert "missing AI Governance pre-push hook" in rendered
