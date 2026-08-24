from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from governance_tools.hook_installer import install_governance_hooks


REPO_ROOT = Path(__file__).resolve().parents[1]
ZERO_OID = "0" * 40


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return (completed.stdout or "").strip()


def _git_bash() -> Path:
    candidates: list[Path] = []
    configured = os.environ.get("BASH")
    if configured:
        candidates.append(Path(configured))
    if os.name == "nt":
        candidates.extend(
            [
                Path("C:/Program Files/Git/bin/bash.exe"),
                Path("C:/Program Files/Git/usr/bin/bash.exe"),
            ]
        )
    discovered = shutil.which("bash")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    pytest.skip("Git Bash/bash is required for managed hook execution tests")


def _make_consumer(
    tmp_path: Path,
    *,
    runtime_exit: int = 0,
    python_helper: str = "set_python_cmd() { PYTHON_CMD=(python); return 0; }\n",
) -> tuple[Path, Path]:
    repo = tmp_path / "consumer"
    framework = tmp_path / "framework"
    repo.mkdir()
    _run_git(repo, "init")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test User")
    _write(repo / "README.md", "baseline\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-m", "baseline")

    for hook_name in ("pre-commit", "pre-push"):
        source = REPO_ROOT / "scripts" / "hooks" / hook_name
        _write(
            framework / "scripts" / "hooks" / hook_name,
            source.read_text(encoding="utf-8"),
        )
    _write(
        framework / "scripts" / "lib" / "python.sh",
        python_helper,
    )
    _write(
        framework / "scripts" / "run-runtime-governance.sh",
        "#!/bin/bash\n"
        "echo SYNTHETIC_PRE_PUSH_RUNTIME_REACHED\n"
        f"exit {runtime_exit}\n",
    )

    result = install_governance_hooks(
        repo,
        framework,
        include_copilot=False,
    )
    assert result.ok is True
    return repo, framework


def _run_pre_push(
    repo: Path,
    update_line: str,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    hook = repo / ".git" / "hooks" / "pre-push"
    return subprocess.run(
        [str(_git_bash()), "--login", hook.as_posix(), "origin", "unused"],
        cwd=repo,
        input=update_line,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )


def _git_executable() -> Path:
    discovered = shutil.which("git")
    if not discovered:
        pytest.skip("git is required for managed hook execution tests")
    return Path(discovered)


def _git_only_path(tmp_path: Path) -> str:
    git = _git_executable()
    if os.name == "nt":
        return str(git.parent)

    bin_dir = tmp_path / "git-only-bin"
    bin_dir.mkdir()
    (bin_dir / "git").symlink_to(git)
    return str(bin_dir)


def _run_actual_push(
    repo: Path,
    remote: Path,
    *,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    _run_git(repo, "remote", "add", "origin", str(remote))
    return subprocess.run(
        [str(_git_executable()), "push", "origin", "HEAD:refs/heads/main"],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )


def _make_bare_remote(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(
        [str(_git_executable()), "init", "--bare", str(remote)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return remote


def _bare_remote_refs(remote: Path) -> str:
    completed = subprocess.run(
        [str(_git_executable()), "ls-remote", str(remote)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return (completed.stdout or "").strip()


def test_memory_policy_authority_stays_in_ci_with_advisory_pre_commit() -> None:
    pre_commit = (REPO_ROOT / "scripts" / "hooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    pre_push = (REPO_ROOT / "scripts" / "hooks" / "pre-push").read_text(
        encoding="utf-8"
    )
    workflow = (REPO_ROOT / ".github" / "workflows" / "governance.yml").read_text(
        encoding="utf-8"
    )

    assert "python -m governance_tools.ci_memory_workflow_check" in workflow
    assert (
        '"$MEMORY_WORKFLOW_TOOL" --repo "$TARGET_REPO_ROOT" --check '
        "--run-guard --format json"
    ) in pre_commit
    assert "pre-commit advisory only; commit is not blocked" in pre_commit

    forbidden_pre_push_tokens = (
        "TODAY_MEMORY_PATH",
        "MEMORY_UPDATED_IN_PUSH",
        "memory_freshness_guard.py",
        "daily_memory_guard.py",
        "blocked: missing required memory file",
        "blocked: push does not include",
    )
    for token in forbidden_pre_push_tokens:
        assert token not in pre_push


def test_git_bash_branch_deletion_is_not_blocked_by_memory_policy(
    tmp_path: Path,
) -> None:
    repo, _framework = _make_consumer(tmp_path)
    remote_head = _run_git(repo, "rev-parse", "HEAD")

    completed = _run_pre_push(
        repo,
        f"refs/heads/topic {ZERO_OID} refs/heads/topic {remote_head}\n",
    )

    assert completed.returncode == 0, completed.stdout
    assert "[governance] blocked:" not in completed.stdout


def test_git_bash_product_push_does_not_require_future_post_push_memory(
    tmp_path: Path,
) -> None:
    repo, _framework = _make_consumer(tmp_path)
    remote_head = _run_git(repo, "rev-parse", "HEAD")
    _write(repo / "product.txt", "product-only change\n")
    _run_git(repo, "add", "product.txt")
    # This fixture targets pre-push behavior. Avoid invoking the independently
    # covered pre-commit hook while constructing the outgoing product commit.
    _run_git(repo, "commit", "--no-verify", "-m", "product change")
    local_head = _run_git(repo, "rev-parse", "HEAD")

    assert not (repo / "memory").exists()
    completed = _run_pre_push(
        repo,
        f"refs/heads/main {local_head} refs/heads/main {remote_head}\n",
    )

    assert completed.returncode == 0, completed.stdout
    assert "[governance] blocked:" not in completed.stdout


def test_pre_push_prerequisites_do_not_depend_on_coreutils() -> None:
    pre_push = (REPO_ROOT / "scripts" / "hooks" / "pre-push").read_text(
        encoding="utf-8"
    )

    assert pre_push.startswith("#!/bin/bash\n")
    assert "$(dirname " not in pre_push
    assert "$(cat " not in pre_push
    assert " | tr " not in pre_push
    assert "$(basename " not in pre_push
    assert " | sed " not in pre_push
    assert "WSL drive-path mapping is intentionally unsupported" in pre_push


@pytest.mark.parametrize("path_mode", ["complete", "git-only"])
def test_external_consumer_runtime_failure_blocks_actual_push_without_fail_open(
    tmp_path: Path,
    path_mode: str,
) -> None:
    repo, framework = _make_consumer(tmp_path, runtime_exit=23)
    remote = _make_bare_remote(tmp_path)
    hook = repo / ".git" / "hooks" / "pre-push"
    # This slice validates the hook source under Bash 3.2, not the Python
    # installer's separate POSIX executable-mode behavior.
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    env = os.environ.copy()
    env.pop("AI_GOVERNANCE_FRAMEWORK_ROOT", None)
    if path_mode == "git-only":
        env["PATH"] = _git_only_path(tmp_path)

    completed = _run_actual_push(repo, remote, env=env)

    assert completed.returncode != 0, completed.stdout
    assert "SYNTHETIC_PRE_PUSH_RUNTIME_REACHED" in completed.stdout
    assert "runtime-governance enforcement failed" in completed.stdout
    assert "command not found" not in completed.stdout
    assert f"framework_root={framework.as_posix()}" in completed.stdout
    assert "/c//" not in completed.stdout.lower()
    assert "/d//" not in completed.stdout.lower()
    assert _bare_remote_refs(remote) == ""


@pytest.mark.parametrize(
    ("case", "expected_error"),
    [
        ("missing-config", "framework root config is missing"),
        ("empty-config", "framework root is not configured"),
        ("missing-root", "framework root does not exist: D:/missing-framework-root"),
        ("missing-python-helper", "missing framework Python helper"),
        (
            "missing-set-python-cmd",
            "framework Python helper does not define set_python_cmd",
        ),
        ("set-python-cmd-fails", "Python is required by the pre-push hook"),
        (
            "empty-python-command",
            "framework Python helper did not select a Python command",
        ),
        ("missing-runtime", "missing runtime governance script"),
    ],
)
def test_pre_push_prerequisite_failures_are_explicit_and_blocking(
    tmp_path: Path,
    case: str,
    expected_error: str,
) -> None:
    repo, framework = _make_consumer(tmp_path)
    hook_dir = repo / ".git" / "hooks"
    config = hook_dir / "ai-governance-framework-root"
    python_helper = framework / "scripts" / "lib" / "python.sh"
    runtime_script = framework / "scripts" / "run-runtime-governance.sh"

    if case == "missing-config":
        config.unlink()
    elif case == "empty-config":
        _write(config, "")
    elif case == "missing-root":
        _write(config, "D:/missing-framework-root\n")
    elif case == "missing-python-helper":
        python_helper.unlink()
    elif case == "missing-set-python-cmd":
        _write(python_helper, ":\n")
    elif case == "set-python-cmd-fails":
        _write(python_helper, "set_python_cmd() { return 1; }\n")
    elif case == "empty-python-command":
        _write(python_helper, "set_python_cmd() { PYTHON_CMD=(); return 0; }\n")
    elif case == "missing-runtime":
        runtime_script.unlink()
    else:  # pragma: no cover - the parametrization is closed above
        raise AssertionError(f"unknown prerequisite case: {case}")

    env = os.environ.copy()
    env.pop("AI_GOVERNANCE_FRAMEWORK_ROOT", None)
    completed = _run_pre_push(
        repo,
        f"refs/heads/main {ZERO_OID} refs/heads/main {ZERO_OID}\n",
        env=env,
    )

    assert completed.returncode != 0, completed.stdout
    assert expected_error in completed.stdout
