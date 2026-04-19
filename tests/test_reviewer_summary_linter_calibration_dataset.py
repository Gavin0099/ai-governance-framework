from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.review_artifact_linter import lint_text


DATASET_PATH = Path("tests/fixtures/reviewer_linter_calibration_dataset.json")
DATASET = json.loads(DATASET_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", DATASET, ids=[item["id"] for item in DATASET])
def test_reviewer_linter_calibration_dataset(case: dict[str, object]) -> None:
    text = str(case["text"])
    expected_status = str(case["expected_status"])
    result = lint_text(text)
    claim_types = {str(v["claim_type"]) for v in result["violations"]}

    assert result["status"] == expected_status
    if expected_status == "clean":
        assert result["violation_count"] == 0

    for claim_type in case.get("must_include_claim_types", []):
        assert str(claim_type) in claim_types
    for claim_type in case.get("must_exclude_claim_types", []):
        assert str(claim_type) not in claim_types
