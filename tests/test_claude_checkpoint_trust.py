"""S1 regression: only prepare-vouched candidate bytes may be checkpointed.

Expected behavior comes from the owner's reproduced tamper/resume/exit case.
All repositories and progress summaries here are synthetic test fixtures.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_claude_session_lifecycle import (
    INPUT, SID_A, SID_B, consumer, end, framework_source, invoke, lc, owner,
    repo, save, start,
)
from runtime_hooks.core import _canonical_closeout as core


def _prepare(root: Path, summary: str) -> dict:
    result = invoke(root, sid=SID_A, inputs={**INPUT, "work_summary": summary})
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def _tamper(path: Path) -> None:
    candidate = json.loads(path.read_bytes())
    candidate["work_summary"] = "TAMPERED summary"
    path.write_text(json.dumps(candidate), encoding="utf-8")


def _assert_untrusted(root: Path, checkpoint: dict) -> None:
    assert checkpoint["candidate"] is None
    assert checkpoint["candidate_rejected"]
    persisted = json.loads((root / lc.CHECKPOINTS_DIR / f"{SID_A}.json").read_bytes())
    assert persisted["candidate"] is None
    assert persisted["candidate_rejected"] == checkpoint["candidate_rejected"]
    resumed = start(root, source="resume")
    assert resumed["readback"]["state"] == "exit_unconfirmed"
    assert resumed["readback"]["summary"] is None
    assert "TAMPERED summary" not in resumed["additional_context"]


def test_refused_summary_is_not_laundered_by_next_session_end(consumer):
    start(consumer)
    prepared = _prepare(consumer, "original summary")
    assert end(consumer)["candidate"] == prepared["candidate_identity"]
    owner_bytes = (consumer / lc.OWNER_RECORD).read_bytes()
    text_bytes = (consumer / "artifacts/session-closeout.txt").read_bytes()
    _tamper(consumer / prepared["candidate_identity"]["relative_path"])

    first = start(consumer, source="resume")["readback"]
    assert first["state"] == "checkpoint_mismatch" and first["summary"] is None
    rejected = end(consumer)
    second = start(consumer, source="resume")
    assert second["readback"]["summary"] is None  # the original bug serves tampered bytes here
    _assert_untrusted(consumer, rejected)
    assert rejected["candidate_rejected"] == "candidate_identity_mismatch"
    # Another exit, without a real prepare, cannot upgrade trust either.
    _assert_untrusted(consumer, end(consumer))
    assert (consumer / lc.OWNER_RECORD).read_bytes() == owner_bytes
    assert (consumer / "artifacts/session-closeout.txt").read_bytes() == text_bytes
    assert not (consumer / "artifacts/runtime/closeout-completions").exists()


def test_real_prepare_recovers_after_a_refused_session_exit(consumer):
    start(consumer)
    first = _prepare(consumer, "first summary")
    end(consumer)
    _tamper(consumer / first["candidate_identity"]["relative_path"])
    assert start(consumer, source="resume")["readback"]["state"] == "checkpoint_mismatch"
    _assert_untrusted(consumer, end(consumer))

    recovered = _prepare(consumer, "recovered summary")
    assert recovered["generation"] == 2
    assert recovered["candidate_identity"] != first["candidate_identity"]
    assert owner(consumer)["candidate_identity"] == recovered["candidate_identity"]
    assert start(consumer, source="resume")["readback"]["summary"] is None
    assert end(consumer)["candidate"] == recovered["candidate_identity"]
    readback = start(consumer, source="resume")["readback"]
    assert readback["state"] == "checkpointed"
    assert "recovered summary" in readback["summary"]
    assert "TAMPERED" not in readback["summary"]


def test_tamper_before_first_exit_is_rejected(repo):
    start(repo)
    candidate = save(repo, SID_A, work_summary="prepared summary")
    _tamper(candidate)
    _assert_untrusted(repo, end(repo))


@pytest.mark.parametrize("fault", [
    "missing_owner", "malformed_owner", "non_object_owner", "missing_identity",
    "non_object_identity", "foreign_session", "foreign_root", "missing_generation",
    "zero_generation", "bool_generation", "wrong_schema", "released_wrong_hash", "hold",
    "wrong_path", "wrong_hash",
])
def test_candidate_requires_a_matching_prepared_owner(repo, fault):
    start(repo)
    save(repo, SID_A, work_summary="untrusted without a matching prepare record")
    record = owner(repo)
    path = repo / lc.OWNER_RECORD
    if fault == "missing_owner":
        path.unlink()
    elif fault in {"malformed_owner", "non_object_owner"}:
        path.write_text("{" if fault == "malformed_owner" else "[]", encoding="utf-8")
    else:
        if fault == "missing_identity":
            record.pop("candidate_identity")
        elif fault == "non_object_identity":
            record["candidate_identity"] = []
        elif fault == "foreign_session":
            record["session_id"] = SID_B
        elif fault == "foreign_root":
            record["consumer_root"] = str(repo / "elsewhere")
        elif fault == "missing_generation":
            record.pop("generation")
        elif fault == "zero_generation":
            record["generation"] = 0
        elif fault == "bool_generation":
            record["generation"] = True
        elif fault == "wrong_schema":
            record["schema_version"] = "unknown"
        elif fault == "released_wrong_hash":
            record["state"] = "RELEASED"
            record["candidate_identity"]["sha256"] = "0" * 64
        elif fault == "hold":
            record.update(state="HOLD", hold_reason="preparation_pending")
        elif fault == "wrong_path":
            record["candidate_identity"]["relative_path"] = "evidence.txt"
        elif fault == "wrong_hash":
            record["candidate_identity"]["sha256"] = "0" * 64
        path.write_text(json.dumps(record), encoding="utf-8")
    before = path.read_bytes() if path.exists() else None
    _assert_untrusted(repo, end(repo))
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize("same_bytes", [False, True])
def test_unprepared_newer_candidate_never_becomes_trusted(repo, same_bytes):
    start(repo)
    prepared = save(repo, SID_A, work_summary="prepared summary")
    prior = end(repo)["candidate"]
    newer = prepared.with_name("99991231T235959999999Z.json")
    newer.write_bytes(prepared.read_bytes())
    if not same_bytes:
        _tamper(newer)
    for _ in range(2):
        assert end(repo)["candidate"] == prior
        readback = start(repo, source="resume")["readback"]
        assert readback["state"] == "newer_summary_after_checkpoint"
        assert readback["source"] == prior["relative_path"]
        assert "prepared summary" in readback["summary"] and "TAMPERED" not in readback["summary"]


def test_candidate_written_without_prepare_has_no_trust_anchor(repo):
    start(repo)
    core.write_candidate(SID_A, repo, {"task_intent": "synthetic", "work_summary": "unprepared"})
    _assert_untrusted(repo, end(repo))


def test_candidate_scan_permission_error_still_writes_rejection(repo, monkeypatch):
    start(repo)
    save(repo, SID_A, work_summary="prepared summary")
    assert end(repo)["candidate"] is not None
    candidate_dir = repo / lc.CANDIDATES_DIR / SID_A
    is_dir = Path.is_dir

    def deny_candidate_scan(path):
        if path == candidate_dir:
            raise PermissionError("synthetic candidate directory probe failure")
        return is_dir(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "is_dir", deny_candidate_scan)
        checkpoint = end(repo)
    assert checkpoint["candidate_rejected"] == "candidate_unreadable"
    _assert_untrusted(repo, checkpoint)


def test_checkpoint_probe_permission_error_still_writes_rejection(repo, monkeypatch):
    start(repo)
    prepared = save(repo, SID_A, work_summary="prepared summary")
    assert end(repo)["candidate"] is not None
    prepared.with_name("99991231T235959999999Z.json").write_bytes(prepared.read_bytes())
    checkpoint_path = repo / lc.CHECKPOINTS_DIR / f"{SID_A}.json"

    def deny_checkpoint_probe(probe):
        def probe_path(path, *args, **kwargs):
            if path == checkpoint_path:
                raise PermissionError("synthetic checkpoint probe failure")
            return probe(path, *args, **kwargs)
        return probe_path

    with monkeypatch.context() as patch:
        patch.setattr(Path, "is_file", deny_checkpoint_probe(Path.is_file))
        patch.setattr(Path, "lstat", deny_checkpoint_probe(Path.lstat))
        checkpoint = end(repo)
    _assert_untrusted(repo, checkpoint)


@pytest.mark.parametrize("fault", ["missing", "hold", "different_sha"])
def test_previous_checkpoint_requires_r2_vouch(repo, fault):
    start(repo)
    save(repo, SID_A, work_summary="prepared summary")
    end(repo)
    path = repo / lc.OWNER_RECORD
    record = owner(repo)
    if fault == "missing":
        path.unlink()
    else:
        if fault == "hold":
            record.update(state="HOLD", hold_reason="preparation_pending")
        else:
            record["candidate_identity"]["sha256"] = "0" * 64
        path.write_text(json.dumps(record), encoding="utf-8")
    _assert_untrusted(repo, end(repo))


@pytest.mark.parametrize("prepared", [False, True])
def test_no_candidate_never_binds_file_bytes(repo, prepared):
    start(repo)
    if prepared:
        save(repo, SID_A).unlink()
    checkpoint = end(repo)
    assert checkpoint["candidate"] is None
    assert json.loads((repo / lc.CHECKPOINTS_DIR / f"{SID_A}.json").read_bytes())["candidate"] is None
    resumed = start(repo, source="resume")["readback"]
    assert resumed["state"] == "exited_without_summary" and resumed["summary"] is None
