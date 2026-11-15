"""Run installed hooks against differently pinned, local-only Git submodules."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from governance_tools.external_governance_submodule_updater import (
    _ensure_hook_advisory, _preexisting_unmanaged_hook_overlaps,
)
from governance_tools.hook_installer import install_governance_hooks


ROOT = Path(__file__).resolve().parents[1]
BASH = (next(str(parent / "bin/bash.exe")
             for parent in Path(shutil.which("git")).resolve().parents
             if (parent / "bin/bash.exe").is_file())
        if os.name == "nt" else shutil.which("bash"))
SUBMODULE = "vendor/framework copy"
ENV = {key: value for key, value in os.environ.items()
       if not key.startswith(("GIT_", "AI_GOVERNANCE_"))}
ENV.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
           AI_GOVERNANCE_PYTHON=sys.executable, PYTHONDONTWRITEBYTECODE="1")


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], env=ENV, check=True,
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    ).stdout.strip()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def init(repo):
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")


def framework_version(repo, version):
    write(repo / "scripts/lib/python.sh",
          f'echo "FRAMEWORK_VERSION={version}"\n'
          'set_python_cmd() { PYTHON_CMD=("$AI_GOVERNANCE_PYTHON"); }\n')
    write(repo / "governance/SYSTEM_PROMPT.md", "# Fixture framework\n")
    write(repo / "governance_tools/hook_installer.py", "# Framework entry\n")
    write(repo / "governance_tools/plan_freshness.py",
          'import json\nprint(json.dumps({"status": "' +
          ("FRESH" if version == "primary" else "CRITICAL") +
          '", "threshold_days": 7, "days_since_update": 30}))\n')
    write(repo / "governance_tools/memory_workflow.py",
          'print(\'{"status":"not_required","warnings":[]}\')\n')
    write(repo / "governance_tools/manual_update_advisory.py", "pass\n")
    write(repo / "governance_tools/external_tree_inventory_guard.py",
          f'print("SCANNER_VERSION={version}")\n'
          f'raise SystemExit({0 if version == "primary" else 4})\n')
    write(repo / "scripts/run-runtime-governance.sh",
          f'#!/bin/bash\necho "SMOKE_VERSION={version}"\n')
    write(repo / ".governance/version_manifest.yaml",
          "default_self_smoke_contract_dependency: not_applicable\n")
    for name in ("pre-commit", "pre-push"):
        write(repo / "scripts/hooks" / name,
              (ROOT / "scripts/hooks" / name).read_text(encoding="utf-8"))


@pytest.fixture
def layout(tmp_path):
    source = tmp_path / "source"
    init(source)
    framework_version(source, "linked")
    for name in ("pre-commit", "pre-push"):
        write(source / "scripts/hooks" / name,
              "#!/bin/bash\n# AI Governance Framework: older fixture hook\nexit 0\n")
    git(source, "add", ".")
    git(source, "commit", "-qm", "linked framework")
    linked_pin = git(source, "rev-parse", "HEAD")
    framework_version(source, "primary")
    git(source, "add", ".")
    git(source, "commit", "-qm", "primary framework")
    primary_pin = git(source, "rev-parse", "HEAD")

    primary, linked = tmp_path / "primary", tmp_path / "linked"
    init(primary)
    git(primary, "-c", "protocol.file.allow=always", "submodule", "add",
        str(source), SUBMODULE)
    git(primary / SUBMODULE, "checkout", "-q", primary_pin)
    write(primary / "PLAN.md", "# Fixture plan\n")
    git(primary, "add", ".")
    git(primary, "commit", "-qm", "primary consumer pin")
    git(primary, "worktree", "add", "--detach", str(linked), "HEAD")
    git(linked, "-c", "protocol.file.allow=always", "submodule", "update", "--init")
    git(linked / SUBMODULE, "checkout", "-q", linked_pin)
    git(linked, "add", "--", SUBMODULE)
    git(linked, "commit", "-qm", "linked consumer pin")

    result = install_governance_hooks(
        primary, primary / SUBMODULE, include_copilot=False,
        repository_identities=["example/consumer"],
    )
    assert result.ok, result.errors
    return primary, linked


def snapshot(root):
    return {p.relative_to(root).as_posix():
            (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def invoke(primary, repo, name, **extra):
    common = primary / ".git"
    before = snapshot(common)
    result = subprocess.run(
        [BASH, (common / "hooks" / name).as_posix()], cwd=repo,
        env={**ENV, **extra}, input="", capture_output=True, text=True,
        encoding="utf-8", timeout=30,
    )
    assert snapshot(common) == before, "hook execution changed the common directory"
    return result


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_linked_hook_runs_its_pinned_framework(layout, name):
    primary, linked = layout
    assert git(primary / SUBMODULE, "rev-parse", "HEAD") != git(linked / SUBMODULE, "rev-parse", "HEAD")
    result = invoke(primary, linked, name)
    assert "FRAMEWORK_VERSION=linked" in result.stdout, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=primary" not in result.stdout
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "linked worktree" in result.stderr
    assert "declared" in result.stderr
    if name == "pre-push":
        assert "SCANNER_VERSION=linked" in result.stdout
        assert "SMOKE_VERSION=" not in result.stdout


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_primary_hook_keeps_shared_root(layout, name):
    primary, _ = layout
    result = invoke(primary, primary, name)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=primary" in result.stdout
    assert "linked worktree" not in result.stderr


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_explicit_framework_override_keeps_priority(layout, name):
    primary, linked = layout
    result = invoke(primary, linked, name,
                    AI_GOVERNANCE_FRAMEWORK_ROOT=(primary / SUBMODULE).as_posix())
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=primary" in result.stdout
    assert "linked worktree" not in result.stderr


@pytest.mark.parametrize("damage", ["missing", "uninitialized", "entry", "pin", "declaration"])
@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_invalid_local_framework_fails_closed(layout, name, damage):
    primary, linked = layout
    local = linked / SUBMODULE
    if damage == "missing":
        shutil.rmtree(local)
    elif damage == "uninitialized":
        (local / ".git").unlink()
    elif damage == "entry":
        (local / "scripts/lib/python.sh").unlink()
    elif damage == "pin":
        git(local, "checkout", "-q", git(primary / SUBMODULE, "rev-parse", "HEAD"))
    else:
        write(linked / ".gitmodules", (linked / ".gitmodules").read_text(encoding="utf-8") + "# dirty\n")
    result = invoke(primary, linked, name)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=" not in result.stdout
    assert "[governance] error:" in result.stderr


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_undeclared_nested_framework_is_never_selected(layout, name):
    primary, linked = layout
    framework_version(linked / "ai-governance-framework", "undeclared")
    result = invoke(primary, linked, name)
    assert "FRAMEWORK_VERSION=linked" in result.stdout
    assert "FRAMEWORK_VERSION=undeclared" not in result.stdout


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_deleted_shared_worktree_still_uses_valid_local_pin(layout, name):
    primary, linked = layout
    deleted = primary.parent / "deleted"
    git(primary, "worktree", "add", "--detach", str(deleted), "HEAD")
    shutil.rmtree(deleted)
    write(primary / ".git/hooks/ai-governance-framework-root",
          (deleted / SUBMODULE).as_posix() + "\n")
    result = invoke(primary, linked, name)
    assert "FRAMEWORK_VERSION=linked" in result.stdout, (result.stdout, result.stderr)
    assert result.returncode == 1


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_pruned_shared_worktree_fails_closed_without_trust_anchor(layout, name):
    primary, linked = layout
    deleted = primary.parent / "deleted"
    git(primary, "worktree", "add", "--detach", str(deleted), "HEAD")
    git(primary, "worktree", "remove", str(deleted))
    write(primary / ".git/hooks/ai-governance-framework-root",
          (deleted / SUBMODULE).as_posix() + "\n")
    result = invoke(primary, linked, name)
    assert result.returncode == 1
    assert "FRAMEWORK_VERSION=" not in result.stdout
    assert "cannot be bound to a registered worktree" in result.stderr


def test_installer_and_updater_recognize_and_refresh_hooks(layout):
    primary, _ = layout
    framework = primary / SUBMODULE
    assert _preexisting_unmanaged_hook_overlaps(primary, framework) == []
    assert _ensure_hook_advisory(primary, framework)["status"] == "verified"
    result = install_governance_hooks(
        primary, framework, include_copilot=False, repository_identities=["example/consumer"],
    )
    assert result.ok, result.errors
    assert not result.backups
    assert _preexisting_unmanaged_hook_overlaps(primary, framework) == []


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_no_declaration_keeps_shared_root_and_ignores_nested_copy(layout, name):
    primary, linked = layout
    (linked / ".gitmodules").unlink()
    framework_version(linked / "ai-governance-framework", "undeclared")
    result = invoke(primary, linked, name)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=primary" in result.stdout
    assert "FRAMEWORK_VERSION=undeclared" not in result.stdout


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_external_installation_is_not_replaced_by_declared_submodule(layout, tmp_path, name):
    primary, linked = layout
    external = tmp_path / "external"
    framework_version(external, "primary")
    write(primary / ".git/hooks/ai-governance-framework-root", external.as_posix() + "\n")
    result = invoke(primary, linked, name)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=primary" in result.stdout
    assert "linked worktree" not in result.stderr


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_nested_external_installation_keeps_its_authority(layout, name):
    primary, linked = layout
    relative = "alternative/framework"
    external = primary / relative
    framework_version(external, "primary")
    (linked / "alternative").mkdir()
    git(linked, "mv", SUBMODULE, relative)
    git(linked, "commit", "--no-verify", "-qam", "move the linked submodule")
    write(primary / ".git/hooks/ai-governance-framework-root", external.as_posix() + "\n")
    result = invoke(primary, linked, name)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=primary" in result.stdout
    assert "FRAMEWORK_VERSION=linked" not in result.stdout


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_local_framework_resolves_under_inherited_hook_git_environment(layout, name):
    primary, linked = layout
    result = invoke(primary, linked, name,
                    GIT_DIR=git(linked, "rev-parse", "--absolute-git-dir"),
                    GIT_WORK_TREE=str(linked), GIT_INDEX_FILE=git(linked, "rev-parse", "--git-path", "index"))
    assert "FRAMEWORK_VERSION=linked" in result.stdout, (result.stdout, result.stderr)
    assert result.returncode == 1


@pytest.mark.parametrize("damage", ["foreign_gitfile", "staged_declaration", "head_declaration", "worktree_config", "hook_entry"])
@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_local_framework_trust_boundary_rejects_invalid_identity(layout, name, damage):
    primary, linked = layout
    local = linked / SUBMODULE
    if damage == "foreign_gitfile":
        # Git marks this file hidden on Windows; update without truncating open.
        data = "gitdir: " + git(primary / SUBMODULE, "rev-parse", "--absolute-git-dir") + "\n"
        with (local / ".git").open("r+b") as stream:
            stream.write(data.encode("utf-8"))
            stream.truncate()
    elif damage == "staged_declaration":
        write(linked / ".gitmodules", (linked / ".gitmodules").read_text(encoding="utf-8") + "# staged\n")
        git(linked, "add", ".gitmodules")
    elif damage == "head_declaration":
        git(linked, "rm", "--cached", ".gitmodules")
        git(linked, "commit", "--no-verify", "-qm", "leave declaration untracked")
    elif damage == "worktree_config":
        git(local, "config", "core.worktree", str(primary / SUBMODULE))
    else:
        (local / "scripts/hooks" / name).unlink()
    result = invoke(primary, linked, name)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=" not in result.stdout
    assert "[governance] error:" in result.stderr


@pytest.mark.parametrize("name", ["pre-commit", "pre-push"])
def test_git_invokes_installed_hook_with_linked_pin(layout, name):
    primary, linked = layout
    before = snapshot(primary / ".git")
    result = subprocess.run(
        ["git", "-C", str(linked), "hook", "run", name], input="", env=ENV,
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert snapshot(primary / ".git") == before
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "FRAMEWORK_VERSION=linked" in result.stdout + result.stderr


def test_prior_consumer_hooks_upgrade_without_relaxing_recognition(layout):
    primary, _ = layout
    framework = primary / SUBMODULE
    prior = ROOT / "tests/fixtures/prior_hooks_b32a45d6"
    current = {}
    for name in ("pre-commit", "pre-push"):
        current[name] = (framework / "scripts/hooks" / name).read_bytes()
        old = (prior / name).read_bytes()
        assert old != current[name], "upgrade fixture must differ from current hooks"
        (framework / "scripts/hooks" / name).write_bytes(old)
    # F-7 checks the installed version before moving the pin and refreshing.
    assert install_governance_hooks(primary, framework, include_copilot=False,
                                    repository_identities=["example/consumer"]).ok
    assert _preexisting_unmanaged_hook_overlaps(primary, framework) == []
    for name, data in current.items():
        (framework / "scripts/hooks" / name).write_bytes(data)
    assert _ensure_hook_advisory(primary, framework)["status"] == "updated"
    assert _preexisting_unmanaged_hook_overlaps(primary, framework) == []
    for name, data in current.items():
        installed = primary / ".git/hooks" / name
        assert installed.read_bytes() == data
        installed.write_bytes(data + b"\n# Unmanaged customization\n")
        assert _preexisting_unmanaged_hook_overlaps(primary, framework) == [f".git/hooks/{name}"]
        installed.write_bytes(data)


def test_both_hooks_share_the_same_read_only_bootstrap():
    blocks = [(ROOT / "scripts/hooks" / name).read_text(encoding="utf-8")
              .split("resolve_worktree_framework() (", 1)[1].split("\n)\n", 1)[0]
              for name in ("pre-commit", "pre-push")]
    assert blocks[0] == blocks[1]
