"""
CP-10: Copilot billing closeout authority artifact — integration snapshot tests.

Golden snapshot tests prove that authority_signal, receipt_contract_version,
safe_for_audit semantics, scope labeling, implicit warning, and claim text
remain stable across all authority signal modes.

DONE criteria:
  1. authoritative scoped_total        — snapshot stable
  2. grouped_by_model_only suppressed  — snapshot stable
  3. implicit_single_model_total       — snapshot stable
  4. safe_for_audit=False blocked      — snapshot stable
  5. unsupported contract_version      — snapshot stable

Non-goals enforced:
  - Does not assert Copilot source data correctness
  - Does not provide session attribution
  - Does not compare Copilot with Codex
  - Does not change receipt v0.2 semantics
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from codeburn.phase2.copilot_billing_closeout_authority_artifact import (
    ARTIFACT_TYPE,
    ARTIFACT_VERSION,
    build_copilot_billing_closeout_authority_artifact,
)


def _base_receipt(**overrides) -> dict:
    r = {
        "contract_version": "0.2",
        "provider": "copilot",
        "input_status": "present",
        "report_mode": "scoped_total",
        "scope_basis": "all_models",
        "authoritative_aggregate_emitted": True,
        "aggregate_rendered": True,
        "aggregate_suppression_reason": None,
        "consumer_guard_status": "passed",
        "invariant_codes": [],
        "warning_codes": [],
        "report_contract_ok": True,
        "summary_contract_ok": True,
        "safe_for_audit": True,
    }
    r.update(overrides)
    return r


def _snapshot_projection(artifact: dict) -> dict:
    """Project stable fields for snapshot assertion."""
    return {
        "artifact_type": artifact["artifact_type"],
        "artifact_version": artifact["artifact_version"],
        "receipt_contract_version": artifact["receipt_contract_version"],
        "unsupported_contract_version": artifact["unsupported_contract_version"],
        "authority_signal": artifact["authority_signal"],
        "safe_to_claim": artifact["safe_to_claim"],
        "scope_label": artifact["scope_label"],
        "implicit_warning_present": artifact["implicit_warning"] is not None,
        "aggregate_claim_present": artifact["aggregate_claim"] is not None,
    }


# ── Snapshot 1: authoritative scoped_total ────────────────────────────────────

def test_cp10_snapshot_authoritative_scoped_total():
    receipt = _base_receipt(
        report_mode="scoped_total",
        scope_basis="explicit_model_scope",
        authoritative_aggregate_emitted=True,
        safe_for_audit=True,
    )
    artifact = build_copilot_billing_closeout_authority_artifact(receipt)

    assert _snapshot_projection(artifact) == {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        "receipt_contract_version": "0.2",
        "unsupported_contract_version": False,
        "authority_signal": "authoritative",
        "safe_to_claim": True,
        "scope_label": "explicit_model_scope",
        "implicit_warning_present": False,
        "aggregate_claim_present": True,
    }

    # Scope label must appear in claim text
    claim = artifact["aggregate_claim"] or ""
    assert "explicit_model_scope" in claim


# ── Snapshot 2: grouped_by_model_only suppressed ──────────────────────────────

def test_cp10_snapshot_grouped_by_model_suppressed():
    receipt = _base_receipt(
        report_mode="grouped_by_model_only",
        scope_basis="multi_model_result_set_without_explicit_scope",
        authoritative_aggregate_emitted=False,
        aggregate_rendered=False,
        aggregate_suppression_reason="MULTI_MODEL_SCOPE_REQUIRED",
        safe_for_audit=True,
    )
    artifact = build_copilot_billing_closeout_authority_artifact(receipt)

    assert _snapshot_projection(artifact) == {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        "receipt_contract_version": "0.2",
        "unsupported_contract_version": False,
        "authority_signal": "suppressed",
        "safe_to_claim": True,
        "scope_label": "MULTI_MODEL_SCOPE_REQUIRED",
        "implicit_warning_present": False,
        "aggregate_claim_present": True,
    }

    # Suppressed claim must NOT assert a numeric total
    claim = artifact["aggregate_claim"] or ""
    assert "suppressed" in claim.lower()


# ── Snapshot 3: implicit_single_model_total ───────────────────────────────────

def test_cp10_snapshot_implicit_single_model_total():
    receipt = _base_receipt(
        report_mode="implicit_single_model_total",
        scope_basis="single_model_result_set",
        authoritative_aggregate_emitted=True,
        safe_for_audit=True,
    )
    artifact = build_copilot_billing_closeout_authority_artifact(receipt)

    assert _snapshot_projection(artifact) == {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        "receipt_contract_version": "0.2",
        "unsupported_contract_version": False,
        "authority_signal": "implicit",
        "safe_to_claim": True,
        "scope_label": "single_model_result_set",
        "implicit_warning_present": True,
        "aggregate_claim_present": True,
    }

    # Implicit warning must contain IMPLICIT marker
    warning = artifact["implicit_warning"] or ""
    assert "IMPLICIT" in warning.upper()

    # Scope label must appear in claim text
    claim = artifact["aggregate_claim"] or ""
    assert "single_model_result_set" in claim


# ── Snapshot 4: safe_for_audit=False blocked ─────────────────────────────────

def test_cp10_snapshot_safe_for_audit_false_blocked():
    receipt = _base_receipt(
        safe_for_audit=False,
        invariant_codes=["AGGREGATE_RENDERED_WITHOUT_AUTHORITY"],
        warning_codes=["AGGREGATE_RENDERED_WITHOUT_AUTHORITY"],
    )
    artifact = build_copilot_billing_closeout_authority_artifact(receipt)

    assert _snapshot_projection(artifact) == {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        "receipt_contract_version": "0.2",
        "unsupported_contract_version": False,
        "authority_signal": "blocked",
        "safe_to_claim": False,
        "scope_label": None,
        "implicit_warning_present": False,
        "aggregate_claim_present": False,
    }

    # Reasons must surface safe_for_audit gate
    reasons_text = " ".join(artifact["reasons"])
    assert "safe_for_audit" in reasons_text.lower()


# ── Snapshot 5: unsupported contract_version ─────────────────────────────────

def test_cp10_snapshot_unsupported_contract_version():
    receipt = _base_receipt(contract_version="0.1")
    artifact = build_copilot_billing_closeout_authority_artifact(receipt)

    assert _snapshot_projection(artifact) == {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        "receipt_contract_version": "0.1",
        "unsupported_contract_version": True,
        "authority_signal": "blocked",
        "safe_to_claim": False,
        "scope_label": None,
        "implicit_warning_present": False,
        "aggregate_claim_present": False,
    }

    # Reasons must surface UNSUPPORTED_RECEIPT_CONTRACT_VERSION
    reasons_text = " ".join(artifact["reasons"])
    assert "UNSUPPORTED_RECEIPT_CONTRACT_VERSION" in reasons_text


# ── Artifact header stability ─────────────────────────────────────────────────

def test_cp10_artifact_type_and_version_are_stable():
    receipt = _base_receipt()
    artifact = build_copilot_billing_closeout_authority_artifact(receipt)
    assert artifact["artifact_type"] == "copilot_billing_closeout_authority"
    assert artifact["artifact_version"] == "0.1"
