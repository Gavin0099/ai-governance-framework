"""
Unit tests for governance_tools/plan_freshness.py

Test groups:
  A. parse_header_fields  — blockquote field extraction
  B. parse_policy         — policy string → threshold days
  C. check_freshness      — missing file / missing fields / FRESH / STALE / CRITICAL
  D. check_freshness      — threshold_override / today_override
  E. format_json          — output structure
"""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.plan_freshness import (
    parse_header_fields,
    parse_policy,
    check_freshness,
    format_json,
    STATUS_FRESH,
    STATUS_STALE,
    STATUS_CRITICAL,
    STATUS_ERROR,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_plan(last_updated: str, owner: str = "Tester", freshness: str = "Sprint (7d)") -> str:
    lines = []
    if last_updated:
        lines.append(f"> **最後更新**: {last_updated}")
    if owner:
        lines.append(f"> **Owner**: {owner}")
    if freshness:
        lines.append(f"> **Freshness**: {freshness}")
    return "\n".join(lines) + "\n"


def _write_plan(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "PLAN.md"
    p.write_text(content, encoding="utf-8")
    return p


TODAY = date(2026, 3, 6)


# ── A. parse_header_fields ────────────────────────────────────────────────────

class TestParseHeaderFields:
    def test_extracts_last_updated(self):
        text = "> **最後更新**: 2026-03-06\n"
        fields = parse_header_fields(text)
        assert fields["最後更新"] == "2026-03-06"

    def test_extracts_owner(self):
        text = "> **Owner**: GavinWu\n"
        fields = parse_header_fields(text)
        assert fields["Owner"] == "GavinWu"

    def test_extracts_freshness(self):
        text = "> **Freshness**: Sprint (7d)\n"
        fields = parse_header_fields(text)
        assert fields["Freshness"] == "Sprint (7d)"

    def test_extracts_multiple_fields(self):
        text = _make_plan("2026-03-06")
        fields = parse_header_fields(text)
        assert "最後更新" in fields
        assert "Owner" in fields
        assert "Freshness" in fields

    def test_empty_text_returns_empty_dict(self):
        assert parse_header_fields("") == {}

    def test_non_blockquote_lines_ignored(self):
        text = "# Title\n**最後更新**: 2026-03-06\n"
        fields = parse_header_fields(text)
        assert "最後更新" not in fields


# ── B. parse_policy ───────────────────────────────────────────────────────────

class TestParsePolicy:
    def test_sprint_with_explicit_days(self):
        assert parse_policy("Sprint (7d)") == 7

    def test_phase_with_explicit_days(self):
        assert parse_policy("Phase (30d)") == 30

    def test_custom_days(self):
        assert parse_policy("Custom (14d)") == 14

    def test_sprint_keyword_fallback(self):
        assert parse_policy("Sprint") == 7

    def test_phase_keyword_fallback(self):
        assert parse_policy("Phase") == 30

    def test_case_insensitive_days(self):
        assert parse_policy("sprint (7D)") == 7

    def test_unknown_policy_returns_none(self):
        assert parse_policy("Weekly") is None

    def test_empty_string_returns_none(self):
        assert parse_policy("") is None

    def test_none_returns_none(self):
        assert parse_policy(None) is None


# ── C. check_freshness — status transitions ───────────────────────────────────

class TestCheckFreshnessStatus:
    def test_missing_file_returns_error(self, tmp_path):
        result = check_freshness(tmp_path / "PLAN.md", today=TODAY)
        assert result.status == STATUS_ERROR
        assert result.days_since_update is None

    def test_missing_last_updated_field_returns_error(self, tmp_path):
        p = _write_plan(tmp_path, "> **Owner**: Tester\n> **Freshness**: Sprint (7d)\n")
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_ERROR
        assert any("最後更新" in e for e in result.errors)

    def test_invalid_date_format_returns_error(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026/03/06"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_ERROR

    def test_same_day_is_fresh(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026-03-06"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_FRESH
        assert result.days_since_update == 0

    def test_within_threshold_is_fresh(self, tmp_path):
        # threshold=7, days=5 → FRESH
        p = _write_plan(tmp_path, _make_plan("2026-03-01"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_FRESH

    def test_at_threshold_is_fresh(self, tmp_path):
        # threshold=7, days=7 → FRESH (≤)
        # TODAY=2026-03-06; 2026-02-27 → 7 days (2026 非閏年，Feb=28天)
        p = _write_plan(tmp_path, _make_plan("2026-02-27"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_FRESH
        assert result.days_since_update == 7

    def test_just_over_threshold_is_stale(self, tmp_path):
        # threshold=7, days=8 → STALE
        # TODAY=2026-03-06; 2026-02-26 → 8 days
        p = _write_plan(tmp_path, _make_plan("2026-02-26"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_STALE

    def test_at_double_threshold_is_stale(self, tmp_path):
        # threshold=7, days=14 → STALE (≤ 14)
        # TODAY=2026-03-06; 2026-02-20 → 14 days
        p = _write_plan(tmp_path, _make_plan("2026-02-20"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_STALE
        assert result.days_since_update == 14

    def test_beyond_double_threshold_is_critical(self, tmp_path):
        # threshold=7, days=15 → CRITICAL
        # TODAY=2026-03-06; 2026-02-19 → 15 days
        p = _write_plan(tmp_path, _make_plan("2026-02-19"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_CRITICAL

    def test_very_old_is_critical(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2025-01-01"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_CRITICAL

    def test_missing_owner_is_warning_not_error(self, tmp_path):
        content = "> **最後更新**: 2026-03-06\n> **Freshness**: Sprint (7d)\n"
        p = _write_plan(tmp_path, content)
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_FRESH
        assert any("Owner" in w for w in result.warnings)

    def test_missing_freshness_uses_default_7d(self, tmp_path):
        content = "> **最後更新**: 2026-03-06\n> **Owner**: Tester\n"
        p = _write_plan(tmp_path, content)
        result = check_freshness(p, today=TODAY)
        assert result.threshold_days == 7

    def test_result_contains_owner(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026-03-06"))
        result = check_freshness(p, today=TODAY)
        assert result.owner == "Tester"

    def test_result_contains_policy(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026-03-06"))
        result = check_freshness(p, today=TODAY)
        assert result.policy == "Sprint (7d)"
        assert result.threshold_days == 7


# ── D. threshold_override / today override ────────────────────────────────────

class TestCheckFreshnessOverrides:
    def test_threshold_override_changes_boundary(self, tmp_path):
        # days=8 from TODAY; default threshold=7 → STALE
        # with override=14 → FRESH
        p = _write_plan(tmp_path, _make_plan("2026-02-27"))
        result = check_freshness(p, threshold_override=14, today=TODAY)
        assert result.status == STATUS_FRESH

    def test_threshold_override_stricter(self, tmp_path):
        # days=3 from TODAY; default threshold=7 → FRESH
        # with override=2 → STALE
        p = _write_plan(tmp_path, _make_plan("2026-03-03"))
        result = check_freshness(p, threshold_override=2, today=TODAY)
        assert result.status == STATUS_STALE

    def test_today_override(self, tmp_path):
        # PLAN updated 2026-03-01; "today" = 2026-03-05 → 4 days → FRESH (threshold=7)
        p = _write_plan(tmp_path, _make_plan("2026-03-01"))
        result = check_freshness(p, today=date(2026, 3, 5))
        assert result.status == STATUS_FRESH
        assert result.days_since_update == 4

    def test_phase_policy_threshold(self, tmp_path):
        # Phase (30d): 15 days ago → FRESH
        p = _write_plan(tmp_path, _make_plan("2026-02-20", freshness="Phase (30d)"))
        result = check_freshness(p, today=TODAY)
        assert result.status == STATUS_FRESH
        assert result.threshold_days == 30


# ── E. format_json ────────────────────────────────────────────────────────────

class TestFormatJson:
    def test_json_has_required_keys(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026-03-06"))
        result = check_freshness(p, today=TODAY)
        output = json.loads(format_json(result, p))
        for key in ("plan_path", "status", "last_updated", "owner", "policy",
                    "threshold_days", "days_since_update", "errors", "warnings"):
            assert key in output

    def test_json_status_fresh(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026-03-06"))
        result = check_freshness(p, today=TODAY)
        output = json.loads(format_json(result, p))
        assert output["status"] == STATUS_FRESH

    def test_json_status_critical_on_old_plan(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2025-01-01"))
        result = check_freshness(p, today=TODAY)
        output = json.loads(format_json(result, p))
        assert output["status"] == STATUS_CRITICAL
        assert len(output["errors"]) > 0

    def test_json_missing_file(self, tmp_path):
        result = check_freshness(tmp_path / "PLAN.md", today=TODAY)
        output = json.loads(format_json(result, tmp_path / "PLAN.md"))
        assert output["status"] == STATUS_ERROR
        assert output["last_updated"] is None

    def test_json_is_valid_json(self, tmp_path):
        p = _write_plan(tmp_path, _make_plan("2026-03-06"))
        result = check_freshness(p, today=TODAY)
        # Should not raise
        parsed = json.loads(format_json(result, p))
        assert isinstance(parsed, dict)
