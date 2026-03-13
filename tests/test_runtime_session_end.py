import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.session_end import run_session_end


@pytest.fixture
def local_project_root():
    path = Path("tests") / "_tmp_session_end"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _contract(**overrides):
    contract = {
        "task": "Runtime governance closeout",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "candidate",
    }
    contract.update(overrides)
    return contract


def test_session_end_auto_promotes_low_risk_candidate(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-01",
        runtime_contract=_contract(),
        checks={"ok": True, "errors": []},
        event_log=[{"event_type": "post_task"}],
        response_text="runtime output",
        summary="Low-risk session",
    )

    assert result["ok"] is True
    assert result["decision"] == "AUTO_PROMOTE"
    assert result["snapshot"] is not None
    assert result["curated"] is not None
    assert result["promotion"] is not None

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["promoted"] is True
    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert curated_payload["curation_status"] == "CURATED"


def test_session_end_requires_review_for_high_risk(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-02",
        runtime_contract=_contract(risk="high", oversight="review-required"),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
        summary="High-risk session",
    )

    assert result["ok"] is True
    assert result["decision"] == "REVIEW_REQUIRED"
    assert result["snapshot"] is not None
    assert result["curated"] is not None
    assert result["promotion"] is None


def test_session_end_does_not_promote_stateless_session(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-03",
        runtime_contract=_contract(memory_mode="stateless"),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
    )

    assert result["ok"] is True
    assert result["decision"] == "DO_NOT_PROMOTE"
    assert result["snapshot"] is None


def test_session_end_blocks_missing_contract_fields(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-04",
        runtime_contract={"task": "Broken session", "rules": []},
        checks={"ok": True, "errors": []},
        response_text="runtime output",
    )

    assert result["ok"] is False
    assert any("runtime_contract missing required fields" in error for error in result["errors"])


def test_session_end_records_public_api_diff_in_summary_and_curated_artifact(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-05",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={
            "ok": True,
            "errors": [],
            "public_api_diff": {
                "ok": True,
                "removed": [],
                "added": ["public int Ping() => 0;"],
                "warnings": ["Public API surface added or changed."],
                "errors": [],
            },
        },
        response_text="runtime output",
        summary="Refactor session with API additions",
    )

    assert result["ok"] is True
    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["public_api_diff_present"] is True
    assert summary_payload["public_api_added_count"] == 1
    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "public_api_diff.added" for item in curated_payload["items"])


def test_session_end_curates_removed_public_api_as_followup(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-06",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={
            "ok": False,
            "errors": ["public-api-diff: Public API surface removed or changed."],
            "public_api_diff": {
                "ok": False,
                "removed": ["public int Run(int value) => value;"],
                "added": [],
                "warnings": [],
                "errors": ["Public API surface removed or changed."],
            },
        },
        response_text="runtime output",
        summary="Refactor session with API removal",
    )

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(
        item["source"] == "public_api_diff.removed" and item["type"] == "followup"
        for item in curated_payload["items"]
    )


def test_session_end_records_architecture_impact_preview(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-07",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={"ok": True, "errors": []},
        architecture_impact_preview={
            "concerns": ["cross-layer-change-risk", "public-api-expansion-risk"],
            "required_evidence": ["architecture-review", "public-api-review"],
            "recommended_risk": "high",
            "recommended_oversight": "human-approval",
            "boundary_risk": "high",
        },
        response_text="runtime output",
        summary="Proposal-time impact preview captured",
    )

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["architecture_impact_present"] is True
    assert summary_payload["architecture_impact_concern_count"] == 2
    assert summary_payload["architecture_impact_recommended_risk"] == "high"

    candidate_payload = json.loads(Path(result["candidate_artifact"]).read_text(encoding="utf-8"))
    assert candidate_payload["architecture_impact_preview"]["boundary_risk"] == "high"

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "architecture_impact_preview.concerns" for item in curated_payload["items"])


def test_session_end_records_proposal_summary_in_audit_chain(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-08",
        runtime_contract=_contract(rules=["common", "refactor"]),
        checks={"ok": True, "errors": []},
        proposal_summary={
            "requested_rules": ["common", "refactor"],
            "recommended_risk": "high",
            "recommended_oversight": "human-approval",
            "required_evidence": ["architecture-review", "public-api-review"],
            "expected_validators": ["architecture_drift_checker", "public_api_diff_checker"],
            "concerns": ["cross-layer-change-risk"],
        },
        response_text="runtime output",
        summary="Proposal summary captured in session audit",
    )

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["proposal_summary_present"] is True
    assert summary_payload["proposal_summary_recommended_risk"] == "high"
    assert summary_payload["proposal_summary_expected_validator_count"] == 2

    candidate_payload = json.loads(Path(result["candidate_artifact"]).read_text(encoding="utf-8"))
    assert candidate_payload["proposal_summary"]["recommended_oversight"] == "human-approval"

    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert any(item["source"] == "proposal_summary.concerns" for item in curated_payload["items"])
    assert any(item["source"] == "proposal_summary.required_evidence" for item in curated_payload["items"])
