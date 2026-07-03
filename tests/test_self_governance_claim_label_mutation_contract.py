from __future__ import annotations

from governance_tools.claim_enforcement_checker import evaluate


def test_self_labeled_bounded_claim_is_currently_allowed_vulnerable_baseline() -> None:
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
        "semantic_drift_risk": False,
    }

    out = evaluate(payload)

    assert out["result"] == "pass"
    assert out["checker_status"] == "pass"
    assert out["semantic_drift_risk"] is False
    assert out["claim_level"] == "bounded"
    assert out["enforcement_action"] == "allow"
    assert out["reviewer_override_required"] is False
    assert out["reasons"] == []
