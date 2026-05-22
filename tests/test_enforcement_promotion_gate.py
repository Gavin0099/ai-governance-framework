"""
Enforcement Promotion Gate

Machine-checks the enforcement-promotion-policy:
  --warn-only must remain in governance.yml until first observed interception.

See: docs/enforcement-promotion-policy.md
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.honest_state_report import _load_ndjson, build_report

_PROJECT_ROOT = Path(__file__).parent.parent
_WORKFLOW_PATH = _PROJECT_ROOT / ".github/workflows/governance.yml"
_INTERCEPTED_PATH = _PROJECT_ROOT / "artifacts/governance/intercepted-events.ndjson"

_POLICY_REF = "docs/enforcement-promotion-policy.md"
_PROMOTION_MATERIALITY = {"high", "medium"}


def _observed_interceptions() -> list[dict]:
    entries = _load_ndjson(_INTERCEPTED_PATH)
    return [
        e for e in entries
        if e.get("evidence_basis") == "observed"
        and e.get("materiality") in _PROMOTION_MATERIALITY
    ]


def _workflow_has_warn_only() -> bool:
    if not _WORKFLOW_PATH.exists():
        return False
    return "--warn-only" in _WORKFLOW_PATH.read_text(encoding="utf-8")


# ── core gate ─────────────────────────────────────────────────────────────────

def test_enforcement_promotion_gate():
    """
    --warn-only must remain until first observed interception (high or medium materiality).
    Removing it without evidence is a promotion bypass and fails this test.
    """
    observed = _observed_interceptions()
    has_warn_only = _workflow_has_warn_only()

    if not observed:
        assert has_warn_only, (
            "enforcement_promotion_gate VIOLATED: --warn-only has been removed from "
            f"{_WORKFLOW_PATH.relative_to(_PROJECT_ROOT)} "
            "but no observed interception (high/medium materiality) exists in the ledger. "
            f"See {_POLICY_REF}."
        )
    # If observed interceptions exist, --warn-only may be present or absent — both are valid.


def test_ci_present_is_not_interception_evidence():
    """
    Verifies that the report's observed_interception_count reflects only ledger entries,
    not CI execution history. CI runs do not write to the interception ledger.
    """
    report = build_report(_PROJECT_ROOT)
    intercepted = _load_ndjson(_INTERCEPTED_PATH)
    observed_in_ledger = [
        e for e in intercepted if e.get("evidence_basis") == "observed"
    ]
    assert report["observed_interception_count"] == len(observed_in_ledger), (
        "observed_interception_count must match ledger entries only — "
        "no ambient or CI-run evidence may inflate this count."
    )


def test_retroactive_analysis_cannot_promote():
    """
    Retroactive analysis entries alone must not satisfy the promotion gate.
    Even if N retroactive entries exist, warn-only must remain.
    """
    intercepted = _load_ndjson(_INTERCEPTED_PATH)
    retroactive_high = [
        e for e in intercepted
        if e.get("evidence_basis") == "retroactive_analysis"
        and e.get("materiality") in _PROMOTION_MATERIALITY
    ]
    observed = _observed_interceptions()

    if retroactive_high and not observed:
        assert _workflow_has_warn_only(), (
            "enforcement_promotion_gate VIOLATED: retroactive_analysis entries exist "
            "but --warn-only has been removed. Retroactive analysis cannot promote enforcement. "
            f"See {_POLICY_REF}."
        )


# ── policy document presence ──────────────────────────────────────────────────

def test_policy_document_exists():
    assert (_PROJECT_ROOT / _POLICY_REF).exists(), (
        f"Enforcement promotion policy document missing: {_POLICY_REF}"
    )


# ── helper unit tests ─────────────────────────────────────────────────────────

def test_observed_interceptions_excludes_test_derived(tmp_path):
    ndjson = tmp_path / "intercepted.ndjson"
    ndjson.write_text(
        json.dumps({"event_id": "IE-T-001", "evidence_basis": "test_derived", "materiality": "high"}) + "\n",
        encoding="utf-8",
    )
    entries = _load_ndjson(ndjson)
    observed = [
        e for e in entries
        if e.get("evidence_basis") == "observed"
        and e.get("materiality") in _PROMOTION_MATERIALITY
    ]
    assert len(observed) == 0


def test_observed_low_materiality_does_not_promote(tmp_path):
    ndjson = tmp_path / "intercepted.ndjson"
    ndjson.write_text(
        json.dumps({"event_id": "IE-T-002", "evidence_basis": "observed", "materiality": "low"}) + "\n",
        encoding="utf-8",
    )
    entries = _load_ndjson(ndjson)
    observed = [
        e for e in entries
        if e.get("evidence_basis") == "observed"
        and e.get("materiality") in _PROMOTION_MATERIALITY
    ]
    assert len(observed) == 0
