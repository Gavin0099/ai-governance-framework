from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.enumd_observe_only_probe import probe_report, run_probe


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "enumd"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    (
        "fixture_name",
        "expected_reevaluation_required",
        "expected_semantic_shift_candidate",
        "expected_candidate_reasons",
        "expected_advisory_signal_present",
        "expected_minor_changed",
        "expected_major_changed",
        "expected_sample_conclusion",
    ),
    [
        (
            "authority_upgrade_unconsumed_no_change_case",
            False,
            False,
            [],
            False,
            False,
            False,
            "safe_for_observe_only",
        ),
        (
            "authority_upgrade_consumed_no_change_case",
            True,
            False,
            [],
            True,
            False,
            False,
            "observe_only_with_inducement_risk",
        ),
        (
            "authority_upgrade_unconsumed_minor_version_case",
            False,
            False,
            [],
            True,
            True,
            False,
            "safe_for_observe_only",
        ),
        (
            "authority_upgrade_consumed_minor_version_case",
            True,
            False,
            [],
            True,
            True,
            False,
            "observe_only_with_inducement_risk",
        ),
        (
            "authority_upgrade_unconsumed_major_version_case",
            True,
            True,
            ["instrumentation_major_change"],
            True,
            True,
            True,
            "observe_only_with_inducement_risk",
        ),
        (
            "authority_upgrade_consumed_major_version_case",
            True,
            True,
            ["instrumentation_major_change"],
            True,
            True,
            True,
            "observe_only_with_inducement_risk",
        ),
    ],
)
def test_authority_upgrade_matrix(
    fixture_name: str,
    expected_reevaluation_required: bool,
    expected_semantic_shift_candidate: bool,
    expected_candidate_reasons: list[str],
    expected_advisory_signal_present: bool,
    expected_minor_changed: bool,
    expected_major_changed: bool,
    expected_sample_conclusion: str,
) -> None:
    sample = _load_fixture(fixture_name)

    result = probe_report(sample, sample_id=fixture_name)

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is expected_reevaluation_required
    assert result["semantic_shift_candidate"] is expected_semantic_shift_candidate
    assert result["semantic_shift_candidate_reasons"] == expected_candidate_reasons
    assert result["advisory_signal_present"] is expected_advisory_signal_present
    assert result["instrumentation_version_change"]["minor_changed"] is expected_minor_changed
    assert result["instrumentation_version_change"]["major_changed"] is expected_major_changed
    assert result["sample_conclusion"] == expected_sample_conclusion


def test_authority_upgrade_minor_change_stays_advisory_only_without_semantic_candidate() -> None:
    sample = _load_fixture("authority_upgrade_unconsumed_minor_version_case")

    result = probe_report(sample, sample_id="authority_upgrade_unconsumed_minor_version_case")

    assert result["advisory_signal_present"] is True
    assert result["semantic_shift_candidate"] is False
    assert result["reevaluation_required"] is False
    assert "instrumentation_minor_change_no_gate_escalation" in result["notes"]


def test_authority_upgrade_consumed_path_requires_review_but_not_boundary_fail() -> None:
    sample = _load_fixture("authority_upgrade_consumed_no_change_case")

    result = probe_report(sample, sample_id="authority_upgrade_consumed_no_change_case")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is True
    assert result["semantic_shift_candidate"] is False
    assert result["sample_conclusion"] == "observe_only_with_inducement_risk"


def test_authority_upgrade_batch_summary_counts_review_required_only_for_candidate_cases() -> None:
    result = run_probe(
        [
            FIXTURES_DIR / "authority_upgrade_unconsumed_no_change_case.json",
            FIXTURES_DIR / "authority_upgrade_unconsumed_minor_version_case.json",
            FIXTURES_DIR / "authority_upgrade_consumed_no_change_case.json",
            FIXTURES_DIR / "authority_upgrade_unconsumed_major_version_case.json",
        ]
    )

    assert result["review_required_advisory_only"] is True
    assert result["review_required_sample_count"] == 2
    assert set(result["review_required_sample_ids"]) == {
        "authority_upgrade_consumed_no_change_case",
        "authority_upgrade_unconsumed_major_version_case",
    }
