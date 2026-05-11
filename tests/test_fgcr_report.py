import json
from pathlib import Path

from governance_tools.fgcr_report import build_fgcr_report


def test_fgcr_insufficient_sample_when_marked_lt_3() -> None:
    events = [
        {
            "event_id": "e-1",
            "window_id": "w-1",
            "lane": "chatgpt",
            "confidence_mark": "PASS",
            "later_failure_type": "hidden_omission",
            "discovery_scope": "same_window",
            "artifact_anchor": "a1",
            "evidence_layer": "run_observed",
        },
        {
            "event_id": "e-2",
            "window_id": "w-1",
            "lane": "chatgpt",
            "confidence_mark": "READY",
            "later_failure_type": "invalid_projection",
            "discovery_scope": "same_window",
            "artifact_anchor": "a2",
            "evidence_layer": "run_observed",
        },
    ]
    r = build_fgcr_report(events, "w-1", min_sample=3)
    assert r["by_window"]["status"] == "insufficient_sample"
    assert r["by_window"]["fgcr"] is None


def test_hypothesis_events_not_in_numerator() -> None:
    events = [
        {
            "event_id": "e-1",
            "window_id": "w-1",
            "lane": "claude",
            "confidence_mark": "PASS",
            "later_failure_type": "hidden_omission",
            "discovery_scope": "same_window",
            "artifact_anchor": "a1",
            "evidence_layer": "hypothesis",
        },
        {
            "event_id": "e-2",
            "window_id": "w-1",
            "lane": "claude",
            "confidence_mark": "READY",
            "later_failure_type": "invalid_projection",
            "discovery_scope": "same_window",
            "artifact_anchor": "a2",
            "evidence_layer": "framework_supported",
        },
        {
            "event_id": "e-3",
            "window_id": "w-1",
            "lane": "claude",
            "confidence_mark": "SAFE",
            "later_failure_type": "stale_evidence_dependency",
            "discovery_scope": "next_window",
            "artifact_anchor": "a3",
            "evidence_layer": "run_observed",
        },
    ]
    r = build_fgcr_report(events, "w-1", min_sample=3)
    assert r["by_lane"]["claude"]["status"] == "ok"
    assert r["by_lane"]["claude"]["confidence_marked_events"] == 3
    assert r["by_lane"]["claude"]["false_confidence_events"] == 2
    assert r["by_lane"]["claude"]["fgcr"] == 0.666667


def test_by_failure_type_and_by_lane_counts() -> None:
    events = [
        {
            "event_id": "e-1",
            "window_id": "w-9",
            "lane": "chatgpt",
            "confidence_mark": "PASS",
            "later_failure_type": "hidden_omission",
            "discovery_scope": "same_window",
            "artifact_anchor": "a1",
            "evidence_layer": "framework_supported",
        },
        {
            "event_id": "e-2",
            "window_id": "w-9",
            "lane": "copilot",
            "confidence_mark": "READY",
            "later_failure_type": "unauthorized_inference",
            "discovery_scope": "next_window",
            "artifact_anchor": "a2",
            "evidence_layer": "run_observed",
        },
        {
            "event_id": "e-3",
            "window_id": "w-9",
            "lane": "copilot",
            "confidence_mark": "SAFE",
            "later_failure_type": "unauthorized_inference",
            "discovery_scope": "next_window",
            "artifact_anchor": "a3",
            "evidence_layer": "run_observed",
        },
    ]
    r = build_fgcr_report(events, "w-9", min_sample=1)
    assert r["by_window"]["by_failure_type"]["unauthorized_inference"] == 2
    assert r["by_lane"]["copilot"]["by_failure_type"]["unauthorized_inference"] == 2
    assert r["by_lane"]["chatgpt"]["by_failure_type"]["hidden_omission"] == 1

