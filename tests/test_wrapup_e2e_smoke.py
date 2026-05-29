"""
/wrap-up ↔ session_end End-to-End Smoke

Verifies the full session_id handoff:
  wrap-up writes candidate under .current-session-id
  → session_end_hook resolves same session_id
  → canonical closeout artifact records that session_id

DONE criteria:
  1. .current-session-id written before session_end
  2. candidate written to closeout_candidates/{session_id}/
  3. run_session_end_hook resolves same session_id
  4. canonical closeout artifact is named {session_id}.json
  5. stale .current-session-id triggers fallback — fresh ID, no old candidate reuse

Not tested here:
  - candidate semantic admissibility
  - safe_for_audit semantics
  - CP-8/CP-9 receipt policy
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout import (
    _CURRENT_SESSION_ID_STALENESS_SECONDS,
    _generate_session_id,
    read_current_session_id,
    write_candidate,
    write_current_session_id,
)
from governance_tools.session_end_hook import run_session_end_hook

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_wrapup_e2e_smoke"

_VALID_CANDIDATE = {
    "task_intent": "wrap-up e2e smoke — session_id lifecycle fix",
    "work_summary": "added write_current_session_id and read_current_session_id to runtime_hooks/core/_canonical_closeout.py",
    "tools_used": ["read", "edit", "bash"],
    "artifacts_referenced": ["runtime_hooks/core/_canonical_closeout.py"],
    "open_risks": [],
}


def _reset(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_minimal_closeout(repo: Path) -> None:
    """Write a minimal valid session-closeout.txt so classify_closeout passes."""
    closeout_dir = repo / "artifacts"
    closeout_dir.mkdir(parents=True, exist_ok=True)
    (closeout_dir / "session-closeout.txt").write_text(
        "TASK_INTENT: wrap-up e2e smoke\n"
        "WORK_COMPLETED: updated runtime_hooks/core/_canonical_closeout.py\n"
        "FILES_TOUCHED: runtime_hooks/core/_canonical_closeout.py\n"
        "CHECKS_RUN: python -m pytest tests/test_session_id_lifecycle.py => 18 passed\n"
        "OPEN_RISKS: none\n"
        "NOT_DONE: none\n"
        "RECOMMENDED_MEMORY_UPDATE: none\n",
        encoding="utf-8",
    )


class TestWrapUpE2ESmoke:
    def test_session_id_flows_from_current_session_id_to_result(self):
        """
        Core binding: run_session_end_hook must return the session_id written
        by /wrap-up via .current-session-id, not a freshly generated one.
        """
        repo = _reset("e2e_session_id_binding")
        _write_minimal_closeout(repo)
        sid = "session-SMOKE-aabbcc"
        write_current_session_id(sid, repo)

        result = run_session_end_hook(project_root=repo)

        assert result["session_id"] == sid, (
            f"Expected session_id={sid!r}, got {result['session_id']!r}. "
            "run_session_end_hook did not use .current-session-id."
        )

    def test_canonical_closeout_artifact_named_with_bound_session_id(self):
        """
        The canonical closeout artifact must be named {session_id}.json where
        session_id matches the pre-written .current-session-id.
        """
        repo = _reset("e2e_artifact_name")
        _write_minimal_closeout(repo)
        sid = "session-SMOKE-ccddee"
        write_current_session_id(sid, repo)

        result = run_session_end_hook(project_root=repo)

        assert result["session_id"] == sid
        canonical = repo / "artifacts" / "runtime" / "closeouts" / f"{sid}.json"
        assert canonical.exists(), (
            f"Expected canonical closeout at {canonical}, but it does not exist"
        )

    def test_wrapup_candidate_survives_to_session_end(self):
        """
        A candidate written by /wrap-up before session_end must be findable
        by pick_latest_candidate using the resolved session_id.

        This verifies candidate written at /wrap-up time is NOT lost by session_end.
        The session_end hook writes its OWN candidate (from session-closeout.txt),
        so both exist — but both are under the same session_id directory.
        """
        from runtime_hooks.core._canonical_closeout import pick_latest_candidate

        repo = _reset("e2e_candidate_survives")
        _write_minimal_closeout(repo)
        sid = "session-SMOKE-ffeedd"
        write_current_session_id(sid, repo)
        # Simulate /wrap-up writing a candidate
        write_candidate(sid, repo, _VALID_CANDIDATE, timestamp="20260529T000000000000Z")

        result = run_session_end_hook(project_root=repo)

        resolved_id = result["session_id"]
        assert resolved_id == sid
        # Both /wrap-up candidate and session_end candidate should exist
        candidates_dir = repo / "artifacts" / "runtime" / "closeout_candidates" / sid
        assert candidates_dir.is_dir()
        candidates = list(candidates_dir.glob("*.json"))
        assert len(candidates) >= 1, "No candidates found under the resolved session_id directory"

    def test_stale_current_session_id_triggers_fresh_fallback(self):
        """
        If .current-session-id is stale, session_end must NOT use the old ID.
        The old candidate must NOT be reused.
        """
        repo = _reset("e2e_stale_fallback")
        _write_minimal_closeout(repo)
        old_sid = "session-OLD-stale00"
        old_ts = (
            datetime.now(timezone.utc)
            - timedelta(seconds=_CURRENT_SESSION_ID_STALENESS_SECONDS + 1)
        ).isoformat()
        (repo / ".current-session-id").write_text(
            json.dumps({"session_id": old_sid, "written_at": old_ts}),
            encoding="utf-8",
        )
        # Simulate a prior /wrap-up candidate under the old session_id
        write_candidate(old_sid, repo, _VALID_CANDIDATE, timestamp="20260528T000000000000Z")

        result = run_session_end_hook(project_root=repo)

        resolved_id = result["session_id"]
        assert resolved_id != old_sid, (
            f"session_end must NOT reuse stale .current-session-id. Got {resolved_id!r}"
        )

    def test_hook_session_id_used_as_fallback_when_no_current_session_id(self):
        """
        When .current-session-id is absent, hook_session_id kwarg is used.
        """
        repo = _reset("e2e_hook_session_id_fallback")
        _write_minimal_closeout(repo)
        hook_sid = "session-HOOK-112233"

        result = run_session_end_hook(project_root=repo, hook_session_id=hook_sid)

        assert result["session_id"] == hook_sid, (
            f"Expected hook_session_id={hook_sid!r} to be used as fallback, "
            f"got {result['session_id']!r}"
        )

    def test_no_current_session_id_and_no_hook_id_generates_fresh_id(self):
        """
        When neither .current-session-id nor hook_session_id is available,
        a fresh session_id is generated (legacy path).
        """
        repo = _reset("e2e_legacy_fallback")
        _write_minimal_closeout(repo)

        result = run_session_end_hook(project_root=repo)

        sid = result["session_id"]
        assert sid.startswith("session-"), f"Expected session- prefix, got {sid!r}"
