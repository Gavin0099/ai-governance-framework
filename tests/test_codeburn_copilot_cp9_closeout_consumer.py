"""
CP-9: Copilot billing receipt-only closeout consumer smoke tests.

DONE criteria:
  1. safe_for_audit=False  => blocked, no aggregate claim
  2. grouped_by_model_only + safe_for_audit=True => suppressed claim, no total quantity
  3. scoped_total + safe_for_audit=True => authoritative claim with scope label
  4. implicit_single_model_total + safe_for_audit=True => implicit claim with warning
  5. contract_version != 0.2 => fail closed, UNSUPPORTED_RECEIPT_CONTRACT_VERSION

Non-goals enforced:
  - Does not assert Copilot source data correctness
  - Does not provide session attribution
  - Does not compare Copilot with Codex
  - Does not change ingest/report/summary semantics
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from codeburn.phase2.copilot_billing_closeout_consumer import (
    SUPPORTED_CONTRACT_VERSION,
    UNSUPPORTED_RECEIPT_CONTRACT_VERSION,
    build_copilot_billing_closeout_summary,
)


def _base_receipt(**overrides) -> dict:
    """Minimal valid receipt v0.2 with safe_for_audit=True and scoped_total defaults."""
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


# ── Criterion 1: safe_for_audit=False blocks all claims ──────────────────────

class TestSafeForAuditFalseBlocked:
    def test_safe_for_audit_false_is_blocked(self):
        receipt = _base_receipt(safe_for_audit=False)
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is False
        assert summary["authority_signal"] == "blocked"
        assert summary["aggregate_claim"] is None

    def test_blocked_reason_mentions_safe_for_audit(self):
        receipt = _base_receipt(safe_for_audit=False)
        summary = build_copilot_billing_closeout_summary(receipt)
        reasons_text = " ".join(summary["reasons"])
        assert "safe_for_audit" in reasons_text.lower()

    def test_invariant_codes_surfaced_when_blocked(self):
        receipt = _base_receipt(
            safe_for_audit=False,
            invariant_codes=["AGGREGATE_RENDERED_WITHOUT_AUTHORITY"],
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is False
        reasons_text = " ".join(summary["reasons"])
        assert "AGGREGATE_RENDERED_WITHOUT_AUTHORITY" in reasons_text

    def test_safe_for_audit_false_with_various_modes_all_blocked(self):
        for mode in ["grouped_by_model_only", "scoped_total", "implicit_single_model_total", "unknown"]:
            receipt = _base_receipt(safe_for_audit=False, report_mode=mode)
            summary = build_copilot_billing_closeout_summary(receipt)
            assert summary["safe_to_claim"] is False, f"mode={mode} should be blocked"
            assert summary["aggregate_claim"] is None, f"mode={mode} should have no claim"


# ── Criterion 2: grouped_by_model_only + safe_for_audit=True ─────────────────

class TestGroupedByModelOnlySuppressed:
    def test_authority_signal_is_suppressed(self):
        receipt = _base_receipt(
            report_mode="grouped_by_model_only",
            authoritative_aggregate_emitted=False,
            aggregate_rendered=False,
            aggregate_suppression_reason="grouped_by_model_contract",
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is True
        assert summary["authority_signal"] == "suppressed"

    def test_aggregate_claim_does_not_include_total_quantity(self):
        receipt = _base_receipt(
            report_mode="grouped_by_model_only",
            authoritative_aggregate_emitted=False,
            aggregate_rendered=False,
            aggregate_suppression_reason="grouped_by_model_contract",
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        claim = summary["aggregate_claim"] or ""
        # Must not assert a numeric total
        assert "total" not in claim.lower() or "suppressed" in claim.lower(), (
            "grouped_by_model claim must not assert a total quantity"
        )

    def test_scope_label_present_for_suppressed_claim(self):
        receipt = _base_receipt(
            report_mode="grouped_by_model_only",
            authoritative_aggregate_emitted=False,
            aggregate_rendered=False,
            aggregate_suppression_reason="grouped_by_model_contract",
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["scope_label"] is not None

    def test_no_implicit_warning_for_suppressed(self):
        receipt = _base_receipt(
            report_mode="grouped_by_model_only",
            authoritative_aggregate_emitted=False,
            aggregate_rendered=False,
            aggregate_suppression_reason="grouped_by_model_contract",
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["implicit_warning"] is None


# ── Criterion 3: scoped_total + safe_for_audit=True ──────────────────────────

class TestScopedTotalAuthoritative:
    def test_authority_signal_is_authoritative(self):
        receipt = _base_receipt(
            report_mode="scoped_total",
            scope_basis="all_models",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is True
        assert summary["authority_signal"] == "authoritative"

    def test_scope_label_is_present(self):
        receipt = _base_receipt(
            report_mode="scoped_total",
            scope_basis="all_models",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["scope_label"] is not None
        assert "all_models" in str(summary["scope_label"])

    def test_scope_label_in_aggregate_claim(self):
        receipt = _base_receipt(
            report_mode="scoped_total",
            scope_basis="claude-3-5-sonnet",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        claim = summary["aggregate_claim"] or ""
        assert "claude-3-5-sonnet" in claim

    def test_no_implicit_warning_for_authoritative(self):
        receipt = _base_receipt(
            report_mode="scoped_total",
            scope_basis="all_models",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["implicit_warning"] is None


# ── Criterion 4: implicit_single_model_total + safe_for_audit=True ───────────

class TestImplicitSingleModelTotal:
    def test_authority_signal_is_implicit(self):
        receipt = _base_receipt(
            report_mode="implicit_single_model_total",
            scope_basis="claude-3-haiku",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is True
        assert summary["authority_signal"] == "implicit"

    def test_implicit_warning_is_present(self):
        receipt = _base_receipt(
            report_mode="implicit_single_model_total",
            scope_basis="claude-3-haiku",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["implicit_warning"] is not None
        warning = summary["implicit_warning"].upper()
        assert "IMPLICIT" in warning

    def test_scope_label_included_for_implicit(self):
        receipt = _base_receipt(
            report_mode="implicit_single_model_total",
            scope_basis="claude-3-haiku",
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["scope_label"] == "claude-3-haiku"

    def test_implicit_without_scope_basis_is_blocked(self):
        receipt = _base_receipt(
            report_mode="implicit_single_model_total",
            scope_basis=None,
            authoritative_aggregate_emitted=True,
        )
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is False
        assert summary["authority_signal"] == "blocked"


# ── Criterion 5: unsupported contract_version ─────────────────────────────────

class TestUnsupportedContractVersion:
    def test_wrong_version_is_blocked(self):
        receipt = _base_receipt(contract_version="0.1")
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is False
        assert summary["authority_signal"] == "blocked"
        assert summary["unsupported_contract_version"] is True

    def test_unsupported_version_code_in_reasons(self):
        receipt = _base_receipt(contract_version="0.1")
        summary = build_copilot_billing_closeout_summary(receipt)
        reasons_text = " ".join(summary["reasons"])
        assert UNSUPPORTED_RECEIPT_CONTRACT_VERSION in reasons_text

    def test_missing_version_is_blocked(self):
        receipt = _base_receipt()
        del receipt["contract_version"]
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is False
        assert summary["unsupported_contract_version"] is True

    def test_future_version_is_blocked(self):
        receipt = _base_receipt(contract_version="1.0")
        summary = build_copilot_billing_closeout_summary(receipt)
        assert summary["safe_to_claim"] is False
        assert summary["unsupported_contract_version"] is True

    def test_supported_version_constant_matches_receipt_contract(self):
        assert SUPPORTED_CONTRACT_VERSION == "0.2"
