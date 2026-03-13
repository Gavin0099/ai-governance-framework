import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_pipeline.memory_curator import curate_candidate_artifact


@pytest.fixture
def local_runtime_root():
    path = Path("tests") / "_tmp_memory_curator"
    if path.exists():
        shutil.rmtree(path)
    (path / "artifacts" / "runtime" / "candidates").mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_curator_keeps_summary_and_rules_and_drops_noise(local_runtime_root):
    candidate_path = local_runtime_root / "artifacts" / "runtime" / "candidates" / "session.json"
    payload = {
        "session_id": "2026-03-12-01",
        "summary": "Added session_end lifecycle close with promotion policy.",
        "runtime_contract": {
            "rules": ["common", "cpp"],
            "risk": "medium",
            "oversight": "review-required",
        },
        "checks": {"errors": []},
        "policy": {"reasons": ["Oversight=review-required requires explicit review before promotion."]},
        "event_log": [
            {"event_type": "post_task", "summary": "11 passed"},
            {"event_type": "session_end", "summary": "Curated candidate memory before promotion."},
        ],
    }
    candidate_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = curate_candidate_artifact(candidate_path)

    assert result["curation_status"] == "CURATED"
    assert result["kept_count"] >= 3
    assert result["dropped_count"] >= 1
    assert any(item["source"] == "summary" for item in result["items"])
    assert any(item["source"] == "runtime_contract.rules" for item in result["items"])
    assert result["promotion_hint"] == "REVIEW_REQUIRED"


def test_curator_marks_runtime_errors_as_followups(local_runtime_root):
    candidate_path = local_runtime_root / "artifacts" / "runtime" / "candidates" / "session.json"
    payload = {
        "session_id": "2026-03-12-02",
        "summary": "Refined runtime governance rules.",
        "runtime_contract": {
            "rules": ["common"],
            "risk": "low",
            "oversight": "auto",
        },
        "checks": {"errors": ["High-risk tasks require oversight != auto"]},
        "policy": {"reasons": []},
        "event_log": [],
    }
    candidate_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = curate_candidate_artifact(candidate_path)

    assert any(item["type"] == "followup" for item in result["items"])
    assert "runtime check errors present" in result["needs_review_reason"]


def test_curator_preserves_architecture_impact_evidence(local_runtime_root):
    candidate_path = local_runtime_root / "artifacts" / "runtime" / "candidates" / "session.json"
    payload = {
        "session_id": "2026-03-12-03",
        "summary": "Captured proposal-time impact signals.",
        "runtime_contract": {
            "rules": ["common", "refactor"],
            "risk": "medium",
            "oversight": "review-required",
        },
        "checks": {"errors": []},
        "policy": {"reasons": []},
        "architecture_impact_preview": {
            "concerns": ["cross-layer-change-risk"],
            "required_evidence": ["architecture-review", "public-api-review"],
        },
        "event_log": [],
    }
    candidate_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = curate_candidate_artifact(candidate_path)

    assert any(item["source"] == "architecture_impact_preview.concerns" for item in result["items"])
    assert any(item["source"] == "architecture_impact_preview.required_evidence" for item in result["items"])


def test_curator_preserves_proposal_summary_evidence(local_runtime_root):
    candidate_path = local_runtime_root / "artifacts" / "runtime" / "candidates" / "session.json"
    payload = {
        "session_id": "2026-03-12-04",
        "summary": "Captured proposal summary for review.",
        "runtime_contract": {
            "rules": ["common", "refactor"],
            "risk": "medium",
            "oversight": "review-required",
        },
        "checks": {"errors": []},
        "policy": {"reasons": []},
        "proposal_summary": {
            "recommended_risk": "high",
            "recommended_oversight": "human-approval",
            "required_evidence": ["architecture-review", "public-api-review"],
            "concerns": ["cross-layer-change-risk"],
        },
        "event_log": [],
    }
    candidate_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = curate_candidate_artifact(candidate_path)

    assert any(item["source"] == "proposal_summary.concerns" for item in result["items"])
    assert any(item["source"] == "proposal_summary.required_evidence" for item in result["items"])
    assert any(item["source"] == "proposal_summary.recommendation" for item in result["items"])
