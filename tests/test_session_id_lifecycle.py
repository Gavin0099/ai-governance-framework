"""
Tests for the /wrap-up ↔ session_end session_id lifecycle fix.

DONE criteria coverage:
  1. /wrap-up (write_current_session_id) writes .current-session-id
  2. /wrap-up candidate path uses that ID
  3. session_end reads candidates from the same session_id
  4. missing .current-session-id falls back to legacy _generate_session_id()
  5. stale .current-session-id does not allow cross-session candidate reuse
  6. canonical closeout artifact persists the same session_id
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout import (
    _CURRENT_SESSION_ID_STALENESS_SECONDS,
    _generate_session_id,
    build_canonical_closeout,
    pick_latest_candidate,
    read_current_session_id,
    write_candidate,
    write_canonical_closeout,
    write_current_session_id,
)

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_session_id_lifecycle"

_VALID_CANDIDATE = {
    "task_intent": "add session_id lifecycle fix",
    "work_summary": "implemented write_current_session_id and read_current_session_id in runtime_hooks/core/_canonical_closeout.py",
    "tools_used": ["read", "edit"],
    "artifacts_referenced": ["runtime_hooks/core/_canonical_closeout.py"],
    "open_risks": [],
}


def _reset(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── Criterion 1: write_current_session_id creates .current-session-id ────────

class TestWriteCurrentSessionId:
    def test_creates_file(self):
        repo = _reset("write_creates_file")
        sid = "session-20260529T000000-aabbcc"
        path = write_current_session_id(sid, repo)
        assert path.exists()
        assert path.name == ".current-session-id"

    def test_file_contains_session_id_and_written_at(self):
        repo = _reset("write_contains_fields")
        sid = "session-20260529T000000-aabbcc"
        path = write_current_session_id(sid, repo)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["session_id"] == sid
        assert "written_at" in data

    def test_second_write_overwrites_first(self):
        repo = _reset("write_overwrites")
        write_current_session_id("session-FIRST-aaaaaa", repo)
        write_current_session_id("session-SECOND-bbbbbb", repo)
        result = read_current_session_id(repo)
        assert result == "session-SECOND-bbbbbb"


# ── Criterion 2: /wrap-up candidate path uses the written ID ─────────────────

class TestWrapUpCandidatePath:
    def test_candidate_dir_uses_written_session_id(self):
        repo = _reset("candidate_uses_id")
        sid = "session-20260529T010000-cccccc"
        write_current_session_id(sid, repo)
        stable_id = read_current_session_id(repo)
        path = write_candidate(stable_id, repo, _VALID_CANDIDATE, timestamp="20260529T010000000000Z")
        assert stable_id in str(path)
        assert (repo / "artifacts" / "runtime" / "closeout_candidates" / stable_id).is_dir()

    def test_second_wrapup_call_reuses_same_id(self):
        repo = _reset("second_call_reuses_id")
        sid = "session-20260529T010001-cccccc"
        write_current_session_id(sid, repo)
        id1 = read_current_session_id(repo) or _generate_session_id()
        write_current_session_id(id1, repo)
        id2 = read_current_session_id(repo) or _generate_session_id()
        assert id1 == id2


# ── Criterion 3: session_end reads candidates from the same session_id ────────

class TestSessionEndReadsSameId:
    def test_read_returns_written_id(self):
        repo = _reset("session_end_reads_id")
        sid = "session-20260529T020000-dddddd"
        write_current_session_id(sid, repo)
        assert read_current_session_id(repo) == sid

    def test_candidate_written_by_wrapup_found_by_session_end(self):
        repo = _reset("wrapup_candidate_found")
        sid = "session-20260529T030000-eeeeee"
        # Simulate /wrap-up writing a candidate
        write_current_session_id(sid, repo)
        written_id = read_current_session_id(repo)
        write_candidate(written_id, repo, _VALID_CANDIDATE, timestamp="20260529T030000000000Z")
        # Simulate session_end resolving the same ID
        resolved_id = read_current_session_id(repo) or _generate_session_id()
        candidate = pick_latest_candidate(resolved_id, repo)
        assert candidate is not None
        assert candidate["task_intent"] == "add session_id lifecycle fix"


# ── Criterion 4: missing file falls back to _generate_session_id() ───────────

class TestMissingFileFallback:
    def test_missing_file_returns_none(self):
        repo = _reset("missing_returns_none")
        assert read_current_session_id(repo) is None

    def test_caller_fallback_generates_valid_id(self):
        repo = _reset("caller_fallback")
        result = read_current_session_id(repo) or _generate_session_id()
        assert result.startswith("session-")

    def test_malformed_json_returns_none(self):
        repo = _reset("malformed_json")
        (repo / ".current-session-id").write_text("NOT JSON {{{", encoding="utf-8")
        assert read_current_session_id(repo) is None

    def test_missing_session_id_field_returns_none(self):
        repo = _reset("missing_session_id_field")
        (repo / ".current-session-id").write_text(
            json.dumps({"written_at": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
        assert read_current_session_id(repo) is None

    def test_missing_written_at_field_returns_none(self):
        repo = _reset("missing_written_at")
        (repo / ".current-session-id").write_text(
            json.dumps({"session_id": "session-20260529T-xxxxxx"}),
            encoding="utf-8",
        )
        assert read_current_session_id(repo) is None


# ── Criterion 5: stale file does not allow cross-session candidate reuse ──────

class TestStalenessProtection:
    def test_stale_file_returns_none(self):
        repo = _reset("stale_returns_none")
        old_ts = (
            datetime.now(timezone.utc)
            - timedelta(seconds=_CURRENT_SESSION_ID_STALENESS_SECONDS + 1)
        ).isoformat()
        (repo / ".current-session-id").write_text(
            json.dumps({"session_id": "session-OLD-aaaaaa", "written_at": old_ts}),
            encoding="utf-8",
        )
        assert read_current_session_id(repo) is None

    def test_fresh_file_is_not_rejected(self):
        repo = _reset("fresh_accepted")
        write_current_session_id("session-FRESH-ffffff", repo)
        assert read_current_session_id(repo) == "session-FRESH-ffffff"

    def test_stale_file_triggers_fresh_id_not_old_id(self):
        repo = _reset("stale_triggers_fresh")
        old_ts = (
            datetime.now(timezone.utc)
            - timedelta(seconds=_CURRENT_SESSION_ID_STALENESS_SECONDS + 60)
        ).isoformat()
        (repo / ".current-session-id").write_text(
            json.dumps({"session_id": "session-OLD-stale0", "written_at": old_ts}),
            encoding="utf-8",
        )
        result = read_current_session_id(repo) or _generate_session_id()
        assert result != "session-OLD-stale0"
        assert result.startswith("session-")

    def test_max_age_zero_forces_stale(self):
        repo = _reset("max_age_zero")
        write_current_session_id("session-ZERO-aaaaaa", repo)
        assert read_current_session_id(repo, max_age_seconds=0) is None

    def test_stale_candidate_not_reused_by_session_end(self):
        repo = _reset("stale_candidate_not_reused")
        old_sid = "session-PRIOR-cccccc"
        write_candidate(old_sid, repo, _VALID_CANDIDATE, timestamp="20260528T000000000000Z")
        old_ts = (
            datetime.now(timezone.utc)
            - timedelta(seconds=_CURRENT_SESSION_ID_STALENESS_SECONDS + 1)
        ).isoformat()
        (repo / ".current-session-id").write_text(
            json.dumps({"session_id": old_sid, "written_at": old_ts}),
            encoding="utf-8",
        )
        resolved_id = read_current_session_id(repo) or _generate_session_id()
        assert resolved_id != old_sid
        # A fresh ID finds no candidate — no cross-session reuse
        assert pick_latest_candidate(resolved_id, repo) is None


# ── Criterion 6: canonical closeout artifact persists the same session_id ─────

class TestReceiptSessionIdBinding:
    def test_canonical_closeout_session_id_matches_candidate_id(self):
        repo = _reset("receipt_session_id_binding")
        sid = "session-20260529T060000-ffffff"
        # Simulate /wrap-up
        write_current_session_id(sid, repo)
        resolved_id = read_current_session_id(repo) or _generate_session_id()
        assert resolved_id == sid
        write_candidate(resolved_id, repo, _VALID_CANDIDATE, timestamp="20260529T060000000000Z")
        # Simulate session_end
        candidate = pick_latest_candidate(resolved_id, repo)
        canonical = build_canonical_closeout(
            session_id=resolved_id,
            closed_at="2026-05-29T06:00:00+00:00",
            candidate_payload=candidate,
            existing_artifacts=frozenset(["runtime_hooks/core/_canonical_closeout.py"]),
            runtime_signals={},
        )
        path = write_canonical_closeout(canonical, repo)
        persisted = json.loads(path.read_text(encoding="utf-8"))
        assert persisted["session_id"] == sid
        assert path.name == f"{sid}.json"
