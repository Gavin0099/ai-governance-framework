from __future__ import annotations

from governance_tools.claim_enforcement_checker import evaluate


def test_self_labeled_bounded_strong_claim_now_downgraded() -> None:
    # S1 (remediated): a strong claim self-labeled bounded, avoiding the
    # proven/production-ready triggers, must no longer pass silently. It routes
    # through the existing advisory downgrade path, never a new hard block.
    payload = {
        "final_claim": (
            "This framework guarantees correct governance decisions across all "
            "repositories and can be relied on as the complete decision authority."
        ),
        "claim_level": "bounded",
        "same_evidence_as_previous": False,
        "posture": "bounded_support",
        "previous_posture": "bounded_support",
        "publication_scope": "public",
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is True
    assert out["enforcement_action"] == "downgrade"
    assert out["reviewer_override_required"] is True
    assert "claim_label_understates_claim_text" in out["reasons"]
    # Advisory only: a downgrade is a pass-with-review, never a hard block.
    assert out["result"] == "pass"


def test_self_labeled_parity_strong_claim_now_downgraded() -> None:
    payload = {
        "final_claim": "Handles every input and never fails.",
        "claim_level": "parity",
        "publication_scope": "public",
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is True
    assert out["enforcement_action"] == "downgrade"
    assert "claim_label_understates_claim_text" in out["reasons"]


def test_markerless_strong_claim_still_allowed_vulnerable_baseline() -> None:
    # S2 (VULNERABLE baseline): a semantically strong claim phrased WITHOUT any
    # lexical strength marker is not detectable by this structural proxy and
    # still passes. Pinned intentionally: if real semantic-vs-label detection is
    # added later, this test should fail and force a contract/catalog update.
    payload = {
        "final_claim": "This resolves the issue for the entire surface under review.",
        "claim_level": "bounded",
        "publication_scope": "public",
    }

    out = evaluate(payload)

    assert out["enforcement_action"] == "allow"
    assert out["semantic_drift_risk"] is False
    assert "claim_label_understates_claim_text" not in out["reasons"]
    assert out["report_only_reasons"] == []


def test_genuine_bounded_claim_without_markers_still_allowed() -> None:
    # Regression: no false positive on a genuinely restrained claim.
    payload = {
        "final_claim": "Adds an advisory report for the current diff only.",
        "claim_level": "bounded",
        "publication_scope": "public",
    }

    out = evaluate(payload)

    assert out["enforcement_action"] == "allow"
    assert out["semantic_drift_risk"] is False
    assert out["reasons"] == []
    assert out["report_only_reasons"] == []


def test_strong_level_with_markers_is_honest_labeling_not_drift() -> None:
    # When the claim_level already matches the text strength (strong), the
    # label-vs-text drift proxy must not fire; it is scoped to restrained levels.
    payload = {
        "final_claim": "This guarantees correctness for all inputs.",
        "claim_level": "strong",
        "publication_scope": "public",
    }

    out = evaluate(payload)

    assert "claim_label_understates_claim_text" not in out["reasons"]
    assert out["report_only_reasons"] == ["claim_support_missing_for_public_strong_claim"]


def test_structured_support_mismatch_reports_without_blocking() -> None:
    # Option A (structured claim support): machine-visible support can expose
    # label-vs-support mismatch, but it is report-only and must not change the
    # existing allow/downgrade/block path.
    payload = {
        "final_claim": "This resolves the issue for the entire surface under review.",
        "claim_level": "strong",
        "publication_scope": "public",
        "claim_support": {
            "supported_claim_level": "bounded",
            "support_source": "tests",
            "evidence_refs": ["pytest tests/test_self_governance_claim_label_mutation_contract.py"],
            "scope_boundaries": ["current checker behavior only"],
            "residual_risks": ["markerless semantic drift remains advisory"],
        },
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["reviewer_override_required"] is False
    assert out["reasons"] == []
    assert out["report_only_reasons"] == ["claim_level_exceeds_structured_support"]


def test_public_strong_claim_missing_support_reports_without_blocking() -> None:
    payload = {
        "final_claim": "This guarantees correctness for all inputs.",
        "claim_level": "strong",
        "publication_scope": "public",
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["reviewer_override_required"] is False
    assert out["report_only_reasons"] == ["claim_support_missing_for_public_strong_claim"]


def test_missing_claim_support_evidence_refs_is_report_only() -> None:
    payload = {
        "final_claim": "Adds bounded reporting for the current checker surface.",
        "claim_level": "bounded",
        "publication_scope": "public",
        "claim_support": {
            "supported_claim_level": "bounded",
            "support_source": "manual",
            "evidence_refs": [],
        },
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["report_only_reasons"] == ["claim_support_missing_evidence_refs"]


def test_invalid_claim_support_shape_is_report_only() -> None:
    payload = {
        "final_claim": "Adds bounded reporting for the current checker surface.",
        "claim_level": "bounded",
        "publication_scope": "public",
        "claim_support": "manual note",
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["report_only_reasons"] == ["claim_support_invalid_shape"]


def test_invalid_supported_claim_level_is_report_only() -> None:
    payload = {
        "final_claim": "Adds bounded reporting for the current checker surface.",
        "claim_level": "bounded",
        "publication_scope": "public",
        "claim_support": {
            "supported_claim_level": "unreviewed",
            "support_source": "manual",
            "evidence_refs": ["manual review note"],
        },
    }

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["report_only_reasons"] == ["claim_support_invalid_supported_claim_level"]
