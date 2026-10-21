"""
Regression tests for issues #216 and #217 (ci_memory_workflow_check path handling).

#216  `git diff --name-only` quotes/octal-escapes non-ASCII names by default, so a
      memory file such as memory/2026-06-12-筆記.md was not recognised as a memory
      file and silently bypassed the CI memory blocker.
#217  `_normalize` used str.lstrip("./"), which strips *every* leading "." and "/"
      and so rewrote ".github/x" -> "github/x" and "../memory/x" -> "memory/x".
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from governance_tools.ci_memory_workflow_check import (
    _changed_files_from_refs,
    _is_memory_file,
    _normalize,
    check,
    main,
)
from governance_tools.memory_provenance import (
    _commit_changed_paths,
    detect_staged_mixed_scope_memory_bindings,
    git_changed_paths,
    normalize_repo_path,
)

_SESSION_SHAPED_ENTRY = (
    "- memory_type: session-derived\n"
    "  what_changed: x\n"
    "  commit: abc1234\n"
    "  session_id: s1\n"
)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "core.quotepath=true", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return done.stdout.strip()


def _init(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "seed")


def _commit_files(repo: Path, files: dict[str, str]) -> tuple[str, str]:
    base = _git(repo, "rev-parse", "HEAD")
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add")
    return base, _git(repo, "rev-parse", "HEAD")


# ── #217 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("./memory/a.md", "memory/a.md"),
        ("././memory/a.md", "memory/a.md"),
        ("memory\\a.md", "memory/a.md"),
        ("memory//a.md", "memory/a.md"),
        ("memory/./a.md", "memory/a.md"),
        ("  memory/a.md  ", "memory/a.md"),
        ("memory/", "memory"),
        (".github/workflows/x.yml", ".github/workflows/x.yml"),
        (".governance/x.json", ".governance/x.json"),
        (".memory/x.md", ".memory/x.md"),
        ("../memory/x.md", "../memory/x.md"),
        ("/memory/x.md", "/memory/x.md"),
        ("", ""),
        (".", ""),
        ("./", ""),
    ],
)
def test_normalize_only_removes_leading_dot_slash(raw, expected):
    assert _normalize(raw) == expected
    assert normalize_repo_path(raw) == expected


@pytest.mark.parametrize(
    "raw", [".memory/x.md", "../memory/x.md", "/memory/x.md", ".github/memory/x.md"]
)
def test_paths_outside_memory_dir_are_not_memory_files(raw):
    assert not _is_memory_file(raw)


@pytest.mark.parametrize("raw", ["memory", "memory/", "./memory/a.md", "memory\\a.md"])
def test_memory_paths_are_still_recognised(raw):
    assert _is_memory_file(raw)


def test_check_does_not_treat_dot_prefixed_or_outside_paths_as_memory(tmp_path):
    result = check(
        tmp_path,
        changed_files=[".memory/x.md", "../memory/x.md", ".github/workflows/x.yml", "./memory/a.md"],
    )
    assert result.changed_memory_files == ["memory/a.md"]
    assert ".github/workflows/x.yml" in result.changed_files
    assert "github/workflows/x.yml" not in result.changed_files


# ── #216 ─────────────────────────────────────────────────────────────────────

def test_git_default_quoting_is_the_hazard_being_guarded(tmp_path):
    """Pins the premise: plain `git diff --name-only` mangles non-ASCII names."""
    _init(tmp_path)
    base, head = _commit_files(tmp_path, {"memory/2026-06-12-筆記.md": "x\n"})
    quoted = _git(tmp_path, "diff", "--name-only", f"{base}..{head}")
    assert quoted.startswith('"') and "\\" in quoted


def test_changed_files_keep_non_ascii_names_verbatim(tmp_path):
    _init(tmp_path)
    base, head = _commit_files(
        tmp_path,
        {
            "memory/2026-06-12-筆記.md": "x\n",
            "memory/2026-06-12 notes.md": "x\n",
            "memory/plain.md": "x\n",
            "docs/中文 文件.md": "x\n",
        },
    )

    files = _changed_files_from_refs(tmp_path, base, head)

    assert files == sorted(
        [
            "memory/2026-06-12-筆記.md",
            "memory/2026-06-12 notes.md",
            "memory/plain.md",
            "docs/中文 文件.md",
        ]
    )
    result = check(tmp_path, changed_files=files)
    assert set(result.changed_memory_files) == {
        "memory/2026-06-12-筆記.md",
        "memory/2026-06-12 notes.md",
        "memory/plain.md",
    }


def test_git_changed_paths_preserves_leading_space_in_names(tmp_path):
    _init(tmp_path)
    base, head = _commit_files(tmp_path, {"memory/ lead.md": "x\n"})
    code, paths, _ = git_changed_paths(tmp_path, ["diff", "--name-only", f"{base}..{head}"])
    assert code == 0
    assert paths == ["memory/ lead.md"]


def test_git_changed_paths_preserves_newline_in_names(tmp_path):
    _init(tmp_path)
    try:
        base, head = _commit_files(tmp_path, {"memory/line\nbreak.md": "x\n"})
    except (OSError, subprocess.CalledProcessError):  # Windows cannot create this name
        pytest.skip("filesystem cannot represent newline in filenames")
    code, paths, _ = git_changed_paths(tmp_path, ["diff", "--name-only", f"{base}..{head}"])
    assert code == 0
    assert paths == ["memory/line\nbreak.md"]


def test_git_changed_paths_reports_git_failure(tmp_path):
    _init(tmp_path)
    code, paths, stderr = git_changed_paths(tmp_path, ["diff", "--name-only", "nope..nada"])
    assert code != 0 and paths == [] and stderr


def test_non_ascii_memory_file_is_checked_by_ci_ref_diff(tmp_path, capsys):
    """End to end through --base-ref/--head-ref, the real CI entry point.

    Before the fix the quoted name never reached the memory guard, so the
    session-shaped entry below produced no finding at all.
    """
    _init(tmp_path)
    base, head = _commit_files(tmp_path, {"memory/2026-06-12-筆記.md": _SESSION_SHAPED_ENTRY})

    main(
        [
            "--project-root", str(tmp_path),
            "--base-ref", base,
            "--head-ref", head,
            "--format", "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_memory_files"] == ["memory/2026-06-12-筆記.md"]
    assert "non_daily_session_shaped_memory_entry=1" in payload["warnings"]


def test_commit_and_staged_path_detection_not_quoted(tmp_path):
    _init(tmp_path)
    _, head = _commit_files(tmp_path, {"memory/2026-06-12-筆記.md": "x\n", "src/a.py": "x\n"})
    assert sorted(_commit_changed_paths(tmp_path, head)) == [
        "memory/2026-06-12-筆記.md",
        "src/a.py",
    ]

    (tmp_path / "memory" / "2026-06-13-備忘.md").write_text("y\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    code, staged, _ = git_changed_paths(tmp_path, ["diff", "--cached", "--name-only"])
    assert code == 0 and staged == ["memory/2026-06-13-備忘.md"]
    # must not raise on non-ASCII staged names
    assert isinstance(detect_staged_mixed_scope_memory_bindings(tmp_path), list)
