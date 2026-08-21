"""Test-local claim guard for the dormant Route C natural-pilot amendment."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
AMENDMENT = (
    REPO_ROOT
    / "docs/governance/"
    "gate3-first-skill-route-c-natural-pilot-amendment-20260821.md"
)
CLAIM_BLOCK_BEGIN = "<!-- route-c-claim-block:begin -->"
CLAIM_BLOCK_END = "<!-- route-c-claim-block:end -->"
EXPECTED_CLAIMS = {
    "countability": "NOT_CLAIMED",
    "process_integrity": "NOT_ESTABLISHED",
    "promotion_evidence": False,
    "skill_effectiveness": "NOT_CLAIMED",
}
REQUIRED_RECORD_FIELDS = (
    "schema",
    "observation_id",
    "observed_at",
    "consumer_repository",
    "natural_bug_reference",
    "natural_bug_basis",
    "workflow_card_sha256",
    "workflow_card_retained_path",
    "workflow_steps",
    "outcome",
    "reviewer_counterfactual",
    "owner_interventions",
    "claims",
    "disposition",
)
FORBIDDEN_POSITIVE_PROSE = (
    re.compile(r"\bGate\s*3\s+passed\b", re.IGNORECASE),
    re.compile(r"\bGate3_pass\b\s*[:=]\s*(?:true|PASS)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:observation|case|result)\s+is\s+countable\b", re.IGNORECASE
    ),
    re.compile(r"\bSkill\s+is\s+effective\b", re.IGNORECASE),
    re.compile(r"\bSkill\s+caused\b", re.IGNORECASE),
    re.compile(r"\bproves?\s+Skill\s+effectiveness\b", re.IGNORECASE),
    re.compile(
        r"\b(?:demonstrates?|establishes?|proves?)\s+(?:a\s+)?causal\s+"
        r"(?:effect|impact)\b",
        re.IGNORECASE,
    ),
)


def _amendment_text() -> str:
    return AMENDMENT.read_text(encoding="utf-8")


def _extract_claim_block(text: str) -> dict[str, Any]:
    assert text.count(CLAIM_BLOCK_BEGIN) == 1
    assert text.count(CLAIM_BLOCK_END) == 1
    marked = text.split(CLAIM_BLOCK_BEGIN, 1)[1].split(CLAIM_BLOCK_END, 1)[0]
    match = re.fullmatch(r"\s*```json\s*\n(?P<body>.*?)\n```\s*", marked, re.DOTALL)
    assert match is not None
    value = json.loads(match.group("body"))
    assert isinstance(value, dict)
    return value


def _claim_guard_errors(claims: object, prose: str = "") -> list[str]:
    errors: list[str] = []
    if not isinstance(claims, dict):
        return ["claims_not_object"]
    if set(claims) != set(EXPECTED_CLAIMS):
        errors.append("claim_keys_changed")
    for key, expected in EXPECTED_CLAIMS.items():
        if claims.get(key) != expected:
            errors.append(f"claim_value_changed:{key}")
    for pattern in FORBIDDEN_POSITIVE_PROSE:
        if pattern.search(prose):
            errors.append(f"positive_claim_prose:{pattern.pattern}")
    return errors


def test_candidate_claim_block_and_prose_are_bounded() -> None:
    text = _amendment_text()
    claims = _extract_claim_block(text)
    assert _claim_guard_errors(claims, text) == []


def test_candidate_declares_closed_record_fields_and_card_bytes() -> None:
    text = _amendment_text()
    for field in REQUIRED_RECORD_FIELDS:
        assert f"`{field}`" in text
    assert "`gate3-route-c-natural-observation.v1`" in text
    assert "workflow_card_sha256" in text
    assert "workflow_card_retained_path" in text


def test_candidate_discloses_material_expiry_change() -> None:
    text = _amendment_text()
    assert "expires for re-review" in text
    assert "2026-09-11" in text
    assert "This is a material amendment" in text
    assert "terminal `STOP`" in text
    assert "There is no automatic extension" in text


def test_second_observation_is_a_recommendation_not_authority() -> None:
    text = _amendment_text()
    normalized = " ".join(text.split())
    assert "`SECOND_OBSERVATION` means only" in normalized
    assert "It does not authorize one" in normalized
    assert "A second observation is a new proposal requiring fresh authority" in normalized


def test_candidate_keeps_helper_test_local() -> None:
    text = _amendment_text()
    assert "intentionally test-local" in text
    assert "not a reusable\nvalidator" in text
    assert "It does not validate a future observation artifact" in text


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("process_integrity", "ESTABLISHED"),
        ("countability", "COUNTABLE"),
        ("promotion_evidence", True),
        ("skill_effectiveness", "ESTABLISHED"),
        ("Gate3_pass", True),
    ),
)
def test_claim_mutations_are_rejected(key: str, value: object) -> None:
    claims = copy.deepcopy(EXPECTED_CLAIMS)
    claims[key] = value
    assert _claim_guard_errors(claims)


@pytest.mark.parametrize(
    "prose",
    (
        "Gate 3 passed.",
        "Gate3_pass=true",
        "This observation is countable.",
        "The Skill is effective.",
        "The Skill caused the improvement.",
        "This proves Skill effectiveness.",
        "This demonstrates a causal effect.",
    ),
)
def test_positive_claim_prose_is_rejected(prose: str) -> None:
    assert _claim_guard_errors(EXPECTED_CLAIMS, prose)
