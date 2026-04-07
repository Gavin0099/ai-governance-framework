import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.classification_session_summary import (
    build_classification_session_summary,
    format_human_result,
)


@pytest.fixture
def project_root(tmp_path):
    summaries = tmp_path / "artifacts" / "runtime" / "summaries"
    summaries.mkdir(parents=True)
    yield tmp_path


def _write_summary(summaries_dir: Path, session_id: str, decision_context: dict) -> None:
    payload = {
        "session_id": session_id,
        "closed_at": "2026-04-07T00:00:00+00:00",
        "decision_context": decision_context,
    }
    (summaries_dir / f"{session_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_empty_summaries_dir(project_root):
    result = build_classification_session_summary(project_root)

    assert result["ok"] is True
    assert result["session_count"] == 0
    assert result["classification_changed_count"] == 0
    assert result["downgrade_count"] == 0
    assert result["anomaly_count"] == 0
    assert result["reason_distribution"] == {}
    assert result["effective_class_distribution"] == {}
    assert result["conservative_downgrade_rate"] is None
    assert result["unknown_reasons"] == []
    # policy_flags: all clear when no data
    assert result["policy_flags"] == {
        "anomaly_alert": False,
        "classifier_review": False,
        "taxonomy_breach": False,
    }
    assert result["policy_ok"] is True


def test_no_summaries_dir(tmp_path):
    # No artifacts/runtime/summaries dir at all — should not raise.
    result = build_classification_session_summary(tmp_path)

    assert result["ok"] is True
    assert result["session_count"] == 0
    assert result["policy_ok"] is True


def test_sessions_without_classification_change(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    for i in range(3):
        _write_summary(
            summaries,
            f"s-{i:03d}",
            {
                "effective_agent_class": "instruction_capable",
                "initial_agent_class": "instruction_capable",
                "classification_changed": False,
                "reclassification_reason": None,
            },
        )

    result = build_classification_session_summary(project_root)

    assert result["session_count"] == 3
    assert result["classification_changed_count"] == 0
    assert result["downgrade_count"] == 0
    assert result["anomaly_count"] == 0
    assert result["reason_distribution"] == {}
    assert result["effective_class_distribution"] == {"instruction_capable": 3}
    assert result["conservative_downgrade_rate"] == 0.0
    assert result["policy_ok"] is True


def test_sessions_with_downgrade(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"

    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_capable",
            "initial_agent_class": "instruction_capable",
            "classification_changed": False,
            "reclassification_reason": None,
        },
    )
    _write_summary(
        summaries,
        "s-002",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "context_degraded",
        },
    )
    _write_summary(
        summaries,
        "s-003",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "conservative_downgrade",
        },
    )

    result = build_classification_session_summary(project_root)

    assert result["session_count"] == 3
    assert result["classification_changed_count"] == 2
    assert result["downgrade_count"] == 2
    assert result["anomaly_count"] == 0
    assert result["reason_distribution"]["context_degraded"] == 1
    assert result["reason_distribution"]["conservative_downgrade"] == 1
    assert result["effective_class_distribution"]["instruction_capable"] == 1
    assert result["effective_class_distribution"]["instruction_limited"] == 2
    # conservative_downgrade_rate = 1/3
    assert abs(result["conservative_downgrade_rate"] - 0.333) < 0.001


def test_anomaly_upgrade_counted_separately(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"

    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_capable",
            "initial_agent_class": "wrapper_only",
            "classification_changed": True,
            "reclassification_reason": "classification_anomaly_upgrade",
        },
    )
    _write_summary(
        summaries,
        "s-002",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "context_degraded",
        },
    )

    result = build_classification_session_summary(project_root)

    assert result["session_count"] == 2
    assert result["classification_changed_count"] == 2
    # anomaly upgrade is NOT counted as a downgrade
    assert result["downgrade_count"] == 1
    assert result["anomaly_count"] == 1
    assert result["reason_distribution"]["classification_anomaly_upgrade"] == 1
    assert result["reason_distribution"]["context_degraded"] == 1


def test_unknown_reason_flagged(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"

    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "some_future_reason",
        },
    )

    result = build_classification_session_summary(project_root)

    assert "some_future_reason" in result["unknown_reasons"]


def test_sessions_without_decision_context_still_counted(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    # Old-format session with no decision_context
    payload = {"session_id": "old-001", "closed_at": "2026-01-01T00:00:00+00:00"}
    (summaries / "old-001.json").write_text(json.dumps(payload), encoding="utf-8")

    result = build_classification_session_summary(project_root)

    assert result["session_count"] == 1
    assert result["effective_class_distribution"].get("unknown", 0) == 1
    assert result["classification_changed_count"] == 0


def test_unreadable_file_listed(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    (summaries / "bad.json").write_text("NOT JSON {{{", encoding="utf-8")

    result = build_classification_session_summary(project_root)

    assert result["session_count"] == 0
    assert len(result["unreadable_files"]) == 1
    assert "bad.json" in result["unreadable_files"][0]


def test_policy_flags_anomaly_alert(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_capable",
            "initial_agent_class": "wrapper_only",
            "classification_changed": True,
            "reclassification_reason": "classification_anomaly_upgrade",
        },
    )

    result = build_classification_session_summary(project_root)

    assert result["policy_flags"]["anomaly_alert"] is True
    assert result["policy_flags"]["classifier_review"] is False
    assert result["policy_flags"]["taxonomy_breach"] is False
    assert result["policy_ok"] is False


def test_policy_flags_classifier_review_above_threshold(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    # 2 out of 3 sessions are conservative_downgrade → rate = 0.667 > 0.10
    for i, reason in enumerate(["conservative_downgrade", "conservative_downgrade", None]):
        _write_summary(
            summaries,
            f"s-{i:03d}",
            {
                "effective_agent_class": "instruction_capable" if reason is None else "instruction_limited",
                "initial_agent_class": "instruction_capable",
                "classification_changed": reason is not None,
                "reclassification_reason": reason,
            },
        )

    result = build_classification_session_summary(project_root)

    assert result["policy_flags"]["classifier_review"] is True
    assert result["policy_flags"]["anomaly_alert"] is False
    assert result["policy_ok"] is False


def test_policy_flags_taxonomy_breach(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "unrecognized_future_reason",
        },
    )

    result = build_classification_session_summary(project_root)

    assert result["policy_flags"]["taxonomy_breach"] is True
    assert result["policy_ok"] is False


def test_policy_flags_all_clear(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    # One session with known reason, rate = 0 for conservative_downgrade
    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "context_degraded",
        },
    )

    result = build_classification_session_summary(project_root)

    assert result["policy_flags"]["anomaly_alert"] is False
    assert result["policy_flags"]["classifier_review"] is False
    assert result["policy_flags"]["taxonomy_breach"] is False
    assert result["policy_ok"] is True


def test_format_human_result_basic(project_root):
    summaries = project_root / "artifacts" / "runtime" / "summaries"
    _write_summary(
        summaries,
        "s-001",
        {
            "effective_agent_class": "instruction_capable",
            "initial_agent_class": "instruction_capable",
            "classification_changed": False,
            "reclassification_reason": None,
        },
    )
    _write_summary(
        summaries,
        "s-002",
        {
            "effective_agent_class": "instruction_limited",
            "initial_agent_class": "instruction_capable",
            "classification_changed": True,
            "reclassification_reason": "context_degraded",
        },
    )

    result = build_classification_session_summary(project_root)
    output = format_human_result(result)

    assert "[classification_session_summary]" in output
    assert "session_count=2" in output
    assert "downgrade_count=1" in output
    assert "anomaly_count=0" in output
    assert "[policy_flags]" in output
    assert "anomaly_alert=False" in output
    assert "classifier_review=False" in output
    assert "taxonomy_breach=False" in output
    assert "[reason_distribution]" in output
    assert "context_degraded=1" in output
    assert "[effective_class_distribution]" in output
    assert "instruction_capable=1" in output
    assert "instruction_limited=1" in output


def test_format_human_result_empty(project_root):
    result = build_classification_session_summary(project_root)
    output = format_human_result(result)

    assert "[classification_session_summary]" in output
    assert "session_count=0" in output
    assert "[policy_flags]" in output
    assert "(none)" in output
