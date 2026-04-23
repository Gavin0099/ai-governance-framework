from runtime_hooks.core.evidence_integrity_gate import evaluate_evidence_integrity_gate


def _codes(result):
    return {v.code for v in result.violations}


def test_pass_when_wrong_case_needs_more_info_without_fake_evidence():
    record = {
        "case_id": "wrong_case_ok",
        "kind": "wrong",
        "ground_truth_direct_evidence": False,
        "decision": {
            "action": "need_more_info",
            "decision_candidates": [
                {
                    "action": "need_more_info",
                    "score": 1.7,
                    "reasons": ["direct_evidence_missing", "high_risk"],
                },
                {
                    "action": "reframe",
                    "score": 0.6,
                    "reasons": ["unverified_user_root_cause"],
                },
            ],
            "direct_evidence_frozen": False,
            "evidence_source": "explicit_no_evidence_marker",
        },
    }
    result = evaluate_evidence_integrity_gate(record)
    assert result.ok is True
    assert result.summary["hard_fail"] is False


def test_fail_when_no_evidence_but_reason_claims_direct_evidence():
    record = {
        "case_id": "fake_evidence_case",
        "kind": "wrong",
        "ground_truth_direct_evidence": False,
        "decision": {
            "action": "need_more_info",
            "decision_candidates": [
                {
                    "action": "proceed",
                    "score": 0.8,
                    "reasons": ["direct_evidence_present", "request_marked_valid"],
                }
            ],
            "direct_evidence_frozen": False,
            "evidence_source": "explicit_no_evidence_marker",
        },
    }
    result = evaluate_evidence_integrity_gate(record)
    assert result.ok is False
    codes = _codes(result)
    assert "EVIDENCE_REASON_MISMATCH" in codes
    assert "WRONG_PROCEED_CANDIDATE_PRESENT" in codes


def test_fail_when_wrong_case_selects_proceed():
    record = {
        "case_id": "wrong_proceed_selected",
        "kind": "wrong",
        "ground_truth_direct_evidence": False,
        "decision": {
            "action": "proceed",
            "decision_candidates": [
                {
                    "action": "proceed",
                    "score": 1.2,
                    "reasons": ["request_marked_valid"],
                }
            ],
            "direct_evidence_frozen": False,
            "evidence_source": "user_assertion_not_evidence",
        },
    }
    result = evaluate_evidence_integrity_gate(record)
    assert result.ok is False
    codes = _codes(result)
    assert "WRONG_PROCEED_SELECTED" in codes
    assert "PROCEED_SUPPORTED_BY_NON_EVIDENCE_ONLY" in codes


def test_pass_when_strong_evidence_allows_proceed():
    record = {
        "case_id": "valid_strong_evidence",
        "kind": "valid",
        "ground_truth_direct_evidence": True,
        "decision": {
            "action": "proceed",
            "decision_candidates": [
                {
                    "action": "proceed",
                    "score": 2.0,
                    "reasons": ["direct_evidence_present", "request_marked_valid"],
                }
            ],
            "direct_evidence_frozen": True,
            "evidence_source": "explicit_strong_markers",
        },
    }
    result = evaluate_evidence_integrity_gate(record)
    assert result.ok is True
