"""
tests/test_enumd_ingestor.py

Smoke tests for the Enumd integration seam (integrations/enumd/ingestor.py).

These tests lock in the semantic-boundary routing directive and provenance
validation so that any drift in the ingestor is caught immediately.

Coverage matrix
---------------
T1  valid_sample_pass          — schema.sample.json → ok, output written
T2  missing_semantic_boundary  — absent field → error, not ok
T3  represents_agent_behavior_true — routing directive violated → error, not ok
T4  missing_provenance_field   — absent top-level required field → error, not ok
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.enumd.ingestor import ingest, validate_report

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent
    / "integrations" / "enumd" / "schema.sample.json"
)


def _load_sample() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def _write_report(tmp_path: Path, report: dict) -> Path:
    p = tmp_path / "governance_report.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# T1 — valid sample passes and produces canonical observation
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_sample_pass(tmp_path: Path) -> None:
    """
    A well-formed governance_report.json (matching schema.sample.json) must:
    - be accepted without errors
    - produce a file under artifacts/external-observations/
    - preserve semantic_boundary.represents_agent_behavior == False at envelope level
    - preserve calibration_profile.name in envelope
    - embed the Enumd payload without alteration of policy_applied fields
    """
    report = _load_sample()
    report_path = _write_report(tmp_path, report)

    result = ingest(report_path, repo_root=tmp_path)

    assert result["ok"] is True, f"Expected ok=True; errors={result['errors']}"
    assert result["errors"] == []

    out_path = Path(result["output_path"])
    assert out_path.exists(), f"Output file not created: {out_path}"

    obs = json.loads(out_path.read_text(encoding="utf-8"))

    # Envelope-level routing directive preserved
    assert obs["observation_class"] == "external_analysis_artifact"
    assert obs["semantic_boundary"]["represents_agent_behavior"] is False

    # Calibration metadata at envelope level
    assert obs["calibration_profile"]["name"] == "production_v1"

    # run_id promoted to envelope
    assert obs["run_id"] == report["run_id"]

    # policy_applied preserved verbatim inside payload
    payload_policy = obs["payload"]["policy_applied"]
    assert payload_policy["policy_id"] == "tiered-enforcement-policy-v1"
    assert payload_policy["calibration_profile"] == "production_v1"
    assert payload_policy["outcomes"]["suppressed"] == 3

    # Output path matches expected pattern
    assert "enumd-wave-5" in str(out_path)


# ─────────────────────────────────────────────────────────────────────────────
# T2 — missing semantic_boundary field → rejected
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_semantic_boundary_fail(tmp_path: Path) -> None:
    """
    A report without semantic_boundary must be rejected.

    semantic_boundary is the routing directive that prevents this observation
    from being counted in lifecycle_class / E1b / session_count statistics.
    Accepting a report without it would silently break the Mode A boundary.
    """
    report = _load_sample()
    del report["semantic_boundary"]
    report_path = _write_report(tmp_path, report)

    result = ingest(report_path, repo_root=tmp_path)

    assert result["ok"] is False
    assert any("semantic_boundary" in e for e in result["errors"]), (
        f"Expected error mentioning 'semantic_boundary'; got: {result['errors']}"
    )
    # No output file should be created
    assert result["output_path"] is None or not Path(result["output_path"]).exists()


# ─────────────────────────────────────────────────────────────────────────────
# T3 — represents_agent_behavior=True → routing directive violated → rejected
# ─────────────────────────────────────────────────────────────────────────────

def test_represents_agent_behavior_true_fail(tmp_path: Path) -> None:
    """
    A report with semantic_boundary.represents_agent_behavior=True must be rejected.

    This is the critical routing guard: if represents_agent_behavior=True were
    accepted for an Enumd report, the observation would be treated as a runtime
    session and would inflate lifecycle_class, E1b, and session_count statistics.

    The error message must clearly identify the violated constraint so it is
    auditable.
    """
    report = _load_sample()
    report["semantic_boundary"]["represents_agent_behavior"] = True
    report_path = _write_report(tmp_path, report)

    result = ingest(report_path, repo_root=tmp_path)

    assert result["ok"] is False
    # Error must reference represents_agent_behavior
    assert any("represents_agent_behavior" in e for e in result["errors"]), (
        f"Expected error mentioning 'represents_agent_behavior'; got: {result['errors']}"
    )
    assert result["output_path"] is None or not Path(result["output_path"]).exists()


# ─────────────────────────────────────────────────────────────────────────────
# T4 — missing provenance field (calibration_profile) → rejected
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_provenance_field_fail(tmp_path: Path) -> None:
    """
    A report missing calibration_profile must be rejected.

    calibration_profile is the provenance root of the Mode A seam:
    - it identifies the exact threshold set applied (prevents silent drift)
    - it enables trend analysis to distinguish behavioral change from
      calibration change

    Without it, downstream analysis cannot distinguish "suppression increased
    because behavior degraded" from "suppression increased because thresholds
    were tightened".  Accepting such a report would corrupt trend analysis.
    """
    report = _load_sample()
    del report["calibration_profile"]
    report_path = _write_report(tmp_path, report)

    result = ingest(report_path, repo_root=tmp_path)

    assert result["ok"] is False
    assert any("calibration_profile" in e for e in result["errors"]), (
        f"Expected error mentioning 'calibration_profile'; got: {result['errors']}"
    )
    assert result["output_path"] is None or not Path(result["output_path"]).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Bonus — validate_report directly (unit coverage, not just integration)
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_report_clean_sample() -> None:
    """validate_report must return an empty list for the canonical sample."""
    report = _load_sample()
    errors = validate_report(report)
    assert errors == [], f"Unexpected validation errors on sample: {errors}"


def test_validate_report_wrong_producer() -> None:
    """validate_report must flag a non-enumd producer."""
    report = _load_sample()
    report["producer"] = "not-enumd"
    errors = validate_report(report)
    assert any("producer" in e for e in errors), (
        f"Expected producer error; got: {errors}"
    )
