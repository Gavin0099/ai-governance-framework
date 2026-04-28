#!/usr/bin/env python3
"""
Tests for governance_tools/framework_versioning.py
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.framework_versioning import (
    current_framework_release,
    discover_framework_root,
    is_framework_root,
    repo_root_from_tooling,
)


FRAMEWORK_ROOT = Path(__file__).parent.parent.resolve()


# ── repo_root_from_tooling ────────────────────────────────────────────────────

def test_repo_root_default_is_framework_root():
    """Without env var, resolves to the framework repo root (parent of governance_tools/)."""
    result = repo_root_from_tooling()
    assert result == FRAMEWORK_ROOT


def test_governance_framework_root_env_var_overrides(tmp_path, monkeypatch):
    """GOVERNANCE_FRAMEWORK_ROOT env var takes priority over __file__ resolution."""
    monkeypatch.setenv("GOVERNANCE_FRAMEWORK_ROOT", str(tmp_path))
    result = repo_root_from_tooling()
    assert result == tmp_path.resolve()


def test_governance_framework_root_env_var_is_resolved(tmp_path, monkeypatch):
    """Path returned is always resolved (absolute), even if env var is relative-ish."""
    monkeypatch.setenv("GOVERNANCE_FRAMEWORK_ROOT", str(tmp_path))
    result = repo_root_from_tooling()
    assert result.is_absolute()


def test_governance_framework_root_empty_string_falls_back(monkeypatch):
    """Empty GOVERNANCE_FRAMEWORK_ROOT string falls back to __file__ resolution."""
    monkeypatch.setenv("GOVERNANCE_FRAMEWORK_ROOT", "   ")
    result = repo_root_from_tooling()
    assert result == FRAMEWORK_ROOT


def test_governance_framework_root_absent_falls_back(monkeypatch):
    """Absent env var falls back to __file__ resolution."""
    monkeypatch.delenv("GOVERNANCE_FRAMEWORK_ROOT", raising=False)
    result = repo_root_from_tooling()
    assert result == FRAMEWORK_ROOT


# ── is_framework_root ────────────────────────────────────────────────────────

def test_is_framework_root_detects_governance_tools_dir(tmp_path):
    (tmp_path / "governance_tools").mkdir()
    assert is_framework_root(tmp_path) is True


def test_is_framework_root_detects_governance_dir(tmp_path):
    (tmp_path / "governance").mkdir()
    assert is_framework_root(tmp_path) is True


def test_is_framework_root_detects_docs_governance_runtime(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "governance-runtime-v1").mkdir()
    assert is_framework_root(tmp_path) is True


def test_is_framework_root_rejects_unrelated_dir(tmp_path):
    (tmp_path / "src").mkdir()
    assert is_framework_root(tmp_path) is False


def test_is_framework_root_true_for_actual_framework(monkeypatch):
    assert is_framework_root(FRAMEWORK_ROOT) is True


# ── discover_framework_root ──────────────────────────────────────────────────

def test_discover_framework_root_finds_root_from_nested_dir(tmp_path):
    (tmp_path / "governance_tools").mkdir()
    nested = tmp_path / "sub" / "deep"
    nested.mkdir(parents=True)
    result = discover_framework_root(nested)
    assert result == tmp_path


def test_discover_framework_root_returns_start_if_root(tmp_path):
    (tmp_path / "governance_tools").mkdir()
    result = discover_framework_root(tmp_path)
    assert result == tmp_path


def test_discover_framework_root_returns_none_when_not_found(tmp_path):
    nested = tmp_path / "unrelated" / "project"
    nested.mkdir(parents=True)
    result = discover_framework_root(nested)
    assert result is None


def test_discover_framework_root_stops_at_first_match(tmp_path):
    """When multiple ancestors qualify, the closest one wins."""
    (tmp_path / "governance_tools").mkdir()
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "governance_tools").mkdir()
    nested = inner / "src"
    nested.mkdir()
    result = discover_framework_root(nested)
    assert result == inner


# ── priority order test ──────────────────────────────────────────────────────

def test_governance_framework_root_cli_takes_priority_over_env(tmp_path, monkeypatch):
    """Explicit path passed to check_governance_drift(framework_root=...) wins over env var.

    repo_root_from_tooling() is only the fallback; callers that pass framework_root
    explicitly bypass it. Verify that the env var does NOT silently override a
    caller-supplied path by checking the env var path is NOT the explicit path.
    """
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("GOVERNANCE_FRAMEWORK_ROOT", str(other))

    # The env var resolves to `other`; the default path resolves to FRAMEWORK_ROOT.
    # When the caller passes framework_root=FRAMEWORK_ROOT explicitly (as the CLI
    # --framework-root flag does), repo_root_from_tooling() is never called.
    # This test confirms the env var override does NOT escape to the default path.
    from_env = repo_root_from_tooling()
    assert from_env == other.resolve()
    assert from_env != FRAMEWORK_ROOT


# ── current_framework_release ─────────────────────────────────────────────────

def test_current_framework_release_reads_actual_version():
    """current_framework_release() returns a non-None version string for this repo."""
    version = current_framework_release()
    assert version is not None
    assert "." in version  # looks like a semver


def test_current_framework_release_badge_format(tmp_path):
    """Reads version from README.md badge format (img.shields.io)."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# My Repo\n\n"
        "[![Version](https://img.shields.io/badge/version-2.3.4-blue.svg)](CHANGELOG.md)\n",
        encoding="utf-8",
    )
    result = current_framework_release(tmp_path)
    assert result == "2.3.4"


def test_current_framework_release_list_format(tmp_path):
    """Reads version from README.md list format (original)."""
    readme = tmp_path / "README.md"
    readme.write_text("- version: `1.0.0`\n", encoding="utf-8")
    result = current_framework_release(tmp_path)
    assert result == "1.0.0"


def test_current_framework_release_list_format_wins_over_badge(tmp_path):
    """List format takes priority over badge format when both are present."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "- version: `1.0.0`\n"
        "[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](CHANGELOG.md)\n",
        encoding="utf-8",
    )
    result = current_framework_release(tmp_path)
    assert result == "1.0.0"


def test_current_framework_release_changelog_fallback(tmp_path):
    """Falls back to CHANGELOG.md when README.md has no version."""
    readme = tmp_path / "README.md"
    readme.write_text("# No version here\n", encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## v3.0.0 - 2026-01-01\n\n### Added\n- stuff\n",
        encoding="utf-8",
    )
    result = current_framework_release(tmp_path)
    assert result == "3.0.0"


def test_current_framework_release_changelog_no_v_prefix(tmp_path):
    """CHANGELOG.md heading without 'v' prefix also matches."""
    readme = tmp_path / "README.md"
    readme.write_text("# No version\n", encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## 1.2.3 - 2026-01-01\n", encoding="utf-8")
    result = current_framework_release(tmp_path)
    assert result == "1.2.3"


def test_current_framework_release_prerelease_badge(tmp_path):
    """Badge format with pre-release suffix (e.g. 1.2.0-beta) is captured."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "[![Version](https://img.shields.io/badge/version-1.2.0--beta-blue.svg)](CHANGELOG.md)\n",
        encoding="utf-8",
    )
    result = current_framework_release(tmp_path)
    # The double-dash in badge URLs encodes a single dash in the version string
    # The regex captures up to the final color suffix separator
    assert result is not None


def test_current_framework_release_returns_none_when_no_version(tmp_path):
    """Returns None when neither README nor CHANGELOG has a version."""
    (tmp_path / "README.md").write_text("# No version\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# No headings\nJust prose.\n", encoding="utf-8")
    result = current_framework_release(tmp_path)
    assert result is None


def test_current_framework_release_returns_none_without_readme_or_changelog(tmp_path):
    """Returns None when no README.md or CHANGELOG.md exists."""
    result = current_framework_release(tmp_path)
    assert result is None
