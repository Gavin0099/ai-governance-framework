from pathlib import Path

from governance_tools.gate_c_decision_set_builder import build_decision_set


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            import json

            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_build_decision_set_filters_invalid_rows(tmp_path: Path) -> None:
    project_root = tmp_path
    status = project_root / "docs" / "status"

    review_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-1",
            "review_start_utc": "2026-05-11T01:00:00Z",
            "review_end_utc": "2026-05-11T01:10:00Z",
            "review_minutes": 10,
        },
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-2",
            "review_start_utc": None,
            "review_end_utc": "2026-05-11T01:12:00Z",
            "review_minutes": None,
        },
    ]
    rework_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-1",
            "reopen_count": 0,
            "revert_count": 0,
            "total_changes": 1,
            "reopen_revert_rate": 0.0,
        },
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "claude",
            "run_id": "run-9",
            "reopen_count": 0,
            "revert_count": 0,
            "total_changes": 0,
            "reopen_revert_rate": None,
        },
    ]
    stability_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-1",
            "integration_stability": "stable",
            "stability_note": "ok",
        },
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "chatgpt",
            "run_id": "run-5",
            "integration_stability": "unknown",
            "stability_note": "",
        },
    ]

    _write_ndjson(status / "gate-c-review-log.ndjson", review_rows)
    _write_ndjson(status / "gate-c-rework-log.ndjson", rework_rows)
    _write_ndjson(status / "gate-c-stability-log.ndjson", stability_rows)

    result = build_decision_set(project_root=project_root, window_id="gate-c-window-2026-05-11")

    assert result.decision_review_count["copilot"] == 1
    assert result.decision_rework_count["copilot"] == 1
    assert result.decision_stability_count["copilot"] == 1
    assert result.filtered_reason_counts["missing_or_invalid_review_start"] == 1
    assert result.filtered_reason_counts["missing_rework_denominator"] == 1
    assert result.filtered_reason_counts["unknown_stability_state"] == 1

    assert Path(result.output_manifest_path).exists()
    assert Path(result.output_report_path).exists()
    assert Path(result.output_review_log_path).exists()
