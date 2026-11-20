"""Claude transcripts may name the consumer's registered framework submodule (#233 follow-up).

Found in the real DeviceTraceKit Claude A→B run (2026-11-11): session A ran
governance tools from the framework submodule, so 18 transcript records had a
cwd there, and the formal closeout failed with TRANSCRIPT_SESSION_MISMATCH even
though the session was legitimate.

Owner ruling 2026-11-11: accept the consumer's own worktree and its one
registered framework submodule whose gitlink, lock and checkout agree; keep
rejecting every other nested repository, path outside the consumer, unregistered
or inconsistent framework, and session id mismatch. SessionStart binding,
SessionEnd payload cwd, ownership, receipts, release proof and the Codex path
are unchanged. A cwd in the framework grants no right to change it.
"""
import os
import subprocess

import pytest

from governance_tools import claude_closeout_publisher as c
from governance_tools import claude_formal_closeout as cli
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2
from governance_tools.prepare_closeout_candidate import PreparationError
from tests.test_shared_closeout_ownership import prepare, owner
from tests.test_claude_closeout_admission import (  # noqa: F401 - fixtures
    GIT, SID, _ready, ready, repo, start_claude, write_rows, claude_rows, place)
from tests.test_claude_formal_closeout import no_release_residue, released
from tests.test_claude_standing_authorization import SLICE, MET, block, commit

FRAMEWORK_REL = "SubModule/framework"


def make_framework_a_repository(root):
    """The unit fixture fakes the framework's .git; git_toplevel needs a real one."""
    framework = root / FRAMEWORK_REL
    (framework / ".git").unlink()
    subprocess.run(GIT + ["init", "--quiet", str(framework)], check=True, capture_output=True)
    subprocess.run(GIT + ["-C", str(framework), "commit", "--quiet", "--allow-empty", "-m", "fw"],
                   check=True, capture_output=True)
    tools = framework / "governance_tools"
    tools.mkdir(exist_ok=True)
    return framework.resolve(), tools.resolve()


def mixed_rows(root, framework, tools, sid=SID):
    """The real shape: consumer cwd, then framework cwds, then consumer again."""
    rows = claude_rows(root, sid=sid)
    for cwd in (framework, tools, root):
        rows.append({"type": "assistant", "sessionId": sid, "cwd": str(cwd),
                     "message": {"role": "assistant", "content": "ran a governance tool"}})
    return rows


@pytest.fixture
def framework_ready(ready, tmp_path):
    root, _, payload = ready
    framework, tools = make_framework_a_repository(root)
    source = write_rows(tmp_path / "mixed.jsonl", mixed_rows(root, framework, tools))
    return root, source, {**payload, "transcript_path": str(source)}, framework, tools


# --------------------------------------------------------------------------
# Unit: what a transcript cwd may name
# --------------------------------------------------------------------------

def test_cwd_rule_accepts_consumer_and_registered_framework_only(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)

    def git(*args):
        subprocess.run(GIT + list(args), check=True, capture_output=True)

    root = tmp_path / "consumer"
    git("init", "--quiet", str(root))
    git("-C", str(root), "commit", "--quiet", "--allow-empty", "-m", "root")
    root = root.resolve()
    for name in ("framework", "library"):
        upstream = tmp_path / name
        git("init", "--quiet", str(upstream))
        git("-C", str(upstream), "commit", "--quiet", "--allow-empty", "-m", name)
        git("-C", str(root), "-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
            upstream.as_posix(), f"vendor/{name}")
    framework = (root / "vendor" / "framework").resolve()
    (framework / "tools").mkdir()
    plain = tmp_path / "plain"
    plain.mkdir()

    allowed = h._transcript_cwd_in_consumer
    assert allowed(str(root), root, framework)
    assert allowed(str(place(root, tmp_path, "subdirectory")), root, framework)
    assert allowed(str(framework), root, framework)
    assert allowed(str(framework / "tools"), root, framework)
    for cwd in (root / "vendor" / "library", place(root, tmp_path, "nested_repo"),
                place(root, tmp_path, "other_worktree"), plain, tmp_path / "missing"):
        assert not allowed(str(cwd), root, framework), cwd
    assert not allowed(None, root, framework)
    assert not allowed("relative/path", root, framework)
    # No registered framework (unregistered or inconsistent): only the consumer counts.
    assert not allowed(str(framework), root, None)
    assert allowed(str(root), root, None)


def test_unqualified_framework_binding_yields_no_framework_root(ready, monkeypatch):
    root = ready[0]

    def unregistered(_root):
        raise PreparationError("framework path must have exactly one submodule registration")

    monkeypatch.setattr(h, "_framework_identity", unregistered)
    assert h._registered_framework_root(root) is None


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------

def test_mixed_consumer_and_framework_cwds_close_out_and_b_takes_over(framework_ready):
    root, source, _, _, _ = framework_ready
    before = owner(root)
    result = cli.close_out(root, SID, "please close out this session", source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"
    assert result["owner_state"] == "RELEASED"
    record = prepare(root, "session-B", session_start=start_claude)
    assert record["generation"] == before["generation"] + 1


def test_another_nested_repository_is_still_rejected(ready, tmp_path):
    root, _, payload = ready
    make_framework_a_repository(root)
    nested = place(root, tmp_path, "nested_repo")
    source = write_rows(tmp_path / "nested.jsonl", claude_rows(root, cwd=nested))
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, {**payload, "transcript_path": str(source)}, deadline_ms=30000)
    assert "TRANSCRIPT_SESSION_MISMATCH" in str(excinfo.value)
    assert no_release_residue(root)


def test_framework_cwd_is_rejected_when_the_binding_does_not_qualify(framework_ready, monkeypatch):
    root, _, payload, _, _ = framework_ready

    def inconsistent(_root):
        raise PreparationError("framework lock adopted_commit differs from index gitlink")

    monkeypatch.setattr(h, "_framework_identity", inconsistent)
    with pytest.raises((h.HandoffError, ValueError)) as excinfo:
        c.publish(root, payload, deadline_ms=30000)
    assert "TRANSCRIPT_SESSION_MISMATCH" in str(excinfo.value) or "adopted_commit" in str(excinfo.value)
    assert no_release_residue(root)


def test_framework_cwd_does_not_excuse_another_session_id(framework_ready, tmp_path):
    root, _, payload, framework, tools = framework_ready
    rows = mixed_rows(root, framework, tools)
    rows.append({"type": "assistant", "sessionId": "session-other", "cwd": str(framework),
                 "message": {"role": "assistant", "content": "x"}})
    source = write_rows(tmp_path / "other-session.jsonl", rows)
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, {**payload, "transcript_path": str(source)}, deadline_ms=30000)
    assert "TRANSCRIPT_SESSION_MISMATCH" in str(excinfo.value)
    assert no_release_residue(root)


def test_session_end_payload_cwd_rule_is_unchanged(framework_ready):
    """Only transcript records widen; the SessionEnd payload cwd keeps the old rule."""
    root, _, payload, framework, _ = framework_ready
    with pytest.raises((h.HandoffError, r2.OwnershipError, ValueError)):
        c.publish(root, {**payload, "cwd": str(framework)}, deadline_ms=30000)
    assert no_release_residue(root)


# --------------------------------------------------------------------------
# The real sequence: blocked by the old rule, framework updated, retried
# --------------------------------------------------------------------------

def test_session_blocked_by_the_old_rule_can_retry_after_the_framework_update(
        repo, monkeypatch, tmp_path):
    """A holds ownership, its closeout fails on the old rule, then a retry succeeds.

    Mirrors the DeviceTraceKit run: a standing owner authorization committed
    before the session, a transcript that names the framework submodule, a
    first attempt refused, and a second attempt by the same session after the
    fix. The refusal must leave nothing that blocks the retry, and the retry
    must not need the transcript or ownership to be rewritten.
    """
    oid = commit(repo, SLICE, block())
    root, _, payload = _ready(repo, monkeypatch, tmp_path, start_claude)
    framework, tools = make_framework_a_repository(root)
    source = write_rows(tmp_path / "a.jsonl", mixed_rows(root, framework, tools))
    ref = f"{SLICE}@{oid}"

    # Before the fix: the framework submodule is not accepted.
    with monkeypatch.context() as old_rule:
        old_rule.setattr(h, "_registered_framework_root", lambda _root: None)
        with pytest.raises(h.HandoffError) as excinfo:
            cli.close_out(root, SID, None, source, deadline_ms=30000,
                          authorization_ref=ref, condition_met=MET)
        assert "TRANSCRIPT_SESSION_MISMATCH" in str(excinfo.value)
    assert not released(root)
    assert owner(root)["session_id"] == SID and owner(root)["state"] == "OWNED"

    # The framework is updated between the attempts (F-7 moves gitlink, lock and
    # checkout together); the session, its candidate and its ownership are not.
    updated = "d" * 40
    monkeypatch.setattr(h, "_framework_identity", lambda _root: {
        "relative_path": FRAMEWORK_REL, "gitlink_oid": updated,
        "checkout_head": updated, "adopted_commit": updated,
        "registration_blob": "b" * 40, "lock_blob": "e" * 40})

    def updated_git(_root, *args):
        if args[0] == "ls-files":
            return ("160000 " + updated + " 0\t" + FRAMEWORK_REL + "\0"
                    + "100644 " + "b" * 40 + " 0\t.gitmodules\0"
                    + "100644 " + "e" * 40 + " 0\tgovernance/framework.lock.json\0")
        if args == ("rev-parse", "--show-toplevel"):
            return str(framework)
        if args[0] == "rev-parse":
            return updated
        if args[0] == "status":
            return "# branch.oid " + updated + "\n# branch.head main"
        raise AssertionError(args)

    monkeypatch.setattr(h, "_git", updated_git)
    assert owner(root)["session_id"] == SID and owner(root)["state"] == "OWNED"

    # After the fix: the same session retries with the same transcript.
    result = cli.close_out(root, SID, None, source, deadline_ms=30000,
                           authorization_ref=ref, condition_met=MET)
    assert result["status"] == "FINALIZED"
    assert result["owner_state"] == "RELEASED"
    assert result["authorization_kind"] == "standing_owner_authorization"
    assert prepare(root, "session-B", session_start=start_claude)["session_id"] == "session-B"
