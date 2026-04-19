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
VALID_FAMILIES = {
    "readiness",
    "promotion",
    "stability",
    "confidence_laundering",
    "directional_hint",
    "safe_disclaimer",
    "status_label_like",
}
REQUIRED_CORE_FAMILIES = {
    "readiness",
    "promotion",
    "stability",
    "confidence_laundering",
    "directional_hint",
    "safe_disclaimer",
}
HIGH_RISK_FAMILIES = {"promotion", "confidence_laundering"}


@pytest.mark.parametrize("case", DATASET, ids=[item["id"] for item in DATASET])
def test_reviewer_linter_calibration_dataset(case: dict[str, object]) -> None:
    text = str(case["text"])
    expected_status = str(case["expected_status"])
    ambiguity_tier = str(case["ambiguity_tier"])
    surface_type = str(case["surface_type"])
    expected_claim_confidence = str(case["expected_claim_confidence"])
    semantic_family = str(case["semantic_family"])
    result = lint_text(text)
    claim_types = {str(v["claim_type"]) for v in result["violations"]}

    assert ambiguity_tier in VALID_TIERS
    assert surface_type in VALID_SURFACES
    assert expected_claim_confidence in VALID_CONFIDENCE
    assert semantic_family in VALID_FAMILIES
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
    families = {str(item["semantic_family"]) for item in DATASET}

    assert tiers == VALID_TIERS
    assert {"heading", "title", "label", "next_step", "shorthand", "mixed_language_phrase"} <= surfaces
    assert confidences == VALID_CONFIDENCE
    assert REQUIRED_CORE_FAMILIES <= families


def test_calibration_dataset_has_family_balance_guards() -> None:
    family_counts: dict[str, int] = {}
    family_surfaces: dict[str, set[str]] = {}
    family_tiers: dict[str, set[str]] = {}
    for item in DATASET:
        family = str(item["semantic_family"])
        surface = str(item["surface_type"])
        tier = str(item["ambiguity_tier"])
        family_counts[family] = family_counts.get(family, 0) + 1
        family_surfaces.setdefault(family, set()).add(surface)
        family_tiers.setdefault(family, set()).add(tier)

    for family in REQUIRED_CORE_FAMILIES:
        assert family_counts.get(family, 0) >= 2
        assert len(family_surfaces.get(family, set())) >= 2

    for family in HIGH_RISK_FAMILIES:
        tiers = family_tiers.get(family, set())
        assert "tier_a_explicit" in tiers
        assert "tier_c_subtle" in tiers
