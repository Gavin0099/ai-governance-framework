"""
Scenario C: Skip Abuse (濫用 skip)

t1: artifact missing, no skip          → signal=True  (test_result_artifact_absent)
t2: artifact missing, skip=True added  → signal=False (suppressed by skip)
t3: artifact missing, skip=True still  → signal=False (still suppressed)

Purpose: demonstrate that skip suppression is observable in the event log.
This scenario does NOT decide whether skip is legitimate — it records the
suppression pattern so a future skip-audit mechanism can query:
  "how many consecutive steps have skip=True AND artifact_exists=False?"

Expected signal_ratio over these 3 steps = 1/3 ≈ 0.33

Skip abuse detection (future):
  From this event log an auditor can detect: *all* steps after t2 have
  skip=True with no artifact, which looks structurally identical to
  a repo that genuinely has no test pipeline.  Distinguishing them requires
  cross-referencing with CI configuration — outside E8a scope, but traceable.
"""
from __future__ import annotations

from tests.fixtures.e8a_event_scenarios.base import EventStep, validate_monotonic_timeline

STEPS: list[EventStep] = [
    EventStep(
        scenario="c_skip_abuse",
        t=1,
        action="delete",
        artifact_exists=False,
        skip_test_result_check=False,
        expected_signal=True,
        description="Artifact missing, no skip declared — signal expected",
    ),
    EventStep(
        scenario="c_skip_abuse",
        t=2,
        action="noop",            # artifact still missing; skip added to policy
        artifact_exists=False,
        skip_test_result_check=True,
        expected_signal=False,
        description="skip=True added; absence now suppressed — no signal",
    ),
    EventStep(
        scenario="c_skip_abuse",
        t=3,
        action="noop",            # unchanged; skip still present
        artifact_exists=False,
        skip_test_result_check=True,
        expected_signal=False,
        description="skip=True still active; sustained suppression — no signal",
    ),
]

validate_monotonic_timeline(STEPS)
