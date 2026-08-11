from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from governance_tools.copilot_instructions_projection import (
    CANONICAL_SECTION_HEADING,
    PROJECTION_END,
    render_projection_block,
    extract_canonical_section,
)
from governance_tools.hook_install_validator import (
    COPILOT_BLOCK_BEGIN,
    COPILOT_BLOCK_END,
    format_human,
    validate_hook_install,
)


FIXTURE_ROOT = Path("tests/_tmp_hook_install_validator")

_CANONICAL_SYSTEM_PROMPT = f"""# SYSTEM_PROMPT.md

{CANONICAL_SECTION_HEADING}

在以下時點輸出此 block：
- task 開始
- milestone 完成

若只是 routine progress commentary 且 state 未變，可省略。

## 3. Next Section
"""


def _governed_instructions(system_prompt_text: str) -> str:
    """A .github/copilot-instructions.md as the current installer would write it."""
    block = render_projection_block(extract_canonical_section(system_prompt_text))
    return (
        f"{COPILOT_BLOCK_BEGIN}\n"
        "# Copilot Workspace Instructions\n"
        "<!-- AI Governance Framework: copilot-instructions v1.1 -->\n"
        f"{block}\n"
        f"{COPILOT_BLOCK_END}\n"
    )


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


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


def test_validate_hook_install_accepts_framework_root_with_bom_prefix() -> None:
    root = _reset_fixture("framework_root_bom_prefix")
    repo_root = root / "target"
    hook_dir = repo_root / ".git" / "hooks"
    framework_root = root / "framework"

    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    hook_dir.mkdir(parents=True, exist_ok=True)
    # Deliberately write BOM-prefixed path to simulate hidden-char corruption.
    (hook_dir / "ai-governance-framework-root").write_text(
        "\ufeff" + str(framework_root.resolve()),
        encoding="utf-8",
    )

    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["framework_root_config_present"] is True
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


def test_copilot_instructions_missing_is_warning_not_error() -> None:
    """Missing .github/copilot-instructions.md is a warning, not a blocking error."""
    root = _reset_fixture("copilot_instructions_missing")
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
    # NOTE: no .github/copilot-instructions.md

    result = validate_hook_install(repo_root)

    assert result.valid is True  # still valid — copilot check is warning only
    assert result.checks["copilot_instructions_present"] is False
    assert result.checks["copilot_instructions_governed"] is False
    assert any("copilot-instructions.md not found" in w for w in result.warnings)


def test_copilot_instructions_governed_version_passes() -> None:
    """Governed copilot-instructions.md (deployed by framework) passes check."""
    root = _reset_fixture("copilot_instructions_governed")
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
    _write(framework_root / "governance" / "SYSTEM_PROMPT.md", _CANONICAL_SYSTEM_PROMPT)
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        _governed_instructions(_CANONICAL_SYSTEM_PROMPT),
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["copilot_instructions_present"] is True
    assert result.checks["copilot_instructions_governed"] is True
    assert result.checks["copilot_checkpoint_projection_present"] is True
    assert result.checks["copilot_checkpoint_version_current"] is True
    assert result.checks["copilot_checkpoint_matches_canonical"] is True
    assert not any("copilot-instructions" in w for w in result.warnings)


def test_copilot_instructions_non_governed_version_warns() -> None:
    """Non-governed copilot-instructions.md (not from framework) triggers warning."""
    root = _reset_fixture("copilot_instructions_non_governed")
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
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        "# Custom Copilot Instructions (not from governance framework)\n",
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True  # still valid
    assert result.checks["copilot_instructions_present"] is True
    assert result.checks["copilot_instructions_governed"] is False
    assert any("not deployed by AI Governance Framework" in w for w in result.warnings)


def _checkpoint_fixture(name: str) -> tuple[Path, Path]:
    root = _reset_fixture(name)
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
    _write(framework_root / "governance" / "SYSTEM_PROMPT.md", _CANONICAL_SYSTEM_PROMPT)
    return repo_root, framework_root


def test_marker_without_checkpoint_projection_warns() -> None:
    """A governed marker is not evidence that the checkpoint rules are installed."""
    repo_root, _ = _checkpoint_fixture("copilot_checkpoint_absent")
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        f"{COPILOT_BLOCK_BEGIN}\n"
        "<!-- AI Governance Framework: copilot-instructions v1.0 -->\n"
        "rules without a projection\n"
        f"{COPILOT_BLOCK_END}\n",
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True  # report-only
    assert result.checks["copilot_instructions_governed"] is True
    assert result.checks["copilot_checkpoint_projection_present"] is False
    assert result.checks["copilot_checkpoint_version_current"] is False
    assert any("no usable checkpoint projection" in w for w in result.warnings)


def test_stale_checkpoint_projection_warns_without_blocking() -> None:
    repo_root, _ = _checkpoint_fixture("copilot_checkpoint_stale")
    governed = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        governed.replace("version=1.1", "version=1.0"),
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["copilot_checkpoint_projection_present"] is True
    assert result.checks["copilot_checkpoint_version_current"] is False
    assert any("checkpoint projection is version 1.0" in w for w in result.warnings)


def test_checkpoint_projection_drift_from_canonical_warns() -> None:
    repo_root, framework_root = _checkpoint_fixture("copilot_checkpoint_drift")
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        _governed_instructions(_CANONICAL_SYSTEM_PROMPT),
    )
    _write(
        framework_root / "governance" / "SYSTEM_PROMPT.md",
        _CANONICAL_SYSTEM_PROMPT.replace("- milestone 完成", "- milestone 完成\n- scope 改變"),
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["copilot_checkpoint_matches_canonical"] is False
    assert any("does not match" in w for w in result.warnings)


def test_duplicate_managed_blocks_warn() -> None:
    repo_root, _ = _checkpoint_fixture("copilot_managed_block_duplicate")
    governed = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    _write(repo_root / ".github" / "copilot-instructions.md", governed + governed)

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["copilot_instructions_managed_block_unique"] is False
    assert any("managed BEGIN" in w for w in result.warnings)


def test_edited_projection_body_with_intact_header_fails_canonical_check() -> None:
    """The header is a claim; the body that shipped is the evidence."""
    repo_root, _ = _checkpoint_fixture("copilot_checkpoint_body_edited")
    governed = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    gutted = governed.replace("- milestone 完成\n", "")
    assert gutted != governed
    _write(repo_root / ".github" / "copilot-instructions.md", gutted)

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_checkpoint_projection_present"] is True
    assert result.checks["copilot_checkpoint_version_current"] is True
    assert result.checks["copilot_checkpoint_body_matches_header"] is False
    assert result.checks["copilot_checkpoint_matches_canonical"] is False
    assert any("body does not match its own header" in w for w in result.warnings)


def test_removed_projection_body_with_intact_header_is_detected() -> None:
    repo_root, _ = _checkpoint_fixture("copilot_checkpoint_body_removed")
    governed = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    header = next(line for line in governed.split("\n") if "checkpoint-projection BEGIN" in line)
    hollow = (
        f"{COPILOT_BLOCK_BEGIN}\n"
        "<!-- AI Governance Framework: copilot-instructions v1.1 -->\n"
        f"{header}\n"
        f"{PROJECTION_END}\n"
        f"{COPILOT_BLOCK_END}\n"
    )
    _write(repo_root / ".github" / "copilot-instructions.md", hollow)

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_checkpoint_body_matches_header"] is False
    assert result.checks["copilot_checkpoint_matches_canonical"] is False


def test_reversed_managed_block_markers_are_not_unique() -> None:
    repo_root, _ = _checkpoint_fixture("copilot_managed_block_reversed")
    body = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    inner = "\n".join(
        line
        for line in body.split("\n")
        if line.strip() not in (COPILOT_BLOCK_BEGIN, COPILOT_BLOCK_END)
    )
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        f"{COPILOT_BLOCK_END}\n{inner}\n{COPILOT_BLOCK_BEGIN}\n",
    )

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_instructions_managed_block_unique"] is False
    assert any("END precedes BEGIN" in w for w in result.warnings)


def test_projection_outside_managed_block_is_reported() -> None:
    repo_root, _ = _checkpoint_fixture("copilot_projection_outside_block")
    governed = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    block_only = f"{COPILOT_BLOCK_BEGIN}\nframework rules\n{COPILOT_BLOCK_END}\n"
    projection = governed.split(COPILOT_BLOCK_BEGIN)[1].split(COPILOT_BLOCK_END)[0]
    _write(repo_root / ".github" / "copilot-instructions.md", block_only + projection)

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_checkpoint_projection_present"] is True
    assert result.checks["copilot_checkpoint_projection_inside_managed_block"] is False
    assert any("outside the framework-managed block" in w for w in result.warnings)


def test_unexpected_projection_source_is_reported() -> None:
    repo_root, _ = _checkpoint_fixture("copilot_projection_source")
    governed = _governed_instructions(_CANONICAL_SYSTEM_PROMPT)
    _write(
        repo_root / ".github" / "copilot-instructions.md",
        governed.replace("source=governance/SYSTEM_PROMPT.md#2.8", "source=vendor/OTHER.md#9.9"),
    )

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_checkpoint_source_expected"] is False
    assert any("claims source vendor/OTHER.md#9.9" in w for w in result.warnings)


def test_projection_checks_are_present_even_when_unverifiable() -> None:
    """Unverifiable must read as False, never as an absent key."""
    root = _reset_fixture("copilot_projection_unverifiable")
    repo_root = root / "target"
    _write(repo_root / ".git" / "hooks" / "pre-commit", "# AI Governance Framework\n")
    _write(repo_root / ".git" / "hooks" / "pre-push", "# AI Governance Framework\n")

    result = validate_hook_install(repo_root)

    for key in (
        "copilot_instructions_managed_block_unique",
        "copilot_checkpoint_projection_present",
        "copilot_checkpoint_projection_inside_managed_block",
        "copilot_checkpoint_source_expected",
        "copilot_checkpoint_version_current",
        "copilot_checkpoint_body_matches_header",
        "copilot_checkpoint_matches_canonical",
    ):
        assert result.checks[key] is False, key


def test_managed_copilot_lifecycle_surface_is_observable_and_advisory() -> None:
    root = _reset_fixture("copilot_lifecycle_managed")
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
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-lifecycle.py",
        '"""Thin lifecycle bridge for VS Code and GitHub Copilot hooks."""\n',
    )
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-vscode.json",
        '{"version":1,"hooks":{'
        '"SessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],'
        '"Stop":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-copilot.json",
        '{"version":1,"hooks":{"sessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],"sessionEnd":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["copilot_lifecycle_installed"] is True
    assert not any("lifecycle hooks are not fully installed" in warning for warning in result.warnings)


def test_missing_copilot_lifecycle_surface_warns_without_blocking() -> None:
    root = _reset_fixture("copilot_lifecycle_missing")
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
    assert result.checks["copilot_lifecycle_installed"] is False
    assert any("lifecycle hooks are not fully installed" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "invalid_entry",
    [
        {
            "type": "command",
            "command": "python .github/hooks/ai-governance-lifecycle.py "
            "--event-type session_start --surface auto",
        },
        {
            "type": "command",
            "command": "python .github/hooks/ai-governance-lifecycle.py "
            "--event-type session_end --surface vscode",
        },
        {
            "type": "http",
            "command": "python .github/hooks/ai-governance-lifecycle.py "
            "--event-type session_end --surface auto",
        },
        {
            "type": "command",
            "command": "python .github/hooks/ai-governance-lifecycle.py",
        },
    ],
)
def test_invalid_lifecycle_routing_never_reports_installed(
    invalid_entry: dict[str, str],
) -> None:
    root = _reset_fixture("copilot_lifecycle_invalid_routing")
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
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-lifecycle.py",
        '"""Thin lifecycle bridge for VS Code and GitHub Copilot hooks."""\n',
    )
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-vscode.json",
        json.dumps({"version": 1, "hooks": {"Stop": [invalid_entry]}}),
    )
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-copilot.json",
        '{"version":1,"hooks":{"sessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],"sessionEnd":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )

    result = validate_hook_install(repo_root)

    assert result.valid is True
    assert result.checks["copilot_lifecycle_installed"] is False


def test_validate_hook_install_resolves_common_hooks_for_linked_worktree(tmp_path: Path) -> None:
    root = tmp_path / "linked_worktree_hooks"
    repo_root = root / "repo"
    linked_worktree = root / "linked"
    framework_root = root / "framework"

    repo_root.mkdir(parents=True)
    _run(["git", "init"], cwd=repo_root)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo_root)
    _run(["git", "config", "user.name", "Test User"], cwd=repo_root)
    _write(repo_root / "README.md", "root\n")
    _run(["git", "add", "README.md"], cwd=repo_root)
    _run(["git", "commit", "-m", "init"], cwd=repo_root)
    _run(["git", "worktree", "add", "--detach", str(linked_worktree), "HEAD"], cwd=repo_root)

    hook_dir = repo_root / ".git" / "hooks"
    _write(hook_dir / "pre-commit", "# AI Governance Framework\n")
    _write(hook_dir / "pre-push", "# AI Governance Framework\n")
    _write(hook_dir / "ai-governance-framework-root", str(framework_root))
    _write(framework_root / "scripts/lib/python.sh", "")
    _write(framework_root / "scripts/run-runtime-governance.sh", "")
    _write(framework_root / "governance_tools/plan_freshness.py", "")
    _write(framework_root / "governance_tools/contract_validator.py", "")

    result = validate_hook_install(linked_worktree)

    assert result.valid is True
    assert result.hook_dir == str((repo_root / ".git" / "hooks").resolve())
    assert result.checks["git_hooks_dir_present"] is True
    assert result.checks["pre_commit_installed"] is True
    assert result.checks["pre_push_installed"] is True


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


def _lifecycle_surface(repo_root: Path, vscode_hooks: str) -> None:
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-lifecycle.py",
        '"""Thin lifecycle bridge for VS Code and GitHub Copilot hooks."""\n',
    )
    _write(repo_root / ".github" / "hooks" / "ai-governance-vscode.json", vscode_hooks)
    _write(
        repo_root / ".github" / "hooks" / "ai-governance-copilot.json",
        '{"version":1,"hooks":{'
        '"sessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],'
        '"sessionEnd":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )


_VSCODE_GOVERNED = (
    '{"version":1,"hooks":{'
    '"SessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],'
    '"Stop":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n'
)


def test_vscode_session_start_plus_stop_is_governed() -> None:
    """AGR-09 §3.3: declaring SessionStart must not mark the config unmanaged."""
    repo_root, _ = _checkpoint_fixture("vscode_session_start")
    _lifecycle_surface(repo_root, _VSCODE_GOVERNED)

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_vscode_hooks_governed"] is True
    assert result.checks["copilot_lifecycle_installed"] is True


def test_vscode_config_tolerates_extra_consumer_events() -> None:
    """A consumer hook the framework does not manage must not fail the check."""
    repo_root, _ = _checkpoint_fixture("vscode_extra_event")
    extra = json.loads(_VSCODE_GOVERNED)
    extra["hooks"]["UserPromptSubmit"] = [{"type": "command", "command": "python ./local-check.py"}]
    _lifecycle_surface(repo_root, json.dumps(extra))

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_vscode_hooks_governed"] is True


def test_vscode_config_missing_session_start_is_not_governed() -> None:
    """Dropping a managed event must still be caught."""
    repo_root, _ = _checkpoint_fixture("vscode_missing_session_start")
    only_stop = json.loads(_VSCODE_GOVERNED)
    del only_stop["hooks"]["SessionStart"]
    _lifecycle_surface(repo_root, json.dumps(only_stop))

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_vscode_hooks_governed"] is False


def test_vscode_config_with_wrong_event_wiring_is_not_governed() -> None:
    repo_root, _ = _checkpoint_fixture("vscode_wrong_wiring")
    miswired = json.loads(_VSCODE_GOVERNED)
    miswired["hooks"]["SessionStart"][0]["command"] = (
        "python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"
    )
    _lifecycle_surface(repo_root, json.dumps(miswired))

    result = validate_hook_install(repo_root)

    assert result.checks["copilot_vscode_hooks_governed"] is False
