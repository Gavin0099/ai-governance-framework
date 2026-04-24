from __future__ import annotations

import json
import pytest
from pathlib import Path

from governance_tools.agents_rule_candidates_inspector import (
    inspect_artifact,
    format_summary,
)
from governance_tools.agents_rule_aggregation_artifact import make_aggregation_artifact
from governance_tools.agents_rule_evidence_aggregation import aggregate_candidate_evidence
from governance_tools.agents_rule_promotion_schema import make_candidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate():
    return make_candidate(
        candidate_type="must_test_path",
        human_candidate="runtime_hooks/core/pre_task_check.py",
        evidence_count=1,
        evidence_window_days=14,
        observed_from=["post_task_check"],
        repo_specificity="high",
        repo_specificity_basis=["real_path"],
        first_seen_at="2026-04-24T10:00:00Z",
        last_seen_at="2026-04-24T12:00:00Z",
        evidence_refs=["session:end:2026-04-24:abc123"],
    )


def _aggregation_result(candidate):
    return aggregate_candidate_evidence(candidate, events=[])


def _write_artifact(tmp_path: Path, **overrides) -> Path:
    candidate = _candidate()
    result = _aggregation_result(candidate)
    artifact = make_aggregation_artifact(
        generated_at="2026-04-24T00:00:00Z",
        candidates=[result],
    )
    data = {**artifact.to_dict(), **overrides}
    path = tmp_path / "agents_rule_candidates.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Missing artifact
# ---------------------------------------------------------------------------

def test_missing_artifact_returns_not_ok(tmp_path: Path) -> None:
    result = inspect_artifact(tmp_path / "nonexistent.json")
    assert result["ok"] is False
    assert result["exists"] is False
    assert result["error"] == "artifact_not_found"
    assert result["active_count"] == 0
    assert result["suppressed_count"] == 0
    assert result["promotion"] == "none"
    assert result["agents_mutation"] == "none"


# ---------------------------------------------------------------------------
# Corrupt / invalid JSON
# ---------------------------------------------------------------------------

def test_corrupt_json_returns_not_ok(tmp_path: Path) -> None:
    path = tmp_path / "agents_rule_candidates.json"
    path.write_text("not json {{{", encoding="utf-8")
    result = inspect_artifact(path)
    assert result["ok"] is False
    assert result["exists"] is True
    assert "artifact_unreadable" in result["error"]


# ---------------------------------------------------------------------------
# Contract violation
# ---------------------------------------------------------------------------

def test_wrong_schema_version_fails_validation(tmp_path: Path) -> None:
    path = _write_artifact(tmp_path, schema_version="9.9")
    result = inspect_artifact(path)
    assert result["ok"] is False
    assert result["validation_ok"] is False
    assert "contract_violation" in result["error"]


def test_bad_source_fails_validation(tmp_path: Path) -> None:
    path = _write_artifact(tmp_path, source="auto_generated")
    result = inspect_artifact(path)
    assert result["ok"] is False
    assert result["validation_ok"] is False


# ---------------------------------------------------------------------------
# Valid artifact — happy path
# ---------------------------------------------------------------------------

def test_valid_empty_artifact_returns_ok(tmp_path: Path) -> None:
    artifact = make_aggregation_artifact(generated_at="2026-04-24T00:00:00Z")
    path = tmp_path / "agents_rule_candidates.json"
    path.write_text(json.dumps(artifact.to_dict()), encoding="utf-8")

    result = inspect_artifact(path)
    assert result["ok"] is True
    assert result["validation_ok"] is True
    assert result["active_count"] == 0
    assert result["suppressed_count"] == 0
    assert result["ledger_ref_count"] == 0
    assert result["promotion"] == "none"
    assert result["agents_mutation"] == "none"


def test_valid_artifact_with_one_active_candidate(tmp_path: Path) -> None:
    path = _write_artifact(tmp_path)
    result = inspect_artifact(path)
    assert result["ok"] is True
    assert result["active_count"] == 1
    assert result["suppressed_count"] == 0
    active = result["active_candidates"]
    assert len(active) == 1
    assert "runtime_hooks/core/pre_task_check.py" in active[0]["candidate_id"]
    assert active[0]["evidence_count"] == 0  # no events were passed


def test_valid_artifact_with_suppressed_candidate(tmp_path: Path) -> None:
    candidate = _candidate()
    agg = _aggregation_result(candidate)
    # suppressed entries must have resurfacing_allowed=False per contract
    entry = agg.to_dict()
    entry["resurfacing_allowed"] = False
    entry["suppressed_by_ledger"] = True
    data = {
        "schema_version": "0.1",
        "generated_at": "2026-04-24T00:00:00Z",
        "source": "manual_or_test_fixture",
        "candidates": [],
        "suppressed_candidates": [entry],
        "ledger_refs": [],
    }
    path = tmp_path / "agents_rule_candidates.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result_out = inspect_artifact(path)
    assert result_out["ok"] is True
    assert result_out["active_count"] == 0
    assert result_out["suppressed_count"] == 1


# ---------------------------------------------------------------------------
# Authority boundary — inspector never promotes
# ---------------------------------------------------------------------------

def test_promotion_field_is_always_none(tmp_path: Path) -> None:
    path = _write_artifact(tmp_path)
    result = inspect_artifact(path)
    assert result["promotion"] == "none"


def test_agents_mutation_field_is_always_none(tmp_path: Path) -> None:
    path = _write_artifact(tmp_path)
    result = inspect_artifact(path)
    assert result["agents_mutation"] == "none"


# ---------------------------------------------------------------------------
# format_summary smoke
# ---------------------------------------------------------------------------

def test_format_summary_missing_artifact(tmp_path: Path) -> None:
    result = inspect_artifact(tmp_path / "nonexistent.json")
    summary = format_summary(result)
    assert "FAIL" in summary
    assert "artifact_not_found" in summary


def test_format_summary_valid_artifact(tmp_path: Path) -> None:
    path = _write_artifact(tmp_path)
    result = inspect_artifact(path)
    summary = format_summary(result)
    assert "ok" in summary
    assert "active" in summary
    assert "promotion" in summary
    assert "none" in summary
    # must not claim any AGENTS.md mutation happened
    assert "landed" not in summary
    assert "approved" not in summary
