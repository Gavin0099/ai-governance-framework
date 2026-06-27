from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime_hooks.core._canonical_closeout import build_canonical_closeout


@dataclass(frozen=True)
class CloseoutFailClosedEvaluation:
    completed: bool
    closeout_status: str
    failure_reason: str | None


@dataclass(frozen=True)
class FailClosedRegressionResult:
    fixture: str
    expected: str
    actual: str
    status: str
    failure_reason: str | None = None


def evaluate_canonical_closeout_fail_closed(
    *,
    candidate_payload: dict[str, Any] | None,
    existing_artifacts: frozenset[str] = frozenset(),
    runtime_signals: dict[str, Any] | None = None,
) -> CloseoutFailClosedEvaluation:
    """Evaluate canonical closeout fail-closed behavior for supplied inputs."""
    canonical = build_canonical_closeout(
        session_id="fail-closed-regression",
        closed_at="2026-06-27T00:00:00+00:00",
        candidate_payload=candidate_payload,
        existing_artifacts=existing_artifacts,
        runtime_signals=runtime_signals or {},
    )
    closeout_status = str(canonical.get("closeout_status", "missing"))
    completed = closeout_status == "valid"
    return CloseoutFailClosedEvaluation(
        completed=completed,
        closeout_status=closeout_status,
        failure_reason=None if completed else f"canonical_closeout_{closeout_status}",
    )


def run_fail_closed_regression_check(
    *,
    fixture: str,
    candidate_payload: dict[str, Any] | None,
    expected: str,
    existing_artifacts: frozenset[str] = frozenset(),
    runtime_signals: dict[str, Any] | None = None,
) -> FailClosedRegressionResult:
    if expected not in {"pass", "fail"}:
        raise ValueError(f"unsupported expected result: {expected}")

    evaluation = evaluate_canonical_closeout_fail_closed(
        candidate_payload=candidate_payload,
        existing_artifacts=existing_artifacts,
        runtime_signals=runtime_signals,
    )
    actual = "pass" if evaluation.completed else "fail"

    if expected == "fail" and actual == "pass":
        return FailClosedRegressionResult(
            fixture=fixture,
            expected=expected,
            actual=actual,
            status="violation",
            failure_reason="fail_closed_regression_violation",
        )
    if expected == "fail" and actual == "fail":
        return FailClosedRegressionResult(
            fixture=fixture,
            expected=expected,
            actual=actual,
            status="protected",
            failure_reason=evaluation.failure_reason,
        )
    if expected == "pass" and actual == "pass":
        return FailClosedRegressionResult(
            fixture=fixture,
            expected=expected,
            actual=actual,
            status="ok",
        )

    return FailClosedRegressionResult(
        fixture=fixture,
        expected=expected,
        actual=actual,
        status="false_block",
        failure_reason=evaluation.failure_reason,
    )
