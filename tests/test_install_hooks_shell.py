"""Issue #374: exercise overwrite refusal through the real shell entrypoint."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from governance_tools import composed_hook
from governance_tools.external_tree_inventory_guard import IDENTITY_CONFIG_REL, IDENTITY_CONFIG_SCHEMA
from governance_tools.hook_installer import install_governance_hooks


REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(WINDOWS_BASH) if os.name == "nt" and WINDOWS_BASH.is_file() else shutil.which("bash")
REPOSITORY_ID = "example.invalid/issue-374"
HOOK_NAMES = ("pre-commit", "pre-push")
OLD_HOOK = b"#!/usr/bin/env bash\n# AI Governance Framework\n# version 1\n# Fail-closed structured memory freshness gate.\nexit 0\n"
NEW_HOOK = OLD_HOOK.replace(b"# version 1", b"# version 2")
COMPOSITION_FIXTURES = REPO_ROOT / "tests/fixtures/lenovo_composed_hook"


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def _commit(repo: Path) -> None:
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-m", "hook fixture")


@pytest.fixture(scope="module")
def framework():
    # Keep Git Bash paths on the checkout drive, and always clean up on failure.
    with tempfile.TemporaryDirectory(prefix="_tmp_issue374_", dir=REPO_ROOT / "tests") as directory:
        root = Path(directory) / "framework"
        shutil.copytree(REPO_ROOT / "governance_tools", root / "governance_tools",
                        ignore=shutil.ignore_patterns("__pycache__"))
        for relative in ("scripts/install-hooks.sh", "scripts/lib/python.sh"):
            _write(root / relative, (REPO_ROOT / relative).read_bytes())
        _write(root / ".governance/version_manifest.yaml",
               b"default_self_smoke_contract_dependency: not_applicable\n")
        for relative in (
            "governance/copilot-instructions-template.md",
            "governance/copilot-hooks-vscode-template.json",
            "governance/copilot-hooks-session-end-template.json",
            "runtime_hooks/adapters/copilot/lifecycle.py",
        ):
            _write(root / relative, (REPO_ROOT / relative).read_bytes())
        for name in HOOK_NAMES:
            _write(root / "scripts/hooks" / name, OLD_HOOK)
        _git(root, "init")
        _commit(root)
        for name in HOOK_NAMES:
            _write(root / "scripts/hooks" / name, NEW_HOOK)
        _commit(root)
        yield root


@pytest.fixture
def consumer(framework: Path):
    with tempfile.TemporaryDirectory(prefix="consumer ", dir=framework.parent) as directory:
        repo = Path(directory)
        _git(repo, "init")
        yield repo


def _snapshot(root: Path) -> dict:
    """Reads may change access times; content, modes and write times must not change."""
    return {
        path.relative_to(root).as_posix(): (
            path.stat().st_mode, path.stat().st_mtime_ns,
            path.read_bytes() if path.is_file() else None,
        )
        for path in (root, *root.rglob("*"))
    }


def _shell(repo: Path, framework: Path, *, dry_run: bool = False):
    assert BASH is not None, "Git Bash/bash is required for shell installer regression tests"
    return subprocess.run(
        [BASH, (framework / "scripts/install-hooks.sh").relative_to(REPO_ROOT).as_posix(),
         "--target", repo.relative_to(REPO_ROOT).as_posix(),
         "--repository-id", REPOSITORY_ID, "--no-verify", *(["--dry-run"] if dry_run else [])],
        cwd=REPO_ROOT, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60,
        env={**os.environ, "AI_GOVERNANCE_PYTHON": Path(sys.executable).as_posix(),
             "PYTHONIOENCODING": "utf-8"},
    )


def _seed_consumer_files(repo: Path, *, identity_present: bool) -> None:
    _write(repo / ".github/copilot-instructions.md", b"# Consumer rules\n")
    _write(repo / ".github/hooks/ai-governance-lifecycle.py", b"# consumer lifecycle\n")
    if identity_present:
        _write(repo / IDENTITY_CONFIG_REL, json.dumps({
            "schema": IDENTITY_CONFIG_SCHEMA,
            "repository_identities": ["example.invalid/existing"],
        }).encode())
        _write(repo / ".git/hooks/ai-governance-framework-root", b"/existing/framework\n")


@pytest.mark.parametrize("hook_name", HOOK_NAMES)
@pytest.mark.parametrize("identity_present", [False, True])
@pytest.mark.parametrize("dry_run", [False, True])
def test_shell_refuses_marked_custom_hook_before_any_write(
    consumer: Path, framework: Path, hook_name: str, identity_present: bool, dry_run: bool,
) -> None:
    _seed_consumer_files(consumer, identity_present=identity_present)
    for name in HOOK_NAMES:
        # The other unmanaged hook must not even be backed up before refusal.
        payload = NEW_HOOK + b"echo consumer customization\n" if name == hook_name else b"# unmanaged\n"
        _write(consumer / ".git/hooks" / name, payload)
    before = _snapshot(consumer)

    result = _shell(consumer, framework, dry_run=dry_run)

    assert result.returncode != 0, result.stdout
    assert "refusing overwrite" in result.stdout
    assert "安裝完成" not in result.stdout
    assert _snapshot(consumer) == before


@pytest.mark.parametrize("hook_name", HOOK_NAMES)
def test_python_refuses_marked_custom_hook_before_identity_write(
    consumer: Path, framework: Path, hook_name: str,
) -> None:
    _write(consumer / ".git/hooks" / hook_name, NEW_HOOK + b"echo consumer customization\n")
    before = _snapshot(consumer)

    result = install_governance_hooks(
        consumer, framework, repository_identities=[REPOSITORY_ID],
    )

    assert not result.ok
    assert any("refusing overwrite" in error for error in result.errors)
    assert result.changed_files == result.backups == []
    assert _snapshot(consumer) == before


def _declare_composition(repo: Path) -> None:
    for relative in composed_hook.FINGERPRINTS:
        _write(repo / relative, (COMPOSITION_FIXTURES / Path(relative).name).read_bytes())
    _write(repo / composed_hook.GATE, b"# test-only consumer gate\nexit 0\n")
    _commit(repo)


def _composed_hook(version: int) -> bytes:
    # Literal expected insertion from the declared consumer wiring.
    return (
        f"#!/usr/bin/env bash\n# AI Governance Framework\n# version {version}\n".encode()
        + (COMPOSITION_FIXTURES / "pre-push.memory-quality.fragment.sh").read_bytes()
        + b"# Fail-closed structured memory freshness gate.\nexit 0\n"
    )


@pytest.mark.parametrize("declared", [False, True])
def test_shell_refuses_unexpected_composition_before_any_write(
    consumer: Path, framework: Path, declared: bool,
) -> None:
    if declared:
        _declare_composition(consumer)
    _seed_consumer_files(consumer, identity_present=True)
    _write(consumer / ".git/hooks/pre-commit", b"# unmanaged\n")
    _write(consumer / ".git/hooks/pre-push", _composed_hook(2) + b"echo unknown\n")
    before = _snapshot(consumer)

    result = _shell(consumer, framework)

    assert result.returncode != 0, result.stdout
    assert "refusing overwrite" in result.stdout
    assert _snapshot(consumer) == before


def test_shell_backs_up_both_unmanaged_hooks(consumer: Path, framework: Path) -> None:
    for name in HOOK_NAMES:
        _write(consumer / ".git/hooks" / name, f"# custom {name}\n".encode())

    result = _shell(consumer, framework)

    assert result.returncode == 0, result.stdout
    for name in HOOK_NAMES:
        assert (consumer / ".git/hooks" / name).read_bytes() == NEW_HOOK
        backups = list((consumer / ".git/hooks").glob(f"{name}.bak.*"))
        assert len(backups) == 1
        assert backups[0].read_bytes() == f"# custom {name}\n".encode()
    assert REPOSITORY_ID in json.loads((consumer / IDENTITY_CONFIG_REL).read_bytes())["repository_identities"]


@pytest.mark.parametrize("prior", [False, True])
@pytest.mark.parametrize("crlf", [False, True])
def test_shell_upgrades_only_exact_standard_hooks(
    consumer: Path, framework: Path, prior: bool, crlf: bool,
) -> None:
    payload = OLD_HOOK if prior else NEW_HOOK
    if crlf:
        payload = payload.replace(b"\n", b"\r\n")
    for name in HOOK_NAMES:
        _write(consumer / ".git/hooks" / name, payload)

    result = _shell(consumer, framework)

    assert result.returncode == 0, result.stdout
    for name in HOOK_NAMES:
        hook = consumer / ".git/hooks" / name
        assert hook.read_bytes() == NEW_HOOK
        if os.name != "nt":
            assert hook.stat().st_mode & 0o111 == 0o111
    assert not list((consumer / ".git/hooks").glob("*.bak.*"))
    assert (consumer / ".git/hooks/ai-governance-framework-root").read_text().strip() == framework.as_posix()


def test_shell_upgrades_declared_composition(consumer: Path, framework: Path) -> None:
    _declare_composition(consumer)
    _write(consumer / ".git/hooks/pre-push", _composed_hook(1))

    result = _shell(consumer, framework)

    assert result.returncode == 0, result.stdout
    assert (consumer / ".git/hooks/pre-push").read_bytes() == _composed_hook(2)
    assert not list((consumer / ".git/hooks").glob("*.bak.*"))


@pytest.mark.parametrize("state", ["empty", "unmanaged", "standard", "prior", "declared"])
def test_shell_dry_run_never_mutates_files(
    consumer: Path, framework: Path, state: str,
) -> None:
    if state == "declared":
        _declare_composition(consumer)
        _write(consumer / ".git/hooks/pre-push", _composed_hook(1))
    elif state != "empty":
        payload = {"unmanaged": b"# custom\n", "standard": NEW_HOOK, "prior": OLD_HOOK}[state]
        for name in HOOK_NAMES:
            _write(consumer / ".git/hooks" / name, payload)
    _seed_consumer_files(consumer, identity_present=state != "empty")
    before = _snapshot(consumer)
    framework_before = _snapshot(framework)

    result = _shell(consumer, framework, dry_run=True)

    assert result.returncode == 0, result.stdout
    assert "[dry-run]" in result.stdout
    assert _snapshot(consumer) == before
    assert _snapshot(framework) == framework_before
