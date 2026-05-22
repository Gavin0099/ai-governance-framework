"""Tests for governance_tools/ci_governance_check.py"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.ci_governance_check import check, format_human, _is_mitigated


# ── _is_mitigated unit tests ─────────────────────────────────────────────────

def test_accepted_risk_true_is_mitigated():
    assert _is_mitigated({"accepted_risk": True}) is True


def test_non_empty_resolution_is_mitigated():
    assert _is_mitigated({"resolution": "commit abc123"}) is True


def test_empty_resolution_is_not_mitigated():
    assert _is_mitigated({"resolution": ""}) is False
    assert _is_mitigated({"resolution": "   "}) is False


def test_no_mitigation_fields_is_not_mitigated():
    assert _is_mitigated({"event_id": "BE-001"}) is False


def test_accepted_risk_false_is_not_mitigated():
    assert _is_mitigated({"accepted_risk": False}) is False


# ── check() integration tests ────────────────────────────────────────────────

def _write_ndjson(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )


def test_empty_ledgers_are_clean(tmp_path):
    result = check(tmp_path)
    assert result["governance_present"] is True
    assert result["clean"] is True
    assert result["unmitigated_bypass_count"] == 0


def test_observed_bypass_with_resolution_is_clean(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [{"event_id": "BE-001", "evidence_basis": "observed", "resolution": "commit abc"}],
    )
    result = check(tmp_path)
    assert result["clean"] is True
    assert result["unmitigated_bypass_count"] == 0


def test_observed_bypass_with_accepted_risk_is_clean(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [{"event_id": "BE-001", "evidence_basis": "observed", "accepted_risk": True}],
    )
    result = check(tmp_path)
    assert result["clean"] is True


def test_unmitigated_observed_bypass_fails(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [{"event_id": "BE-999", "evidence_basis": "observed"}],
    )
    result = check(tmp_path)
    assert result["clean"] is False
    assert result["unmitigated_bypass_count"] == 1
    assert "BE-999" in result["unmitigated_bypass_ids"]


def test_retroactive_bypass_does_not_fail(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [{"event_id": "BE-001", "evidence_basis": "retroactive_analysis"}],
    )
    result = check(tmp_path)
    assert result["clean"] is True
    assert result["observed_bypass_count"] == 0


def test_mixed_bypasses_only_unmitigated_observed_fails(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [
            {"event_id": "BE-001", "evidence_basis": "observed", "resolution": "commit x"},
            {"event_id": "BE-002", "evidence_basis": "observed"},  # unmitigated
            {"event_id": "BE-003", "evidence_basis": "retroactive_analysis"},
        ],
    )
    result = check(tmp_path)
    assert result["clean"] is False
    assert result["unmitigated_bypass_count"] == 1
    assert result["observed_bypass_count"] == 2
    assert result["unmitigated_bypass_ids"] == ["BE-002"]


def test_governance_present_always_true(tmp_path):
    result = check(tmp_path)
    assert result["governance_present"] is True


def test_ledger_file_presence_reported(tmp_path):
    result = check(tmp_path)
    assert result["ledger_files"]["intercepted"] is False
    assert result["ledger_files"]["bypass"] is False

    _write_ndjson(tmp_path / "artifacts/governance/bypass-events.ndjson", [])
    result2 = check(tmp_path)
    assert result2["ledger_files"]["bypass"] is True


# ── format_human output tests ─────────────────────────────────────────────────

def test_format_human_contains_governance_present(tmp_path):
    result = check(tmp_path)
    output = format_human(result)
    assert "governance_present:      True" in output


def test_format_human_shows_pass_for_clean(tmp_path):
    result = check(tmp_path)
    output = format_human(result)
    assert "check: PASS" in output


def test_format_human_shows_fail_with_unmitigated(tmp_path):
    _write_ndjson(
        tmp_path / "artifacts/governance/bypass-events.ndjson",
        [{"event_id": "BE-FAIL", "evidence_basis": "observed"}],
    )
    result = check(tmp_path)
    output = format_human(result)
    assert "FAIL" in output
    assert "BE-FAIL" in output


# ── current seed data regression test ────────────────────────────────────────

def test_current_seed_data_is_clean():
    """BE-001 and BE-002 both have resolution fields — seed state must be clean."""
    project_root = Path(__file__).parent.parent
    bypass_path = project_root / "artifacts/governance/bypass-events.ndjson"
    if not bypass_path.exists():
        pytest.skip("seed bypass ledger not present")
    result = check(project_root)
    assert result["clean"] is True, (
        f"Seed bypass ledger has unmitigated entries: {result['unmitigated_bypass_ids']}"
    )
