from governance_tools.claim_enforcement_checker import evaluate


def test_drift_true_bounded_maps_to_downgrade():
    payload = {
        "final_claim": "governance proven",  # disallowed phrase => drift
        "claim_level": "bounded",
        "same_evidence_as_previous": False,
        "posture": "bounded_support",
        "previous_posture": "bounded_support",
        "publication_scope": "public",
    }
    out = evaluate(payload)
    assert out["semantic_drift_risk"] is True
    assert out["enforcement_action"] == "downgrade"
    assert out["result"] == "pass"


def test_drift_true_strong_maps_to_block():
    payload = {
        "final_claim": "governance proven",  # disallowed phrase => drift
        "claim_level": "strong",
        "same_evidence_as_previous": False,
        "posture": "bounded_support",
        "previous_posture": "bounded_support",
        "publication_scope": "public",
    }
    out = evaluate(payload)
    assert out["semantic_drift_risk"] is True
    assert out["enforcement_action"] == "block"
    assert out["result"] == "fail"


def test_local_only_claim_level_must_not_exceed_bounded():
    payload = {
        "final_claim": "bounded_support wording",
        "claim_level": "parity",
        "same_evidence_as_previous": False,
        "posture": "bounded_support",
        "previous_posture": "bounded_support",
        "publication_scope": "local_only",
    }
    out = evaluate(payload)
    assert out["semantic_drift_risk"] is True
    assert out["enforcement_action"] == "downgrade"
    assert "local_only_claim_level_exceeds_bounded" in out["reasons"]
