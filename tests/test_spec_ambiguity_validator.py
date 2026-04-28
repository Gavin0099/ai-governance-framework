from __future__ import annotations

from validators.spec_ambiguity_validator import evaluate_spec_ambiguity


def test_flags_empty_spec_as_high_severity():
    result = evaluate_spec_ambiguity("")

    assert result["ok"] is False
    assert result["severity"] == "high"
    assert result["requires_human_clarification"] is True
    assert "empty_spec_text" in result["findings"]


def test_flags_ambiguous_language_without_acceptance_signal():
    text = "Implement behavior as needed with best effort. TBD details."
    result = evaluate_spec_ambiguity(text)

    assert result["ok"] is False
    assert result["requires_human_clarification"] is True
    assert "ambiguous_token_present" in result["findings"]
    assert "missing_acceptance_criteria_signal" in result["findings"]


def test_passes_when_spec_has_acceptance_and_numeric_constraints():
    text = (
        "The system shall return status code 200 within 2 seconds. "
        "Acceptance criteria: pass if response payload includes request_id."
    )
    result = evaluate_spec_ambiguity(text, title="API latency requirement")

    assert result["ok"] is True
    assert result["requires_human_clarification"] is False
    assert result["title"] == "API latency requirement"
    assert result["signals"]["has_acceptance_criteria_signal"] is True
    assert result["signals"]["has_numeric_constraint"] is True
