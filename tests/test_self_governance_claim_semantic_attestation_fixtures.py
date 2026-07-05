from __future__ import annotations

from pathlib import Path

from governance_tools.claim_enforcement_checker import evaluate


MISSING_CODE = "claim_semantic_attestation_missing"
INVALID_CODE = "claim_semantic_attestation_invalid"
OVERSTATED_CODE = "claim_semantic_attestation_overstated"
UNCLEAR_CODE = "claim_semantic_attestation_unclear"


def _markerless_payload() -> dict:
    return {
        "final_claim": "This resolves the issue for the entire surface under review.",
        "claim_level": "bounded",
        "publication_scope": "public",
    }


def _valid_receipt(**overrides: object) -> dict:
    receipt = {
        "receipt_schema": "claim_semantic_attestation.v0.1",
        "status": "report_only",
        "reviewed_claim": "This resolves the issue for the entire surface under review.",
        "reviewed_claim_level": "bounded",
        "evidence_refs": [
            "pytest tests/test_self_governance_claim_label_mutation_contract.py"
        ],
        "attested_support_level": "bounded",
        "attestation_result": "aligned",
        "attested_by": "agent-reviewer",
        "linked_commit": "0123456789abcdef0123456789abcdef01234567",
        "cannot_claim": [
            "receipt does not prove the reviewer was correct",
            "receipt does not prove evidence truth",
        ],
    }
    receipt.update(overrides)
    return receipt


def test_missing_semantic_attestation_reports_without_blocking() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = True

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert MISSING_CODE in out["report_only_reasons"]


def test_string_false_semantic_review_claim_does_not_count_as_claimed() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = "false"

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert MISSING_CODE not in out["report_only_reasons"]


def test_invalid_semantic_attestation_reports_without_blocking() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = True
    payload["claim_semantic_attestation"] = _valid_receipt(receipt_schema="wrong.v9")

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert INVALID_CODE in out["report_only_reasons"]


def test_moving_head_semantic_attestation_linked_commit_is_invalid() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = True
    payload["claim_semantic_attestation"] = _valid_receipt(linked_commit="HEAD")

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert INVALID_CODE in out["report_only_reasons"]


def test_nonexistent_hex_linked_commit_is_invalid_when_project_root_is_supplied() -> None:
    payload = _markerless_payload()
    payload["project_root"] = str(Path(__file__).resolve().parents[1])
    payload["semantic_review_claimed"] = True
    payload["claim_semantic_attestation"] = _valid_receipt(
        linked_commit="0000000000000000000000000000000000000000"
    )

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert INVALID_CODE in out["report_only_reasons"]


def test_overstated_semantic_attestation_reports_without_blocking() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = True
    payload["claim_semantic_attestation"] = _valid_receipt(
        attestation_result="overstated"
    )

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert OVERSTATED_CODE in out["report_only_reasons"]


def test_unclear_semantic_attestation_reports_without_blocking() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = True
    payload["claim_semantic_attestation"] = _valid_receipt(attestation_result="unclear")

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert UNCLEAR_CODE in out["report_only_reasons"]


def test_aligned_semantic_attestation_payload_reports_no_warning() -> None:
    payload = _markerless_payload()
    payload["semantic_review_claimed"] = True
    payload["claim_semantic_attestation"] = _valid_receipt()

    out = evaluate(payload)

    assert out["semantic_drift_risk"] is False
    assert out["enforcement_action"] == "allow"
    assert out["report_only_reasons"] == []
