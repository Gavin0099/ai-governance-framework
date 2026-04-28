from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.external_observation_adapter import normalize_external_observation


_CORPUS = Path("tests/fixtures/external_observation_corpus.json")


def test_external_observation_corpus_cases():
    cases = json.loads(_CORPUS.read_text(encoding="utf-8"))
    for case in cases:
        out = normalize_external_observation(case["input"])
        assert out["ingest_status"] == case["expect_status"], case["name"]
        assert out["observation"]["misuse_evidence_status"] == case["expect_misuse_status"], case["name"]
        assert out["decision_constraints"]["promotion_authority"] is False, case["name"]
        assert out["decision_constraints"]["verdict_authority"] is False, case["name"]


def test_invalid_payload_type_rejected():
    with pytest.raises(ValueError):
        normalize_external_observation("bad-payload")  # type: ignore[arg-type]


def test_observed_without_evidence_refs_degrades():
    out = normalize_external_observation(
        {
            "source": {"source_id": "ext", "source_type": "external_analyzer"},
            "observation": {
                "misuse_evidence_status": "observed",
                "confidence_level": "high",
            },
        }
    )
    assert out["ingest_status"] == "degraded"
    assert out["observation"]["misuse_evidence_status"] == "observed"
    assert any("observed status without evidence_refs" in w for w in out["advisory"]["warnings"])


def test_forbidden_authority_fields_are_ignored_and_degraded():
    out = normalize_external_observation(
        {
            "source": {"source_id": "ext", "source_type": "external_analyzer"},
            "observation": {
                "misuse_evidence_status": "not_observed_in_window",
                "confidence_level": "medium",
            },
            "phase3_entry_allowed": True,
            "promote_eligible": True,
            "current_state": "closure_verified",
        }
    )
    assert out["ingest_status"] == "degraded"
    assert out["decision_constraints"]["promotion_authority"] is False
    assert any("forbidden authority fields detected" in w for w in out["advisory"]["warnings"])

