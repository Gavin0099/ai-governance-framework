from __future__ import annotations

from pathlib import Path

from governance_tools.ci_memory_workflow_check import check


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _canonical_entry() -> str:
    return (
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: test\n"
        "  commit: abc1234\n"
        "  commit_hash: abc1234\n"
        "  session_id: test-session\n"
        "  memory_binding: bound\n"
        "  test_evidence: test\n"
        "  next_step: none\n"
    )


def test_blocks_current_diff_active_non_canonical_writer(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory" / "2026-06-12.md",
        "- memory_type: session-derived\n"
        "  what_changed: direct write\n"
        "  commit: abc1234\n",
    )

    result = check(tmp_path, changed_files=["memory/2026-06-12.md"])

    assert result.clean is False
    assert result.current_diff_active_non_canonical_writer_count == 1
    assert result.blockers == [
        {
            "code": "active_non_canonical_writer",
            "file": "memory/2026-06-12.md",
            "reason": "session_derived_entry_not_written_by_memory_record",
        }
    ]


def test_historical_active_debt_does_not_block_unrelated_diff(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory" / "2026-06-12.md",
        "- memory_type: session-derived\n"
        "  what_changed: direct write\n"
        "  commit: abc1234\n",
    )

    result = check(tmp_path, changed_files=["README.md"])

    assert result.clean is True
    assert result.active_non_canonical_writer_count == 1
    assert result.current_diff_active_non_canonical_writer_count == 0
    assert result.blockers == []


def test_clean_canonical_memory_diff_does_not_block(tmp_path: Path) -> None:
    _write(tmp_path / "memory" / "2026-06-12.md", _canonical_entry())

    result = check(tmp_path, changed_files=["memory/2026-06-12.md"])

    assert result.clean is True
    assert result.blockers == []
    assert result.current_diff_active_non_canonical_writer_count == 0


def test_historical_warning_window_does_not_block_current_diff(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory" / "2026-05-20.md",
        "- what_changed: legacy direct write\n"
        "  commit: abc1234\n",
    )

    result = check(tmp_path, changed_files=["memory/2026-05-20.md"])

    assert result.clean is True
    assert result.blockers == []
    assert result.current_diff_active_non_canonical_writer_count == 0


def test_ci_surfaces_test_evidence_provenance_warning_without_blocking(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "memory" / "2026-07-05.md",
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: provenance warning fixture\n"
        "  test_evidence: PASS: 67 passed\n"
        "  next_step: none\n",
    )

    result = check(tmp_path, changed_files=["memory/2026-07-05.md"])

    assert result.clean is True
    assert result.blockers == []
    assert "test_evidence_provenance_not_found=1" in result.warnings
