"""Operator-approved protected safety configuration must survive scanner setup."""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.external_tree_inventory_guard import main
from tests.test_external_tree_inventory_guard import EXPECTED_REPOSITORY, ZERO_OID, _commit_bytes, _repository


@pytest.mark.parametrize("scope", ["global", "system"])
@pytest.mark.parametrize("approved", [False, True])
def test_real_git_ownership_check_respects_only_approved_protected_config(
    tmp_path: Path, monkeypatch, capsys, scope: str, approved: bool,
):
    repo = _repository(tmp_path)
    tip = _commit_bytes(repo, "safe.json", b'{"ok":true}\n', "safe")
    home = tmp_path / "home"
    home.mkdir()
    config = home / ".gitconfig"
    config.write_text(f'[safe]\n\tdirectory = {repo.as_posix()}\n' if approved else "", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "xdg"))
    original_run, original_popen = subprocess.run, subprocess.Popen

    def owner_test_environment(kwargs):
        kwargs = dict(kwargs)
        env = dict(kwargs["env"])
        # Test-only control activates Git's real dubious-ownership check without
        # privileged chown. Inject AFTER scanner filtering, as actual ownership
        # is filesystem state rather than a production GIT_* selector.
        env["GIT_TEST_ASSUME_DIFFERENT_OWNER"] = "1"
        if scope == "global":
            env["GIT_CONFIG_NOSYSTEM"] = "1"
        else:
            env["GIT_CONFIG_SYSTEM"] = str(config)
            env["GIT_CONFIG_GLOBAL"] = os.devnull
        kwargs["env"] = env
        return kwargs

    def owned_run(command, *args, **kwargs):
        return original_run(command, *args, **owner_test_environment(kwargs))

    def owned_popen(command, *args, **kwargs):
        return original_popen(command, *args, **owner_test_environment(kwargs))

    monkeypatch.setattr("governance_tools.external_tree_inventory_guard.subprocess.run", owned_run)
    monkeypatch.setattr("governance_tools.external_tree_inventory_guard.subprocess.Popen", owned_popen)
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/new {tip} refs/heads/new {ZERO_OID}\n"))
    result = main(["--pre-push-updates", "--repo-root", str(repo), "--repository-id", EXPECTED_REPOSITORY])
    output = capsys.readouterr()
    assert result == (0 if approved else 4)
    assert ("guard passed" in output.out) if approved else ("local object is unavailable" in output.err)


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable test shim; portable real-Git cases run above")
@pytest.mark.parametrize("approved", [False, True])
def test_outer_scanner_cli_preserves_global_safe_directory(tmp_path: Path, approved: bool):
    repo = _repository(tmp_path)
    tip = _commit_bytes(repo, "safe.json", b'{"ok":true}\n', "safe")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(f'[safe]\n\tdirectory = {repo.as_posix()}\n' if approved else "", encoding="utf-8")
    bin_dir = tmp_path / "test-bin"
    bin_dir.mkdir()
    actual_git = shutil.which("git")
    assert actual_git
    shim = bin_dir / "git"
    # Deliberate test-only launcher: the real outer CLI resolves this fixture
    # executable, which activates Git's ownership check after env filtering.
    # It never launches production code, uses credentials or writes a remote.
    shim.write_text(f'#!{sys.executable}\nimport os, sys\nos.environ["GIT_TEST_ASSUME_DIFFERENT_OWNER"] = "1"\nos.environ["GIT_CONFIG_NOSYSTEM"] = "1"\nos.execv({actual_git!r}, [{actual_git!r}, *sys.argv[1:]])\n', encoding="utf-8")
    shim.chmod(0o755)
    env = os.environ.copy()
    env.update(HOME=str(home), USERPROFILE=str(home), XDG_CONFIG_HOME=str(home / "xdg"),
               PATH=str(bin_dir) + os.pathsep + env.get("PATH", ""))
    result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "governance_tools/external_tree_inventory_guard.py"),
        "--pre-push-updates", "--repo-root", str(repo), "--repository-id", EXPECTED_REPOSITORY],
        input=f"refs/heads/new {tip} refs/heads/new {ZERO_OID}\n", env=env,
        capture_output=True, text=True, check=False)
    assert result.returncode == (0 if approved else 4), result.stderr
    assert ("guard passed" in result.stdout) if approved else ("local object is unavailable" in result.stderr)
