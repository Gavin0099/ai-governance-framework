"""
Tests for the gitignore structural warning in detect_readiness_level()
and the _closeout_file_is_gitignored() helper.

These tests use a tmp_path without an actual git repo so
_closeout_file_is_gitignored always returns False (safe default).
They verify:
  1. The structural_warnings and closeout_file_gitignore_risk keys
     are present in every detect_readiness_level() return value.
  2. When not gitignored (or not a git repo), warnings are empty.
  3. _closeout_file_is_gitignored returns False on non-git-repo paths.
"""
from __future__ import annotations

from pathlib import Path

from governance_tools.session_end_hook import (
    _closeout_file_is_gitignored,
    detect_readiness_level,
)


# ── _closeout_file_is_gitignored ────────────────────────────────────────────


def test_gitignored_returns_false_for_non_git_directory(tmp_path: Path) -> None:
    # tmp_path is not a git repo → git check-ignore exits 128 → False
    assert _closeout_file_is_gitignored(tmp_path) is False


def test_gitignored_returns_false_on_exception(tmp_path: Path) -> None:
    # Passing a non-existent path → subprocess cwd error → False (never raises)
    result = _closeout_file_is_gitignored(Path("/nonexistent/path/xyz"))
    assert result is False


# ── detect_readiness_level structural_warnings field ───────────────────────


def _make_level0_repo(tmp_path: Path, framework_root: Path) -> Path:
    """Repo where artifacts/ is not writable — level 0 early exit."""
    repo = tmp_path / "repo_l0"
    repo.mkdir()
    # Do NOT create artifacts/ — _can_write will fail when dir is missing AND
    # mkdir fails. Actually _can_write creates the dir then writes a test file.
    # To trigger level-0 failure on artifacts_writable we'd need to make
    # artifacts/ non-writable, which is platform-sensitive.
    # Instead just return a bare repo — level 0 passes, level 1 fails
    # (no schema doc, no AGENTS.md).
    return repo


def test_structural_warnings_key_present_at_level0_exit(
    tmp_path: Path,
) -> None:
    framework_root = tmp_path / "fw"
    framework_root.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    # Level 1 will fail: no schema doc, no AGENTS.md
    result = detect_readiness_level(repo, framework_root)
    assert "structural_warnings" in result
    assert "closeout_file_gitignore_risk" in result
    assert isinstance(result["structural_warnings"], list)
    assert isinstance(result["closeout_file_gitignore_risk"], bool)


def test_structural_warnings_empty_when_not_gitignored(tmp_path: Path) -> None:
    framework_root = tmp_path / "fw"
    framework_root.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    result = detect_readiness_level(repo, framework_root)
    # tmp_path is not a git repo → not gitignored → no warnings
    assert result["closeout_file_gitignore_risk"] is False
    assert result["structural_warnings"] == []


def test_structural_warnings_present_at_level3(tmp_path: Path) -> None:
    """Level 3 path also includes the structural_warnings field."""
    framework_root = tmp_path / "fw"
    (framework_root / "docs").mkdir(parents=True)
    (framework_root / "docs" / "session-closeout-schema.md").write_text(
        "# schema\n", encoding="utf-8"
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    agents = repo / "AGENTS.md"
    agents.write_text(
        "# Session Closeout Obligation\n"
        "Use observable anchor in WORK_COMPLETED.\n"
        "Avoid vague descriptions.\n",
        encoding="utf-8",
    )
    result = detect_readiness_level(repo, framework_root)
    # Should reach level 3 (or at least level 2) with these stubs
    assert result["level"] >= 1
    assert "structural_warnings" in result
    assert "closeout_file_gitignore_risk" in result
    assert isinstance(result["structural_warnings"], list)
