"""Tests for the consumer .gitignore hygiene block in adopt_governance.

Covers _ensure_gitignore_hygiene():
  1. creates .gitignore with the managed block when none exists
  2. appends the block while preserving existing user lines
  3. is idempotent (no duplicate block on a second call)
  4. dry-run writes nothing
  5. the block carries the key artifact/pyc ignore patterns
"""

from pathlib import Path

from governance_tools.adopt_governance import (
    _GITIGNORE_HYGIENE_START,
    _ensure_gitignore_hygiene,
    _gitignore_hygiene_block,
)


def test_creates_gitignore_when_missing(tmp_path: Path) -> None:
    _ensure_gitignore_hygiene(tmp_path, dry_run=False)
    gitignore = tmp_path / ".gitignore"
    assert gitignore.exists()
    text = gitignore.read_text(encoding="utf-8")
    assert _GITIGNORE_HYGIENE_START in text
    assert "artifacts/runtime/" in text


def test_appends_block_preserving_existing_lines(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n*.log\n", encoding="utf-8")
    _ensure_gitignore_hygiene(tmp_path, dry_run=False)
    text = gitignore.read_text(encoding="utf-8")
    # user lines preserved
    assert "node_modules/" in text
    assert "*.log" in text
    # managed block added
    assert _GITIGNORE_HYGIENE_START in text
    # user content comes before the managed block
    assert text.index("node_modules/") < text.index(_GITIGNORE_HYGIENE_START)


def test_idempotent_no_duplicate_block(tmp_path: Path) -> None:
    _ensure_gitignore_hygiene(tmp_path, dry_run=False)
    first = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    _ensure_gitignore_hygiene(tmp_path, dry_run=False)
    second = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert first == second
    assert second.count(_GITIGNORE_HYGIENE_START) == 1


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    _ensure_gitignore_hygiene(tmp_path, dry_run=True)
    assert not (tmp_path / ".gitignore").exists()

    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("keep-me\n", encoding="utf-8")
    _ensure_gitignore_hygiene(tmp_path, dry_run=True)
    assert gitignore.read_text(encoding="utf-8") == "keep-me\n"


def test_block_contains_key_patterns() -> None:
    block = _gitignore_hygiene_block()
    for pattern in (
        "__pycache__/",
        "*.py[cod]",
        "artifacts/runtime/",
        "artifacts/session-index.ndjson",
        "artifacts/governance/version_compatibility.json",
        "**/artifacts/runtime/",
    ):
        assert pattern in block
    # memory is intentionally NOT ignored: no active (non-comment) line targets it
    active_lines = [
        ln.strip()
        for ln in block.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert not any("memory" in ln for ln in active_lines)
