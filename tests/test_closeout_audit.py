"""
Tests for governance_tools/closeout_audit.py

Coverage:
- build_closeout_audit(): empty / missing dir → zero counts, no policy flags
- build_closeout_audit(): status_distribution counts for all 5 status values
- build_closeout_audit(): valid_rate calculation
- build_closeout_audit(): recent_7d_valid_rate (sessions with recent closed_at)
- build_closeout_audit(): has_open_risks_count
- build_closeout_audit(): policy_flags — quality_review, schema_drift, taxonomy_breach
- build_closeout_audit(): unknown_statuses
- build_closeout_audit(): unreadable_files tolerance
- Trust boundary: never reads candidates/ or session-index.ndjson
- format_human_result(): output structure
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.closeout_audit import build_closeout_audit, format_human_result


def _write_closeout(tmp_path, session_id, status, closed_at=None, open_risks=None):
    d = tmp_path / "artifacts" / "runtime" / "closeouts"
    d.mkdir(parents=True, exist_ok=True)
    closed_at = closed_at or "2026-04-08T00:00:00+00:00"
    payload = {
        "session_id": session_id,
        "closed_at": closed_at,
        "closeout_status": status,
        "task_intent": None,
        "work_summary": None,
        "evidence_summary": {"tools_used": [], "artifacts_referenced": []},
        "open_risks": open_risks or [],
    }
    (d / f"{session_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _days_ago_iso(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:

    def test_no_dir_returns_zero_counts(self, tmp_path):
        result = build_closeout_audit(tmp_path)
        assert result["ok"] is True
        assert result["session_count"] == 0

    def test_empty_dir_returns_zero_counts(self, tmp_path):
        (tmp_path / "artifacts" / "runtime" / "closeouts").mkdir(parents=True)
        result = build_closeout_audit(tmp_path)
        assert result["session_count"] == 0

    def test_no_policy_flags_when_no_sessions(self, tmp_path):
        result = build_closeout_audit(tmp_path)
        assert result["policy_ok"] is True
        assert not any(result["policy_flags"].values())

    def test_unreadable_file_counted_not_crashed(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "bad.json").write_text("NOT JSON {{{{", encoding="utf-8")
        result = build_closeout_audit(tmp_path)
        assert result["session_count"] == 0
        assert len(result["unreadable_files"]) == 1

    def test_valid_rate_none_when_no_sessions(self, tmp_path):
        result = build_closeout_audit(tmp_path)
        assert result["valid_rate"] is None
        assert result["recent_7d_valid_rate"] is None


# ---------------------------------------------------------------------------
# Status distribution
# ---------------------------------------------------------------------------

class TestStatusDistribution:

    def test_single_valid(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["session_count"] == 1
        assert result["valid_count"] == 1
        assert result["status_distribution"]["valid"] == 1

    def test_all_five_statuses_counted(self, tmp_path):
        for i, status in enumerate(
            ["valid", "missing", "schema_invalid", "content_insufficient", "inconsistent"]
        ):
            _write_closeout(tmp_path, f"s{i}", status)
        result = build_closeout_audit(tmp_path)
        assert result["session_count"] == 5
        assert result["valid_count"] == 1
        assert result["missing_count"] == 1
        assert result["schema_invalid_count"] == 1
        assert result["content_insufficient_count"] == 1
        assert result["inconsistent_count"] == 1

    def test_multiple_sessions_same_status(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        _write_closeout(tmp_path, "s2", "valid")
        _write_closeout(tmp_path, "s3", "missing")
        result = build_closeout_audit(tmp_path)
        assert result["valid_count"] == 2
        assert result["missing_count"] == 1


# ---------------------------------------------------------------------------
# valid_rate
# ---------------------------------------------------------------------------

class TestValidRate:

    def test_valid_rate_100_percent(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        _write_closeout(tmp_path, "s2", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["valid_rate"] == 1.0

    def test_valid_rate_50_percent(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        _write_closeout(tmp_path, "s2", "missing")
        result = build_closeout_audit(tmp_path)
        assert result["valid_rate"] == 0.5

    def test_valid_rate_zero(self, tmp_path):
        _write_closeout(tmp_path, "s1", "missing")
        _write_closeout(tmp_path, "s2", "missing")
        result = build_closeout_audit(tmp_path)
        assert result["valid_rate"] == 0.0


# ---------------------------------------------------------------------------
# recent_7d_valid_rate
# ---------------------------------------------------------------------------

class TestRecentRate:

    def test_recent_valid_rate_counts_only_last_7_days(self, tmp_path):
        _write_closeout(tmp_path, "old", "missing", closed_at=_days_ago_iso(10))
        _write_closeout(tmp_path, "new-valid", "valid", closed_at=_days_ago_iso(1))
        _write_closeout(tmp_path, "new-missing", "missing", closed_at=_days_ago_iso(2))
        result = build_closeout_audit(tmp_path)
        assert result["recent_7d_session_count"] == 2
        assert result["recent_7d_valid_rate"] == 0.5

    def test_recent_rate_none_when_no_recent_sessions(self, tmp_path):
        _write_closeout(tmp_path, "old", "valid", closed_at=_days_ago_iso(10))
        result = build_closeout_audit(tmp_path)
        assert result["recent_7d_session_count"] == 0
        assert result["recent_7d_valid_rate"] is None

    def test_sessions_without_closed_at_excluded_from_recent(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "no-date.json").write_text(
            json.dumps({"session_id": "x", "closeout_status": "valid", "closed_at": ""}),
            encoding="utf-8",
        )
        result = build_closeout_audit(tmp_path)
        assert result["recent_7d_session_count"] == 0


# ---------------------------------------------------------------------------
# has_open_risks_count
# ---------------------------------------------------------------------------

class TestOpenRisks:

    def test_open_risks_counted(self, tmp_path):
        _write_closeout(tmp_path, "risky", "valid", open_risks=["something might break"])
        _write_closeout(tmp_path, "clean", "valid", open_risks=[])
        result = build_closeout_audit(tmp_path)
        assert result["has_open_risks_count"] == 1

    def test_no_open_risks(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["has_open_risks_count"] == 0


# ---------------------------------------------------------------------------
# Policy flags
# ---------------------------------------------------------------------------

class TestPolicyFlags:

    def test_quality_review_false_when_valid_rate_above_threshold(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["policy_flags"]["quality_review"] is False

    def test_quality_review_true_when_valid_rate_below_threshold(self, tmp_path):
        # 0 valid out of 2 sessions → rate = 0.0 < 0.5
        _write_closeout(tmp_path, "s1", "missing")
        _write_closeout(tmp_path, "s2", "missing")
        result = build_closeout_audit(tmp_path)
        assert result["policy_flags"]["quality_review"] is True
        assert result["policy_ok"] is False

    def test_schema_drift_false_when_no_schema_invalid(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["policy_flags"]["schema_drift"] is False

    def test_schema_drift_true_when_schema_invalid_present(self, tmp_path):
        _write_closeout(tmp_path, "s1", "schema_invalid")
        result = build_closeout_audit(tmp_path)
        assert result["policy_flags"]["schema_drift"] is True
        assert result["policy_ok"] is False

    def test_taxonomy_breach_false_for_known_statuses(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["policy_flags"]["taxonomy_breach"] is False

    def test_taxonomy_breach_true_for_unknown_status(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "weird.json").write_text(
            json.dumps({
                "session_id": "weird",
                "closed_at": "2026-04-08T00:00:00+00:00",
                "closeout_status": "custom_invented_status",
                "open_risks": [],
            }),
            encoding="utf-8",
        )
        result = build_closeout_audit(tmp_path)
        assert result["policy_flags"]["taxonomy_breach"] is True
        assert "custom_invented_status" in result["unknown_statuses"]

    def test_policy_ok_true_when_all_flags_false(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        _write_closeout(tmp_path, "s2", "valid")
        result = build_closeout_audit(tmp_path)
        assert result["policy_ok"] is True


# ---------------------------------------------------------------------------
# Trust boundary
# ---------------------------------------------------------------------------

class TestTrustBoundary:

    def test_does_not_read_candidates_dir(self, tmp_path):
        cand = tmp_path / "artifacts" / "runtime" / "closeout_candidates" / "s1"
        cand.mkdir(parents=True)
        (cand / "20260408T000000000000Z.json").write_text(
            json.dumps({"closeout_status": "valid"}), encoding="utf-8"
        )
        result = build_closeout_audit(tmp_path)
        assert result["session_count"] == 0

    def test_does_not_read_session_index(self, tmp_path):
        (tmp_path / "artifacts").mkdir(parents=True)
        (tmp_path / "artifacts" / "session-index.ndjson").write_text(
            json.dumps({"session_id": "x", "closeout_status": "valid"}) + "\n",
            encoding="utf-8",
        )
        result = build_closeout_audit(tmp_path)
        assert result["session_count"] == 0


# ---------------------------------------------------------------------------
# format_human_result
# ---------------------------------------------------------------------------

class TestFormatHumanResult:

    def test_contains_section_headers(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        output = format_human_result(result)
        assert "[closeout_audit]" in output
        assert "[policy_flags]" in output
        assert "[status_distribution]" in output

    def test_contains_valid_rate(self, tmp_path):
        _write_closeout(tmp_path, "s1", "valid")
        result = build_closeout_audit(tmp_path)
        output = format_human_result(result)
        assert "valid_rate=" in output

    def test_all_policy_flags_shown(self, tmp_path):
        result = build_closeout_audit(tmp_path)
        output = format_human_result(result)
        assert "quality_review=" in output
        assert "schema_drift=" in output
        assert "taxonomy_breach=" in output
