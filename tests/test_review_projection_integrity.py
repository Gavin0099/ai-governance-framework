from __future__ import annotations

import json
from pathlib import Path

from scripts.build_review_projection import build_projection


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8")


def test_partial_not_rewritten_as_mostly_complete(tmp_path: Path) -> None:
    _write_ndjson(
        tmp_path / "artifacts" / "session-index.ndjson",
        [
            {"session_id": "s1", "closeout_status": "missing"},
            {"session_id": "s2", "closeout_status": "valid"},
        ],
    )
    summary, _ = build_projection(tmp_path)
    assert summary["runtime_completeness"] == "PARTIAL"
    assert summary["integrity_status"] == "PARTIAL"


def test_unverified_or_missing_signal_not_low_risk(tmp_path: Path) -> None:
    _write_ndjson(
        tmp_path / "artifacts" / "session-index.ndjson",
        [{"session_id": "s1", "closeout_status": "valid"}],
    )
    summary, _ = build_projection(tmp_path)
    claim = next(s for s in summary["signals"] if s["id"] == "claim_drift_detected")
    assert claim["epistemic_status"] == "MISSING"
    assert claim["severity"] in {"high", "medium"}


def test_no_overall_health_synthesis_field(tmp_path: Path) -> None:
    _write_ndjson(
        tmp_path / "artifacts" / "session-index.ndjson",
        [{"session_id": "s1", "closeout_status": "valid"}],
    )
    summary, _ = build_projection(tmp_path)
    assert "overall_system_health" not in summary
    assert "deployment_ready" not in summary
    assert "operationally_safe" not in summary


def test_coverage_incomplete_is_visible(tmp_path: Path) -> None:
    _write_ndjson(
        tmp_path / "artifacts" / "session-index.ndjson",
        [{"session_id": "s1", "closeout_status": "valid"}],
    )
    summary, sections = build_projection(tmp_path)
    assert summary["coverage_complete"] is False
    assert summary["omitted_sections_count"] >= 1
    assert "retrieval_authority_advisory" in summary["omitted_section_categories"]
    assert sections["coverage_complete"] is False


def test_high_severity_section_not_collapsed(tmp_path: Path) -> None:
    _write_ndjson(
        tmp_path / "artifacts" / "session-index.ndjson",
        [{"session_id": "s1", "closeout_status": "missing"}],
    )
    _, sections = build_projection(tmp_path)
    runtime = next(s for s in sections["sections"] if s["id"] == "runtime")
    assert runtime["severity"] == "high"
    assert runtime["collapsed"] is False

