"""
Tests for runtime_hooks/core/_canonical_closeout_context.py
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout_context import load_closeout_context

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_canonical_closeout_context"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_closeout(repo_root, session_id, status, closed_at="2026-04-08T00:00:00+00:00", **extra):
    d = repo_root / "artifacts" / "runtime" / "closeouts"
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
    (d / f"{session_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class TestGracefulDegradation:
    def test_no_closeouts_dir_returns_no_context(self):
        assert load_closeout_context(_reset_fixture("no_closeouts_dir"))["inject"] is False

    def test_empty_closeouts_dir_returns_no_context(self):
        repo = _reset_fixture("empty_closeouts_dir")
        (repo / "artifacts" / "runtime" / "closeouts").mkdir(parents=True)
        assert load_closeout_context(repo)["inject"] is False

    def test_unreadable_json_returns_no_context(self):
        repo = _reset_fixture("unreadable_json")
        d = repo / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "bad.json").write_text("NOT JSON {{{{", encoding="utf-8")
        assert load_closeout_context(repo)["inject"] is False

    def test_always_returns_required_keys(self):
        result = load_closeout_context(_reset_fixture("required_keys"))
        required = {"inject", "closeout_status", "session_id", "closed_at", "injection_level", "task_intent", "work_summary", "open_risks", "diagnostic"}
        assert required.issubset(result.keys())


class TestValidCloseout:
    def test_valid_gives_full_injection(self):
        repo = _reset_fixture("valid_full")
        _write_closeout(repo, "s-001", "valid", task_intent="add feature X", work_summary="implemented X in src/x.py", open_risks=["migration needed"])
        result = load_closeout_context(repo)
        assert result["inject"] is True
        assert result["injection_level"] == "full"
        assert result["closeout_status"] == "valid"

    def test_valid_populates_task_intent(self):
        repo = _reset_fixture("valid_task_intent")
        _write_closeout(repo, "s-001", "valid", task_intent="build Y")
        assert load_closeout_context(repo)["task_intent"] == "build Y"

    def test_valid_populates_work_summary(self):
        repo = _reset_fixture("valid_work_summary")
        _write_closeout(repo, "s-001", "valid", work_summary="edited foo.py")
        assert load_closeout_context(repo)["work_summary"] == "edited foo.py"

    def test_valid_populates_open_risks(self):
        repo = _reset_fixture("valid_open_risks")
        _write_closeout(repo, "s-001", "valid", open_risks=["risk A", "risk B"])
        assert load_closeout_context(repo)["open_risks"] == ["risk A", "risk B"]

    def test_valid_diagnostic_is_none(self):
        repo = _reset_fixture("valid_diagnostic_none")
        _write_closeout(repo, "s-001", "valid")
        assert load_closeout_context(repo)["diagnostic"] is None


class TestContentInsufficientCloseout:
    def test_content_insufficient_gives_warning_only(self):
        repo = _reset_fixture("content_insufficient_warning")
        _write_closeout(repo, "s-001", "content_insufficient")
        result = load_closeout_context(repo)
        assert result["inject"] is True
        assert result["injection_level"] == "warning_only"

    def test_content_insufficient_has_diagnostic(self):
        repo = _reset_fixture("content_insufficient_diagnostic")
        _write_closeout(repo, "s-001", "content_insufficient")
        assert load_closeout_context(repo)["diagnostic"] is not None


class TestMinimalStatusCloseout:
    @pytest.mark.parametrize("status", ["missing", "schema_invalid", "inconsistent"])
    def test_gives_none_injection_level(self, status):
        repo = _reset_fixture(f"minimal_{status}")
        _write_closeout(repo, "s-001", status)
        result = load_closeout_context(repo)
        assert result["inject"] is True
        assert result["injection_level"] == "none"

    @pytest.mark.parametrize("status", ["missing", "schema_invalid", "inconsistent"])
    def test_has_diagnostic_with_status(self, status):
        repo = _reset_fixture(f"minimal_diag_{status}")
        _write_closeout(repo, "s-001", status)
        assert status in load_closeout_context(repo)["diagnostic"]


class TestLatestSelection:
    def test_selects_most_recent_by_closed_at(self):
        repo = _reset_fixture("latest_by_closed_at")
        _write_closeout(repo, "old-session", "valid", closed_at="2026-04-07T00:00:00+00:00", task_intent="older task")
        _write_closeout(repo, "new-session", "valid", closed_at="2026-04-08T12:00:00+00:00", task_intent="newer task")
        result = load_closeout_context(repo)
        assert result["task_intent"] == "newer task"
        assert result["session_id"] == "new-session"

    def test_ignores_files_with_no_closed_at(self):
        repo = _reset_fixture("ignores_no_closed_at")
        d = repo / "artifacts" / "runtime" / "closeouts"
        d.mkdir(parents=True)
        (d / "no-date.json").write_text(json.dumps({"session_id": "x", "closeout_status": "valid"}), encoding="utf-8")
        _write_closeout(repo, "dated", "valid", closed_at="2026-04-08T00:00:00+00:00", task_intent="the one with a date")
        assert load_closeout_context(repo)["session_id"] == "dated"

    def test_session_id_and_closed_at_present_in_result(self):
        repo = _reset_fixture("session_id_and_closed_at")
        _write_closeout(repo, "my-session", "valid", closed_at="2026-04-08T09:00:00+00:00")
        result = load_closeout_context(repo)
        assert result["session_id"] == "my-session"
        assert result["closed_at"] == "2026-04-08T09:00:00+00:00"


class TestTrustBoundary:
    def test_does_not_read_candidates_dir(self):
        repo = _reset_fixture("trust_candidates")
        cand_dir = repo / "artifacts" / "runtime" / "closeout_candidates" / "s-001"
        cand_dir.mkdir(parents=True)
        (cand_dir / "20260408T000000000000Z.json").write_text(json.dumps({"task_intent": "from candidate"}), encoding="utf-8")
        assert load_closeout_context(repo)["inject"] is False

    def test_does_not_read_session_index(self):
        repo = _reset_fixture("trust_session_index")
        artifacts_dir = repo / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "session-index.ndjson").write_text(json.dumps({"session_id": "x", "closeout_status": "valid", "task_intent": "from index"}) + "\n", encoding="utf-8")
        assert load_closeout_context(repo)["inject"] is False
