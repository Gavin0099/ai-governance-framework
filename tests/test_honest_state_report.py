"""Tests for governance_tools/honest_state_report.py"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from governance_tools.honest_state_report import (
    build_report,
    format_human,
    _derive_effectiveness,
)


def _write_ndjson(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )


# ── _derive_effectiveness unit tests ────────────────────────────────────────

def test_no_observed_interceptions_is_not_yet_demonstrated():
    assert _derive_effectiveness(0, 0) == "not_yet_demonstrated"


def test_observed_but_no_high_materiality_is_insufficient():
    assert _derive_effectiveness(3, 0) == "insufficient_evidence"


def test_high_materiality_observed_is_partially_demonstrated():
    assert _derive_effectiveness(2, 1) == "partially_demonstrated"


def test_demonstrated_not_returned():
    # 'demonstrated' is intentionally absent from the vocabulary
    for obs, hi in [(0, 0), (5, 0), (5, 5), (100, 100)]:
        assert _derive_effectiveness(obs, hi) != "demonstrated"


# ── build_report integration tests ──────────────────────────────────────────

@pytest.fixture()
def empty_root(tmp_path):
    return tmp_path


def test_empty_ledgers_return_not_yet_demonstrated(empty_root):
    report = build_report(empty_root)
    assert report["operational_effectiveness"] == "not_yet_demonstrated"
    assert report["observed_interception_count"] == 0
    assert report["observed_bypass_count"] == 0
    assert report["high_materiality_observed_count"] == 0


def test_retroactive_analysis_does_not_count_as_observed(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/intercepted-events.ndjson",
        [
            {
                "event_id": "IE-TEST-001",
                "evidence_basis": "retroactive_analysis",
                "materiality": "high",
            }
        ],
    )
    report = build_report(tmp_path)
    assert report["observed_interception_count"] == 0
    assert report["high_materiality_observed_count"] == 0
    assert report["operational_effectiveness"] == "not_yet_demonstrated"


def test_test_derived_does_not_count_as_observed(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/intercepted-events.ndjson",
        [
            {
                "event_id": "IE-TEST-002",
                "evidence_basis": "test_derived",
                "materiality": "high",
            }
        ],
    )
    report = build_report(tmp_path)
    assert report["observed_interception_count"] == 0
    assert report["operational_effectiveness"] == "not_yet_demonstrated"


def test_observed_bypass_increments_correctly(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [
            {"event_id": "BE-TEST-001", "evidence_basis": "observed"},
            {"event_id": "BE-TEST-002", "evidence_basis": "observed"},
            {"event_id": "BE-TEST-003", "evidence_basis": "retroactive_analysis"},
        ],
    )
    report = build_report(tmp_path)
    assert report["observed_bypass_count"] == 2
    assert report["bypass_total"] == 3


def test_basis_distribution_reflects_interception_ledger_only(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/intercepted-events.ndjson",
        [
            {"event_id": "IE-T-001", "evidence_basis": "retroactive_analysis"},
            {"event_id": "IE-T-002", "evidence_basis": "retroactive_analysis"},
            {"event_id": "IE-T-003", "evidence_basis": "test_derived"},
        ],
    )
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [
            {"event_id": "BE-T-001", "evidence_basis": "observed"},
        ],
    )
    report = build_report(tmp_path)
    dist = report["interception_basis_distribution"]
    assert dist.get("retroactive_analysis") == 2
    assert dist.get("test_derived") == 1
    assert "observed" not in dist  # bypass ledger must not bleed in


def test_high_materiality_only_counts_observed_evidence(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/intercepted-events.ndjson",
        [
            {"event_id": "IE-T-001", "evidence_basis": "observed", "materiality": "high"},
            {"event_id": "IE-T-002", "evidence_basis": "test_derived", "materiality": "high"},
            {"event_id": "IE-T-003", "evidence_basis": "retroactive_analysis", "materiality": "high"},
        ],
    )
    report = build_report(tmp_path)
    assert report["high_materiality_observed_count"] == 1
    assert report["operational_effectiveness"] == "partially_demonstrated"


# ── format_human output tests ─────────────────────────────────────────────────

def test_format_human_contains_forbidden_conclusion(tmp_path):
    report = build_report(tmp_path)
    output = format_human(report)
    assert "Forbidden:" in output
    assert "demonstrated operational leverage" in output


def test_format_human_contains_operational_effectiveness_line(tmp_path):
    report = build_report(tmp_path)
    output = format_human(report)
    assert "OPERATIONAL EFFECTIVENESS:" in output
    assert "not_yet_demonstrated" in output


def test_format_human_shows_cold_output_for_seed_data(tmp_path):
    """Confirm the expected 'cold' output given the current seed data structure."""
    # seed: 0 observed interceptions, 2 observed bypasses
    _write_ndjson(
        tmp_path / "artifacts/governance/intercepted-events.ndjson",
        [
            {"event_id": "IE-S-001", "evidence_basis": "retroactive_analysis", "materiality": "medium"},
            {"event_id": "IE-S-002", "evidence_basis": "test_derived", "materiality": "high"},
            {"event_id": "IE-S-003", "evidence_basis": "retroactive_analysis", "materiality": "high"},
        ],
    )
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [
            {"event_id": "BE-S-001", "evidence_basis": "observed"},
            {"event_id": "BE-S-002", "evidence_basis": "observed"},
        ],
    )
    report = build_report(tmp_path)
    assert report["observed_interception_count"] == 0
    assert report["observed_bypass_count"] == 2
    assert report["high_materiality_observed_count"] == 0
    assert report["operational_effectiveness"] == "not_yet_demonstrated"
    output = format_human(report)
    assert "OBSERVED INTERCEPTIONS:        0" in output
    assert "OBSERVED BYPASSES:             2" in output
    assert "not_yet_demonstrated" in output
