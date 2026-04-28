"""
tests/test_enumd_integration_state.py

pytest wrapper for scripts/check_enumd_integration_state.run_checks().

Purpose
-------
These tests make the Enumd integration seam a formal regression surface:
every pytest run verifies that the seam has not silently drifted from its
declared state in PLAN.md.

They are complementary to tests/test_enumd_ingestor.py:
  - test_enumd_ingestor.py   checks behaviour contracts (inputs → outputs)
  - this file                checks structure contracts (does the seam exist
                             in the expected shape?)

If any check here fails, the most likely cause is that a file was moved,
renamed, or had its critical content removed without updating the seam.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_enumd_integration_state import run_checks


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate check (fast path: one call, fail with full context)
# ─────────────────────────────────────────────────────────────────────────────

def test_enumd_integration_state_all_pass() -> None:
    """
    All 12 seam-state checks must pass.

    This is the canonical guard: if any single check fails, the error message
    names the specific check that drifted, making triage immediate.
    """
    results = run_checks()
    failed = [r for r in results if not r["ok"]]
    assert not failed, (
        f"Enumd integration seam has drifted ({len(failed)} check(s) failed):\n"
        + "\n".join(f"  ✗ [{r['id']}] {r['message']}" for r in failed)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual checks (granular: pinpoint which layer broke on failure)
# ─────────────────────────────────────────────────────────────────────────────

def _get_check(check_id: str) -> dict:
    results = run_checks()
    for r in results:
        if r["id"] == check_id:
            return r
    pytest.fail(f"check_id {check_id!r} not found in run_checks() output")


@pytest.mark.parametrize("check_id", [
    "seam_ingestor_exists",
    "seam_schema_sample_exists",
    "seam_mapping_doc_exists",
    "seam_usage_doc_exists",
])
def test_seam_files_exist(check_id: str) -> None:
    """integrations/enumd/ must contain all four seam artifacts."""
    r = _get_check(check_id)
    assert r["ok"], f"[{check_id}] {r['message']}"


def test_p1_test_file_exists() -> None:
    """tests/test_enumd_ingestor.py must exist (P1 guard)."""
    r = _get_check("p1_test_file_exists")
    assert r["ok"], r["message"]


def test_ingestor_routing_directive_present() -> None:
    """
    ingestor.py must contain represents_agent_behavior assertion.

    This is the critical routing directive guard: removing or commenting it
    out would allow an Enumd observation to be routed into lifecycle statistics.
    """
    r = _get_check("ingestor_routing_directive_present")
    assert r["ok"], r["message"]


def test_ingestor_provenance_root_present() -> None:
    """
    ingestor.py must validate calibration_profile (provenance root).

    Without this, trend analysis cannot distinguish behavioral degradation
    from threshold changes across Enumd waves.
    """
    r = _get_check("ingestor_provenance_root_present")
    assert r["ok"], r["message"]


def test_p2_analysis_boundary_present() -> None:
    """
    analyze_e1b_distribution.py must contain is_runtime_eligible().

    This is the P2 analysis boundary: without it, Enumd external observations
    could silently enter lifecycle / E1b / Phase 2 gate computations.
    """
    r = _get_check("p2_analysis_boundary_present")
    assert r["ok"], r["message"]


@pytest.mark.parametrize("check_id,label", [
    ("p1_guard_test_valid_sample_pass",                  "T1 valid sample pass"),
    ("p1_guard_test_missing_semantic_boundary_fail",      "T2 missing semantic_boundary"),
    ("p1_guard_test_represents_agent_behavior_true_fail", "T3 routing directive violation"),
    ("p1_guard_test_missing_provenance_field_fail",       "T4 missing provenance field"),
])
def test_p1_semantic_guards_present(check_id: str, label: str) -> None:
    """Each of the four semantic guard tests must exist in the test file."""
    r = _get_check(check_id)
    assert r["ok"], f"Semantic guard missing — {label}: {r['message']}"
