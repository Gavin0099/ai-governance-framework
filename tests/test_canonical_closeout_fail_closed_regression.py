import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.canonical_closeout_fail_closed_regression import (
    evaluate_canonical_closeout_fail_closed,
    run_fail_closed_regression_check,
)


VALID_CANDIDATE = {
    "task_intent": "add fail-closed regression coverage",
    "work_summary": "implemented canonical closeout fail-closed regression helper",
    "tools_used": ["pytest"],
    "artifacts_referenced": [],
    "open_risks": [],
}


def test_valid_canonical_closeout_can_complete():
    result = evaluate_canonical_closeout_fail_closed(
        candidate_payload=VALID_CANDIDATE,
        runtime_signals={"tools_executed": ["pytest"]},
    )

    assert result.completed is True
    assert result.closeout_status == "valid"
    assert result.failure_reason is None


def test_missing_canonical_closeout_fails_closed():
    result = evaluate_canonical_closeout_fail_closed(candidate_payload=None)

    assert result.completed is False
    assert result.closeout_status == "missing"
    assert result.failure_reason == "canonical_closeout_missing"


def test_malformed_canonical_closeout_fails_closed():
    result = evaluate_canonical_closeout_fail_closed(
        candidate_payload={"task_intent": "only one field"}
    )

    assert result.completed is False
    assert result.closeout_status == "schema_invalid"
    assert result.failure_reason == "canonical_closeout_schema_invalid"


def test_expected_fail_actual_fail_is_protected():
    result = run_fail_closed_regression_check(
        fixture="missing_closeout",
        candidate_payload=None,
        expected="fail",
    )

    assert result.status == "protected"
    assert result.expected == "fail"
    assert result.actual == "fail"
    assert result.failure_reason == "canonical_closeout_missing"


def test_expected_pass_actual_pass_is_ok():
    result = run_fail_closed_regression_check(
        fixture="valid_closeout",
        candidate_payload=VALID_CANDIDATE,
        expected="pass",
        runtime_signals={"tools_executed": ["pytest"]},
    )

    assert result.status == "ok"
    assert result.expected == "pass"
    assert result.actual == "pass"
    assert result.failure_reason is None


def test_expected_pass_actual_fail_is_false_block():
    result = run_fail_closed_regression_check(
        fixture="valid_shape_missing_runtime_signal",
        candidate_payload=VALID_CANDIDATE,
        expected="pass",
    )

    assert result.status == "false_block"
    assert result.expected == "pass"
    assert result.actual == "fail"
    assert result.failure_reason == "canonical_closeout_inconsistent"


def test_unsupported_expected_result_is_rejected():
    try:
        run_fail_closed_regression_check(
            fixture="invalid_expectation",
            candidate_payload=None,
            expected="maybe",
        )
    except ValueError as exc:
        assert "unsupported expected result" in str(exc)
    else:
        raise AssertionError("expected ValueError")
