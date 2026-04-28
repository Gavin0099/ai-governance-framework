from __future__ import annotations

from pathlib import Path

from governance_tools.framework_risk_signal import read_risk_signal, write_risk_signal
from governance_tools.runtime_enforcement_feedback import (
    build_feedback_record,
    read_feedback_history,
    record_feedback,
    summarize_feedback_trend,
)


def test_build_feedback_record_keeps_metric_boundary_explicit() -> None:
    record = build_feedback_record(mode="enforce", smoke_status="pass", pytest_status="fail")
    assert record["quality_metrics"]["score"] == 2
    assert record["workflow_metrics"]["score"] is None
    assert record["workflow_metrics"]["status"] == "not_measured"
    assert record["system_risk"]["derived_from"] == "quality_trend_only"


def test_summarize_feedback_trend_requires_multiple_samples() -> None:
    records = [
        build_feedback_record(mode="enforce", smoke_status="fail", pytest_status="skipped"),
        build_feedback_record(mode="enforce", smoke_status="fail", pytest_status="skipped"),
    ]
    trend = summarize_feedback_trend(records)
    assert trend["sample_count"] == 2
    assert trend["threshold_state"] == "insufficient_data"


def test_record_feedback_writes_advisory_signal_for_sustained_quality_degradation(tmp_path: Path) -> None:
    for _ in range(3):
        result = record_feedback(
            tmp_path,
            mode="enforce",
            smoke_status="fail",
            pytest_status="skipped",
            emit_risk_signal=True,
        )
    signal = read_risk_signal(tmp_path)
    assert result["trend"]["average_quality_score"] == 4.0
    assert result["trend"]["threshold_state"] == "advisory"
    assert signal is not None
    assert signal["source"] == "runtime_enforcement_feedback"
    assert signal["severity"] == "warning"
    assert signal["affected_components"] == ["runtime_enforcement_quality_trend"]


def test_record_feedback_clears_only_its_own_signal_when_trend_recovers(tmp_path: Path) -> None:
    for _ in range(3):
        record_feedback(
            tmp_path,
            mode="enforce",
            smoke_status="fail",
            pytest_status="skipped",
            emit_risk_signal=True,
        )
    assert read_risk_signal(tmp_path) is not None

    for _ in range(3):
        result = record_feedback(
            tmp_path,
            mode="enforce",
            smoke_status="pass",
            pytest_status="pass",
            emit_risk_signal=True,
        )
    assert result["trend"]["threshold_state"] == "ok"
    assert read_risk_signal(tmp_path) is None


def test_record_feedback_does_not_clear_foreign_signal(tmp_path: Path) -> None:
    write_risk_signal(
        tmp_path,
        affected_components=["drift_baseline_integrity"],
        severity="critical",
        source="governance_drift_checker",
    )
    result = record_feedback(
        tmp_path,
        mode="enforce",
        smoke_status="pass",
        pytest_status="pass",
        emit_risk_signal=True,
    )
    assert result["signal_cleared"] is False
    signal = read_risk_signal(tmp_path)
    assert signal is not None
    assert signal["source"] == "governance_drift_checker"


def test_read_feedback_history_filters_to_recent_window(tmp_path: Path) -> None:
    record_feedback(
        tmp_path,
        mode="enforce",
        smoke_status="pass",
        pytest_status="pass",
        emit_risk_signal=False,
    )
    records = read_feedback_history(tmp_path)
    assert len(records) == 1