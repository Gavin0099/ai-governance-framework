"""First R2 initialization: ADR-0002 D1-D3 and the 2026-11-07 ruling (#256).

An envelope is identity, not a closeout obligation, and a session end that
recorded no candidate has nothing to reconcile. Every other unexplained
closeout-side state must still refuse, and nothing may be written on refusal.
"""
import json

import pytest

from governance_tools import shared_closeout_ownership as own
from tests.test_shared_closeout_ownership import (  # noqa: F401
    invoke, inputs, owner, prepare, repo, sha, start_session,
)

SESSION_END_OUTPUTS = ("candidates", "curated", "summaries", "verdicts", "traces")


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def finished_without_candidate(root, sid="session-B", status="missing", outputs=True):
    """The shape a per-turn Stop closeout leaves when the session had no candidate."""
    start_session(root, sid)
    _write(root / f"artifacts/runtime/closeouts/{sid}.json",
           {"session_id": sid, "closeout_status": status, "task_intent": None})
    if outputs:
        for directory in SESSION_END_OUTPUTS:
            _write(root / f"artifacts/runtime/{directory}/{sid}.json", {"session_id": sid})


def acquire(root, sid="session-A"):
    ci, _, text = inputs(root, sid)
    with own.execution_exclusion(root) as lease:
        return own.acquire_owner(lease, sid, ci, sha(text))


LOCK = f"{own.AREA}/execution.lock"


def snapshot(root):
    # The OS lock that execution_exclusion creates is the one entry _initial
    # allows; everything else must be byte-identical after a refusal.
    base = root / "artifacts"
    return {rel: p.read_bytes() for p in base.rglob("*") if p.is_file()
            and (rel := p.relative_to(root).as_posix()) != LOCK}


def refused(root, code, detail=None):
    before = snapshot(root)
    with pytest.raises(own.OwnershipError) as caught:
        acquire(root)
    assert caught.value.code == code, str(caught.value)
    if detail is not None:
        assert detail in str(caught.value)
    assert not (root / own.AREA / "owner.json").exists()
    assert snapshot(root) == before, "a refusal must not write"


# ---- ADR-0002 D1: IDENTITY_ONLY does not block -------------------------------

def test_two_sessions_started_before_either_saved_can_initialise(repo):
    # The #256 reproduction: A and B both started, neither saved progress.
    start_session(repo, "session-A")
    start_session(repo, "session-B")
    assert acquire(repo)["state"] == "HOLD"


def test_many_identity_only_sessions_do_not_block(repo):
    start_session(repo, "session-A")
    for i in range(5):
        start_session(repo, f"older-{i}")
    acquire(repo)
    assert (repo / own.AREA / "owner.json").exists()


# ---- 2026-11-07 ruling: a session end that recorded no candidate ------------

@pytest.mark.parametrize("outputs", [True, False])
def test_session_end_without_candidate_does_not_block(repo, outputs):
    start_session(repo, "session-A")
    finished_without_candidate(repo, outputs=outputs)
    acquire(repo)
    assert (repo / own.AREA / "owner.json").exists()


def test_formal_closeout_completes_beside_such_history(repo, monkeypatch):
    # DTK shape: identity-only sessions plus no-candidate session ends.
    start_session(repo, "older-identity")
    finished_without_candidate(repo, "older-missing")
    prepare(repo, "session-A")
    assert invoke(repo, monkeypatch) == 0
    assert owner(repo)["state"] == "RELEASED"
    assert (repo / "artifacts/runtime/closeout-completions/session-A.json").exists()
    # History is kept byte for byte.
    assert json.loads((repo / "artifacts/runtime/closeouts/older-missing.json").read_text(
        encoding="utf-8"))["closeout_status"] == "missing"
    assert (repo / "artifacts/runtime/sessions/older-identity/session-envelope.json").exists()


def test_acquiring_session_own_earlier_missing_record_does_not_block(repo):
    # Stop runs a closeout every turn; before the first prepare it records
    # "missing" for the acquiring session itself. Same ruled shape, so no block.
    finished_without_candidate(repo, "session-A")
    acquire(repo)
    assert (repo / own.AREA / "owner.json").exists()


# ---- still fail-closed --------------------------------------------------------

def test_open_handoff_request_of_another_session_still_refuses(repo):
    start_session(repo, "session-A")
    finished_without_candidate(repo)
    _write(repo / "artifacts/runtime/closeout-requests/session-B/request.json", {"session_id": "session-B"})
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")


@pytest.mark.parametrize("sibling", ["closeouts/session-B.txt", "traces/session-B/nested.json"])
def test_ruled_shape_accepts_only_its_json_records(repo, sibling):
    start_session(repo, "session-A")
    finished_without_candidate(repo)
    _write(repo / f"artifacts/runtime/{sibling}", {"anything": True})
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")

def test_missing_record_with_a_closeout_candidate_still_refuses(repo):
    start_session(repo, "session-A")
    finished_without_candidate(repo)
    _write(repo / "artifacts/runtime/closeout_candidates/session-B/000001.json", {"session_id": "session-B"})
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")


def test_missing_record_with_a_receipt_still_refuses(repo):
    start_session(repo, "session-A")
    finished_without_candidate(repo)
    _write(repo / "artifacts/runtime/closeout-receipts/legacy.json", {"session_id": "session-B"})
    refused(repo, "AMBIGUOUS_LEGACY_STATE")


@pytest.mark.parametrize("status", ["valid", "inconsistent", "", None])
def test_other_closeout_statuses_without_completion_still_refuse(repo, status):
    start_session(repo, "session-A")
    finished_without_candidate(repo, status=status)
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")


def test_missing_record_without_an_identity_still_refuses(repo):
    start_session(repo, "session-A")
    _write(repo / "artifacts/runtime/closeouts/ghost.json", {"session_id": "ghost", "closeout_status": "missing"})
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")


def test_missing_record_naming_another_session_still_refuses(repo):
    start_session(repo, "session-A")
    start_session(repo, "session-B")
    _write(repo / "artifacts/runtime/closeouts/session-B.json", {"session_id": "session-C", "closeout_status": "missing"})
    refused(repo, "AMBIGUOUS_LEGACY_STATE")


def test_unreadable_missing_record_still_refuses_as_legacy_state(repo):
    start_session(repo, "session-A")
    start_session(repo, "session-B")
    path = repo / "artifacts/runtime/closeouts/session-B.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    refused(repo, "AMBIGUOUS_LEGACY_STATE")


@pytest.mark.parametrize("directory", SESSION_END_OUTPUTS)
def test_session_end_output_without_a_closeout_record_still_refuses(repo, directory):
    start_session(repo, "session-A")
    start_session(repo, "session-B")
    _write(repo / f"artifacts/runtime/{directory}/session-B.json", {"session_id": "session-B"})
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")


def test_legacy_shared_text_still_refuses_even_with_only_identity_history(repo):
    start_session(repo, "session-A")
    start_session(repo, "session-B")
    (repo / own.TEXT).write_bytes(b"legacy text")
    refused(repo, "AMBIGUOUS_LEGACY_STATE")


# ---- ADR-0002 D3: containment has its own code -------------------------------

def test_stray_file_in_the_acquiring_session_directory_names_the_path(repo):
    start_session(repo, "session-A")
    (repo / "artifacts/runtime/sessions/session-A/planted.txt").write_text("x", encoding="utf-8")
    refused(repo, "SESSION_DIR_UNEXPECTED_FILE", "artifacts/runtime/sessions/session-A/planted.txt")


def test_extra_file_in_an_unclosed_other_session_is_not_identity_only(repo):
    start_session(repo, "session-A")
    start_session(repo, "session-B")
    (repo / "artifacts/runtime/sessions/session-B/session-closeout.txt").write_text("x", encoding="utf-8")
    refused(repo, "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")


def test_closed_other_session_with_extra_files_still_does_not_block(repo, monkeypatch):
    # An older Copilot closeout left extra files in a session it completed;
    # completed sessions were accepted before this change and still are.
    prepare(repo, "session-B")
    assert invoke(repo, monkeypatch, "session-B") == 0
    extra = repo / "artifacts/runtime/sessions/session-B/copilot-closeout-state.json"
    extra.write_text("{}", encoding="utf-8")
    # Shape of a consumer whose closeout predates R2 ownership: completion
    # present, no owner record, no release records, no shared text.
    (repo / own.TEXT).unlink()
    (repo / own.AREA / "owner.json").unlink()
    for release in (repo / own.AREA / "releases").iterdir():
        release.unlink()
    (repo / own.AREA / "releases").rmdir()
    start_session(repo, "session-A")
    acquire(repo)
    assert extra.read_text(encoding="utf-8") == "{}"
