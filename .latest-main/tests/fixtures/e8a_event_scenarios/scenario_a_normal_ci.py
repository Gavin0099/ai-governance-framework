"""
Scenario A: Normal CI Flow (健康流)

t1: artifact absent, no skip  → signal=True  (test_result_artifact_absent)
t2: artifact created (CI ran)  → signal=False (footprint present)
t3: artifact present, stale   → signal=False (key still present — stale is ok)

Purpose: baseline for a repo that actually runs CI.
Expected signal_ratio over these 3 steps = 1/3 ≈ 0.33
"""
from __future__ import annotations

from tests.fixtures.e8a_event_scenarios.base import EventStep, validate_monotonic_timeline

_CANONICAL_JSON = """{
  "test_run_id": "run-a",
  "failure_disposition": null,
  "summary": {"total": 5, "passed": 5, "failed": 0}
}"""

_STALE_JSON = """{
  "test_run_id": "run-a-stale",
  "failure_disposition": null,
  "summary": {"total": 5, "passed": 5, "failed": 0}
}"""

STEPS: list[EventStep] = [
    EventStep(
        scenario="a_normal_ci",
        t=1,
        action="delete",          # artifact does not exist yet
        artifact_exists=False,
        skip_test_result_check=False,
        expected_signal=True,
        description="CI has not run; artifact absent — signal expected",
    ),
    EventStep(
        scenario="a_normal_ci",
        t=2,
        action="create",          # CI completed, artifact written
        artifact_exists=True,
        content=_CANONICAL_JSON,
        skip_test_result_check=False,
        expected_signal=False,
        description="CI ran; canonical artifact present — no signal",
    ),
    EventStep(
        scenario="a_normal_ci",
        t=3,
        action="touch",           # artifact exists but content updated (stale touch)
        artifact_exists=True,
        content=_STALE_JSON,
        skip_test_result_check=False,
        expected_signal=False,
        description="Artifact still present after touch — no signal",
    ),
]

validate_monotonic_timeline(STEPS)
