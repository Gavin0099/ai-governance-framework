from __future__ import annotations

from pathlib import Path

import pytest

from governance_tools import dirty_runtime_ledger_detector as detector


def test_parse_porcelain_status_ignores_unrelated_files() -> None:
    rows = detector.parse_porcelain_status(
        [
            " M README.md",
            "M  governance_tools/example.py",
        ]
    )

    assert rows == []


def test_parse_porcelain_status_detects_unstaged_manual_promotion_ledgers() -> None:
    rows = detector.parse_porcelain_status(
        [
            " M .governance-state.yaml",
            " M artifacts/claim-enforcement/claim-enforcement-receipts.ndjson",
            " M artifacts/session-index.ndjson",
        ]
    )

    assert [row.path for row in rows] == [
        ".governance-state.yaml",
        "artifacts/claim-enforcement/claim-enforcement-receipts.ndjson",
        "artifacts/session-index.ndjson",
    ]
    assert all(row.unstaged for row in rows)
    assert not any(row.staged for row in rows)


def test_parse_porcelain_status_detects_staged_manual_promotion_ledger() -> None:
    rows = detector.parse_porcelain_status(
        ["M  artifacts/claim-enforcement/claim-enforcement-receipts.ndjson"]
    )

    assert len(rows) == 1
    assert rows[0].staged is True
    assert rows[0].unstaged is False
    assert rows[0].untracked is False


def test_parse_porcelain_status_detects_untracked_manual_promotion_ledger() -> None:
    rows = detector.parse_porcelain_status(["?? artifacts/session-index.ndjson"])

    assert len(rows) == 1
    assert rows[0].path == "artifacts/session-index.ndjson"
    assert rows[0].untracked is True


def test_warning_mode_remains_ok_when_ledgers_are_dirty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        detector,
        "_git_status",
        lambda _project_root: [" M artifacts/session-index.ndjson"],
    )

    result = detector.inspect_ledgers(Path("."), fail_on_dirty=False)

    assert result.ok is True
    assert result.mode == "warning_only"
    assert result.dirty_count == 1


def test_fail_on_dirty_mode_returns_not_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        detector,
        "_git_status",
        lambda _project_root: [" M artifacts/session-index.ndjson"],
    )

    result = detector.inspect_ledgers(Path("."), fail_on_dirty=True)

    assert result.ok is False
    assert result.mode == "fail_on_dirty"
    assert result.dirty_count == 1


def test_format_human_includes_required_next_action_for_dirty_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        detector,
        "_git_status",
        lambda _project_root: ["M  artifacts/claim-enforcement/claim-enforcement-receipts.ndjson"],
    )

    text = detector.format_human(detector.inspect_ledgers(Path(".")))

    assert "dirty_count=1" in text
    assert "manual_promotion_ledgers" in text
    assert "required_next_action" in text
    assert "explicit evidence-capture scope" in text
