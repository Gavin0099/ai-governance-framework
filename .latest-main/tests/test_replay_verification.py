"""
tests/test_replay_verification.py — E6 replay verification tests.

Five focused tests covering:
  1. All seed corpus cases pass (both layers)
  2. Classification mismatch is detected
  3. Gate-effect mismatch is detected (kind matches but gate consequence differs)
  4. JSON format output is serialisable machine-readable evidence
  5. Evidence scope statement is present and precise (does not overclaim)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from governance_tools.replay_verification import (
    CaseResult,
    ReplayEvidence,
    _evaluate_case,
    _format_human,
    run_replay,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_BLOCKING_ACTIONS = ["production_fix_required"]

# A minimal valid corpus case (stale_assertion / test_fix_only / non-blocking).
_GOOD_CASE = {
    "case_id": "TEST-001",
    "test_id": "tests/test_tool_adapter.py::TestRunUpdateWindowsCommand::test_folder_flag_always_present",
    "extra_signals": ["'-folder' not in cmd", "assert '-folder' in"],
    "expected_kind": "stale_assertion",
    "expected_action": "test_fix_only",
    "expected_confidence": "high",
    "expected_gate_blocking": False,
    "expected_reviewer_note_contains": "assertion reflects removed",
    "source": "test",
    "added_by": "test",
    "added_at": "2026-04-13",
}

# An integration_drift case that should be gate-blocking.
_BLOCKING_CASE = {
    "case_id": "TEST-002",
    "test_id": "tests/test_runner_integration.py::TestDfuModeSequence::test_run_dfu_check_called_once",
    "extra_signals": ["run_dfu_check", "called 0 times", "expected 1"],
    "expected_kind": "integration_drift",
    "expected_action": "production_fix_required",
    "expected_confidence": "high",
    "expected_gate_blocking": True,
    "expected_reviewer_note_contains": "decoupled from current production call path",
    "source": "test",
    "added_by": "test",
    "added_at": "2026-04-13",
}


def _write_temp_corpus(cases: list[dict], *, with_header: bool = True) -> Path:
    """Write a minimal corpus JSON to a temp file and return its path."""
    payload: list[dict] = []
    if with_header:
        payload.append({
            "_schema": "failure_disposition_corpus_v1",
            "_corpus_version": "test",
            "_ground_truth_provenance": {
                "labelled_by": "test",
                "labelled_at": "test",
            },
        })
    payload.extend(cases)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", mode="w", delete=False, encoding="utf-8"
    )
    json.dump(payload, tmp)
    tmp.close()
    return Path(tmp.name)


# ── Test 1: All seed corpus cases pass ────────────────────────────────────────


def test_replay_all_seed_corpus_cases_pass():
    """All 10 seed cases must pass both classification and gate-effect layers."""
    ev = run_replay()

    assert ev.corpus_case_count == 10, f"Expected 10 corpus cases, got {ev.corpus_case_count}"
    assert ev.classification_match_rate == "10/10", (
        f"Classification match rate: {ev.classification_match_rate}"
    )
    assert ev.gate_effect_match_rate == "10/10", (
        f"Gate-effect match rate: {ev.gate_effect_match_rate}"
    )
    assert ev.all_match is True, f"Expected all_match=True, mismatch_cases={ev.mismatch_cases}"
    assert ev.mismatch_cases == [], f"Unexpected mismatches: {ev.mismatch_cases}"


# ── Test 2: Classification mismatch detection ─────────────────────────────────


def test_replay_detects_classification_mismatch():
    """When expected_kind is wrong, classification_match must be False."""
    bad_case = dict(_GOOD_CASE)
    bad_case["expected_kind"] = "integration_drift"  # real kind is stale_assertion

    corp = _write_temp_corpus([bad_case])
    try:
        ev = run_replay(corpus_path=corp)
        assert ev.all_match is False
        assert ev.classification_match_rate == "0/1"
        assert any(
            m["layer"] == "classification" and m["case_id"] == "TEST-001"
            for m in ev.mismatch_cases
        ), f"Expected classification mismatch in mismatch_cases: {ev.mismatch_cases}"
    finally:
        corp.unlink(missing_ok=True)


# ── Test 3: Gate-effect mismatch detection ────────────────────────────────────


def test_replay_detects_gate_effect_mismatch():
    """When expected_gate_blocking is wrong, gate_effect_match must be False."""
    # _GOOD_CASE produces action=test_fix_only (non-blocking), but we claim it's True.
    bad_case = dict(_GOOD_CASE)
    bad_case["expected_gate_blocking"] = True   # wrong — should be False

    corp = _write_temp_corpus([bad_case])
    try:
        ev = run_replay(corpus_path=corp)
        assert ev.all_match is False
        assert ev.gate_effect_match_rate == "0/1"
        assert any(
            m["layer"] == "gate_effect" and m["case_id"] == "TEST-001"
            for m in ev.mismatch_cases
        ), f"Expected gate_effect mismatch in mismatch_cases: {ev.mismatch_cases}"
    finally:
        corp.unlink(missing_ok=True)


# ── Test 4: JSON output is machine-readable ───────────────────────────────────


def test_replay_output_is_machine_readable():
    """Evidence artifact must be serialisable and contain required top-level keys."""
    ev = run_replay()
    d = ev.to_dict()

    # Must be round-trip serialisable.
    raw = json.dumps(d, default=str)
    parsed = json.loads(raw)

    required_keys = {
        "corpus_schema_version",
        "corpus_version",
        "corpus_case_count",
        "corpus_provenance",
        "policy_source",
        "blocking_actions",
        "classification_match_rate",
        "gate_effect_match_rate",
        "mismatch_cases",
        "evidence_scope",
        "generated_at",
        "all_match",
        "cases",
    }
    missing = required_keys - set(parsed.keys())
    assert not missing, f"Missing keys in evidence artifact: {missing}"

    # cases array must have the right length and per-case keys
    assert len(parsed["cases"]) == 10
    case_keys = {
        "case_id", "classification_match", "gate_effect_match",
        "expected_kind", "actual_kind", "expected_gate_blocking", "actual_gate_blocking",
    }
    for c in parsed["cases"]:
        missing_case_keys = case_keys - set(c.keys())
        assert not missing_case_keys, f"Missing case keys in {c.get('case_id')}: {missing_case_keys}"


# ── Test 5: Evidence scope statement is present and non-overclaiming ──────────


def test_replay_evidence_scope_statement_present_and_precise():
    """evidence_scope must be present, non-empty, and contain key precision phrases."""
    ev = run_replay()

    assert ev.evidence_scope, "evidence_scope must not be empty"

    # Must name the corpus case count explicitly.
    assert "10 cases" in ev.evidence_scope, (
        f"evidence_scope must mention case count: {ev.evidence_scope!r}"
    )

    # Must explicitly limit the claim to seed corpus — must not say "verified" broadly.
    assert "seed corpus only" in ev.evidence_scope or "Scope is limited" in ev.evidence_scope, (
        f"evidence_scope must state scope limitation: {ev.evidence_scope!r}"
    )

    # Must mention both match layers.
    assert "classification" in ev.evidence_scope, (
        f"evidence_scope must mention classification layer"
    )
    assert "gate-effect" in ev.evidence_scope, (
        f"evidence_scope must mention gate-effect layer"
    )
