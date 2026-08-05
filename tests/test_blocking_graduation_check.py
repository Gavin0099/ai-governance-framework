"""Advisory→blocking graduation: silence is not evidence, and AI cannot self-sign.

The two properties that matter most here are negative ones. A quiet observation
window must not read as readiness, and no attestation signed by an agent may
count — least of all the owner approval.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools.blocking_graduation_check import (  # noqa: E402
    ATTESTATION_SCHEMA,
    CRITERIA_SCHEMA,
    MET,
    NOT_MET,
    UNEVALUABLE,
    _criteria_digest,
    evaluate,
    load_criteria,
)
from governance_tools.guard_enforcement_census import (  # noqa: E402
    REGISTRY_SCHEMA as CENSUS_SCHEMA,
)

NOW = datetime(2026, 8, 5, tzinfo=timezone.utc)

CRITERIA = {
    "criteria_schema": CRITERIA_SCHEMA,
    "observation_window_days": 30,
    "attestation_max_age_days": 90,
    "ai_identities_may_not_attest": ["claude", "codex", "copilot", "agent"],
    "owner_registry": ["GavinWu"],
    "authority_ref_patterns": ["governance/*.md", "AUTHORITY.md"],
    "require_criteria_digest": True,
    "rejected_criterion": {"name": "consecutive_days_with_zero_findings"},
    "criteria": [
        {
            "id": "session_coverage",
            "kind": "machine",
            "evidence_glob": "artifacts/receipts/*.json",
            "ran_key": "guard_ran",
            "min_ratio": 0.9,
            "min_sessions": 3,
        },
        {
            "id": "owner_approval",
            "kind": "attestation",
            "attestation": "artifacts/attest/owner-approval.json",
            "human_only": True,
        },
    ],
}


def _repo(tmp_path: Path, criteria: dict | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "governance").mkdir(parents=True)
    (repo / "memory").mkdir(parents=True)
    (repo / "governance" / "blocking_graduation_criteria.json").write_text(
        json.dumps(criteria or CRITERIA), encoding="utf-8"
    )
    (repo / "governance" / "guard_surface_registry.json").write_text(
        json.dumps({"registry_schema": CENSUS_SCHEMA, "surfaces": []}), encoding="utf-8"
    )
    (repo / "AUTHORITY.md").write_text("# authority", encoding="utf-8")
    return repo


def _receipts(repo: Path, ran: int, total: int, *, age_days: float = 0.0) -> None:
    root = repo / "artifacts" / "receipts"
    root.mkdir(parents=True, exist_ok=True)
    for index in range(total):
        path = root / f"r{index}.json"
        path.write_text(json.dumps({"guard_ran": index < ran}), encoding="utf-8")
        if age_days:
            stamp = time.time() - age_days * 86400
            os.utime(path, (stamp, stamp))


def _attest(repo: Path, **overrides) -> None:
    payload = {
        "attestation_schema": ATTESTATION_SCHEMA,
        "attested_by": "GavinWu",
        "criteria_digest": None,  # filled in by _attest
        "authority_ref": "AUTHORITY.md",
        "result": True,
        "attested_at": (NOW - timedelta(days=1)).isoformat(),
    }
    if payload.get("criteria_digest") is None and "criteria_digest" not in overrides:
        payload["criteria_digest"] = _criteria_digest(repo)
    payload.update(overrides)
    path = repo / "artifacts" / "attest" / "owner-approval.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _by_id(result: dict, cid: str) -> dict:
    return next(item for item in result["criteria"] if item["id"] == cid)


# ── silence is not evidence ───────────────────────────────────────────────────

def test_no_sessions_is_unevaluable_not_met(tmp_path: Path) -> None:
    """The core rejection: an empty window answers nothing."""
    repo = _repo(tmp_path)
    result = evaluate(repo, now=NOW)
    coverage = _by_id(result, "session_coverage")
    assert coverage["status"] == UNEVALUABLE
    assert "insufficient_sessions" in coverage["detail"]


def test_unevaluable_criteria_block_the_proposal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo)
    result = evaluate(repo, now=NOW)
    assert _by_id(result, "session_coverage")["status"] == UNEVALUABLE
    assert result["ready_to_propose"] is False


def test_sessions_outside_the_window_do_not_count(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _receipts(repo, ran=10, total=10, age_days=120)
    assert _by_id(evaluate(repo, now=NOW), "session_coverage")["status"] == UNEVALUABLE


def test_partial_coverage_is_not_met(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _receipts(repo, ran=5, total=10)
    coverage = _by_id(evaluate(repo, now=NOW), "session_coverage")
    assert coverage["status"] == NOT_MET
    assert "0.50" in coverage["detail"]


def test_sufficient_coverage_is_met(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _receipts(repo, ran=10, total=10)
    assert _by_id(evaluate(repo, now=NOW), "session_coverage")["status"] == MET


# ── attestations ──────────────────────────────────────────────────────────────

def test_missing_attestation_is_not_met(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert approval["status"] == NOT_MET
    assert "attestation_absent" in approval["detail"]


def test_valid_owner_attestation_is_met(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo)
    assert _by_id(evaluate(repo, now=NOW), "owner_approval")["status"] == MET


@pytest.mark.parametrize(
    "signer", ["claude", "Claude Opus", "codex-cli", "github copilot", "agent-7"]
)
def test_ai_identities_cannot_attest(tmp_path: Path, signer: str) -> None:
    """An agent signing off on its own enforcement proves nothing."""
    repo = _repo(tmp_path)
    _attest(repo, attested_by=signer)
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert approval["status"] == NOT_MET
    assert "attested_by_ai_identity_rejected" in approval["detail"]


def test_attestation_without_authority_reference_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo, authority_ref="")
    assert "authority_ref" in _by_id(evaluate(repo, now=NOW), "owner_approval")["detail"]


def test_attestation_pointing_at_a_missing_document_is_rejected(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _attest(repo, authority_ref="docs/does-not-exist.md")
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert "authority_ref_missing" in approval["detail"]


def test_stale_attestation_expires(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo, attested_at=(NOW - timedelta(days=200)).isoformat())
    assert "attestation_stale" in _by_id(evaluate(repo, now=NOW), "owner_approval")["detail"]


def test_attestation_recording_a_negative_result_is_not_met(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo, result=False)
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert approval["status"] == NOT_MET
    assert "result_not_true" in approval["detail"]


def test_wrong_attestation_schema_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo, attestation_schema="freeform.v1")
    assert "schema_mismatch" in _by_id(evaluate(repo, now=NOW), "owner_approval")["detail"]


# ── overall gating ────────────────────────────────────────────────────────────

def test_all_criteria_met_permits_a_proposal_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _receipts(repo, ran=10, total=10)
    _attest(repo)

    result = evaluate(repo, now=NOW)
    assert result["ready_to_propose"] is True
    # Proposing is not enabling: no policy file was written.
    assert not (repo / "governance" / "memory_blocking_policy.json").exists()
    assert any("human edit" in line for line in result["claim_ceiling"])


def test_zero_findings_is_a_documented_non_criterion(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = evaluate(repo, now=NOW)
    assert result["rejected_criterion"]["name"] == "consecutive_days_with_zero_findings"
    assert not any(
        "zero_findings" in item["id"] for item in result["criteria"]
    )


def test_missing_criteria_file_is_an_error_not_a_pass(tmp_path: Path) -> None:
    repo = tmp_path / "bare"
    repo.mkdir()
    result = evaluate(repo, now=NOW)
    assert result["error"] == "criteria_not_found"
    assert result["ready_to_propose"] is False


def test_criteria_schema_mismatch_is_an_error(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"criteria_schema": "other.v9", "criteria": []})
    assert load_criteria(repo)["error"] == "criteria_schema_mismatch"


# ── authority binding: a name is not an authorisation ────────────────────────

def test_signer_outside_the_owner_registry_is_rejected(tmp_path: Path) -> None:
    """"Gavin" is a name; only a registered owner can approve enforcement."""
    repo = _repo(tmp_path)
    _attest(repo, attested_by="Gavin")
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert approval["status"] == NOT_MET
    assert "not_in_owner_registry" in approval["detail"]


def test_arbitrary_existing_file_is_not_an_authority_document(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("# readme", encoding="utf-8")
    _attest(repo, authority_ref="README.md")
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert approval["status"] == NOT_MET
    assert "not_an_authority_document" in approval["detail"]


def test_approval_is_bound_to_the_criteria_it_approved(tmp_path: Path) -> None:
    """Weakening the criteria after signing must invalidate the signature."""
    repo = _repo(tmp_path)
    _attest(repo)
    assert _by_id(evaluate(repo, now=NOW), "owner_approval")["status"] == MET

    criteria = json.loads(
        (repo / "governance" / "blocking_graduation_criteria.json").read_text("utf-8")
    )
    criteria["observation_window_days"] = 1
    (repo / "governance" / "blocking_graduation_criteria.json").write_text(
        json.dumps(criteria), encoding="utf-8"
    )

    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert approval["status"] == NOT_MET
    assert "criteria_digest_mismatch" in approval["detail"]


def test_attestation_without_a_criteria_digest_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _attest(repo, criteria_digest="")
    approval = _by_id(evaluate(repo, now=NOW), "owner_approval")
    assert "missing_criteria_digest" in approval["detail"]


# ── observation window cannot be washed by rebuilding the baseline ───────────

def _write_baseline(repo: Path, buckets: list[dict], *, age_days: float) -> Path:
    root = repo / "artifacts" / "governance"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "memory-authority-baseline-2026-01-01.json"
    path.write_text(json.dumps({"buckets": buckets}), encoding="utf-8")
    stamp = time.time() - age_days * 86400
    os.utime(path, (stamp, stamp))
    return path


def test_baseline_rebuilt_inside_the_window_invalidates_it(tmp_path: Path) -> None:
    """Re-freezing current debt can zero active findings without fixing anything."""
    criteria = {
        **CRITERIA,
        "baseline_glob": "artifacts/governance/memory-authority-baseline-*.json",
        "criteria": [
            {
                "id": "active_violations_clear",
                "kind": "machine",
                "code": "non_canonical_writer",
            }
        ],
    }
    repo = _repo(tmp_path, criteria)
    _write_baseline(repo, [], age_days=2)

    entry = _by_id(evaluate(repo, now=NOW), "active_violations_clear")
    assert entry["status"] == UNEVALUABLE
    assert "baseline_rebuilt_inside_observation_window" in entry["detail"]


def test_baseline_freezing_an_in_window_finding_fails_non_interference(
    tmp_path: Path,
) -> None:
    criteria = {
        **CRITERIA,
        "criteria": [
            {
                "id": "baseline_non_interference",
                "kind": "machine",
                "baseline_glob": (
                    "artifacts/governance/memory-authority-baseline-*.json"
                ),
            }
        ],
    }
    repo = _repo(tmp_path, criteria)
    # 2026-07-01 is inside the active window (cutoff 2026-06-02), so freezing
    # it into the baseline would hide a finding enforcement must still see.
    _write_baseline(
        repo,
        [{"code": "non_canonical_writer", "file": "2026-07-01.md"}],
        age_days=400,
    )
    entry = _by_id(evaluate(repo, now=NOW), "baseline_non_interference")
    assert entry["status"] == NOT_MET
    assert "in_window_buckets_frozen=1" in entry["detail"]


def test_historical_baseline_buckets_do_not_fail_non_interference(
    tmp_path: Path,
) -> None:
    criteria = {
        **CRITERIA,
        "criteria": [
            {
                "id": "baseline_non_interference",
                "kind": "machine",
                "baseline_glob": (
                    "artifacts/governance/memory-authority-baseline-*.json"
                ),
            }
        ],
    }
    repo = _repo(tmp_path, criteria)
    _write_baseline(
        repo,
        [{"code": "non_canonical_writer", "file": "2026-05-01.md"}],
        age_days=400,
    )
    assert _by_id(evaluate(repo, now=NOW), "baseline_non_interference")["status"] == MET


# ── rollback ─────────────────────────────────────────────────────────────────

def test_policy_without_a_documented_kill_switch_is_not_met(tmp_path: Path) -> None:
    criteria = {
        **CRITERIA,
        "criteria": [
            {
                "id": "rollback_available",
                "kind": "machine",
                "policy_path": "governance/memory_blocking_policy.json",
            }
        ],
    }
    repo = _repo(tmp_path, criteria)
    (repo / "governance" / "memory_blocking_policy.json").write_text(
        json.dumps({"enabled": True, "blocking_codes": []}), encoding="utf-8"
    )
    entry = _by_id(evaluate(repo, now=NOW), "rollback_available")
    assert entry["status"] == NOT_MET
    assert "no kill-switch note" in entry["detail"]


def test_documented_kill_switch_satisfies_rollback(tmp_path: Path) -> None:
    criteria = {
        **CRITERIA,
        "criteria": [
            {
                "id": "rollback_available",
                "kind": "machine",
                "policy_path": "governance/memory_blocking_policy.json",
            }
        ],
    }
    repo = _repo(tmp_path, criteria)
    (repo / "governance" / "memory_blocking_policy.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "blocking_codes": [],
                "scope_note": "Kill switch: set enabled to false or delete this file.",
            }
        ),
        encoding="utf-8",
    )
    assert _by_id(evaluate(repo, now=NOW), "rollback_available")["status"] == MET
