"""
Tests for governance_tools/failure_disposition.py — E1 decision boundary layer.

Coverage strategy
-----------------
- All four FailureKinds with high confidence (seed corpus cases)
- Unknown fallback → action must be escalate, never ignore_for_verdict
- Unknown count >= threshold → taxonomy_expansion_signal
- Confidence levels: high, tentative, unknown
- extra_signals augment classification
- Batch result: verdict_blocked when production_fix_required or escalate present
- Seed corpus calibration: every entry in failure_disposition_corpus.json
  must classify to expected_kind and expected_action
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.failure_disposition import (
    FAILURE_KINDS,
    ACTION_POLICIES,
    CONFIDENCE_LEVELS,
    UNKNOWN_ESCALATION_THRESHOLD,
    classify_failure,
    classify_batch,
    DispositionResult,
)

CORPUS_PATH = Path(__file__).parent / "fixtures" / "failure_disposition_corpus.json"


# ── Enum / constant integrity ─────────────────────────────────────────────────

def test_failure_kinds_are_defined():
    assert "stale_assertion" in FAILURE_KINDS
    assert "platform_mock" in FAILURE_KINDS
    assert "integration_drift" in FAILURE_KINDS
    assert "external_exclusion" in FAILURE_KINDS
    assert "unknown" in FAILURE_KINDS


def test_action_policies_are_defined():
    assert "ignore_for_verdict" in ACTION_POLICIES
    assert "test_fix_only" in ACTION_POLICIES
    assert "production_fix_required" in ACTION_POLICIES
    assert "escalate" in ACTION_POLICIES
    assert "quarantine" in ACTION_POLICIES


def test_confidence_levels_are_defined():
    assert "high" in CONFIDENCE_LEVELS
    assert "tentative" in CONFIDENCE_LEVELS
    assert "unknown" in CONFIDENCE_LEVELS


# ── Unknown is always conservative ───────────────────────────────────────────

def test_unknown_failure_action_is_escalate():
    result = classify_failure("some_completely_unrecognised_test_xyz_abc")
    assert result.kind == "unknown"
    assert result.action == "escalate", (
        "Unknown failures MUST escalate — never ignore_for_verdict"
    )


def test_unknown_failure_confidence_is_unknown():
    result = classify_failure("xyzzy_no_pattern_matches")
    assert result.confidence == "unknown"


def test_unknown_failure_has_reviewer_note():
    result = classify_failure("unclassifiable_test_abc")
    assert result.reviewer_note
    assert "reviewer" in result.reviewer_note.lower()


def test_unknown_action_is_never_ignore_for_verdict():
    # Exhaustive: run 10 synthetic unknown IDs
    for i in range(10):
        r = classify_failure(f"unrecognised_synthetic_{i}")
        if r.kind == "unknown":
            assert r.action != "ignore_for_verdict", (
                f"Unknown kind must never produce ignore_for_verdict (got for {r.test_id})"
            )


# ── taxonomy_expansion_signal ─────────────────────────────────────────────────

def test_taxonomy_expansion_signal_fires_at_threshold():
    ids = [f"unknown_test_{i}" for i in range(UNKNOWN_ESCALATION_THRESHOLD)]
    result = classify_batch(ids)
    assert result.taxonomy_expansion_signal is True


def test_taxonomy_expansion_signal_not_fired_below_threshold():
    ids = [f"unknown_test_{i}" for i in range(UNKNOWN_ESCALATION_THRESHOLD - 1)]
    result = classify_batch(ids)
    assert result.taxonomy_expansion_signal is False


# ── stale_assertion ───────────────────────────────────────────────────────────

def test_folder_flag_classifies_as_stale_assertion():
    r = classify_failure(
        "tests/test_tool_adapter.py::TestRunUpdateWindowsCommand::test_folder_flag_always_present"
    )
    assert r.kind == "stale_assertion"
    assert r.action == "test_fix_only"
    assert r.confidence == "high"


def test_stale_assertion_reviewer_note_present():
    r = classify_failure("test_folder_flag_always_present")
    assert r.reviewer_note
    assert "assertion" in r.reviewer_note.lower()


# ── platform_mock ─────────────────────────────────────────────────────────────

def test_posix_path_classifies_as_platform_mock():
    r = classify_failure(
        "tests/test_tool_adapter.py::TestRunUpdateMacOSExeDetection::test_folder_a_uses_its_own_bundle_binary",
        extra_signals=["UnsupportedOperation: cannot instantiate PosixPath"],
    )
    assert r.kind == "platform_mock"
    assert r.action == "test_fix_only"
    assert r.confidence == "high"


def test_platform_mock_without_extra_signals_still_classifiable():
    r = classify_failure(
        "tests/test_tool_adapter.py::TestRunUpdateMacOSExeDetection::test_falls_back_to_plain_binary_when_no_bundle_binary"
    )
    assert r.kind == "platform_mock"


# ── integration_drift ────────────────────────────────────────────────────────

def test_dfu_sequence_classifies_as_integration_drift():
    r = classify_failure(
        "tests/test_runner_integration.py::TestDfuModeSequence::test_run_dfu_check_called_once",
        extra_signals=["run_dfu_check", "called 0 times, expected 1"],
    )
    assert r.kind == "integration_drift"
    assert r.action == "production_fix_required"
    assert r.confidence == "high"


def test_integration_drift_blocks_verdict():
    result = classify_batch([
        "tests/test_runner_integration.py::TestDfuModeSequence::test_run_dfu_check_called_once"
    ])
    assert result.verdict_blocked is True


# ── external_exclusion ────────────────────────────────────────────────────────

def test_trust_signal_classifies_as_external_exclusion():
    r = classify_failure("tests/test_trust_signal_overview.py::test_trust_signal_overview_runs")
    assert r.kind == "external_exclusion"
    assert r.action == "quarantine"


def test_reviewer_handoff_classifies_as_external_exclusion():
    r = classify_failure("tests/test_reviewer_handoff_summary.py::test_reviewer_handoff")
    assert r.kind == "external_exclusion"


def test_publication_reader_classifies_as_external_exclusion():
    r = classify_failure("tests/test_release_package_publication_reader.py::test_reader")
    assert r.kind == "external_exclusion"


# ── Batch result integrity ────────────────────────────────────────────────────

def test_batch_verdict_not_blocked_when_only_test_fix():
    ids = [
        "test_folder_flag_always_present",
        "test_includes_log_flag",
    ]
    result = classify_batch(ids)
    assert result.verdict_blocked is False


def test_batch_verdict_blocked_when_production_fix_required():
    ids = [
        "test_folder_flag_always_present",  # test_fix_only
        "tests/test_runner_integration.py::TestDfuModeSequence::test_run_dfu_check_called_once",  # production_fix_required
    ]
    result = classify_batch(ids)
    assert result.verdict_blocked is True


def test_batch_result_totals_match():
    ids = ["test_folder_flag_always_present", "test_trust_signal_overview"]
    result = classify_batch(ids)
    assert result.total == 2
    assert sum(result.by_kind.values()) == 2


def test_batch_result_serialisable():
    ids = ["test_folder_flag_always_present"]
    result = classify_batch(ids)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "results" in d
    import json
    _ = json.dumps(d)  # must not raise


# ── F3: unknown_threshold artifact context ────────────────────────────────────

def test_batch_result_carries_unknown_threshold():
    """BatchDispositionResult.to_dict() must expose unknown_threshold so reviewers
    can verify the taxonomy_expansion_signal basis without reading source code."""
    from governance_tools.failure_disposition import UNKNOWN_ESCALATION_THRESHOLD
    ids = ["test_folder_flag_always_present"]
    result = classify_batch(ids)
    d = result.to_dict()
    assert "unknown_threshold" in d, "artifact must carry unknown_threshold"
    assert d["unknown_threshold"] == UNKNOWN_ESCALATION_THRESHOLD
    assert isinstance(d["unknown_threshold"], int)


def test_taxonomy_signal_threshold_matches_at_boundary():
    """Signal fires at exactly UNKNOWN_ESCALATION_THRESHOLD unknowns and not below."""
    from governance_tools.failure_disposition import UNKNOWN_ESCALATION_THRESHOLD
    threshold = UNKNOWN_ESCALATION_THRESHOLD
    # Build threshold-many unrecognised test ids (guaranteed unknown)
    below = [f"test_zzz_unrecognised_xyzzy_{i}" for i in range(threshold - 1)]
    at = [f"test_zzz_unrecognised_xyzzy_{i}" for i in range(threshold)]
    result_below = classify_batch(below)
    result_at = classify_batch(at)
    assert result_below.taxonomy_expansion_signal is False, "below threshold must not fire"
    assert result_at.taxonomy_expansion_signal is True, "at threshold must fire"
    assert result_at.unknown_threshold == threshold


# ── Seed corpus calibration ───────────────────────────────────────────────────

def _load_corpus():
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    # corpus is a flat list; filter out the comment object (has _comment key)
    return [item for item in raw if "case_id" in item]


@pytest.mark.parametrize("entry", _load_corpus(), ids=[e["case_id"] for e in _load_corpus()])
def test_corpus_case_classifies_correctly(entry):
    """Each ground-truth corpus entry must match expected kind and action."""
    extra = entry.get("extra_signals") or []
    result = classify_failure(entry["test_id"], extra_signals=extra)
    assert result.kind == entry["expected_kind"], (
        f"[{entry['case_id']}] kind mismatch: got {result.kind!r}, "
        f"expected {entry['expected_kind']!r}"
    )
    assert result.action == entry["expected_action"], (
        f"[{entry['case_id']}] action mismatch: got {result.action!r}, "
        f"expected {entry['expected_action']!r}"
    )
    note_expected = entry.get("expected_reviewer_note_contains", "")
    if note_expected:
        assert note_expected.lower() in (result.reviewer_note or "").lower(), (
            f"[{entry['case_id']}] reviewer_note missing expected substring: "
            f"{note_expected!r}"
        )
