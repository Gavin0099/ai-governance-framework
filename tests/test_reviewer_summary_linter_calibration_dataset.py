from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.review_artifact_linter import lint_text


DATASET_PATH = Path("tests/fixtures/reviewer_linter_calibration_dataset.json")
DATASET = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
VALID_TIERS = {"tier_a_explicit", "tier_b_packaged", "tier_c_subtle"}
VALID_SURFACES = {
    "title",
    "heading",
    "label",
    "next_step",
    "summary_sentence",
    "mixed_language_phrase",
    "shorthand",
}
VALID_CONFIDENCE = {"high_confidence_claim", "borderline_claim", "safe_non_claim"}


@pytest.mark.parametrize("case", DATASET, ids=[item["id"] for item in DATASET])
def test_reviewer_linter_calibration_dataset(case: dict[str, object]) -> None:
    text = str(case["text"])
    expected_status = str(case["expected_status"])
    ambiguity_tier = str(case["ambiguity_tier"])
    surface_type = str(case["surface_type"])
    expected_claim_confidence = str(case["expected_claim_confidence"])
    result = lint_text(text)
    claim_types = {str(v["claim_type"]) for v in result["violations"]}

    assert ambiguity_tier in VALID_TIERS
    assert surface_type in VALID_SURFACES
    assert expected_claim_confidence in VALID_CONFIDENCE
    assert result["status"] == expected_status
    if expected_status == "clean":
        assert result["violation_count"] == 0

    for claim_type in case.get("must_include_claim_types", []):
        assert str(claim_type) in claim_types
    for claim_type in case.get("must_exclude_claim_types", []):
        assert str(claim_type) not in claim_types


def test_calibration_dataset_has_required_tier_and_surface_coverage() -> None:
    tiers = {str(item["ambiguity_tier"]) for item in DATASET}
    surfaces = {str(item["surface_type"]) for item in DATASET}
    confidences = {str(item["expected_claim_confidence"]) for item in DATASET}

    assert tiers == VALID_TIERS
    assert {"heading", "title", "label", "next_step", "shorthand", "mixed_language_phrase"} <= surfaces
    assert confidences == VALID_CONFIDENCE
