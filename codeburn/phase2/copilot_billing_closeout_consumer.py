#!/usr/bin/env python3
"""
CP-9: Copilot billing receipt-only closeout consumer.

Reads receipt v0.2 and produces a closeout summary with controlled authority claims.
Refuses to make aggregate authority claims unless safe_for_audit=True and the
receipt semantics explicitly permit the claim type.

Authority signal vocabulary:
  authoritative  — report emitted an authoritative aggregate (scoped_total / implicit)
  suppressed     — aggregate was suppressed by report contract (grouped_by_model_only)
  implicit       — total inferred from single-model scope, carries implicit warning
  blocked        — safe_for_audit=False or contract_version unsupported — no claim allowed

Non-goals (enforced by this module):
  - Does NOT assert Copilot billing source data correctness
  - Does NOT provide session-level attribution
  - Does NOT compare Copilot with Codex
  - Does NOT change ingest, report, or summary semantics
"""

from __future__ import annotations

from typing import Any

SUPPORTED_CONTRACT_VERSION = "0.2"
UNSUPPORTED_RECEIPT_CONTRACT_VERSION = "UNSUPPORTED_RECEIPT_CONTRACT_VERSION"

_AUTHORITY_AUTHORITATIVE = "authoritative"
_AUTHORITY_SUPPRESSED = "suppressed"
_AUTHORITY_IMPLICIT = "implicit"
_AUTHORITY_BLOCKED = "blocked"


def build_copilot_billing_closeout_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    """
    Build a closeout summary from a Copilot billing receipt v0.2.

    Returns a dict with:
      safe_to_claim:      bool — True only when a controlled claim is permitted
      authority_signal:   str  — authoritative | suppressed | implicit | blocked
      aggregate_claim:    str | None — the allowed claim text, or None if blocked
      scope_label:        str | None — required for authoritative/implicit claims
      implicit_warning:   str | None — required for implicit claims
      reasons:            list[str] — why blocked or what caveats apply
      receipt_version:    str — echoed from receipt
      unsupported_contract_version: bool
    """
    contract_version = str(receipt.get("contract_version") or "")
    reasons: list[str] = []
    unsupported = False

    # ── Contract version gate ──────────────────────────────────────────────
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        unsupported = True
        reasons.append(
            f"{UNSUPPORTED_RECEIPT_CONTRACT_VERSION}: expected {SUPPORTED_CONTRACT_VERSION!r}, "
            f"got {contract_version!r}"
        )
        return {
            "safe_to_claim": False,
            "authority_signal": _AUTHORITY_BLOCKED,
            "aggregate_claim": None,
            "scope_label": None,
            "implicit_warning": None,
            "reasons": reasons,
            "receipt_version": contract_version,
            "unsupported_contract_version": unsupported,
        }

    # ── safe_for_audit gate ────────────────────────────────────────────────
    safe_for_audit = bool(receipt.get("safe_for_audit"))
    if not safe_for_audit:
        reasons.append("safe_for_audit=False — no aggregate authority claim is permitted")
        invariant_codes = list(receipt.get("invariant_codes") or [])
        if invariant_codes:
            reasons.append(f"invariant violations: {', '.join(invariant_codes)}")
        return {
            "safe_to_claim": False,
            "authority_signal": _AUTHORITY_BLOCKED,
            "aggregate_claim": None,
            "scope_label": None,
            "implicit_warning": None,
            "reasons": reasons,
            "receipt_version": contract_version,
            "unsupported_contract_version": False,
        }

    # ── safe_for_audit=True — determine claim type by report_mode ─────────
    report_mode = str(receipt.get("report_mode") or "")
    authoritative = bool(receipt.get("authoritative_aggregate_emitted"))
    scope_basis = receipt.get("scope_basis")
    suppression_reason = receipt.get("aggregate_suppression_reason")

    if report_mode == "grouped_by_model_only":
        # Aggregate suppressed — can announce suppression, cannot announce total
        reasons.append("report_mode=grouped_by_model_only: aggregate total suppressed by contract")
        return {
            "safe_to_claim": True,
            "authority_signal": _AUTHORITY_SUPPRESSED,
            "aggregate_claim": "Copilot billing aggregate is suppressed — grouped-by-model report does not emit a total.",
            "scope_label": str(suppression_reason) if suppression_reason else "suppressed",
            "implicit_warning": None,
            "reasons": reasons,
            "receipt_version": contract_version,
            "unsupported_contract_version": False,
        }

    if report_mode == "implicit_single_model_total":
        # Implicit total — allowed but MUST carry warning
        if not scope_basis:
            reasons.append("scope_basis missing — implicit claim requires a scope label")
            return {
                "safe_to_claim": False,
                "authority_signal": _AUTHORITY_BLOCKED,
                "aggregate_claim": None,
                "scope_label": None,
                "implicit_warning": None,
                "reasons": reasons,
                "receipt_version": contract_version,
                "unsupported_contract_version": False,
            }
        implicit_warning = (
            "IMPLICIT SCOPE: total inferred from single-model data only — "
            "may not represent full Copilot billing."
        )
        reasons.append(f"report_mode=implicit_single_model_total: scope={scope_basis!r}")
        return {
            "safe_to_claim": True,
            "authority_signal": _AUTHORITY_IMPLICIT,
            "aggregate_claim": f"Copilot billing total (implicit, scope={scope_basis}).",
            "scope_label": str(scope_basis),
            "implicit_warning": implicit_warning,
            "reasons": reasons,
            "receipt_version": contract_version,
            "unsupported_contract_version": False,
        }

    if authoritative and scope_basis:
        # Authoritative scoped total — strongest claim, must carry scope label
        reasons.append(f"authoritative_aggregate_emitted=True, scope={scope_basis!r}")
        return {
            "safe_to_claim": True,
            "authority_signal": _AUTHORITY_AUTHORITATIVE,
            "aggregate_claim": f"Copilot billing total (scope={scope_basis}).",
            "scope_label": str(scope_basis),
            "implicit_warning": None,
            "reasons": reasons,
            "receipt_version": contract_version,
            "unsupported_contract_version": False,
        }

    # Fallback: safe_for_audit=True but report_mode not recognised or authoritative not emitted
    reasons.append(
        f"report_mode={report_mode!r} not recognised or authoritative_aggregate_emitted=False — "
        "no claim permitted"
    )
    return {
        "safe_to_claim": False,
        "authority_signal": _AUTHORITY_BLOCKED,
        "aggregate_claim": None,
        "scope_label": None,
        "implicit_warning": None,
        "reasons": reasons,
        "receipt_version": contract_version,
        "unsupported_contract_version": False,
    }
