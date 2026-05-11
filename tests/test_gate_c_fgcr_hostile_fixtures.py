import json
from pathlib import Path

from governance_tools.fgcr_report import build_fgcr_report
from governance_tools.gate_c_dual_report import generate_dual_report


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_hostile_gate_c_and_fgcr_boundaries(tmp_path: Path) -> None:
    project_root = tmp_path
    status = project_root / "docs" / "status"
    review_log = status / "gate-c-review-log.ndjson"
    rework_log = status / "gate-c-rework-log.ndjson"
    stability_log = status / "gate-c-stability-log.ndjson"
    fgcr_events = status / "fgcr-events.ndjson"

    # hostile gate-c review rows:
    # - one valid row
    # - one missing timestamp row (should be filtered, not deleted from canonical)
    # - one reconstructed/no timestamp row (same behavior as above)
    review_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-valid",
            "review_start_utc": "2026-05-11T01:00:00Z",
            "review_end_utc": "2026-05-11T01:10:00Z",
            "review_minutes": 10,
        },
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "claude",
            "run_id": "run-missing-ts",
            "review_start_utc": None,
            "review_end_utc": "2026-05-11T01:12:00Z",
            "review_minutes": None,
            "capture_mode": "missing_timestamp",
        },
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "chatgpt",
            "run_id": "run-reconstructed",
            "review_start_utc": None,
            "review_end_utc": None,
            "review_minutes": None,
            "capture_mode": "reconstructed_no_timestamp",
        },
    ]
    rework_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-valid",
            "reopen_count": 0,
            "revert_count": 0,
            "total_changes": 1,
            "reopen_revert_rate": 0.0,
        }
    ]
    stability_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-valid",
            "integration_stability": "stable",
            "stability_note": "ok",
        }
    ]
    _write_ndjson(review_log, review_rows)
    _write_ndjson(rework_log, rework_rows)
    _write_ndjson(stability_log, stability_rows)

    # FGCR hostile sample:
    # - 2 marked events only => insufficient_sample
    # - 1 hypothesis event should not enter numerator
    fgcr_rows = [
        {
            "event_id": "fg-1",
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "confidence_mark": "PASS",
            "later_failure_type": "hidden_omission",
            "discovery_scope": "same_window",
            "artifact_anchor": "a1",
            "evidence_layer": "hypothesis",
        },
        {
            "event_id": "fg-2",
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "confidence_mark": "READY",
            "later_failure_type": "invalid_projection",
            "discovery_scope": "same_window",
            "artifact_anchor": "a2",
            "evidence_layer": "run_observed",
        },
    ]
    _write_ndjson(fgcr_events, fgcr_rows)

    result = generate_dual_report(
        project_root=project_root,
        window_id="gate-c-window-2026-05-11",
        fgcr_events=fgcr_events,
    )

    # 1) missing timestamp -> filtered_reason_counts increases
    manifest = json.loads(Path(result.decision_manifest_path).read_text(encoding="utf-8"))
    assert manifest["filtered_reason_counts"]["missing_or_invalid_review_start"] == 2

    # 2) reconstructed row not in decision-set, still in canonical
    decision_rows = [
        json.loads(line)
        for line in Path(result.decision_review_log_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(decision_rows) == 1
    assert decision_rows[0]["run_id"] == "run-valid"
    canonical_report = Path(result.canonical_report_path).read_text(encoding="utf-8")
    assert "canonical_count" in canonical_report

    # 3) hypothesis FGCR event not in numerator
    fgcr_summary = json.loads(Path(result.fgcr_summary_path).read_text(encoding="utf-8"))
    assert fgcr_summary["by_window"]["confidence_marked_events"] == 2
    assert fgcr_summary["by_window"]["false_confidence_events"] == 1

    # 4) insufficient_sample -> no percentage in report
    assert fgcr_summary["by_window"]["status"] == "insufficient_sample"
    assert fgcr_summary["by_window"]["fgcr"] is None
    assert "fgcr:" not in canonical_report

    # 5) valid rows only -> decision_count correct
    assert manifest["decision_count"]["review"]["copilot"] == 1
    assert manifest["decision_count"]["review"]["claude"] == 0
    assert manifest["decision_count"]["review"]["chatgpt"] == 0
