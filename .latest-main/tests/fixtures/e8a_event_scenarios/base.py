"""
tests/fixtures/e8a_event_scenarios/base.py
------------------------------------------
Base types and helpers for E8a event-based lifecycle fixtures.

Design contract (釘住)
----------------------
An "event" is defined as: (artifact state + action) that changes the observable
world, uniquely identified and replayable.

event_id  = sha1(repo + scenario + str(t) + state_hash)
state_hash = sha1(str(exists) + content_hash + str(mtime_floor))

Deduplication invariant:
  Two consecutive steps with the same state_hash → same event, second is a
  noop from the measurement perspective.  effective_entries counts DISTINCT
  event_ids only.

Entropy:
  entropy = count(distinct state_hash values) / len(all steps)
  If entropy < MIN_VALID_ENTROPY the dataset is considered invalid for E1b.

These are data-structure and computation helpers only.
IO (create/delete/touch) and hook invocation live in run_e8a_fixture.py.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Minimum entropy ratio below which the event dataset is invalid for E1b.
MIN_VALID_ENTROPY = 0.3

Action = Literal["create", "delete", "touch", "noop"]
Scenario = Literal["a_normal_ci", "b_broken_pipeline", "c_skip_abuse"]


@dataclass(frozen=True)
class EventStep:
    """
    One time-step in a lifecycle scenario.

    Fields
    ------
    scenario        : scenario identifier (used in event_id)
    t               : strictly increasing integer; monotonic timeline enforced
                      by the scenario constructors
    action          : what happens to the artifact at this step
    artifact_exists : expected artifact existence AFTER the action
    content         : artifact file content (used for content_hash); ignored
                      when artifact_exists=False
    skip_test_result_check : gate_policy value for this step
    expected_signal : whether a canonical path signal is expected this step
    description     : human-readable note for reports
    """

    scenario: Scenario
    t: int
    action: Action
    artifact_exists: bool
    content: str = ""
    skip_test_result_check: bool = False
    expected_signal: bool = False
    description: str = ""

    def content_hash(self) -> str:
        """SHA-1 of artifact content (empty string if no artifact)."""
        data = self.content if self.artifact_exists else ""
        return hashlib.sha1(data.encode()).hexdigest()

    def state_hash(self, mtime_floor: int = 0) -> str:
        """
        SHA-1 of (exists, content_hash, mtime_floor).
        mtime_floor is Unix timestamp truncated to seconds to avoid sub-second
        filesystem noise.  Pass 0 when artifact does not exist.
        """
        raw = f"{self.artifact_exists}|{self.content_hash()}|{mtime_floor}"
        return hashlib.sha1(raw.encode()).hexdigest()

    def event_id(self, repo: str, mtime_floor: int = 0) -> str:
        """
        Stable, unique identifier for this (repo, scenario, t, state) tuple.
        Deterministic: same inputs always produce same event_id.
        """
        raw = f"{repo}|{self.scenario}|{self.t}|{self.state_hash(mtime_floor)}"
        return hashlib.sha1(raw.encode()).hexdigest()


# ── Entropy calculation ────────────────────────────────────────────────────────

def compute_entropy(state_hashes: list[str]) -> float:
    """
    Ratio of distinct state hashes to total steps.
    Range [0, 1].  0 = all identical states (useless).  1 = all distinct.
    """
    if not state_hashes:
        return 0.0
    return len(set(state_hashes)) / len(state_hashes)


def compute_effective_entries(event_ids: list[str]) -> int:
    """Count of unique event_ids (deduplicated)."""
    return len(set(event_ids))


def compute_signal_ratio(steps_with_signal: int, effective_entries: int) -> float:
    """signal_ratio = steps_with_signal / effective_entries."""
    if effective_entries == 0:
        return 0.0
    return round(steps_with_signal / effective_entries, 4)


def validate_monotonic_timeline(steps: list[EventStep]) -> None:
    """Raise ValueError if t values are not strictly increasing."""
    for i in range(1, len(steps)):
        if steps[i].t <= steps[i - 1].t:
            raise ValueError(
                f"Timeline not monotonic at index {i}: "
                f"t={steps[i].t} <= previous t={steps[i-1].t}"
            )
