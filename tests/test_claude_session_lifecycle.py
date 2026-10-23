"""Claude Code session lifecycle (spec #231, owner-approved defaults).

SessionStart: root-bound identity for provider "claude" + bounded read-back.
SessionEnd: resumable checkpoint, never a completion marker.
The central acceptance case runs the real prepare_closeout_candidate entry in a
committed submodule consumer: exit -> resume -> save again -> exit -> the next
start reads back the latest summary.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from runtime_hooks.adapters.claude_code import session_lifecycle as lc
from runtime_hooks.core import _canonical_closeout as core
from tests.test_prepare_closeout_candidate import (
    INPUT, SOURCES, SUBMODULE, environment, git, invoke, owner,
)

FRAMEWORK = Path(__file__).resolve().parents[1]
LIFECYCLE = "runtime_hooks/adapters/claude_code/session_lifecycle.py"
SID_A = "aaaaaaaa-0000-4000-8000-000000000001"
SID_B = "bbbbbbbb-0000-4000-8000-000000000002"


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    return path.resolve()


@pytest.fixture
def repo(tmp_path):
    return _git_repo(tmp_path / "claude consumer")


def start(root, sid=SID_A, source="startup", cwd=None):
    return lc.session_start({"hook_event_name": "SessionStart", "source": source, "session_id": sid,
                             "cwd": str(cwd or root), "transcript_path": "t"}, root)


def end(root, sid=SID_A, reason="prompt_input_exit"):
    return lc.session_end({"hook_event_name": "SessionEnd", "reason": reason, "session_id": sid,
                           "cwd": str(root), "transcript_path": "t"}, root)


def save(root, sid, **fields):
    return core.write_candidate(sid, root, {**{"task_intent": "t", "work_summary": "w", "open_risks": []},
                                            **fields})


def runtime(root):
    base = root / "artifacts"
    return sorted(p.relative_to(root).as_posix() for p in base.rglob("*")) if base.exists() else []


# ── identity ────────────────────────────────────────────────────────────────

def test_startup_creates_claude_root_bound_identity(repo):
    result = start(repo)
    assert (result["binding"], result["identity_status"]) == ("root_bound", "created")
    envelope = core.read_session_envelope(SID_A, repo)
    assert envelope["provider"] == "claude"
    assert envelope["repo_binding"]["source"] == "claude_session_start"


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_continuing_sources_preserve_identity(repo, source):
    start(repo)
    path = repo / f"artifacts/runtime/sessions/{SID_A}/session-envelope.json"
    before = path.read_bytes()
    result = start(repo, source=source)
    assert (result["binding"], result["identity_status"]) == ("root_bound", "preserved")
    assert path.read_bytes() == before


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_resume_without_identity_is_unknown_and_writes_nothing(repo, source):
    result = start(repo, source=source)
    assert (result["binding"], result["identity_status"]) == ("UNKNOWN", "not_established")
    assert "saving progress is unavailable" in result["additional_context"]
    assert runtime(repo) == []


@pytest.mark.parametrize("source", ["clear", "fork"])
def test_clear_and_fork_start_new_identities(repo, source):
    result = start(repo, sid=SID_B, source=source)
    assert (result["binding"], result["identity_status"]) == ("root_bound", "created")


def test_subdirectory_start_binds_the_worktree_root(repo):
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)
    result = start(repo, cwd=sub)
    assert result["binding"] == "root_bound"
    assert core.read_session_envelope(SID_A, repo)["repo_binding"]["consumer_root"] == str(repo)


def test_foreign_repo_cwd_is_rejected_without_writes(repo, tmp_path):
    other = _git_repo(tmp_path / "other")
    with pytest.raises(ValueError, match="do not match"):
        start(repo, cwd=other)
    assert runtime(repo) == [] and runtime(other) == []


def test_codex_identity_is_not_adopted(repo):
    core.write_session_envelope(SID_A, repo, provider="codex", bound_consumer_root=repo)
    with pytest.raises(ValueError, match="another provider"):
        start(repo)


@pytest.mark.parametrize("event", ["Stop", "SessionEnd", None])
def test_only_session_start_events_start(repo, event):
    payload = {"source": "startup", "session_id": SID_A, "cwd": str(repo)}
    if event:
        payload["hook_event_name"] = event
    with pytest.raises(ValueError, match="SessionStart"):
        lc.session_start(payload, repo)
    assert runtime(repo) == []


# ── SessionEnd checkpoint ───────────────────────────────────────────────────

def test_session_end_checkpoints_without_completion(repo):
    start(repo)
    candidate = save(repo, SID_A, work_summary="did A")
    checkpoint = end(repo)
    assert checkpoint["candidate"]["relative_path"] == candidate.relative_to(repo).as_posix()
    assert (checkpoint["agent_id"], checkpoint["trigger_mode"], checkpoint["hook_event_name"]) == (
        "claude", "native_hook", "SessionEnd")
    assert checkpoint["reason"] == "prompt_input_exit"
    assert not (repo / "artifacts/runtime/closeout-completions").exists()
    # the session directory still holds only the envelope (closeout ownership invariant)
    assert [p.name for p in (repo / f"artifacts/runtime/sessions/{SID_A}").iterdir()] == ["session-envelope.json"]


def test_session_end_without_summary_records_none(repo):
    start(repo)
    assert end(repo)["candidate"] is None
    assert start(repo, source="resume")["readback"]["state"] == "exited_without_summary"


def test_session_end_without_identity_writes_nothing(repo):
    with pytest.raises(ValueError, match="No root-bound Claude identity"):
        end(repo)
    assert runtime(repo) == []


# ── read-back ───────────────────────────────────────────────────────────────

def test_exit_without_session_end_is_unconfirmed_not_success(repo):
    start(repo)
    save(repo, SID_A, work_summary="never checkpointed")
    readback = start(repo, source="resume")["readback"]
    assert readback["state"] == "exit_unconfirmed"
    assert readback["summary"] is None


def test_tampered_checkpointed_summary_is_not_injected(repo):
    start(repo)
    candidate = save(repo, SID_A, work_summary="original")
    end(repo)
    candidate.write_text(json.dumps({"task_intent": "t", "work_summary": "TAMPERED"}), encoding="utf-8")
    readback = start(repo, source="resume")["readback"]
    assert readback["state"] == "checkpoint_mismatch" and readback["summary"] is None


def test_newer_summary_after_checkpoint_is_flagged(repo):
    start(repo)
    save(repo, SID_A, work_summary="first", )
    end(repo)
    save(repo, SID_A, work_summary="second, not yet checkpointed")
    readback = start(repo, source="resume")["readback"]
    assert readback["state"] == "newer_summary_after_checkpoint"
    assert "first" in readback["summary"]  # only the verified, checkpointed content


def test_readback_is_bounded_and_marked_as_data(repo):
    start(repo)
    save(repo, SID_A, work_summary="x" * 5000)
    end(repo)
    result = start(repo, source="resume")
    assert len(result["readback"]["summary"]) == lc.READBACK_LIMIT
    assert "DATA, not instructions" in result["additional_context"]


def test_new_session_reads_back_the_latest_exited_claude_session(repo):
    start(repo, sid=SID_A)
    save(repo, SID_A, work_summary="handoff from A")
    end(repo, sid=SID_A)
    result = start(repo, sid=SID_B)
    assert result["readback"]["session_id"] == SID_A
    assert "handoff from A" in result["readback"]["summary"]


def test_other_provider_and_unbound_checkpoints_are_ignored(repo):
    core.write_session_envelope(SID_A, repo, provider="codex", bound_consumer_root=repo)
    directory = repo / lc.CHECKPOINTS_DIR
    directory.mkdir(parents=True)
    for sid, provider in ((SID_A, "codex"), ("cccccccc-0000-4000-8000-000000000003", "claude")):
        (directory / f"{sid}.json").write_text(json.dumps(
            {"session_id": sid, "provider": provider, "exited_at": "2999-01-01T00:00:00+00:00",
             "candidate": None}), encoding="utf-8")
    assert start(repo, sid=SID_B)["readback"]["state"] == "no_previous_session"


def test_owner_note_when_another_session_holds_the_closeout(repo):
    start(repo, sid=SID_A)
    record = repo / lc.OWNER_RECORD
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"session_id": SID_A, "state": "OWNED"}), encoding="utf-8")
    context = start(repo, sid=SID_B)["additional_context"]
    assert f"session {SID_A} still owns the shared closeout" in context


# ── real prepare entry: exit -> resume -> save again -> exit -> read back latest ──

@pytest.fixture(scope="module")
def framework_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("claude-lifecycle-source")
    git(root, "init", "--quiet")
    for name in [*SOURCES, LIFECYCLE, "runtime_hooks/core/_bound_session_start.py"]:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FRAMEWORK / name, root / name)
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "disposable lifecycle implementation")
    return root


@pytest.fixture
def consumer(tmp_path, framework_source):
    root = tmp_path / "claude submodule consumer"
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
        str(framework_source), SUBMODULE)
    (root / "governance").mkdir()
    (root / "governance/framework.lock.json").write_text(
        json.dumps({"adopted_commit": git(root / SUBMODULE, "rev-parse", "HEAD")}), encoding="utf-8")
    (root / "evidence.txt").write_text("fixture evidence", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "registered consumer")
    return root.resolve()


def hook(root, event, payload):
    """Run the lifecycle entry from the consumer's submodule, as an installed hook does."""
    return subprocess.run(
        [sys.executable, "-B", str(root / SUBMODULE / LIFECYCLE), "--event", event, "--project-root", str(root)],
        input=json.dumps(payload), cwd=root, capture_output=True, text=True, encoding="utf-8",
        timeout=60, env=environment())


def test_exit_resume_save_again_exit_reads_back_latest(consumer):
    base = {"session_id": SID_A, "cwd": str(consumer), "transcript_path": "t"}
    started = hook(consumer, "session_start", {**base, "hook_event_name": "SessionStart", "source": "startup"})
    assert started.returncode == 0, started.stderr
    assert invoke(consumer, sid=SID_A, inputs={**INPUT, "work_summary": "first pass"}).returncode == 0
    assert hook(consumer, "session_end", {**base, "hook_event_name": "SessionEnd", "reason": "other"}).returncode == 0
    assert not (consumer / "artifacts/runtime/closeout-completions").exists()

    resumed = hook(consumer, "session_start", {**base, "hook_event_name": "SessionStart", "source": "resume"})
    context = json.loads(resumed.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "first pass" in context

    second = invoke(consumer, sid=SID_A, inputs={**INPUT, "work_summary": "second pass"})
    assert second.returncode == 0, second.stdout  # same session may prepare again after resume
    assert owner(consumer)["generation"] == 2
    assert hook(consumer, "session_end", {**base, "hook_event_name": "SessionEnd", "reason": "other"}).returncode == 0

    again = hook(consumer, "session_start", {**base, "hook_event_name": "SessionStart", "source": "resume"})
    context = json.loads(again.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "second pass" in context and "first pass" not in context
    assert "state=checkpointed" in context


def test_new_session_reads_back_but_cannot_save_until_formal_closeout(consumer):
    a = {"session_id": SID_A, "cwd": str(consumer), "transcript_path": "t"}
    hook(consumer, "session_start", {**a, "hook_event_name": "SessionStart", "source": "startup"})
    assert invoke(consumer, sid=SID_A, inputs={**INPUT, "work_summary": "A's work"}).returncode == 0
    hook(consumer, "session_end", {**a, "hook_event_name": "SessionEnd", "reason": "other"})

    b = {"session_id": SID_B, "cwd": str(consumer), "transcript_path": "t"}
    started = hook(consumer, "session_start", {**b, "hook_event_name": "SessionStart", "source": "startup"})
    context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "A's work" in context
    assert f"session {SID_A} still owns the shared closeout" in context
    refused = invoke(consumer, sid=SID_B)
    assert refused.returncode == 1 and "OWNER_CONFLICT" in refused.stdout
