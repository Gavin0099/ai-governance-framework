"""
Scenario B: Broken Pipeline (壞掉的 CI)

t1: artifact present, canonical key present  → signal=False  (healthy)
t2: artifact deleted (pipeline broken)       → signal=True   (test_result_artifact_absent)
t3: artifact still missing (not recovered)   → signal=True   (sustained absence)

Purpose: verify that sustained artifact absence produces sustained signal.
Expected signal_ratio over these 3 steps = 2/3 ≈ 0.67

Note on t2 vs t3 deduplication:
  t2 and t3 have the same artifact_exists=False and content_hash.
  BUT their mtime_floor will differ because t3 is run at a later wall-clock
  time.  The runner must ensure t3 is invoked >= 1 second after t2 so
  mtime_floor changes.  If they share the same mtime_floor (same second),
  state_hash is equal and effective_entries drops to 2, making
  signal_ratio = 1/2 = 0.5 — still clearly elevated.
"""
from __future__ import annotations

from tests.fixtures.e8a_event_scenarios.base import EventStep, validate_monotonic_timeline

_HEALTHY_JSON = """{
  "test_run_id": "run-b-initial",
  "failure_disposition": null,
  "summary": {"total": 10, "passed": 10, "failed": 0}
}"""

STEPS: list[EventStep] = [
    EventStep(
        scenario="b_broken_pipeline",
        t=1,
        action="create",
        artifact_exists=True,
        content=_HEALTHY_JSON,
        skip_test_result_check=False,
        expected_signal=False,
        description="Healthy state: artifact present with canonical key",
    ),
    EventStep(
        scenario="b_broken_pipeline",
        t=2,
        action="delete",
        artifact_exists=False,
        skip_test_result_check=False,
        expected_signal=True,
        description="Pipeline broken: artifact deleted — signal expected",
    ),
    EventStep(
        scenario="b_broken_pipeline",
        t=3,
        action="noop",         # nothing changes; artifact still missing
        artifact_exists=False,
        skip_test_result_check=False,
        expected_signal=True,
        description="Pipeline still broken: sustained absence — signal expected",
    ),
]

validate_monotonic_timeline(STEPS)
