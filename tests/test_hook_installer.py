from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from governance_tools.hook_install_validator import validate_hook_install
from governance_tools.hook_installer import (
    COPILOT_BLOCK_BEGIN,
    COPILOT_BLOCK_END,
    LEGACY_COPILOT_TEMPLATE_DIGESTS,
    _content_digest,
    install_copilot_instructions,
    install_governance_hooks,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

MANAGED_TEMPLATE = (
    f"{COPILOT_BLOCK_BEGIN}\n"
    "# Copilot Workspace Instructions\n"
    "<!-- AI Governance Framework: copilot-instructions v1.1 -->\n"
    "framework rules\n"
    f"{COPILOT_BLOCK_END}\n"
)


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
        '{"version":1,"hooks":{'
        '"SessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],'
        '"Stop":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
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


def _managed_framework(root: Path) -> Path:
    _make_framework(root)
    _write(root / "governance" / "copilot-instructions-template.md", MANAGED_TEMPLATE)
    return root


def _instructions(repo: Path) -> Path:
    return repo / ".github" / "copilot-instructions.md"


def test_copilot_instructions_created_when_target_is_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    assert result.copilot_instructions_mode == "created"
    assert _instructions(repo).read_text(encoding="utf-8") == MANAGED_TEMPLATE


def test_copilot_instructions_preserve_consumer_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    _write(_instructions(repo), "# House rules\n\nUse tabs, never spaces.\n")

    result = install_governance_hooks(repo, framework)

    assert result.copilot_instructions_mode == "appended"
    text = _instructions(repo).read_text(encoding="utf-8")
    assert "Use tabs, never spaces." in text
    assert "framework rules" in text
    assert text.count(COPILOT_BLOCK_BEGIN) == 1
    # The consumer's own file was not framework-written, so it is also backed up.
    assert any(Path(item).name.startswith("copilot-instructions.md.bak.") for item in result.backups)


def test_copilot_instructions_replace_only_managed_block_on_update(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    _write(_instructions(repo), "# House rules\n\nUse tabs.\n")
    install_governance_hooks(repo, framework)

    _write(
        framework / "governance" / "copilot-instructions-template.md",
        MANAGED_TEMPLATE.replace("framework rules", "framework rules v2"),
    )
    result = install_governance_hooks(repo, framework)

    assert result.copilot_instructions_mode == "replaced"
    text = _instructions(repo).read_text(encoding="utf-8")
    assert "Use tabs." in text
    assert "framework rules v2" in text
    assert "framework rules\n" not in text
    assert text.count(COPILOT_BLOCK_BEGIN) == 1


LEGACY_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "copilot_legacy_templates"


def _legacy_shipped_templates() -> list[str]:
    """Every pre-managed-block template this framework shipped, verbatim.

    These are checked in rather than read out of git history: CI clones are
    shallow, so `git log` on the template returns only the tip — which now has a
    managed block and is not legacy at all. The fixtures are the evidence for
    what a consumer may still be holding, and they work from a tarball too.
    """
    files = sorted(LEGACY_FIXTURE_DIR.glob("*.md.fixture"))
    return [path.read_text(encoding="utf-8") for path in files]


def _legacy_shipped_template() -> str:
    """One pre-managed-block template, for tests that only need a legacy file."""
    legacy = _legacy_shipped_templates()
    assert legacy, f"no legacy template fixtures in {LEGACY_FIXTURE_DIR}"
    return legacy[0]


def test_copilot_instructions_migrate_pre_managed_block_install(tmp_path: Path) -> None:
    """A whole-file install from an older framework version becomes one managed block."""
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    _write(_instructions(repo), _legacy_shipped_template())

    result = install_governance_hooks(repo, framework)

    assert result.copilot_instructions_mode == "migrated"
    text = _instructions(repo).read_text(encoding="utf-8")
    assert text == MANAGED_TEMPLATE
    assert "DONE Boundary Rules" not in text  # the old shipped rules are gone
    # Migration rewrites the whole file, so the previous content is kept.
    assert any(Path(item).name.startswith("copilot-instructions.md.bak.") for item in result.backups)


def test_edited_legacy_install_is_not_migrated_away(tmp_path: Path) -> None:
    """A hand-edited legacy file must not lose its consumer rules to migration."""
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    edited = _legacy_shipped_template().rstrip("\n") + "\n\n## House rule\n\nNever touch vendor/.\n"
    _write(_instructions(repo), edited)

    result = install_governance_hooks(repo, framework)

    assert result.ok is False
    assert any("edited after install" in error for error in result.errors)
    # The active file is untouched — the consumer rule is still where Copilot reads it.
    assert _instructions(repo).read_text(encoding="utf-8") == edited
    assert "Never touch vendor/." in _instructions(repo).read_text(encoding="utf-8")


def test_legacy_fixtures_and_pinned_digests_agree() -> None:
    """The fixtures and LEGACY_COPILOT_TEMPLATE_DIGESTS must describe the same set.

    Checked in both directions: a fixture with no pinned digest means a consumer
    would be refused, and a pinned digest with no fixture is content nothing
    verifies.
    """
    fixture_digests = {_content_digest(text) for text in _legacy_shipped_templates()}

    assert fixture_digests, f"no legacy template fixtures in {LEGACY_FIXTURE_DIR}"
    assert fixture_digests == set(LEGACY_COPILOT_TEMPLATE_DIGESTS)

    # Fixture filenames carry their own digest, so a mangled fixture is obvious.
    for path in sorted(LEGACY_FIXTURE_DIR.glob("*.md.fixture")):
        digest = _content_digest(path.read_text(encoding="utf-8"))
        assert digest.startswith(path.name.split(".")[0]), path.name


def test_every_shipped_template_digest_is_recognised_as_legacy(tmp_path: Path) -> None:
    """Each pre-managed-block template must still migrate cleanly.

    Guards LEGACY_COPILOT_TEMPLATE_DIGESTS against drift: a consumer holding any
    template this framework ever shipped must not be refused.
    """
    legacy = _legacy_shipped_templates()
    assert len(legacy) >= 2

    for index, shipped in enumerate(legacy):
        repo = tmp_path / f"repo{index}"
        framework = _managed_framework(tmp_path / f"framework{index}")
        (repo / ".git" / "hooks").mkdir(parents=True)
        _write(_instructions(repo), shipped)

        result = install_governance_hooks(repo, framework)

        assert result.ok is True, f"legacy[{index}]: {result.errors}"
        assert result.copilot_instructions_mode == "migrated", f"legacy[{index}]"


def test_managed_block_template_is_not_treated_as_legacy(tmp_path: Path) -> None:
    """The shipped template itself must take the `replaced` path, not `migrated`."""
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    current = (REPO_ROOT / "governance" / "copilot-instructions-template.md").read_text(
        encoding="utf-8"
    )
    _write(_instructions(repo), current)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    assert result.copilot_instructions_mode == "replaced"


def test_copilot_instructions_install_is_byte_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    _write(_instructions(repo), "# House rules\n\nUse tabs.\n")

    install_governance_hooks(repo, framework)
    first = _instructions(repo).read_bytes()
    second_result = install_governance_hooks(repo, framework)

    assert second_result.changed_files == []
    assert _instructions(repo).read_bytes() == first


def test_copilot_instructions_tolerate_crlf_checkout(tmp_path: Path) -> None:
    """core.autocrlf=true checkouts must not be reported as a pending change."""
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    install_governance_hooks(repo, framework)
    target = _instructions(repo)
    crlf = target.read_bytes().replace(b"\n", b"\r\n")
    target.write_bytes(crlf)

    result = install_governance_hooks(repo, framework)

    assert result.changed_files == []
    assert result.backups == []
    assert target.read_bytes() == crlf


def test_copilot_instructions_refuse_to_merge_ambiguous_markers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    damaged = MANAGED_TEMPLATE + f"{COPILOT_BLOCK_BEGIN}\nstray\n{COPILOT_BLOCK_END}\n"
    _write(_instructions(repo), damaged)

    result = install_governance_hooks(repo, framework)

    assert result.ok is False
    assert any("managed BEGIN" in error for error in result.errors)
    assert _instructions(repo).read_text(encoding="utf-8") == damaged


def test_copilot_instructions_only_leaves_git_hooks_untouched(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)

    result = install_copilot_instructions(repo, framework)

    assert result.ok is True
    assert result.copilot_instructions_mode == "created"
    assert _instructions(repo).is_file()
    assert not (repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (repo / ".git" / "hooks" / "ai-governance-framework-root").exists()


def test_legacy_template_without_markers_is_wrapped(tmp_path: Path) -> None:
    """Older framework fixtures ship an unwrapped template; it still installs."""
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)  # writes the v1.0 unwrapped template
    (repo / ".git" / "hooks").mkdir(parents=True)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    text = _instructions(repo).read_text(encoding="utf-8")
    assert text.startswith(COPILOT_BLOCK_BEGIN)
    assert text.rstrip("\n").endswith(COPILOT_BLOCK_END)


def test_shipped_template_is_a_single_managed_block() -> None:
    text = (REPO_ROOT / "governance" / "copilot-instructions-template.md").read_text(encoding="utf-8")

    assert text.count(COPILOT_BLOCK_BEGIN) == 1
    assert text.count(COPILOT_BLOCK_END) == 1
    assert text.startswith(COPILOT_BLOCK_BEGIN)


def _shell_fixture_repo(name: str) -> Path:
    """Fixture inside the repo tree: Git Bash launched from Python resolves only
    cwd-relative paths, so the target must share a drive with the script."""
    path = REPO_ROOT / "tests" / "_tmp_shell_installer" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_shell_installer_fails_loudly_when_copilot_merge_is_refused() -> None:
    """A refused merge must not exit 0 or claim the install completed."""
    repo = _shell_fixture_repo("ambiguous_markers")
    _run(["git", "init"], cwd=repo)
    damaged = (
        f"{COPILOT_BLOCK_BEGIN}\nframework rules\n{COPILOT_BLOCK_END}\n"
        f"{COPILOT_BLOCK_BEGIN}\nstray\n{COPILOT_BLOCK_END}\n"
    )
    _write(_instructions(repo), damaged)
    before = _instructions(repo).read_bytes()
    relative_target = repo.relative_to(REPO_ROOT).as_posix()

    completed = subprocess.run(
        ["bash", "scripts/install-hooks.sh", "--target", relative_target, "--no-verify"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode != 0, completed.stdout
    assert "安裝完成" not in completed.stdout
    assert "partial install" in completed.stdout
    assert _instructions(repo).read_bytes() == before
    shutil.rmtree(repo, ignore_errors=True)


def test_shell_installer_preserves_consumer_instructions_end_to_end() -> None:
    repo = _shell_fixture_repo("consumer_content")
    _run(["git", "init"], cwd=repo)
    _write(_instructions(repo), "# House rules\n\nNever touch vendor/.\n")
    relative_target = repo.relative_to(REPO_ROOT).as_posix()

    completed = subprocess.run(
        ["bash", "scripts/install-hooks.sh", "--target", relative_target, "--no-verify"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    text = _instructions(repo).read_text(encoding="utf-8")
    assert "Never touch vendor/." in text
    assert text.count(COPILOT_BLOCK_BEGIN) == 1
    assert "checkpoint-projection BEGIN" in text
    shutil.rmtree(repo, ignore_errors=True)


def test_shell_installer_delegates_copilot_merge_to_python_installer() -> None:
    text = (REPO_ROOT / "scripts" / "install-hooks.sh").read_text(encoding="utf-8")

    assert "--copilot-instructions-only" in text
    assert 'cp "$COPILOT_TEMPLATE" "$COPILOT_DST"' not in text


def test_shell_installer_deploys_copilot_lifecycle_surface() -> None:
    text = (REPO_ROOT / "scripts" / "install-hooks.sh").read_text(encoding="utf-8")
    assert "runtime_hooks/adapters/copilot/lifecycle.py" in text
    assert "ai-governance-vscode.json" in text
    assert "ai-governance-copilot.json" in text


def _lifecycle(repo: Path) -> Path:
    return repo / ".github" / "hooks" / "ai-governance-lifecycle.py"


def _vscode_config(repo: Path) -> Path:
    return repo / ".github" / "hooks" / "ai-governance-vscode.json"


def test_edited_lifecycle_bridge_is_backed_up_before_replacement(tmp_path: Path) -> None:
    """AGR-09: a consumer edit to the managed bridge must not vanish silently.

    The edited file still carries the framework marker, so a marker check alone
    would skip the backup and overwrite the edit with no record of it.
    """
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    install_governance_hooks(repo, framework)

    edited = _lifecycle(repo).read_text(encoding="utf-8") + "\n# CFU: dynamic memory pressure\n"
    _write(_lifecycle(repo), edited)

    result = install_governance_hooks(repo, framework)

    assert result.ok is True
    backups = [Path(item) for item in result.backups]
    assert any(item.name.startswith("ai-governance-lifecycle.py.bak.") for item in backups)
    kept = next(item for item in backups if item.name.startswith("ai-governance-lifecycle.py.bak."))
    assert "CFU: dynamic memory pressure" in kept.read_text(encoding="utf-8")


def test_edited_vscode_hook_config_is_backed_up_before_replacement(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    install_governance_hooks(repo, framework)
    _write(_vscode_config(repo), '{"version":1,"hooks":{"UserPromptSubmit":[]}}\n')

    result = install_governance_hooks(repo, framework)

    assert any(
        Path(item).name.startswith("ai-governance-vscode.json.bak.") for item in result.backups
    )


def test_unmodified_lifecycle_files_are_not_backed_up_on_reinstall(tmp_path: Path) -> None:
    """Framework upgrades must not litter consumer repos with backups."""
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    install_governance_hooks(repo, framework)

    # Framework ships a new bridge; the consumer never touched theirs.
    source = framework / "runtime_hooks" / "adapters" / "copilot" / "lifecycle.py"
    _write(source, source.read_text(encoding="utf-8") + "\n# upstream v2\n")

    result = install_governance_hooks(repo, framework)

    assert result.backups == []
    assert "upstream v2" in _lifecycle(repo).read_text(encoding="utf-8")


def test_managed_manifest_records_installed_lifecycle_digests(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)

    install_governance_hooks(repo, framework)

    manifest = json.loads(
        (repo / ".github" / "hooks" / ".ai-governance-managed.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == 1
    assert manifest["files"][".github/hooks/ai-governance-lifecycle.py"] == _content_digest(
        _lifecycle(repo).read_text(encoding="utf-8")
    )


def test_lifecycle_install_stays_byte_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    install_governance_hooks(repo, framework)

    second = install_governance_hooks(repo, framework)

    assert second.changed_files == []
    assert second.backups == []


def test_shipped_vscode_template_registers_session_start_and_stop() -> None:
    payload = json.loads(
        (REPO_ROOT / "governance" / "copilot-hooks-vscode-template.json").read_text(encoding="utf-8")
    )

    assert set(payload["hooks"]) == {"SessionStart", "Stop"}
    assert "--event-type session_start" in payload["hooks"]["SessionStart"][0]["command"]
    assert "--event-type session_end" in payload["hooks"]["Stop"][0]["command"]
