"""Actual hook execution with isolated Git worktrees and observable smoke stubs."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')


def init(repo):
    repo.mkdir()
    git(repo, 'init')
    git(repo, 'config', 'user.name', 'Fixture')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')


def runtime(repo, code):
    write(repo / 'scripts/run-runtime-governance.sh', f'#!/bin/bash\necho "SMOKE_EXECUTED=$PWD"\nexit {code}\n')


@pytest.fixture
def framework(tmp_path):
    main = tmp_path / 'framework main'
    init(main)
    write(main / 'scripts/lib/python.sh', 'set_python_cmd() { PYTHON_CMD=("$AI_GOVERNANCE_PYTHON"); }\n')
    write(main / 'governance_tools/external_tree_inventory_guard.py', 'import os,sys\nprint("GUARD_EXECUTED")\nsys.exit(int(os.environ.get("FIXTURE_GUARD_EXIT", "0")))\n')
    runtime(main, 0)
    git(main, 'add', '.')
    git(main, 'commit', '-m', 'fixture')
    linked = tmp_path / 'candidate linked'
    git(main, 'worktree', 'add', '--detach', str(linked), 'HEAD')
    return main, linked


def invoke(repo, installed, extra_env=None):
    hook_dir = Path(git(repo, 'rev-parse', '--git-path', 'hooks'))
    if not hook_dir.is_absolute():
        hook_dir = repo / hook_dir
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook = hook_dir / 'pre-push'
    shutil.copyfile(ROOT / 'scripts/hooks/pre-push', hook)
    write(hook_dir / 'ai-governance-framework-root', installed.as_posix() + '\n')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('GIT_', 'AI_GOVERNANCE_'))}
    env.update(AI_GOVERNANCE_PYTHON=sys.executable)
    env.update(extra_env or {})
    return subprocess.run([BASH, hook.as_posix()], cwd=repo, env=env, input='', capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize('main_exit,candidate_exit', [(1,0), (0,7)])
def test_linked_framework_smokes_candidate_not_main(framework, main_exit, candidate_exit):
    main, linked = framework
    runtime(main, main_exit)
    runtime(linked, candidate_exit)
    result = invoke(linked, main)
    assert (result.returncode == 0) == (candidate_exit == 0), (result.stdout, result.stderr)
    assert 'SMOKE_EXECUTED=' in result.stdout
    assert 'candidate linked' in result.stdout.split('SMOKE_EXECUTED=')[1]
    assert 'SMOKE_EXECUTED=' + main.as_posix() not in result.stdout


def test_missing_candidate_script_does_not_fall_back_to_passing_main(framework):
    main, linked = framework
    (linked / 'scripts/run-runtime-governance.sh').unlink()
    result = invoke(linked, main)
    assert result.returncode != 0
    assert 'missing selected self-smoke script' in result.stderr
    assert 'SMOKE_EXECUTED=' not in result.stdout


@pytest.mark.parametrize('git_env', [False, True])
def test_separate_consumer_keeps_installed_framework_even_with_git_environment(framework, tmp_path, git_env):
    main, _ = framework
    consumer = tmp_path / 'consumer'
    init(consumer)
    runtime(consumer, 9)  # Similar-looking consumer files are not repository identity.
    runtime(main, 0)
    env = {'GIT_DIR': str(consumer / '.git'), 'GIT_WORK_TREE': str(consumer)} if git_env else {}
    result = invoke(consumer, main, env)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert 'framework main' in result.stdout.split('SMOKE_EXECUTED=')[1]


def test_plain_framework_directory_inside_consumer_is_not_framework_worktree(tmp_path):
    consumer = tmp_path / 'consumer'
    init(consumer)
    installed = consumer / 'vendor/framework'
    write(installed / 'scripts/lib/python.sh', 'set_python_cmd() { PYTHON_CMD=("$AI_GOVERNANCE_PYTHON"); }\n')
    write(installed / 'governance_tools/external_tree_inventory_guard.py', 'pass\n')
    runtime(installed, 0)
    runtime(consumer, 9)
    result = invoke(consumer, installed)
    assert result.returncode == 0, result.stderr
    assert 'vendor/framework' in result.stdout.split('SMOKE_EXECUTED=')[1]


def test_scanner_failure_still_blocks_before_smoke(framework):
    main, linked = framework
    result = invoke(linked, main, {'FIXTURE_GUARD_EXIT':'4'})
    assert result.returncode != 0
    assert 'SMOKE_EXECUTED=' not in result.stdout
    assert 'external tree inventory guard blocked' in result.stderr


def test_main_framework_smokes_itself(framework):
    main, _ = framework
    result = invoke(main, main)
    assert result.returncode == 0, result.stderr
    assert 'framework main' in result.stdout.split('SMOKE_EXECUTED=')[1]
