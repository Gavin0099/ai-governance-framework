"""
Tests for governance_tools/closeout_audit.py
"""

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.closeout_audit import (
    build_closeout_audit,
    build_status_markdown,
    format_human_result,
    write_status_outputs,
)

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_closeout_audit"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_closeout(repo_root, session_id, status, closed_at=None, open_risks=None):
    d = repo_root / "artifacts" / "runtime" / "closeouts"
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "closed_at": closed_at or "2026-04-08T00:00:00+00:00",
        "closeout_status": status,
        "task_intent": None,
        "work_summary": None,
        "evidence_summary": {"tools_used": [], "artifacts_referenced": []},
        "open_risks": open_risks or [],
    }
    (d / f"{session_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class TestGracefulDegradation:
    def test_no_dir_returns_zero_counts(self):
        result = build_closeout_audit(_reset_fixture("no_dir"))
        assert result["ok"] is True
        assert result["session_count"] == 0

    def test_empty_dir_returns_zero_counts(self):
        repo = _reset_fixture("empty_dir")
        (repo / "artifacts" / "runtime" / "closeouts").mkdir(parents=True)
        assert build_closeout_audit(repo)["session_count"] == 0

    def test_no_policy_flags_when_no_sessions(self):
        result = build_closeout_audit(_reset_fixture("no_policy_flags"))
        assert result["policy_ok"] is True
        assert not any(result["policy_flags"].values())

    def test_unreadable_file_counted_not_crashed(self):
        repo = _reset_fixture("unreadable_file")
        d = repo / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "bad.json").write_text("NOT JSON {{{{", encoding="utf-8")
        result = build_closeout_audit(repo)
        assert result["session_count"] == 0
        assert len(result["unreadable_files"]) == 1

    def test_valid_rate_none_when_no_sessions(self):
        result = build_closeout_audit(_reset_fixture("valid_rate_none"))
        assert result["valid_rate"] is None
        assert result["recent_7d_valid_rate"] is None


class TestStatusDistribution:
    def test_single_valid(self):
        repo = _reset_fixture("single_valid")
        _write_closeout(repo, "s1", "valid")
        result = build_closeout_audit(repo)
        assert result["session_count"] == 1
        assert result["valid_count"] == 1
        assert result["status_distribution"]["valid"] == 1

    def test_all_five_statuses_counted(self):
        repo = _reset_fixture("all_five_statuses")
        for i, status in enumerate(["valid", "missing", "schema_invalid", "content_insufficient", "inconsistent"]):
            _write_closeout(repo, f"s{i}", status)
        result = build_closeout_audit(repo)
        assert result["session_count"] == 5
        assert result["valid_count"] == 1
        assert result["missing_count"] == 1
        assert result["schema_invalid_count"] == 1
        assert result["content_insufficient_count"] == 1
        assert result["inconsistent_count"] == 1

    def test_multiple_sessions_same_status(self):
        repo = _reset_fixture("multiple_same_status")
        _write_closeout(repo, "s1", "valid")
        _write_closeout(repo, "s2", "valid")
        _write_closeout(repo, "s3", "missing")
        result = build_closeout_audit(repo)
        assert result["valid_count"] == 2
        assert result["missing_count"] == 1


class TestValidRate:
    def test_valid_rate_100_percent(self):
        repo = _reset_fixture("valid_rate_100")
        _write_closeout(repo, "s1", "valid")
        _write_closeout(repo, "s2", "valid")
        assert build_closeout_audit(repo)["valid_rate"] == 1.0

    def test_valid_rate_50_percent(self):
        repo = _reset_fixture("valid_rate_50")
        _write_closeout(repo, "s1", "valid")
        _write_closeout(repo, "s2", "missing")
        assert build_closeout_audit(repo)["valid_rate"] == 0.5

    def test_valid_rate_zero(self):
        repo = _reset_fixture("valid_rate_zero")
        _write_closeout(repo, "s1", "missing")
        _write_closeout(repo, "s2", "missing")
        assert build_closeout_audit(repo)["valid_rate"] == 0.0


class TestRecentRate:
    def test_recent_valid_rate_counts_only_last_7_days(self):
        repo = _reset_fixture("recent_valid_rate")
        _write_closeout(repo, "old", "missing", closed_at=_days_ago_iso(10))
        _write_closeout(repo, "new-valid", "valid", closed_at=_days_ago_iso(1))
        _write_closeout(repo, "new-missing", "missing", closed_at=_days_ago_iso(2))
        result = build_closeout_audit(repo)
        assert result["recent_7d_session_count"] == 2
        assert result["recent_7d_valid_rate"] == 0.5

    def test_recent_rate_none_when_no_recent_sessions(self):
        repo = _reset_fixture("recent_rate_none")
        _write_closeout(repo, "old", "valid", closed_at=_days_ago_iso(10))
        result = build_closeout_audit(repo)
        assert result["recent_7d_session_count"] == 0
        assert result["recent_7d_valid_rate"] is None

    def test_sessions_without_closed_at_excluded_from_recent(self):
        repo = _reset_fixture("recent_excludes_no_closed_at")
        d = repo / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "no-date.json").write_text(json.dumps({"session_id": "x", "closeout_status": "valid", "closed_at": ""}), encoding="utf-8")
        assert build_closeout_audit(repo)["recent_7d_session_count"] == 0


class TestOpenRisks:
    def test_open_risks_counted(self):
        repo = _reset_fixture("open_risks_counted")
        _write_closeout(repo, "risky", "valid", open_risks=["something might break"])
        _write_closeout(repo, "clean", "valid", open_risks=[])
        assert build_closeout_audit(repo)["has_open_risks_count"] == 1

    def test_no_open_risks(self):
        repo = _reset_fixture("no_open_risks")
        _write_closeout(repo, "s1", "valid")
        assert build_closeout_audit(repo)["has_open_risks_count"] == 0


class TestPolicyFlags:
    def test_quality_review_false_when_valid_rate_above_threshold(self):
        repo = _reset_fixture("quality_review_false")
        _write_closeout(repo, "s1", "valid")
        assert build_closeout_audit(repo)["policy_flags"]["quality_review"] is False

    def test_quality_review_true_when_valid_rate_below_threshold(self):
        repo = _reset_fixture("quality_review_true")
        _write_closeout(repo, "s1", "missing")
        _write_closeout(repo, "s2", "missing")
        result = build_closeout_audit(repo)
        assert result["policy_flags"]["quality_review"] is True
        assert result["policy_ok"] is False

    def test_schema_drift_false_when_no_schema_invalid(self):
        repo = _reset_fixture("schema_drift_false")
        _write_closeout(repo, "s1", "valid")
        assert build_closeout_audit(repo)["policy_flags"]["schema_drift"] is False

    def test_schema_drift_true_when_schema_invalid_present(self):
        repo = _reset_fixture("schema_drift_true")
        _write_closeout(repo, "s1", "schema_invalid")
        result = build_closeout_audit(repo)
        assert result["policy_flags"]["schema_drift"] is True
        assert result["policy_ok"] is False

    def test_taxonomy_breach_false_for_known_statuses(self):
        repo = _reset_fixture("taxonomy_breach_false")
        _write_closeout(repo, "s1", "valid")
        assert build_closeout_audit(repo)["policy_flags"]["taxonomy_breach"] is False

    def test_taxonomy_breach_true_for_unknown_status(self):
        repo = _reset_fixture("taxonomy_breach_true")
        d = repo / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "weird.json").write_text(json.dumps({"session_id": "weird", "closed_at": "2026-04-08T00:00:00+00:00", "closeout_status": "custom_invented_status", "open_risks": []}), encoding="utf-8")
        result = build_closeout_audit(repo)
        assert result["policy_flags"]["taxonomy_breach"] is True
        assert "custom_invented_status" in result["unknown_statuses"]

    def test_policy_ok_true_when_all_flags_false(self):
        repo = _reset_fixture("policy_ok_true")
        _write_closeout(repo, "s1", "valid")
        _write_closeout(repo, "s2", "valid")
        assert build_closeout_audit(repo)["policy_ok"] is True


class TestTrustBoundary:
    def test_does_not_read_candidates_dir(self):
        repo = _reset_fixture("trust_candidates")
        cand = repo / "artifacts" / "runtime" / "closeout_candidates" / "s1"
        cand.mkdir(parents=True)
        (cand / "20260408T000000000000Z.json").write_text(json.dumps({"closeout_status": "valid"}), encoding="utf-8")
        assert build_closeout_audit(repo)["session_count"] == 0

    def test_does_not_read_session_index(self):
        repo = _reset_fixture("trust_session_index")
        (repo / "artifacts").mkdir(parents=True)
        (repo / "artifacts" / "session-index.ndjson").write_text(json.dumps({"session_id": "x", "closeout_status": "valid"}) + "\n", encoding="utf-8")
        assert build_closeout_audit(repo)["session_count"] == 0


class TestClaimBindingFutureGateFields:
    def test_missing_claim_enforcement_check_sets_future_gate_required(self):
        repo = _reset_fixture("claim_binding_missing_check")
        _write_closeout(repo, "s1", "valid")
        result = build_closeout_audit(repo)
        assert result["closeout_claim_binding_valid"] is False
        assert result["future_gate_required"] is True
        assert "missing_claim_enforcement_check" in result["invalid_reasons"]

    def test_missing_reviewer_response_when_action_not_allow(self):
        repo = _reset_fixture("claim_binding_missing_reviewer_response")
        _write_closeout(repo, "s1", "valid")
        d = repo / "artifacts" / "claim-enforcement" / "case1"
        d.mkdir(parents=True, exist_ok=True)
        (d / "claim-enforcement-check.json").write_text(
            json.dumps(
                {
                    "enforcement_action": "downgrade",
                    "reviewer_override_required": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = build_closeout_audit(repo)
        assert result["closeout_claim_binding_valid"] is False
        assert result["future_gate_required"] is True
        assert "missing_reviewer_response" in result["invalid_reasons"]

    def test_missing_override_reason_when_override_required(self):
        repo = _reset_fixture("claim_binding_missing_override_reason")
        _write_closeout(repo, "s1", "valid")
        d = repo / "artifacts" / "claim-enforcement" / "case1"
        d.mkdir(parents=True, exist_ok=True)
        (d / "claim-enforcement-check.json").write_text(
            json.dumps(
                {
                    "enforcement_action": "downgrade",
                    "reviewer_override_required": True,
                    "reviewer_response": {
                        "decision": "override",
                        "override_reason": "",
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = build_closeout_audit(repo)
        assert result["closeout_claim_binding_valid"] is False
        assert result["future_gate_required"] is True
        assert "missing_override_reason" in result["invalid_reasons"]

    def test_advisory_mode_does_not_force_policy_not_ok(self):
        repo = _reset_fixture("claim_binding_advisory_mode")
        _write_closeout(repo, "s1", "valid")
        result = build_closeout_audit(repo, require_claim_binding=False)
        assert result["closeout_claim_binding_valid"] is False
        assert result["future_gate_required"] is True
        assert result["claim_binding_required_violation"] is False
        assert result["policy_ok"] is True

    def test_require_mode_enforces_policy_not_ok(self):
        repo = _reset_fixture("claim_binding_require_mode")
        _write_closeout(repo, "s1", "valid")
        result = build_closeout_audit(repo, require_claim_binding=True)
        assert result["closeout_claim_binding_valid"] is False
        assert result["future_gate_required"] is True
        assert result["claim_binding_required_violation"] is True
        assert result["policy_ok"] is False


class TestFormatHumanResult:
    def test_contains_section_headers(self):
        repo = _reset_fixture("format_headers")
        _write_closeout(repo, "s1", "valid")
        output = format_human_result(build_closeout_audit(repo))
        assert "[closeout_audit]" in output
        assert "[policy_flags]" in output
        assert "[status_distribution]" in output

    def test_contains_valid_rate(self):
        repo = _reset_fixture("format_valid_rate")
        _write_closeout(repo, "s1", "valid")
        assert "valid_rate=" in format_human_result(build_closeout_audit(repo))

    def test_all_policy_flags_shown(self):
        output = format_human_result(build_closeout_audit(_reset_fixture("format_policy_flags")))
        assert "quality_review=" in output
        assert "schema_drift=" in output
        assert "taxonomy_breach=" in output


class TestStatusOutputs:
    def test_build_status_markdown_contains_summary(self):
        repo = _reset_fixture("status_markdown")
        _write_closeout(repo, "s1", "valid")
        result = build_closeout_audit(repo)
        result["generated_at"] = "2026-04-08T00:00:00+00:00"

        output = build_status_markdown(result)

        assert "# Closeout Audit" in output
        assert "- valid_rate: `1.0`" in output
        assert "| `valid` | `1` |" in output

    def test_write_status_outputs_writes_json_and_markdown(self):
        repo = _reset_fixture("write_status_outputs")
        _write_closeout(repo, "s1", "missing")
        result = build_closeout_audit(repo)
        result["generated_at"] = "2026-04-08T00:00:00+00:00"

        written = write_status_outputs(repo, result)

        json_path = Path(written["json"])
        md_path = Path(written["markdown"])
        assert json_path.exists()
        assert md_path.exists()
        assert '"missing_count": 1' in json_path.read_text(encoding="utf-8")
        assert "# Closeout Audit" in md_path.read_text(encoding="utf-8")
