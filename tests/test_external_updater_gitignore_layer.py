"""Tests for the F-7 updater's consumer .gitignore hygiene layer.

Covers _ensure_gitignore_hygiene() and _check_gitignore_hygiene() in
external_governance_submodule_updater. The staging/commit integration is covered
by the apply tests in test_external_governance_submodule_updater.py; these tests
verify the layer logic in isolation and that it reuses the canonical block from
adopt_governance (single source of truth).
"""

from pathlib import Path

from governance_tools.adopt_governance import _GITIGNORE_HYGIENE_START
from governance_tools.external_governance_submodule_updater import (
    _check_gitignore_hygiene,
    _ensure_gitignore_hygiene,
)


def test_check_reports_missing_then_verified(tmp_path: Path) -> None:
    assert _check_gitignore_hygiene(tmp_path) == "missing"
    _ensure_gitignore_hygiene(tmp_path)
    assert _check_gitignore_hygiene(tmp_path) == "verified"


def test_ensure_creates_block_when_missing(tmp_path: Path) -> None:
    report = _ensure_gitignore_hygiene(tmp_path)
    assert report["status"] == "updated"
    assert report["changed_files"] == [".gitignore"]
    assert report["errors"] == []
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert _GITIGNORE_HYGIENE_START in text
    assert "artifacts/runtime/" in text


def test_ensure_is_idempotent(tmp_path: Path) -> None:
    _ensure_gitignore_hygiene(tmp_path)
    report = _ensure_gitignore_hygiene(tmp_path)
    assert report["status"] == "verified"
    assert report["changed_files"] == []
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text.count(_GITIGNORE_HYGIENE_START) == 1


def test_ensure_preserves_existing_lines(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("dist/\n*.tmp\n", encoding="utf-8")
    _ensure_gitignore_hygiene(tmp_path)
    text = gitignore.read_text(encoding="utf-8")
    assert "dist/" in text
    assert "*.tmp" in text
    assert text.index("dist/") < text.index(_GITIGNORE_HYGIENE_START)
