"""
Tests for runtime_hooks/core/_canonical_closeout_context.py

Coverage:
- load_closeout_context(): graceful degradation paths
- load_closeout_context(): injection_level rules for all 5 closeout_status values
- _load_latest_canonical(): selection by closed_at (not filename)
- Trust boundary: never reads candidates/ or session-index.ndjson
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout_context import load_closeout_context


def _write_closeout(tmp_path, session_id, status, closed_at="2026-04-08T00:00:00+00:00", **extra):
    d = tmp_path / "artifacts" / "runtime" / "closeouts"
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "closed_at": closed_at,
        "closeout_status": status,
        "task_intent": extra.get("task_intent"),
        "work_summary": extra.get("work_summary"),
        "evidence_summary": {
            "tools_used": extra.get("tools_used", []),
            "artifacts_referenced": extra.get("artifacts_referenced", []),
        },
        "open_risks": extra.get("open_risks", []),
    }
    (d / f"{session_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:

    def test_no_closeouts_dir_returns_no_context(self, tmp_path):
        result = load_closeout_context(tmp_path)
        assert result["inject"] is False
        assert result["closeout_status"] is None

    def test_empty_closeouts_dir_returns_no_context(self, tmp_path):
        (tmp_path / "artifacts" / "runtime" / "closeouts").mkdir(parents=True)
        result = load_closeout_context(tmp_path)
        assert result["inject"] is False

    def test_unreadable_json_returns_no_context(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "bad.json").write_text("NOT JSON {{{{", encoding="utf-8")
        result = load_closeout_context(tmp_path)
        assert result["inject"] is False

    def test_always_returns_required_keys(self, tmp_path):
        result = load_closeout_context(tmp_path)
        required = {"inject", "closeout_status", "session_id", "closed_at",
                    "injection_level", "task_intent", "work_summary",
                    "open_risks", "diagnostic"}
        assert required.issubset(result.keys())


# ---------------------------------------------------------------------------
# Injection level: valid
# ---------------------------------------------------------------------------

class TestValidCloseout:

    def test_valid_gives_full_injection(self, tmp_path):
        _write_closeout(
            tmp_path, "s-001", "valid",
            task_intent="add feature X",
            work_summary="implemented X in src/x.py",
            open_risks=["migration needed"],
        )
        result = load_closeout_context(tmp_path)
        assert result["inject"] is True
        assert result["injection_level"] == "full"
        assert result["closeout_status"] == "valid"

    def test_valid_populates_task_intent(self, tmp_path):
        _write_closeout(tmp_path, "s-001", "valid", task_intent="build Y")
        result = load_closeout_context(tmp_path)
        assert result["task_intent"] == "build Y"

    def test_valid_populates_work_summary(self, tmp_path):
        _write_closeout(tmp_path, "s-001", "valid", work_summary="edited foo.py")
        result = load_closeout_context(tmp_path)
        assert result["work_summary"] == "edited foo.py"

    def test_valid_populates_open_risks(self, tmp_path):
        _write_closeout(tmp_path, "s-001", "valid", open_risks=["risk A", "risk B"])
        result = load_closeout_context(tmp_path)
        assert result["open_risks"] == ["risk A", "risk B"]

    def test_valid_diagnostic_is_none(self, tmp_path):
        _write_closeout(tmp_path, "s-001", "valid")
        result = load_closeout_context(tmp_path)
        assert result["diagnostic"] is None


# ---------------------------------------------------------------------------
# Injection level: content_insufficient
# ---------------------------------------------------------------------------

class TestContentInsufficientCloseout:

    def test_content_insufficient_gives_warning_only(self, tmp_path):
        _write_closeout(tmp_path, "s-001", "content_insufficient")
        result = load_closeout_context(tmp_path)
        assert result["inject"] is True
        assert result["injection_level"] == "warning_only"
        assert result["task_intent"] is None
        assert result["work_summary"] is None
        assert result["open_risks"] == []

    def test_content_insufficient_has_diagnostic(self, tmp_path):
        _write_closeout(tmp_path, "s-001", "content_insufficient")
        result = load_closeout_context(tmp_path)
        assert result["diagnostic"] is not None
        assert len(result["diagnostic"]) > 0


# ---------------------------------------------------------------------------
# Injection level: missing / schema_invalid / inconsistent
# ---------------------------------------------------------------------------

class TestMinimalStatusCloseout:

    @pytest.mark.parametrize("status", ["missing", "schema_invalid", "inconsistent"])
    def test_gives_none_injection_level(self, tmp_path, status):
        _write_closeout(tmp_path, "s-001", status)
        result = load_closeout_context(tmp_path)
        assert result["inject"] is True
        assert result["injection_level"] == "none"
        assert result["task_intent"] is None
        assert result["work_summary"] is None
        assert result["open_risks"] == []

    @pytest.mark.parametrize("status", ["missing", "schema_invalid", "inconsistent"])
    def test_has_diagnostic_with_status(self, tmp_path, status):
        _write_closeout(tmp_path, "s-001", status)
        result = load_closeout_context(tmp_path)
        assert result["diagnostic"] is not None
        assert status in result["diagnostic"]


# ---------------------------------------------------------------------------
# Latest selection: by closed_at (not filename)
# ---------------------------------------------------------------------------

class TestLatestSelection:

    def test_selects_most_recent_by_closed_at(self, tmp_path):
        _write_closeout(tmp_path, "old-session", "valid",
                        closed_at="2026-04-07T00:00:00+00:00",
                        task_intent="older task")
        _write_closeout(tmp_path, "new-session", "valid",
                        closed_at="2026-04-08T12:00:00+00:00",
                        task_intent="newer task")
        result = load_closeout_context(tmp_path)
        assert result["task_intent"] == "newer task"
        assert result["session_id"] == "new-session"

    def test_ignores_files_with_no_closed_at(self, tmp_path):
        # File with no closed_at should be ignored
        d = tmp_path / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "no-date.json").write_text(
            json.dumps({"session_id": "x", "closeout_status": "valid"}),
            encoding="utf-8",
        )
        _write_closeout(tmp_path, "dated", "valid",
                        closed_at="2026-04-08T00:00:00+00:00",
                        task_intent="the one with a date")
        result = load_closeout_context(tmp_path)
        assert result["session_id"] == "dated"

    def test_session_id_and_closed_at_present_in_result(self, tmp_path):
        _write_closeout(tmp_path, "my-session", "valid",
                        closed_at="2026-04-08T09:00:00+00:00")
        result = load_closeout_context(tmp_path)
        assert result["session_id"] == "my-session"
        assert result["closed_at"] == "2026-04-08T09:00:00+00:00"


# ---------------------------------------------------------------------------
# Trust boundary: no candidates/ or session-index.ndjson access
# ---------------------------------------------------------------------------

class TestTrustBoundary:

    def test_does_not_read_candidates_dir(self, tmp_path):
        # Write a candidate file but no canonical closeout
        cand_dir = (
            tmp_path / "artifacts" / "runtime" / "closeout_candidates" / "s-001"
        )
        cand_dir.mkdir(parents=True)
        (cand_dir / "20260408T000000000000Z.json").write_text(
            json.dumps({"task_intent": "from candidate"}), encoding="utf-8"
        )
        result = load_closeout_context(tmp_path)
        # No canonical → no context
        assert result["inject"] is False

    def test_does_not_read_session_index(self, tmp_path):
        # Write a session-index but no canonical closeout
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "session-index.ndjson").write_text(
            json.dumps({"session_id": "x", "closeout_status": "valid", "task_intent": "from index"}) + "\n",
            encoding="utf-8",
        )
        result = load_closeout_context(tmp_path)
        assert result["inject"] is False
