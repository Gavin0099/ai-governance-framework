#!/usr/bin/env python3
"""
CP-10: Copilot billing closeout authority artifact builder.

Wraps CP-9 closeout consumer output into a stable, snapshot-testable artifact
that records the authority signal, claim surface, and receipt provenance.

Artifact type: copilot_billing_closeout_authority
Artifact version: 0.1

This artifact records WHAT authority claim the closeout consumer produced —
not source-data correctness, session attribution, or Codex comparability.

Non-goals:
  - Does NOT assert Copilot source data correctness
  - Does NOT provide session-level attribution
  - Does NOT compare Copilot with Codex
  - Does NOT change ingest, report, summary, or receipt v0.2 semantics
"""

from __future__ import annotations

from typing import Any

from codeburn.phase2.copilot_billing_closeout_consumer import (
    build_copilot_billing_closeout_summary,
)

ARTIFACT_TYPE = "copilot_billing_closeout_authority"
ARTIFACT_VERSION = "0.1"


def build_copilot_billing_closeout_authority_artifact(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a stable closeout authority artifact from a Copilot billing receipt v0.2.

    Calls the CP-9 closeout consumer and wraps its output with artifact metadata
    (artifact_type, artifact_version) for snapshot-testable persistence.

    Returns a dict suitable for golden snapshot comparison.
    """
    summary = build_copilot_billing_closeout_summary(receipt)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        # Receipt provenance
        "receipt_contract_version": summary["receipt_version"],
        "unsupported_contract_version": summary["unsupported_contract_version"],
        # Authority claim surface
        "authority_signal": summary["authority_signal"],
        "safe_to_claim": summary["safe_to_claim"],
        "aggregate_claim": summary["aggregate_claim"],
        "scope_label": summary["scope_label"],
        "implicit_warning": summary["implicit_warning"],
        # Traceability
        "reasons": summary["reasons"],
    }
