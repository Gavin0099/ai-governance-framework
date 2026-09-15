from pathlib import Path
import os
import shutil
import subprocess
import sys
import json

import pytest

from governance_tools import composed_hook as composition
from governance_tools.external_governance_submodule_updater import (
    _ensure_hook_advisory, _preexisting_unmanaged_hook_overlaps, SubmoduleUpdateError,
)
from governance_tools.hook_installer import install_governance_hooks

FIXTURES = Path(__file__).parent / "fixtures" / "lenovo_composed_hook"
BASE = b'''#!/usr/bin/env bash
# AI Governance Framework
TARGET_REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ "${FRAMEWORK_REJECT:-0}" = 1 ]; then exit 41; fi
# MEMORY_WORKFLOW_TOOL memory_workflow
# Fail-closed structured memory freshness gate.
exit 0
'''


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture
def layout(tmp_path):
    repo, framework = tmp_path / "consumer", tmp_path / "framework"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    for relative in composition.FINGERPRINTS:
        write(repo / relative, (FIXTURES / Path(relative).name).read_bytes())
    write(repo / composition.GATE, b"# test-only gate; production gate behavior is not claimed\nexit 0\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "tracked composition fixture")
    for name in ("pre-commit", "pre-push"):
        write(framework / "scripts/hooks" / name, BASE)
    write(framework / ".governance/version_manifest.yaml", b"default_self_smoke_contract_dependency: not_applicable\n")
    return repo, framework


def expected(base=BASE):
    # Independent fixture construction: literal split at the known insertion
    # boundary, not a call to the production composer under test.
    before, after = base.split(b"# Fail-closed structured memory freshness gate.")
    fragment = (FIXTURES / "pre-push.memory-quality.fragment.sh").read_bytes()
    return before + fragment + b"# Fail-closed structured memory freshness gate." + after


def install(repo, framework):
    return install_governance_hooks(repo, framework, include_copilot=False, repository_identities=["example.invalid/consumer"])


def test_raw_without_declaration_remains_supported(tmp_path):
    repo, framework = tmp_path / "repo", tmp_path / "framework"
    repo.mkdir()
    git(repo, "init")
    for name in ("pre-commit", "pre-push"):
        write(framework / "scripts/hooks" / name, BASE)
        write(repo / ".git/hooks" / name, BASE)
    assert _preexisting_unmanaged_hook_overlaps(repo, framework) == []
    assert composition.expected_hook(repo, "pre-push", BASE) == BASE


def test_committed_composition_install_guard_and_idempotence(layout):
    repo, framework = layout
    assert install(repo, framework).ok
    target = repo / ".git/hooks/pre-push"
    assert target.read_bytes() == expected()
    assert _preexisting_unmanaged_hook_overlaps(repo, framework) == []
    before = (target.read_bytes(), target.stat().st_mtime_ns)
    assert install(repo, framework).ok
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before


@pytest.mark.parametrize("bad", [BASE, expected() + b"echo unknown\n", None])
def test_declared_extension_missing_or_unknown_mutation_rejected(layout, bad):
    repo, framework = layout
    assert install(repo, framework).ok
    target = repo / ".git/hooks/pre-push"
    if bad is None:
        target.unlink()
    else:
        target.write_bytes(bad)
    assert ".git/hooks/pre-push" in _preexisting_unmanaged_hook_overlaps(repo, framework)
    if bad is not None:
        assert not install(repo, framework).ok
        assert target.read_bytes() == bad


@pytest.mark.parametrize("kind", ["dirty", "staged", "missing", "untracked"])
def test_declaration_must_be_committed_and_unchanged(layout, kind):
    repo, framework = layout
    path = repo / composition.FRAGMENT
    if kind == "missing":
        path.unlink()
    elif kind == "untracked":
        git(repo, "rm", "--cached", composition.FRAGMENT)
    else:
        path.write_bytes(path.read_bytes() + b"# edit\n")
        if kind == "staged":
            git(repo, "add", composition.FRAGMENT)
    with pytest.raises(SubmoduleUpdateError):
        _preexisting_unmanaged_hook_overlaps(repo, framework)
    assert not install(repo, framework).ok
    assert not (repo / ".git/hooks/pre-push").exists()


def test_removed_declaration_cannot_downgrade_installed_composition(layout):
    repo, framework = layout
    assert install(repo, framework).ok
    target = repo / ".git/hooks/pre-push"
    before = target.read_bytes()
    for relative in composition.FINGERPRINTS:
        (repo / relative).unlink()
    assert not install(repo, framework).ok
    assert target.read_bytes() == before
    assert ".git/hooks/pre-push" in _preexisting_unmanaged_hook_overlaps(repo, framework)


def test_update_base_preserves_extension_and_second_refresh_is_stable(layout):
    repo, framework = layout
    assert install(repo, framework).ok
    assert _preexisting_unmanaged_hook_overlaps(repo, framework) == []
    newer = BASE.replace(b"# AI Governance Framework", b"# AI Governance Framework\n# new base")
    (framework / "scripts/hooks/pre-push").write_bytes(newer)
    assert _ensure_hook_advisory(repo, framework)["status"] == "updated"
    target = repo / ".git/hooks/pre-push"
    assert target.read_bytes() == expected(newer)
    assert _preexisting_unmanaged_hook_overlaps(repo, framework) == []
    assert install(repo, framework).ok
    before = target.stat().st_mtime_ns
    assert _ensure_hook_advisory(repo, framework)["status"] == "verified"
    assert target.stat().st_mtime_ns == before


def commit_framework(framework):
    if not (framework / '.git').exists():
        git(framework, 'init')
        git(framework, 'config', 'user.email', 'fixture@example.invalid')
        git(framework, 'config', 'user.name', 'Fixture')
    git(framework, 'add', '.')
    git(framework, 'commit', '-m', 'framework fixture')


def test_standalone_upgrade_accepts_exact_prior_composition(layout):
    repo, framework = layout
    commit_framework(framework)
    assert install(repo, framework).ok
    newer = BASE.replace(b'# AI Governance Framework', b'# AI Governance Framework\n# new base')
    write(framework / 'scripts/hooks/pre-push', newer)
    commit_framework(framework)
    # No updater/advisory pre-step: exercise the standalone installer itself.
    result = install(repo, framework)
    assert result.ok, result.errors
    target = repo / '.git/hooks/pre-push'
    assert target.read_bytes() == expected(newer)
    before = (target.read_bytes(), target.stat().st_mtime_ns)
    assert install(repo, framework).ok
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before


def test_standalone_cli_upgrade_preserves_extension(layout):
    repo, framework = layout
    commit_framework(framework)
    assert install(repo, framework).ok
    newer = BASE.replace(b'# AI Governance Framework', b'# AI Governance Framework\n# CLI upgrade')
    write(framework / 'scripts/hooks/pre-push', newer)
    commit_framework(framework)
    result = subprocess.run([
        sys.executable, '-m', 'governance_tools.hook_installer', '--repo', str(repo),
        '--framework-root', str(framework), '--hooks-only', '--repository-id',
        'example.invalid/consumer', '--format', 'json',
    ], capture_output=True, text=True, encoding='utf-8',
        env={**os.environ, 'PYTHONIOENCODING':'utf-8'}, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['ok'] is True
    assert (repo / '.git/hooks/pre-push').read_bytes() == expected(newer)


@pytest.mark.parametrize('bad', [BASE, expected() + b'echo unknown\n',
                               expected().replace(b'exit 41', b'exit 0')])
def test_history_does_not_authorize_mutated_prior_composition(layout, bad):
    repo, framework = layout
    commit_framework(framework)
    assert install(repo, framework).ok
    newer = BASE.replace(b'# AI Governance Framework', b'# AI Governance Framework\n# newer')
    write(framework / 'scripts/hooks/pre-push', newer)
    commit_framework(framework)
    target = repo / '.git/hooks/pre-push'
    target.write_bytes(bad)
    assert not install(repo, framework).ok
    assert target.read_bytes() == bad


def test_prior_base_without_history_is_refused(layout):
    repo, framework = layout
    assert install(repo, framework).ok
    target = repo / '.git/hooks/pre-push'
    before = target.read_bytes()
    write(framework / 'scripts/hooks/pre-push', BASE + b'# new base\n')
    # A source archive carries no old-base authority.
    assert not install(repo, framework).ok
    assert target.read_bytes() == before


def test_unrelated_branch_cannot_authorize_prior_base(layout):
    repo, framework = layout
    commit_framework(framework)
    original = git(framework, 'rev-parse', 'HEAD').decode().strip()
    git(framework, 'checkout', '-b', 'unrelated')
    other = BASE + b'# unrelated base\n'
    write(framework / 'scripts/hooks/pre-push', other)
    commit_framework(framework)
    git(framework, 'checkout', '--detach', original)
    target = repo / '.git/hooks/pre-push'
    write(target, expected(other))
    assert not install(repo, framework).ok
    assert target.read_bytes() == expected(other)


def test_atomic_replace_failure_keeps_old_complete_hook(layout, monkeypatch):
    repo, framework = layout
    assert install(repo, framework).ok
    target = repo / ".git/hooks/pre-push"
    old = target.read_bytes()
    (framework / "scripts/hooks/pre-push").write_bytes(BASE + b"# new\n")
    replace = composition.os.replace

    def fail_pre_push(source, destination):
        if Path(destination) == target:
            raise OSError("injected replacement failure")
        return replace(source, destination)

    monkeypatch.setattr(composition.os, "replace", fail_pre_push)
    result = _ensure_hook_advisory(repo, framework)
    assert result["errors"]
    assert target.read_bytes() == old
    assert not list(target.parent.glob(".governance-hook-*"))


def test_unsupported_new_base_does_not_publish_raw_hook(layout):
    repo, framework = layout
    assert install(repo, framework).ok
    target = repo / ".git/hooks/pre-push"
    before = target.read_bytes()
    (framework / "scripts/hooks/pre-push").write_bytes(b"#!/bin/bash\necho no anchor\n")
    assert _ensure_hook_advisory(repo, framework)["errors"]
    assert target.read_bytes() == before


@pytest.mark.parametrize("framework_reject,extension_reject,code,calls", [(False, False, 0, 1), (True, False, 41, 0), (False, True, 1, 1)])
def test_real_shell_propagates_each_gate_failure(layout, framework_reject, extension_reject, code, calls):
    repo, framework = layout
    assert install(repo, framework).ok
    bash = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")
    if not bash or not Path(bash).exists():
        pytest.skip("bash unavailable; no runtime gate propagation claim")
    # Test-only PowerShell stand-in records actual extension dispatch and exit.
    # It does not claim to validate the consumer's PowerShell gate internals.
    shim = repo / "test-bin/pwsh"
    write(shim, b'#!/usr/bin/env bash\nprintf called >> "$EXTENSION_LOG"\nexit "${EXTENSION_REJECT:-0}"\n')
    shim.chmod(0o755)
    log = repo / "extension.log"
    env = dict(os.environ, PATH=str(shim.parent) + os.pathsep + os.environ["PATH"], EXTENSION_LOG=str(log), FRAMEWORK_REJECT=str(int(framework_reject)), EXTENSION_REJECT="43" if extension_reject else "0")
    result = subprocess.run([bash, str(repo / ".git/hooks/pre-push")], cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == code, result.stderr
    assert (log.read_text().count("called") if log.exists() else 0) == calls
