"""Codex Stop hook output contract (#250).

Codex runs Stop at the end of every turn and reads stdout on exit 0 as its hook-response
JSON: empty stdout is success, a JSON object with fields Codex does not know marks the run
failed. These tests drive the real entry the way the installed hook does
(`--agent-id codex --trigger-mode native_hook`, payload on stdin) and check that:

- a turn with nothing to close is a silent success and writes nothing;
- a prepared session closes out with empty stdout;
- real failures (an unreadable owner record, a HOLD state for this session) still fail.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from governance_tools import shared_closeout_ownership as own
from tests.test_shared_closeout_ownership import owner, prepare, repo, start_session  # noqa: F401

ENTRY = Path(__file__).resolve().parents[1] / "governance_tools" / "session_closeout_entry.py"


def stop(root: Path, sid: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"session_id": sid, "hook_event_name": "Stop", "stop_hook_active": False})
    return subprocess.run(
        [sys.executable, str(ENTRY), "--project-root", str(root), "--format", "json",
         "--agent-id", "codex", "--trigger-mode", "native_hook", "--no-ledger-write"],
        input=payload, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120,
    )


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for sub in ("artifacts", "memory") for p in (root / sub).rglob("*") if p.is_file()}


def completion(root: Path, sid: str) -> Path:
    return root / "artifacts" / "runtime" / "closeout-completions" / f"{sid}.json"


def test_turn_without_owner_is_a_silent_success_and_writes_nothing(repo):
    start_session(repo, "session-A")
    before = snapshot(repo)

    result = stop(repo, "session-A")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "nothing to close" in result.stderr
    after = snapshot(repo)
    assert {k: v for k, v in after.items() if not k.endswith("execution.lock")} == \
           {k: v for k, v in before.items() if not k.endswith("execution.lock")}
    assert not completion(repo, "session-A").exists()


def test_legacy_shared_text_without_owner_is_skipped_with_its_reason(repo):
    start_session(repo, "session-A")
    (repo / own.TEXT).parent.mkdir(parents=True, exist_ok=True)
    (repo / own.TEXT).write_text("TASK_INTENT: pre-R2 record\n", encoding="utf-8")

    result = stop(repo, "session-A")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "legacy shared closeout text is present" in result.stderr


def test_other_sessions_turn_is_silent_and_leaves_the_prepared_owner_untouched(repo):
    prepare(repo, "session-A")
    start_session(repo, "session-B")
    held = owner(repo)

    result = stop(repo, "session-B")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "another session" in result.stderr
    assert owner(repo) == held
    assert owner(repo)["state"] == "OWNED"
    assert not completion(repo, "session-A").exists()
    assert not completion(repo, "session-B").exists()


def test_prepared_session_closes_out_with_empty_stdout(repo):
    prepare(repo, "session-A")

    result = stop(repo, "session-A")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "closeout_status=valid" in result.stderr
    assert completion(repo, "session-A").exists()
    assert owner(repo)["state"] == "RELEASED"


def test_later_turn_of_a_released_session_is_silent_and_writes_nothing(repo):
    prepare(repo, "session-A")
    assert stop(repo, "session-A").returncode == 0
    before = snapshot(repo)

    result = stop(repo, "session-A")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "already released" in result.stderr
    assert snapshot(repo) == before


def test_hold_state_for_this_session_still_fails(repo):
    prepare(repo, "session-A")
    record = owner(repo)
    record.update(state="HOLD", hold_reason="failed")
    (repo / own.AREA / "owner.json").write_text(json.dumps(record), encoding="utf-8")

    result = stop(repo, "session-A")

    assert result.returncode == 1
    assert not completion(repo, "session-A").exists()


def test_unreadable_owner_record_still_fails(repo):
    prepare(repo, "session-A")
    (repo / own.AREA / "owner.json").write_text("{not json", encoding="utf-8")

    result = stop(repo, "session-A")

    assert result.returncode == 1
    assert not completion(repo, "session-A").exists()
