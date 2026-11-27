from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools import hook_installer
from governance_tools.copilot_instructions_projection import extract_projection_region
from governance_tools.external_tree_inventory_guard import (
    IDENTITY_CONFIG_REL,
    IDENTITY_CONFIG_SCHEMA,
    REPOSITORY_ROOT_TOKEN,
)
from governance_tools.hook_install_validator import VSCODE_MANAGED_STOP_ENTRY, validate_hook_install
from governance_tools.hook_installer import (
    AGENT_CONTRACT_BLOCK_BEGIN,
    AGENT_CONTRACT_BLOCK_END,
    COPILOT_BLOCK_BEGIN,
    COPILOT_BLOCK_END,
    LEGACY_COPILOT_TEMPLATE_DIGESTS,
    _content_digest,
    install_claude_instructions,
    install_copilot_instructions,
    install_external_tree_identity_config,
    install_governance_hooks as _install_governance_hooks,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_REPOSITORY_ID = "example.test/governance-consumer"
_WINDOWS_GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH_COMMAND = (
    str(_WINDOWS_GIT_BASH)
    if os.name == "nt" and _WINDOWS_GIT_BASH.is_file()
    else (shutil.which("bash") or "bash")
)

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


def install_governance_hooks(
    repo_root: Path,
    framework_root: Path,
    **kwargs: object,
):
    """Keep legacy fixtures explicit now that identity-free install fails closed."""

    kwargs.setdefault("repository_identities", (TEST_REPOSITORY_ID,))
    return _install_governance_hooks(repo_root, framework_root, **kwargs)


def _make_framework(root: Path) -> None:
    # This fixture's stub pre-push does not run default self-smoke.
    _write(root / ".governance/version_manifest.yaml", "default_self_smoke_contract_dependency: not_applicable\n")
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
        (REPO_ROOT / "governance/copilot-hooks-vscode-template.json").read_text(encoding="utf-8"),
    )
    _write(
        root / "governance/copilot-hooks-session-end-template.json",
        '{"version":1,"hooks":{"sessionStart":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto"}],"sessionEnd":[{"type":"command","command":"python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}]}}\n',
    )


def _make_push_framework(root: Path) -> None:
    """Minimal framework whose real pre-push guard can run in a consumer fixture."""
    # The wrapper below is a stub, not the A1 default smoke implementation.
    _write(root / ".governance/version_manifest.yaml", "default_self_smoke_contract_dependency: not_applicable\n")

    _write(root / "scripts" / "hooks" / "pre-commit", "#!/bin/bash\n# AI Governance Framework\n")
    (root / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        REPO_ROOT / "scripts" / "hooks" / "pre-push",
        root / "scripts" / "hooks" / "pre-push",
    )
    python_executable = Path(sys.executable).as_posix()
    _write(
        root / "scripts" / "lib" / "python.sh",
        f"set_python_cmd() {{ PYTHON_CMD=('{python_executable}'); return 0; }}\n",
    )
    _write(root / "scripts" / "run-runtime-governance.sh", "#!/bin/bash\nexit 0\n")
    (root / "governance_tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        REPO_ROOT / "governance_tools" / "external_tree_inventory_guard.py",
        root / "governance_tools" / "external_tree_inventory_guard.py",
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


def _preflight_layout(tmp_path: Path, identity_present: bool) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    _make_framework(framework)
    for name in ("pre-commit", "pre-push"):
        _write(repo / ".git/hooks" / name, f"# custom {name}\n")
    if identity_present:
        _write(repo / IDENTITY_CONFIG_REL, json.dumps({
            "schema": IDENTITY_CONFIG_SCHEMA,
            "repository_identities": ["example/existing"],
        }))
        _write(repo / ".git/hooks/ai-governance-framework-root", "/existing/framework\n")
    return repo, framework


def _install_tree_snapshot(root: Path) -> dict:
    """Include link entries and write times so a refused install cannot hide writes."""
    return {
        path.relative_to(root).as_posix(): (
            path.lstat().st_mode, path.lstat().st_mtime_ns,
            os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None,
        )
        for path in (root, *root.rglob("*"))
    }


@pytest.mark.parametrize("hook_name", ["pre-commit", "pre-push"])
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("identity_present", [False, True])
@pytest.mark.parametrize("read_error", [PermissionError, OSError])
def test_install_refuses_unreadable_hook_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook_name: str,
    dry_run: bool, identity_present: bool, read_error: type[OSError],
) -> None:
    repo, framework = _preflight_layout(tmp_path, identity_present)
    target = repo / ".git/hooks" / hook_name
    before = _install_tree_snapshot(repo)
    original_open = Path.open

    def unreadable_hook(path: Path, *args, **kwargs):
        if path == target:
            raise read_error(f"unreadable existing hook: {path}")
        return original_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        # Both text and byte reads fail, including the old marker helper's read.
        patch.setattr(Path, "open", unreadable_hook)
        result = install_governance_hooks(repo, framework, dry_run=dry_run)

    assert result.ok is False
    assert any("unreadable existing hook" in error for error in result.errors)
    assert result.installed_files == result.changed_files == result.backups == []
    assert _install_tree_snapshot(repo) == before


@pytest.mark.parametrize("hook_name", ["pre-commit", "pre-push"])
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("identity_present", [False, True])
@pytest.mark.parametrize("dangling", [False, True])
def test_install_refuses_symlink_hook_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook_name: str,
    dry_run: bool, identity_present: bool, dangling: bool,
) -> None:
    repo, framework = _preflight_layout(tmp_path, identity_present)
    target = repo / ".git/hooks" / hook_name
    destination = tmp_path / "hook-destination"
    payload = b"# consumer hook destination\n"
    if not dangling:
        destination.write_bytes(payload)
    target.unlink()
    try:
        target.symlink_to(destination)
    except OSError:
        # Windows may forbid symlink creation. Model the link metadata while
        # retaining the same exists()/is_file() behavior as a dangling entry.
        if not dangling:
            target.write_bytes(payload)
        original_is_symlink = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or original_is_symlink(path))
        monkeypatch.setattr(os, "readlink", lambda path: str(destination))
    link_before = os.readlink(target)
    before = _install_tree_snapshot(repo)

    result = install_governance_hooks(repo, framework, dry_run=dry_run)

    assert result.ok is False
    assert any("symlink" in error and "refusing overwrite" in error for error in result.errors)
    assert result.installed_files == result.changed_files == result.backups == []
    assert target.is_symlink()
    assert os.readlink(target) == link_before
    assert _install_tree_snapshot(repo) == before
    if dangling:
        assert not destination.exists()
    else:
        assert destination.read_bytes() == payload


@pytest.mark.parametrize("hook_name", ["pre-commit", "pre-push"])
def test_historical_standard_hook_git_trust_is_scoped_and_environment_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook_name: str,
) -> None:
    framework = tmp_path / "framework"
    _make_framework(framework)
    historical = b"#!/bin/sh\n# AI Governance Framework\n# historical version\n"
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "other.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "other"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "safe.directory")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "*")
    monkeypatch.setenv("GIT_GRAFT_FILE", str(tmp_path / "grafts"))
    monkeypatch.setenv("HOOK_INSTALL_TEST_ENV", "preserved")
    prefix = ["git", "--no-replace-objects", "-c",
              f"safe.directory={framework.resolve().as_posix()}", "-C", str(framework.resolve())]
    outputs = iter([
        f"{framework.resolve()}\n".encode(), b"a" * 40 + b"\n",
        f"100644 blob {'b' * 40}\tscripts/hooks/{hook_name}\0".encode(), historical,
    ])
    calls = []

    def git_run(args, **kwargs):
        calls.append(args)
        assert args[:len(prefix)] == prefix
        env = kwargs["env"]
        assert {key for key in env if key.upper().startswith("GIT_")} == {"GIT_GRAFT_FILE"}
        assert env["GIT_GRAFT_FILE"] == os.devnull
        assert env["HOOK_INSTALL_TEST_ENV"] == "preserved"
        return subprocess.CompletedProcess(args, 0, next(outputs), b"")

    monkeypatch.setattr(hook_installer.subprocess, "run", git_run)

    assert hook_installer._matches_standard_hook(framework / ".." / framework.name, hook_name, historical)
    assert len(calls) == 4


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
    assert (repo / IDENTITY_CONFIG_REL).is_file()
    assert not (repo / ".github" / "copilot-instructions.md").exists()
    assert not (repo / ".github" / "hooks").exists()
    assert all(".github" not in changed for changed in result.changed_files)
    assert all(".github" not in installed for installed in result.installed_files)


def test_identity_config_uses_exact_origin_and_repository_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    origin = "git@github.com:example/consumer.git"
    _run(["git", "remote", "add", "origin", origin], cwd=repo)

    result = install_external_tree_identity_config(repo, framework)

    assert result.ok is True, result.errors
    document = json.loads((repo / IDENTITY_CONFIG_REL).read_text(encoding="utf-8"))
    assert document == {
        "schema": IDENTITY_CONFIG_SCHEMA,
        "repository_identities": [origin, REPOSITORY_ROOT_TOKEN],
    }


def test_identity_config_requires_explicit_identity_or_origin(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)

    result = install_external_tree_identity_config(repo, framework)

    assert result.ok is False
    assert any("configure origin or pass --repository-id" in error for error in result.errors)
    assert not (repo / IDENTITY_CONFIG_REL).exists()


def test_identity_config_preserves_valid_aliases_and_adds_repository_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    config = repo / IDENTITY_CONFIG_REL
    _write(
        config,
        json.dumps(
            {
                "schema": IDENTITY_CONFIG_SCHEMA,
                "repository_identities": ["git@gitlab.com:example/consumer.git", "legacy/alias"],
            }
        ),
    )
    result = install_external_tree_identity_config(
        repo,
        framework,
        repository_identities=("https://gitlab.com/example/consumer.git",),
    )

    assert result.ok is True, result.errors
    values = json.loads(config.read_text(encoding="utf-8"))["repository_identities"]
    assert values == [
        "git@gitlab.com:example/consumer.git",
        "legacy/alias",
        "https://gitlab.com/example/consumer.git",
        REPOSITORY_ROOT_TOKEN,
    ]


def test_invalid_identity_config_is_not_overwritten_or_partially_installed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    (repo / ".git" / "hooks").mkdir(parents=True)
    _make_framework(framework)
    config = repo / IDENTITY_CONFIG_REL
    invalid = b'{"schema":"wrong","repository_identities":["example/consumer"]}\n'
    config.parent.mkdir(parents=True)
    config.write_bytes(invalid)

    result = _install_governance_hooks(
        repo,
        framework,
        include_copilot=False,
        repository_identities=(TEST_REPOSITORY_ID,),
    )

    assert result.ok is False
    assert config.read_bytes() == invalid
    assert not (repo / ".git" / "hooks" / "pre-push").exists()


def test_external_consumer_install_allows_clean_push_and_blocks_external_inventory(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    bare = tmp_path / "remote.git"
    framework = tmp_path / "framework"
    repo.mkdir()
    bare.mkdir()
    _run(["git", "init", "--bare"], cwd=bare)
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)
    _run(["git", "remote", "add", "origin", bare.as_posix()], cwd=repo)
    _make_push_framework(framework)

    installed = _install_governance_hooks(repo, framework, include_copilot=False)
    assert installed.ok is True, installed.errors
    if os.name != "nt":
        for hook_name in ("pre-commit", "pre-push"):
            assert (repo / ".git" / "hooks" / hook_name).stat().st_mode & 0o111 == 0o111
    _write(repo / "README.md", "clean consumer\n")
    _run(["git", "add", "README.md", IDENTITY_CONFIG_REL.as_posix()], cwd=repo)
    _run(["git", "commit", "--no-verify", "-m", "initial clean consumer"], cwd=repo)
    clean_commit = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    clean_push = subprocess.run(
        ["git", "push", "origin", "HEAD:refs/heads/main"],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert clean_push.returncode == 0, clean_push.stdout

    inventory = {
        "repository": "example/private-consumer",
        "inventory": [
            {"path": f"private/{index}.txt", "oid": f"{index:040x}"}
            for index in range(120)
        ],
    }
    _write(repo / "external-inventory.json", json.dumps(inventory))
    _run(["git", "add", "external-inventory.json"], cwd=repo)
    _run(["git", "commit", "--no-verify", "-m", "add external inventory"], cwd=repo)

    blocked_push = subprocess.run(
        ["git", "push", "origin", "HEAD:refs/heads/main"],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert blocked_push.returncode != 0, blocked_push.stdout
    assert "status: BLOCKED" in blocked_push.stdout
    assert "present in the updated-ref object history" in blocked_push.stdout
    assert "deleting the file in a later commit does not remove" in blocked_push.stdout
    assert "amend, rebase, or filter" in blocked_push.stdout
    assert "run git fetch" not in blocked_push.stdout
    assert _run(["git", "rev-parse", "refs/heads/main"], cwd=bare) == clean_commit


def test_external_consumer_hook_missing_remote_old_object_recommends_fetch(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    bare = tmp_path / "remote.git"
    framework = tmp_path / "framework"
    repo.mkdir()
    bare.mkdir()
    _run(["git", "init", "--bare"], cwd=bare)
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)
    _run(["git", "remote", "add", "origin", bare.as_posix()], cwd=repo)
    _make_push_framework(framework)
    installed = _install_governance_hooks(repo, framework, include_copilot=False)
    assert installed.ok is True, installed.errors
    _write(repo / "README.md", "clean consumer\n")
    _run(["git", "add", "README.md", IDENTITY_CONFIG_REL.as_posix()], cwd=repo)
    _run(["git", "commit", "--no-verify", "-m", "initial clean consumer"], cwd=repo)
    local_oid = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    missing_remote_oid = "f" * 40
    hook_input = (
        f"refs/heads/main {local_oid} refs/heads/main {missing_remote_oid}\n"
    )

    completed = subprocess.run(
        [BASH_COMMAND, (repo / ".git" / "hooks" / "pre-push").as_posix(), "origin", bare.as_posix()],
        cwd=repo,
        input=hook_input,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode != 0, completed.stdout
    assert "run git fetch and retry" in completed.stdout
    assert "already present in your unpushed history" not in completed.stdout


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
    pre_commit = (REPO_ROOT / "scripts" / "hooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    pre_push = (REPO_ROOT / "scripts" / "hooks" / "pre-push").read_text(
        encoding="utf-8"
    )

    assert 'TARGET_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"' in pre_commit
    assert 'TARGET_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"' in pre_push
    assert 'git -C "$HOOK_DIR" rev-parse --show-toplevel' in pre_push
    assert 'governance_error "cannot resolve target repository root"' in pre_push


def test_managed_hooks_normalize_windows_framework_paths() -> None:
    pre_commit = (REPO_ROOT / "scripts" / "hooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    pre_push = (REPO_ROOT / "scripts" / "hooks" / "pre-push").read_text(
        encoding="utf-8"
    )

    assert 'case "$FRAMEWORK_ROOT" in' in pre_commit
    assert 'DRIVE_PATH="${FRAMEWORK_ROOT:2}"' in pre_commit
    assert 'FRAMEWORK_ROOT="/mnt/$DRIVE_LOWER/$DRIVE_PATH"' in pre_commit
    assert 'FRAMEWORK_ROOT="${FRAMEWORK_ROOT//\\\\//}"' in pre_push
    assert "WSL drive-path mapping is intentionally unsupported" in pre_push
    assert 'FRAMEWORK_PYTHON_ROOT="$FRAMEWORK_ROOT"' in pre_push


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


@pytest.mark.parametrize("has_managed_block", [False, True], ids=["append", "replace"])
def test_copilot_instructions_crlf_write_matches_b6a04e3c(tmp_path, has_managed_block):
    framework = _managed_framework(tmp_path / "framework")
    target = _instructions(tmp_path / "repo")
    target.parent.mkdir(parents=True)
    prefix = b"# House rules  \r\n\r\n"
    if has_managed_block:
        old_block = MANAGED_TEMPLATE.replace("framework rules", "stale rules").rstrip("\n")
        target.write_bytes(prefix + old_block.replace("\n", "\r\n").encode() + b"\r\n\r\n# More rules\r\n\r\n")
    else:
        target.write_bytes(prefix + b"\r\n")

    result = install_copilot_instructions(tmp_path / "repo", framework)

    assert result.ok, result.errors
    assert result.copilot_instructions_mode == ("replaced" if has_managed_block else "appended")
    # Exact output from the b6a04e3c installer for the same input and template.
    expected_suffix = b"\n# More rules\n" if has_managed_block else b""
    assert target.read_bytes() == b"# House rules  \n\n" + MANAGED_TEMPLATE.encode() + expected_suffix


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
        [BASH_COMMAND, "scripts/install-hooks.sh", "--target", relative_target, "--repository-id", TEST_REPOSITORY_ID, "--no-verify"],
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
        [BASH_COMMAND, "scripts/install-hooks.sh", "--target", relative_target, "--repository-id", TEST_REPOSITORY_ID, "--no-verify"],
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


def test_shell_installer_deploys_copilot_lifecycle_surface() -> None:
    """Deployment is asserted by running the installer, not by grepping it.

    The lifecycle files now come from the shared Python path, so their source
    paths no longer appear in the shell script at all.
    """
    repo = _shell_fixture_repo("lifecycle_surface")
    _run(["git", "init"], cwd=repo)
    relative_target = repo.relative_to(REPO_ROOT).as_posix()

    completed = subprocess.run(
        [BASH_COMMAND, "scripts/install-hooks.sh", "--target", relative_target, "--repository-id", TEST_REPOSITORY_ID, "--no-verify"],
        cwd=REPO_ROOT, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )

    assert completed.returncode == 0, completed.stdout
    identity_document = json.loads((repo / IDENTITY_CONFIG_REL).read_text(encoding="utf-8"))
    assert identity_document == {
        "schema": IDENTITY_CONFIG_SCHEMA,
        "repository_identities": [TEST_REPOSITORY_ID, REPOSITORY_ROOT_TOKEN],
    }
    hooks = repo / ".github" / "hooks"
    for name in (
        "ai-governance-lifecycle.py",
        "ai-governance-vscode.json",
        "ai-governance-copilot.json",
        ".ai-governance-managed.json",
    ):
        assert (hooks / name).is_file(), name
    assert validate_hook_install(repo).checks["copilot_lifecycle_installed"] is True
    shutil.rmtree(repo, ignore_errors=True)


def test_shell_installer_does_not_copy_managed_files_itself() -> None:
    text = (REPO_ROOT / "scripts" / "install-hooks.sh").read_text(encoding="utf-8")

    assert 'cp "$COPILOT_TEMPLATE" "$COPILOT_DST"' not in text
    assert 'cp "$source" "$target"' not in text


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


def test_custom_vscode_hook_config_is_preserved_without_replacement(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    install_governance_hooks(repo, framework)
    _write(_vscode_config(repo), '{"version":1,"hooks":{"UserPromptSubmit":[]}}\n')

    result = install_governance_hooks(repo, framework)

    assert result.ok, result.errors
    # The consumer's own events stay; only the managed Stop execution point is added.
    assert json.loads(_vscode_config(repo).read_text(encoding="utf-8")) == {
        "version": 1, "hooks": {"UserPromptSubmit": [], "Stop": [VSCODE_MANAGED_STOP_ENTRY]}}
    before = _vscode_config(repo).read_bytes()
    again = install_governance_hooks(repo, framework)
    assert again.ok, again.errors
    assert _vscode_config(repo).read_bytes() == before


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


def test_installed_configs_register_each_session_boundary_exactly_once(tmp_path: Path) -> None:
    """The invariant is the merged event set, not either file on its own.

    VS Code loads every *.json under .github/hooks and normalizes the Copilot
    config's lowerCamelCase names to PascalCase, so both installed files land in
    one event table. A second start handler there writes the session envelope
    twice — see docs/stop-hook-setup.md.
    """
    repo = tmp_path / "repo"
    framework = _managed_framework(tmp_path / "framework")
    (repo / ".git" / "hooks").mkdir(parents=True)
    _write(
        framework / "governance" / "copilot-hooks-vscode-template.json",
        (REPO_ROOT / "governance" / "copilot-hooks-vscode-template.json").read_text(encoding="utf-8"),
    )
    _write(
        framework / "governance" / "copilot-hooks-session-end-template.json",
        (REPO_ROOT / "governance" / "copilot-hooks-session-end-template.json").read_text(
            encoding="utf-8"
        ),
    )

    install_governance_hooks(repo, framework)

    merged: dict[str, list[str]] = {}
    for name in ("ai-governance-vscode.json", "ai-governance-copilot.json"):
        payload = json.loads((repo / ".github" / "hooks" / name).read_text(encoding="utf-8"))
        for event, entries in payload["hooks"].items():
            # VS Code's normalization of the Copilot config's event names.
            normalized = event[0].upper() + event[1:]
            merged.setdefault(normalized, []).extend(entry["command"] for entry in entries)

    starts = [cmd for cmds in merged.values() for cmd in cmds if "--event-type session_start" in cmd]
    ends = [cmd for cmds in merged.values() for cmd in cmds if "--event-type session_end" in cmd]

    assert len(starts) == 1, merged
    assert "SessionStart" in merged
    # Stop ends one execution, not the session. Only the genuine sessionEnd
    # registration may reach closeout.
    assert len(ends) == 1, merged
    assert "SessionEnd" in merged
    # Stop carries only the prepared-closeout execution point (owner ruling 2026-11-11),
    # never session_start or session_end.
    assert merged["Stop"] == ["python .github/hooks/ai-governance-lifecycle.py --event-type agent_stop --surface vscode"]


def test_shell_installer_backs_up_edited_lifecycle_file_end_to_end() -> None:
    """AGR-09 through the shell entry point, which had its own copy of the rules.

    Both entry points must apply the same backup semantics; a marker check plus
    an unconditional cp is what destroyed the consumer's work.
    """
    repo = _shell_fixture_repo("lifecycle_edit")
    _run(["git", "init"], cwd=repo)
    relative_target = repo.relative_to(REPO_ROOT).as_posix()
    shell = [
        BASH_COMMAND,
        "scripts/install-hooks.sh",
        "--target",
        relative_target,
        "--repository-id",
        TEST_REPOSITORY_ID,
        "--no-verify",
    ]

    first = subprocess.run(
        shell, cwd=REPO_ROOT, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    assert first.returncode == 0, first.stdout

    bridge = repo / ".github" / "hooks" / "ai-governance-lifecycle.py"
    assert bridge.is_file(), first.stdout
    _write(bridge, bridge.read_text(encoding="utf-8") + "\n# CFU: dynamic memory pressure\n")

    second = subprocess.run(
        shell, cwd=REPO_ROOT, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )

    assert second.returncode == 0, second.stdout
    backups = sorted((repo / ".github" / "hooks").glob("ai-governance-lifecycle.py.bak.*"))
    assert backups, sorted(p.name for p in (repo / ".github" / "hooks").iterdir())
    assert "CFU: dynamic memory pressure" in backups[0].read_text(encoding="utf-8")
    shutil.rmtree(repo, ignore_errors=True)


def test_shell_installer_has_no_second_copy_of_lifecycle_rules() -> None:
    text = (REPO_ROOT / "scripts" / "install-hooks.sh").read_text(encoding="utf-8")

    assert "--copilot-only" in text
    assert "deploy_copilot_lifecycle_hooks" not in text
    assert "COPILOT_LIFECYCLE_TARGETS" not in text


class TestAgentContractSurfaces:
    """Consumers had Copilot rules only; the other three agents got nothing.

    Projecting into the framework's own AGENTS.md / CLAUDE.md / GEMINI.md gave the
    framework repo parity. Nothing deployed those to a consumer, so every consumer
    measured had `AGENTS.md` with no contract and no CLAUDE.md/GEMINI.md at all.
    """

    def _consumer(self, tmp_path, agents_text=None):
        repo = tmp_path / "consumer"
        (repo / ".git" / "hooks").mkdir(parents=True)
        if agents_text is not None:
            _write(repo / "AGENTS.md", agents_text)
        return repo

    def test_all_three_surfaces_receive_the_contract(self, tmp_path):
        repo = self._consumer(tmp_path, "# AGENTS\n\nHouse rules.\n")

        result = install_governance_hooks(repo, Path("."))

        assert result.ok is True, result.errors
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
            text = (repo / name).read_text(encoding="utf-8")
            assert text.count("checkpoint-projection BEGIN") == 1, name

    def test_existing_consumer_content_survives(self, tmp_path):
        repo = self._consumer(tmp_path, "# AGENTS\n\n## House rules\n\nNever touch vendor/.\n")

        result = install_governance_hooks(repo, Path("."))

        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert "Never touch vendor/." in text
        assert any(Path(b).name.startswith("AGENTS.md.bak.") for b in result.backups)

    def test_missing_surfaces_are_created(self, tmp_path):
        repo = self._consumer(tmp_path, "# AGENTS\n")

        install_governance_hooks(repo, Path("."))

        assert (repo / "CLAUDE.md").is_file()
        assert (repo / "GEMINI.md").is_file()

    def test_reinstall_is_idempotent(self, tmp_path):
        repo = self._consumer(tmp_path, "# AGENTS\n\nHouse rules.\n")
        install_governance_hooks(repo, Path("."))

        second = install_governance_hooks(repo, Path("."))

        assert second.changed_files == []
        assert second.backups == []

    def test_a_consumer_file_is_never_replaced_wholesale(self, tmp_path):
        """No legacy whole-file form exists for these, so migration must not apply."""
        repo = self._consumer(tmp_path, "# AGENTS\n\nAI Governance Framework mentions itself.\n")

        result = install_governance_hooks(repo, Path("."))

        assert result.ok is True, result.errors
        assert "AI Governance Framework mentions itself." in (
            repo / "AGENTS.md"
        ).read_text(encoding="utf-8")

    def test_all_surfaces_carry_the_same_canonical_digest(self, tmp_path):
        repo = self._consumer(tmp_path, "# AGENTS\n")
        install_governance_hooks(repo, Path("."))

        digests = set()
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
            header, _, _, _ = extract_projection_region(
                (repo / name).read_text(encoding="utf-8")
            )
            digests.add(header["sha256"])

        assert len(digests) == 1


@pytest.mark.parametrize("has_managed_block", [False, True], ids=["append", "replace"])
def test_claude_install_preserves_bytes_outside_managed_block(tmp_path, has_managed_block):
    target = tmp_path / "CLAUDE.md"
    begin, end = AGENT_CONTRACT_BLOCK_BEGIN.encode(), AGENT_CONTRACT_BLOCK_END.encode()
    prefix = b"\xef\xbb\xbf# Local notes  \r\n\r\n\r\n"
    suffix = b"\r\n\r\n# More local notes\r\n\r\n" if has_managed_block else b""
    old_block = begin + b"\r\nstale rules\r\n" + end if has_managed_block else b""
    target.write_bytes(prefix + old_block + suffix)

    result = install_claude_instructions(tmp_path, REPO_ROOT)
    assert result.ok, result.errors
    updated = target.read_bytes()
    before, block_and_suffix = updated.split(begin, 1)
    block, after = block_and_suffix.split(end, 1)
    assert before == prefix
    assert after == (suffix if has_managed_block else b"\r\n")
    assert b"\n" not in block.replace(b"\r\n", b"")
    assert b"Formal Closeout on Request" in block
    assert install_claude_instructions(tmp_path, REPO_ROOT).changed_files == []
    assert target.read_bytes() == updated


class TestCodexProjectDocBudget:
    """Codex tail-truncates an over-budget root AGENTS.md; the install must say so."""

    def _consumer(self, tmp_path, agents_text):
        repo = tmp_path / "consumer"
        (repo / ".git" / "hooks").mkdir(parents=True)
        (repo / "AGENTS.md").write_bytes(agents_text.encode("utf-8"))
        return repo

    def test_over_budget_agents_md_produces_a_warning(self, tmp_path):
        from governance_tools.hook_installer import CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES

        repo = self._consumer(tmp_path, "# AGENTS\n\n" + ("House rule line.\n" * 2000))

        result = install_governance_hooks(repo, Path("."))

        assert result.ok is True, result.errors
        budget = result.codex_project_doc_budget
        size = len((repo / "AGENTS.md").read_bytes())
        assert size > CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES
        assert budget["on_disk_bytes"] == size
        assert budget["overflow_bytes"] == size - CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES
        assert budget["crlf_worst_case_bytes"] > size
        assert budget["over_budget"] is True
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert f"{budget['overflow_bytes']} bytes" in warning
        assert "may not be delivered to Codex" in warning
        assert "Codex's default" in warning

    def test_under_budget_agents_md_has_no_warning(self, tmp_path):
        repo = self._consumer(tmp_path, "# AGENTS\n\nHouse rules.\n")

        result = install_governance_hooks(repo, Path("."))

        assert result.ok is True, result.errors
        assert result.warnings == []
        budget = result.codex_project_doc_budget
        assert budget["over_budget"] is False
        assert budget["over_budget_with_crlf"] is False
        assert budget["overflow_bytes"] == 0

    def test_crlf_worst_case_alone_is_reported(self, tmp_path):
        from governance_tools.hook_installer import (
            CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES,
            _codex_project_doc_budget,
        )

        repo = tmp_path / "consumer"
        repo.mkdir()
        target = repo / "AGENTS.md"
        # Fits on disk with LF; 200 extra CR bytes would push it over.
        line = b"x" * 99 + b"\n"
        lines = (CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES - 100) // len(line)
        target.write_bytes(line * lines)

        report, warnings = _codex_project_doc_budget(repo, [str(target)])

        assert report["over_budget"] is False
        assert report["over_budget_with_crlf"] is True
        assert report["crlf_worst_case_bytes"] == len(line) * lines + lines
        assert len(warnings) == 1 and "with CRLF line endings" in warnings[0]

    def test_budget_boundary_is_exclusive(self, tmp_path):
        from governance_tools.hook_installer import (
            CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES,
            _codex_project_doc_budget,
        )

        repo = tmp_path / "consumer"
        repo.mkdir()
        target = repo / "AGENTS.md"
        # No newlines, so the CRLF worst case equals the on-disk size.
        target.write_bytes(b"x" * CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES)
        report, warnings = _codex_project_doc_budget(repo, [str(target)])
        assert report["over_budget"] is False and warnings == []

        target.write_bytes(b"x" * (CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES + 1))
        report, warnings = _codex_project_doc_budget(repo, [str(target)])
        assert report["over_budget"] is True and report["overflow_bytes"] == 1
        assert len(warnings) == 1

    def test_human_output_names_the_warning(self, tmp_path, capsys):
        from governance_tools.hook_installer import main

        repo = self._consumer(tmp_path, "# AGENTS\n\n" + ("House rule line.\n" * 2000))

        exit_code = main([
            "--repo", str(repo), "--framework-root", ".",
            "--repository-id", TEST_REPOSITORY_ID,
        ])

        out = capsys.readouterr().out
        assert exit_code == 0
        assert "ok=True" in out
        assert "codex_project_doc_bytes=" in out
        assert "warning: codex-project-doc-budget:" in out
