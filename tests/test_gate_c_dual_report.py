import hashlib
import json
from pathlib import Path

from governance_tools.gate_c_dual_report import generate_dual_report


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dual_report_preserves_canonical_and_exposes_required_counts(tmp_path: Path) -> None:
    project_root = tmp_path
    status = project_root / "docs" / "status"
    review_log = status / "gate-c-review-log.ndjson"
    rework_log = status / "gate-c-rework-log.ndjson"
    stability_log = status / "gate-c-stability-log.ndjson"

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
            "lane": "claude",
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
        }
    ]
    stability_rows = [
        {
            "window_id": "gate-c-window-2026-05-11",
            "lane": "copilot",
            "run_id": "run-1",
            "integration_stability": "stable",
            "stability_note": "ok",
        }
    ]

    _write_ndjson(review_log, review_rows)
    _write_ndjson(rework_log, rework_rows)
    _write_ndjson(stability_log, stability_rows)

    before_hash = _sha256(review_log)
    result = generate_dual_report(project_root=project_root, window_id="gate-c-window-2026-05-11")
    after_hash = _sha256(review_log)

    # canonical surface unchanged
    assert before_hash == after_hash

    # decision-set includes only valid review rows
    decision_review_path = Path(result.decision_review_log_path)
    decision_rows = [json.loads(line) for line in decision_review_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(decision_rows) == 1
    assert decision_rows[0]["lane"] == "copilot"

    # filtered reasons + required count fields exposed
    manifest = json.loads(Path(result.decision_manifest_path).read_text(encoding="utf-8"))
    assert "filtered_reason_counts" in manifest
    assert "canonical_count" in manifest
    assert "decision_count" in manifest
    assert manifest["filtered_reason_counts"]["missing_or_invalid_review_start"] == 1

    canonical_report_text = Path(result.canonical_report_path).read_text(encoding="utf-8")
    assert "canonical_count" in canonical_report_text
    assert "decision_count" in canonical_report_text
    assert "filtered_reason_counts" in canonical_report_text
