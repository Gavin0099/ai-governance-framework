from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.gate_c_report import evaluate_gate_c_window


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_gate_c_report" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_gate_c_passes_with_complete_window_evidence():
    root = _tmp_dir("pass")
    _write_ndjson(
        root / "docs" / "status" / "gate-c-review-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": f"run-{index:03d}",
                "review_start_utc": f"2026-05-11T10:{index:02d}:00+00:00",
                "review_end_utc": f"2026-05-11T10:{index + 10:02d}:00+00:00",
                "review_minutes": 10.0,
                "review_decision": "accept" if index < 9 else "accept_with_note",
            }
            for index in range(10)
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-rework-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "reopen_count": 0,
                "revert_count": 0,
                "total_changes": 10,
                "reopen_revert_rate": 0.0,
            }
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-stability-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "integration_stability": "stable",
                "stability_note": "No incidents in the window.",
            }
        ],
    )

    report = evaluate_gate_c_window(root, window_id="gate-c-window-2026-05-11")
    copilot = next(item for item in report.lane_reports if item.lane == "copilot")

    assert copilot.gate_c_result == "pass"
    assert copilot.review_effort["avg_review_minutes"] == 10.0
    assert copilot.review_effort["median_review_minutes"] == 10.0
    assert copilot.review_effort["p90_review_minutes"] == 10.0
    assert copilot.review_effort["valid_review_timing_count"] == 10
    assert copilot.quality_rework["reopen_revert_rate"] == 0.0


def test_gate_c_is_provisional_when_evidence_is_missing():
    root = _tmp_dir("provisional")
    _write_ndjson(root / "docs" / "status" / "gate-c-review-log.ndjson", [])
    _write_ndjson(root / "docs" / "status" / "gate-c-rework-log.ndjson", [])
    _write_ndjson(root / "docs" / "status" / "gate-c-stability-log.ndjson", [])

    report = evaluate_gate_c_window(root, window_id="gate-c-window-2026-05-11")
    copilot = next(item for item in report.lane_reports if item.lane == "copilot")

    assert copilot.gate_c_result == "provisional-pass"
    assert "review log entries missing" in copilot.evidence_gaps
    assert "stability log entry missing" in copilot.evidence_gaps
    assert "reopen/revert denominator missing" in copilot.evidence_gaps


def test_gate_c_pauses_when_lane_is_unstable():
    root = _tmp_dir("pause")
    _write_ndjson(
        root / "docs" / "status" / "gate-c-review-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": f"run-{index:03d}",
                "review_start_utc": "2026-05-11T10:00:00+00:00",
                "review_end_utc": "2026-05-11T10:08:00+00:00",
                "review_minutes": 8.0,
                "review_decision": "accept",
            }
            for index in range(10)
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-rework-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "reopen_count": 1,
                "revert_count": 0,
                "total_changes": 10,
                "reopen_revert_rate": 0.1,
            }
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-stability-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "integration_stability": "degraded",
                "stability_note": "Integration degraded during the observation window.",
            }
        ],
    )

    report = evaluate_gate_c_window(root, window_id="gate-c-window-2026-05-11")
    copilot = next(item for item in report.lane_reports if item.lane == "copilot")

    assert copilot.gate_c_result == "pause"
    assert copilot.integration_stability["integration_stability"] == "degraded"


def test_gate_c_is_provisional_when_review_sample_is_below_threshold():
    root = _tmp_dir("below_threshold")
    _write_ndjson(
        root / "docs" / "status" / "gate-c-review-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": f"run-{index:03d}",
                "review_start_utc": "2026-05-11T10:00:00+00:00",
                "review_end_utc": "2026-05-11T10:05:00+00:00",
                "review_minutes": 5.0,
                "review_decision": "accept",
            }
            for index in range(5)
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-rework-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "reopen_count": 0,
                "revert_count": 0,
                "total_changes": 5,
                "reopen_revert_rate": 0.0,
            }
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-stability-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "integration_stability": "stable",
                "stability_note": "Stable but insufficient review sample.",
            }
        ],
    )

    report = evaluate_gate_c_window(root, window_id="gate-c-window-2026-05-11")
    copilot = next(item for item in report.lane_reports if item.lane == "copilot")

    assert copilot.gate_c_result == "provisional-pass"
    assert "valid review timing count below 10" in copilot.evidence_gaps


def test_gate_c_is_provisional_when_rework_rate_is_invalid():
    root = _tmp_dir("bad_rework")
    _write_ndjson(
        root / "docs" / "status" / "gate-c-review-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": f"run-{index:03d}",
                "review_start_utc": "2026-05-11T10:00:00+00:00",
                "review_end_utc": "2026-05-11T10:05:00+00:00",
                "review_minutes": 5.0,
                "review_decision": "accept",
            }
            for index in range(10)
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-rework-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "reopen_count": 1,
                "revert_count": 1,
                "total_changes": 10,
                "reopen_revert_rate": 0.1,
            }
        ],
    )
    _write_ndjson(
        root / "docs" / "status" / "gate-c-stability-log.ndjson",
        [
            {
                "window_id": "gate-c-window-2026-05-11",
                "lane": "copilot",
                "run_id": "window-rollup",
                "integration_stability": "stable",
                "stability_note": "Stable but rework math is wrong.",
            }
        ],
    )

    report = evaluate_gate_c_window(root, window_id="gate-c-window-2026-05-11")
    copilot = next(item for item in report.lane_reports if item.lane == "copilot")

    assert copilot.gate_c_result == "provisional-pass"
    assert "some rework rows have invalid denominator or rate" in copilot.evidence_gaps