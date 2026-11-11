"""Owner authorization given in advance (owner ruling 2026-11-11, #233).

The owner may authorize a closeout or handover condition once, in a committed
`[Owner Closeout Authorization]` block, so a Claude session that meets it can
formally close out without asking again. What must still hold:

- legal: a block already in the history the session started from (the HEAD
  its SessionStart hook recorded), naming a verifiable owner source, lets the
  session close out and the next one take over;
- refused, with no release residue: no authorization at all, an authorization
  the session wrote for itself (backdated or not), a plan line without the
  block, a source no one can check, a record reused for another session, and a
  record that no longer matches the history it names.

Git proves bytes and order, not authorship; these tests do not claim more.
"""
import json
import os
import subprocess

import pytest

from governance_tools import claude_formal_closeout as cli
from governance_tools import closeout_attestation as attestation
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2
from tests.test_shared_closeout_ownership import prepare, owner
from tests.test_claude_closeout_admission import (  # noqa: F401 - fixtures
    ENVELOPE, SID, _ready, ready, repo, start_claude, write_rows, claude_rows)
from tests.test_claude_formal_closeout import no_release_residue, released

SLICE = "docs/slices/HANDOVER-01.md"
SOURCE = "https://github.com/example/repo/issues/1#issuecomment-1"
CONDITION = "Session A closes out after stage 1 tests pass; session B continues stage 2."
MET = "stage 1 tests pass"
BEFORE_ANY_SESSION = "2020-01-01T00:00:00+00:00"
PLAN_ONLY = "# PLAN\n\n- next: hand over to session B\n"


def block(source=SOURCE, condition=CONDITION):
    return ("# Handover slice\n\n```text\n" + attestation.AUTHORIZATION_HEADER + "\n"
            f"SOURCE    = {source}\nCONDITION = {condition}\n```\n")


def commit(root, path, text, *, when=BEFORE_ANY_SESSION, branch=None):
    """Commit one file. `when` sets both dates; None keeps the real clock."""
    env = dict(os.environ)
    if when is not None:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    git = ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
    if branch:
        subprocess.run(git + ["checkout", "--quiet", "-b", branch], check=True, env=env)
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    subprocess.run(git + ["add", "--", path], check=True, env=env)
    subprocess.run(git + ["commit", "--quiet", "-m", "authorization fixture"], check=True, env=env)
    oid = subprocess.run(git + ["rev-parse", "HEAD"], check=True, capture_output=True,
                         text=True).stdout.strip()
    if branch:
        subprocess.run(git + ["checkout", "--quiet", "-"], check=True, env=env)
    return oid


def started_after(repo, monkeypatch, tmp_path, path=SLICE, text=None, **kwargs):
    """Commit the authorization first, then start session A on top of it."""
    oid = commit(repo, path, block() if text is None else text, **kwargs)
    root, source, payload = _ready(repo, monkeypatch, tmp_path, start_claude)
    return root, source, payload, oid


def close(root, source, ref, met=MET, sid=SID):
    return cli.close_out(root, sid, None, source, deadline_ms=30000,
                         authorization_ref=ref, condition_met=met)


def refused(root, source, ref, expected):
    with pytest.raises(h.HandoffError) as excinfo:
        close(root, source, ref)
    assert expected in str(excinfo.value)
    assert not released(root)
    assert no_release_residue(root)
    assert owner(root)["session_id"] == SID


# --------------------------------------------------------------------------
# Legal: authorized in advance, no new owner statement
# --------------------------------------------------------------------------

def test_preauthorized_condition_closes_out_and_b_takes_over(repo, monkeypatch, tmp_path):
    root, source, _, oid = started_after(repo, monkeypatch, tmp_path)
    before = owner(root)

    result = close(root, source, f"{SLICE}@{oid}")

    assert result["status"] == "FINALIZED"
    assert result["owner_state"] == "RELEASED"
    assert result["authorization_kind"] == "standing_owner_authorization"
    model = result["authorization_model"]
    assert "not authentication" in model and "person must check" in model

    stored = attestation.find(root, {k: before[k] for k in attestation._BOUND})
    assert stored is not None
    a = stored["attestation"]
    assert a["schema_version"] == attestation.STANDING_SCHEMA_VERSION
    assert "owner_statement" not in a
    assert a["condition_met"] == MET
    assert a["authorization"]["path"] == SLICE
    assert a["authorization"]["commit"] == oid
    assert a["authorization"]["session_start_head"] == oid
    assert a["authorization"]["source"] == SOURCE
    assert a["authorization"]["condition"] == CONDITION

    record = prepare(root, "session-B", session_start=start_claude)
    assert record["session_id"] == "session-B"
    assert record["generation"] == before["generation"] + 1


def test_owner_request_path_still_works_unchanged(ready):
    root, source, _ = ready
    result = cli.close_out(root, SID, "please close out this session", source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"
    assert result["authorization_kind"] == "owner_request"


# --------------------------------------------------------------------------
# Refused: no authorization, or an authorization that is not the owner's
# --------------------------------------------------------------------------

def test_no_authorization_at_all_is_refused(ready):
    root, source, _ = ready
    with pytest.raises(h.HandoffError) as excinfo:
        cli.close_out(root, SID, None, source, deadline_ms=30000)
    assert "AUTHORIZATION_REQUIRED" in str(excinfo.value)
    assert no_release_residue(root)


def test_both_kinds_at_once_are_refused(repo, monkeypatch, tmp_path):
    root, source, _, oid = started_after(repo, monkeypatch, tmp_path)
    with pytest.raises(h.HandoffError) as excinfo:
        cli.close_out(root, SID, "close out", source, deadline_ms=30000,
                      authorization_ref=f"{SLICE}@{oid}", condition_met=MET)
    assert "AUTHORIZATION_REQUIRED" in str(excinfo.value)
    assert no_release_residue(root)


@pytest.mark.parametrize("when", [None, BEFORE_ANY_SESSION], ids=["real-date", "backdated"])
def test_authorization_the_session_wrote_for_itself_is_refused(ready, when):
    """Committed during the session: refused even with a commit date years earlier.

    Dates are whatever the committer sets; the decision is by history, against
    the HEAD the SessionStart hook recorded before the agent acted.
    """
    root, source, _ = ready
    oid = commit(root, SLICE, block(), when=when)
    refused(root, source, f"{SLICE}@{oid}", "AUTHORIZATION_NOT_PRIOR")


def test_plan_line_without_the_block_is_refused(repo, monkeypatch, tmp_path):
    root, source, _, oid = started_after(repo, monkeypatch, tmp_path, path="PLAN.md", text=PLAN_ONLY)
    refused(root, source, f"PLAN.md@{oid}", "AUTHORIZATION_BLOCK_MISSING")


@pytest.mark.parametrize("source_text", ["owner said so in chat", "", "http://example.invalid/x"])
def test_source_no_one_can_check_is_refused(repo, monkeypatch, tmp_path, source_text):
    root, source, _, oid = started_after(repo, monkeypatch, tmp_path, text=block(source=source_text))
    expected = "AUTHORIZATION_BLOCK_INVALID" if not source_text else "AUTHORIZATION_SOURCE_UNVERIFIABLE"
    refused(root, source, f"{SLICE}@{oid}", expected)


def test_sha256_of_the_owner_record_is_a_checkable_source(repo, monkeypatch, tmp_path):
    root, source, _, oid = started_after(
        repo, monkeypatch, tmp_path, text=block(source="owner archive record sha256 " + "a" * 64))
    assert close(root, source, f"{SLICE}@{oid}")["status"] == "FINALIZED"


def test_commit_outside_the_history_of_head_is_refused(repo, monkeypatch, tmp_path):
    root, source, _, oid = started_after(repo, monkeypatch, tmp_path, branch="side")
    refused(root, source, f"{SLICE}@{oid}", "AUTHORIZATION_REF_INVALID")


@pytest.mark.parametrize("ref", ["../outside.md@abcd", "/abs/path.md@abcd", "docs\\x.md@abcd",
                                 "docs/x.md", "docs/x.md@not-a-commit", "a@b@c"])
def test_malformed_reference_is_refused(ready, ref):
    root, source, _ = ready
    refused(root, source, ref, "AUTHORIZATION_REF_INVALID")


# --------------------------------------------------------------------------
# A record is bound to one session, one generation and the history it names
# --------------------------------------------------------------------------

def test_record_cannot_be_reused_for_another_session(repo, monkeypatch, tmp_path):
    """B reusing A's record is refused; B citing the same authorization is not."""
    root, source, _, oid = started_after(repo, monkeypatch, tmp_path)
    close(root, source, f"{SLICE}@{oid}")
    a_record = next((root / attestation.AREA / SID).glob("*.json"))

    prepare(root, "session-B", session_start=start_claude)
    b_dir = root / attestation.AREA / "session-B"
    b_dir.mkdir(parents=True, exist_ok=True)
    (b_dir / a_record.name).write_bytes(a_record.read_bytes())
    b_owner = owner(root)
    assert attestation.find(root, {k: b_owner[k] for k in attestation._BOUND}) is None

    b_source = write_rows(source.parent / "claude-b.jsonl", claude_rows(root, sid="session-B"))
    result = close(root, b_source, f"{SLICE}@{oid}", met="stage 2 done", sid="session-B")
    assert result["status"] == "FINALIZED"


def test_record_that_no_longer_matches_its_history_is_refused(repo, monkeypatch, tmp_path):
    """Edited fields, even with a recomputed id, do not survive re-resolution."""
    root, source, payload, oid = started_after(repo, monkeypatch, tmp_path)
    stored = attestation.record_standing(root, SID, f"{SLICE}@{oid}", MET)
    path = root / attestation.AREA / SID / f'{stored["attestation_id"]}.json'
    path.unlink()
    forged = json.loads(json.dumps(stored))
    forged["attestation"]["authorization"]["source"] = "https://example.invalid/someone-else"
    forged["attestation_id"] = h._sha(h.canonical_bytes(forged["attestation"]))
    (path.parent / f'{forged["attestation_id"]}.json').write_bytes(h.canonical_bytes(forged))

    from governance_tools import claude_closeout_publisher as publisher
    result = publisher.publish(root, payload, deadline_ms=30000)
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, result["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert "CLOSEOUT_NOT_ATTESTED" in str(excinfo.value)
    assert not released(root)


def test_codex_release_path_does_not_need_this(repo):
    """The gate stays Claude-only; Codex keeps its native Stop closeout."""
    assert "codex" not in r2._ATTESTATION_REQUIRED_PROVIDERS
