"""
Tests for the pre-closeout transcript ingest bridge.

Gap 2: repo-local DB (artifacts/codeburn_closeout_ingest.db) is used,
       not ~/.codeburn/codeburn.db.
Gap 1: closeout session_id is used as the DB key, not transcript stem.

Together these enable scope=current_session in the closeout token summary.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.session_end_hook import (
    _detect_transcript_provider,
    _ingest_transcript_for_closeout,
)
from governance_tools.codeburn_token_summary import (
    build_codeburn_token_observation,
    find_latest_codeburn_db,
)

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_codeburn_ingest_bridge"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_claude_transcript(path: Path, turns: int = 2) -> Path:
    """Write a minimal Claude Code JSONL transcript with token data."""
    lines = []
    for i in range(turns):
        lines.append(json.dumps({
            "type": "assistant",
            "uuid": f"turn-{i}",
            "timestamp": f"2026-05-28T{i:02d}:00:00.000Z",
            "message": {
                "usage": {
                    "input_tokens": 100 * (i + 1),
                    "output_tokens": 20 * (i + 1),
                }
            }
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_codex_transcript(path: Path, turns: int = 2) -> Path:
    """Write a minimal Codex JSONL transcript with token data."""
    lines = []
    for i in range(turns):
        lines.append(json.dumps({
            "type": "event_msg",
            "timestamp": f"2026-05-28T{i:02d}:00:00.000Z",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 200 * (i + 1),
                        "output_tokens": 30 * (i + 1),
                    }
                }
            }
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

class TestDetectTranscriptProvider:
    def test_detects_claude_from_assistant_type(self):
        repo = _reset_fixture("detect_claude")
        t = _write_claude_transcript(repo / "transcript.jsonl")
        assert _detect_transcript_provider(t) == "claude"

    def test_detects_codex_from_event_msg_type(self):
        repo = _reset_fixture("detect_codex")
        t = _write_codex_transcript(repo / "transcript.jsonl")
        assert _detect_transcript_provider(t) == "codex"

    def test_defaults_to_claude_on_empty_file(self, tmp_path):
        t = tmp_path / "empty.jsonl"
        t.write_text("", encoding="utf-8")
        assert _detect_transcript_provider(t) == "claude"

    def test_defaults_to_claude_on_missing_file(self, tmp_path):
        assert _detect_transcript_provider(tmp_path / "missing.jsonl") == "claude"


# ---------------------------------------------------------------------------
# Gap 2: repo-local DB path
# ---------------------------------------------------------------------------

class TestGap2DbPath:
    def test_ingest_creates_repo_local_db(self):
        """Gap 2: codeburn_closeout_ingest.db must be in artifacts/, not ~/.codeburn/."""
        repo = _reset_fixture("gap2_db_path")
        t = _write_claude_transcript(repo / "transcript.jsonl")
        _ingest_transcript_for_closeout(repo, "session-test-001", t)
        db = repo / "artifacts" / "codeburn_closeout_ingest.db"
        assert db.exists(), "codeburn_closeout_ingest.db must be in artifacts/"

    def test_find_latest_codeburn_db_finds_ingest_db(self):
        """find_latest_codeburn_db must resolve to the repo-local ingest DB."""
        repo = _reset_fixture("gap2_find_db")
        t = _write_claude_transcript(repo / "transcript.jsonl")
        _ingest_transcript_for_closeout(repo, "session-test-002", t)
        found = find_latest_codeburn_db(repo)
        assert found is not None
        assert found.name == "codeburn_closeout_ingest.db"
        assert found.parent == repo / "artifacts"

    def test_ingest_does_not_write_to_home_codeburn(self):
        """Ingest bridge must NOT write to ~/.codeburn/codeburn.db."""
        import os
        repo = _reset_fixture("gap2_no_home_write")
        t = _write_claude_transcript(repo / "transcript.jsonl")
        home_db = Path.home() / ".codeburn" / "codeburn.db"
        mtime_before = home_db.stat().st_mtime if home_db.exists() else None
        _ingest_transcript_for_closeout(repo, "session-test-003", t)
        mtime_after = home_db.stat().st_mtime if home_db.exists() else None
        assert mtime_before == mtime_after, "Must not touch ~/.codeburn/codeburn.db"


# ---------------------------------------------------------------------------
# Gap 1: session_id binding
# ---------------------------------------------------------------------------

class TestGap1SessionIdBinding:
    def test_ingest_writes_steps_with_closeout_session_id(self):
        """Gap 1: steps in DB must carry the closeout session_id, not transcript stem."""
        import sqlite3
        repo = _reset_fixture("gap1_session_id")
        t = _write_claude_transcript(repo / "my-session-stem.jsonl", turns=2)
        session_id = "session-20260528T120000-abc999"
        _ingest_transcript_for_closeout(repo, session_id, t)
        db = repo / "artifacts" / "codeburn_closeout_ingest.db"
        conn = sqlite3.connect(str(db))
        rows = conn.execute(
            "SELECT COUNT(*) FROM steps WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert rows[0] >= 1, f"Expected steps with session_id={session_id}"

    def test_ingest_does_not_use_transcript_stem_as_session_id(self):
        """The transcript filename stem must NOT appear as a session_id in the DB."""
        import sqlite3
        repo = _reset_fixture("gap1_no_stem")
        t = _write_claude_transcript(repo / "some-random-stem.jsonl", turns=1)
        _ingest_transcript_for_closeout(repo, "session-20260528T120000-bound01", t)
        db = repo / "artifacts" / "codeburn_closeout_ingest.db"
        conn = sqlite3.connect(str(db))
        bad = conn.execute(
            "SELECT COUNT(*) FROM steps WHERE session_id = ?", ("some-random-stem",)
        ).fetchone()
        conn.close()
        assert bad[0] == 0, "Transcript stem must not be used as session_id"


# ---------------------------------------------------------------------------
# End-to-end: scope=current_session
# ---------------------------------------------------------------------------

class TestCurrentSessionScope:
    def test_token_summary_returns_current_session_scope_after_ingest(self):
        """After ingest with closeout session_id, token summary must show scope=current_session."""
        repo = _reset_fixture("e2e_current_session")
        t = _write_claude_transcript(repo / "transcript.jsonl", turns=3)
        session_id = "session-20260528T130000-e2e001"
        _ingest_transcript_for_closeout(repo, session_id, t)
        obs = build_codeburn_token_observation(repo, preferred_session_id=session_id)
        assert obs["scope"] == "current_session", (
            f"Expected scope=current_session, got scope={obs['scope']!r}. "
            f"summary_text={obs['summary_text']!r}"
        )

    def test_token_values_match_transcript_content(self):
        """Token counts must reflect what was in the transcript."""
        repo = _reset_fixture("e2e_token_values")
        # 2 turns: input 100+200=300, output 20+40=60
        t = _write_claude_transcript(repo / "transcript.jsonl", turns=2)
        session_id = "session-20260528T130000-vals01"
        _ingest_transcript_for_closeout(repo, session_id, t)
        obs = build_codeburn_token_observation(repo, preferred_session_id=session_id)
        assert obs["input_tokens"] == 300
        assert obs["output_tokens"] == 60
        assert obs["total_tokens"] == 360

    def test_codex_transcript_also_produces_current_session_scope(self):
        """Codex transcripts must also produce scope=current_session after ingest."""
        repo = _reset_fixture("e2e_codex_current")
        t = _write_codex_transcript(repo / "codex.jsonl", turns=2)
        session_id = "session-20260528T140000-codex01"
        _ingest_transcript_for_closeout(repo, session_id, t)
        obs = build_codeburn_token_observation(repo, preferred_session_id=session_id)
        assert obs["scope"] == "current_session"

    def test_without_ingest_scope_is_not_current_session(self):
        """Without ingest, a fresh repo must NOT return scope=current_session."""
        repo = _reset_fixture("e2e_no_ingest")
        obs = build_codeburn_token_observation(repo, preferred_session_id="session-20260528T999999-none")
        assert obs["scope"] != "current_session"

    def test_wrong_session_id_does_not_produce_current_session(self):
        """Querying a different session_id after ingest must not produce current_session."""
        repo = _reset_fixture("e2e_wrong_id")
        t = _write_claude_transcript(repo / "transcript.jsonl", turns=1)
        _ingest_transcript_for_closeout(repo, "session-20260528T150000-right01", t)
        obs = build_codeburn_token_observation(repo, preferred_session_id="session-20260528T150000-wrong01")
        assert obs["scope"] != "current_session"

    def test_summary_text_contains_current_session_label(self):
        """summary_text string must contain 'scope=current_session'."""
        repo = _reset_fixture("e2e_summary_text")
        t = _write_claude_transcript(repo / "transcript.jsonl", turns=1)
        session_id = "session-20260528T160000-txt01"
        _ingest_transcript_for_closeout(repo, session_id, t)
        obs = build_codeburn_token_observation(repo, preferred_session_id=session_id)
        assert "scope=current_session" in obs["summary_text"]
        assert "authority=analysis-only" in obs["summary_text"]
        assert "decision_authority=none" in obs["summary_text"]


# ---------------------------------------------------------------------------
# Fail-silent contract
# ---------------------------------------------------------------------------

class TestFailSilent:
    def test_missing_transcript_does_not_raise(self, tmp_path):
        _ingest_transcript_for_closeout(tmp_path, "session-x", tmp_path / "missing.jsonl")

    def test_empty_transcript_does_not_raise(self, tmp_path):
        t = tmp_path / "empty.jsonl"
        t.write_text("", encoding="utf-8")
        _ingest_transcript_for_closeout(tmp_path, "session-x", t)
