"""Gemini CLI formal closeout and version 1.3 handoff admission tests.

Verifies that a prepared Gemini session can release R2 ownership only through an
owner-attested formal closeout with a valid Gemini CLI .jsonl transcript, and
that wrong session, wrong provider, missing/tampered/replayed attestation,
tampered snapshot bytes, foreign worktree, nested repo, and manual_fallback are
all refused fail-closed without release residue.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess

import pytest

from governance_tools import (
    closeout_attestation as attestation,
    closeout_handoff as h,
    closeout_status as status,
    gemini_closeout_publisher as gp,
    gemini_formal_closeout as cli,
    session_closeout_entry as entry,
    shared_closeout_ownership as r2,
)
from runtime_hooks.adapters.claude_code.session_lifecycle import session_start as claude_session_start
from runtime_hooks.adapters.gemini.session_lifecycle import session_start as gemini_session_start
from tests.test_shared_closeout_ownership import owner, prepare, repo, start_session as start_codex

SID = "session-A"
SID_B = "session-B"
ENVELOPE = f"artifacts/runtime/sessions/{SID}/session-envelope.json"
REQUEST = "Owner requested formal closeout for this Gemini CLI session."


def start_gemini(root, sid=SID):
    gemini_session_start(
        dict(hook_event_name="SessionStart", source="startup", session_id=sid, cwd=str(root)),
        root,
    )


def start_claude(root, sid=SID):
    claude_session_start(
        dict(hook_event_name="SessionStart", source="startup", session_id=sid, cwd=str(root)),
        root,
    )


def gemini_rows(root, *, sid=SID, cwd=None):
    project_hash = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    meta = {
        "sessionId": sid,
        "projectHash": project_hash,
        "startTime": "2026-11-20T00:00:00.000Z",
        "lastUpdated": "2026-11-20T00:00:02.000Z",
        "kind": "main",
    }
    if cwd is not None:
        meta["directories"] = [str(cwd)]
    return [
        meta,
        {
            "id": "msg-user-1",
            "timestamp": "2026-11-20T00:00:01.000Z",
            "type": "user",
            "content": [{"text": "do the thing"}],
        },
        {
            "id": "msg-gemini-1",
            "timestamp": "2026-11-20T00:00:02.000Z",
            "type": "gemini",
            "model": "gemini-2.5-pro",
            "content": "done",
            "tokens": {
                "input": 25,
                "output": 10,
                "cached": 0,
                "thoughts": 5,
                "tool": 0,
                "total": 40,
            },
        },
    ]


def write_rows(path, rows):
    path.write_bytes(b"".join(json.dumps(row).encode("utf-8") + b"\n" for row in rows))
    return path


def _ready(repo, monkeypatch, tmp_path, session_start):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    framework = repo / "SubModule/framework"
    framework.mkdir(parents=True)
    (framework / ".git").write_text("unit metadata", encoding="utf-8")
    (repo / ".gitmodules").write_text("unit registration", encoding="utf-8")
    (repo / "governance/framework.lock.json").write_text(
        '{"adopted_commit":"' + "a" * 40 + '"}', encoding="utf-8"
    )
    monkeypatch.setattr(h, "FRAMEWORK", framework)
    monkeypatch.setattr(h, "_framework_identity", lambda root: {
        "relative_path": "SubModule/framework",
        "gitlink_oid": "a" * 40,
        "checkout_head": "a" * 40,
        "adopted_commit": "a" * 40,
        "registration_blob": "b" * 40,
        "lock_blob": "c" * 40,
    })

    def git(root, *args):
        if args[0] == "ls-files":
            return (
                "160000 " + "a" * 40 + " 0\tSubModule/framework\0"
                + "100644 " + "b" * 40 + " 0\t.gitmodules\0"
                + "100644 " + "c" * 40 + " 0\tgovernance/framework.lock.json\0"
            )
        if args == ("rev-parse", "--show-toplevel"):
            return str(framework)
        if args[0] == "rev-parse":
            return "a" * 40
        if args[0] == "status":
            return "# branch.oid " + "a" * 40 + "\n# branch.head main"
        raise AssertionError(args)

    monkeypatch.setattr(h, "_git", git)
    prepare(repo, session_start=session_start)
    source = write_rows(tmp_path / "gemini.jsonl", gemini_rows(repo))
    payload = dict(
        hook_event_name="SessionEnd",
        session_id=SID,
        cwd=str(repo),
        transcript_path=str(source),
        reason="other",
    )
    return repo, source, payload


@pytest.fixture
def ready(repo, monkeypatch, tmp_path):
    return _ready(repo, monkeypatch, tmp_path, start_gemini)


def released(root):
    return owner(root)["state"] == "RELEASED"


def no_release_residue(root, *, sid=SID):
    record = owner(root)
    releases = root / r2.AREA / "releases"
    return (
        record["state"] != "RELEASED"
        and record["receipt_identity"] is None
        and not (root / "artifacts/runtime/closeout-completions" / f"{sid}.json").exists()
        and (not any(releases.glob("*.json")) if releases.is_dir() else True)
    )


# ── Positive paths ──────────────────────────────────────────────────────────

def test_p1_next_session_cannot_take_over_before_a_closes_out(ready):
    root = ready[0]
    assert owner(root)["session_id"] == SID
    with pytest.raises(r2.OwnershipError) as excinfo:
        prepare(root, SID_B, session_start=start_gemini)
    assert "OWNER_CONFLICT" in str(excinfo.value)
    assert owner(root)["session_id"] == SID


def test_p2_attested_formal_closeout_releases_and_next_session_acquires(ready):
    root, source, _ = ready
    before = owner(root)
    result = cli.close_out(root, SID, REQUEST, source, deadline_ms=30000)

    assert result["status"] == "FINALIZED"
    assert result["owner_state"] == "RELEASED"
    assert result["transcript_ingestion"] == "VERIFIED"
    assert result["attestation_id"] and result["request_id"]
    model = result["authorization_model"]
    assert "cooperative" in model
    assert "not authentication" in model
    assert "not attribution" in model
    assert released(root)

    stored = attestation.find(root, {
        k: before[k]
        for k in ("consumer_root", "session_id", "generation", "candidate_identity", "text_digest")
    })
    assert stored is not None
    assert stored["attestation_id"] == result["attestation_id"]
    assert stored["attestation"]["owner_statement"] == REQUEST

    db = root / "artifacts/codeburn_closeout_ingest.db"
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT p.provider, s.prompt_tokens, s.completion_tokens "
            "FROM step_ingestion_provenance p JOIN steps s ON p.step_id=s.step_id "
            "WHERE s.session_id=?",
            (SID,),
        ).fetchall()
    assert rows == [("gemini", 25, 10)]
    assert status.inspect_closeout(root, SID)["status"] == "FINALIZED"

    record = prepare(root, SID_B, session_start=start_gemini)
    assert record["session_id"] == SID_B
    assert record["generation"] == before["generation"] + 1


def test_p3_subdirectory_and_registered_framework_submodule_transcript_accepted(ready, tmp_path):
    root, _, _ = ready
    sub = root / "src" / "deep"
    sub.mkdir(parents=True)
    framework_sub = root / "SubModule/framework"
    (framework_sub / ".git").unlink()
    subprocess.run(["git", "init", "--quiet", str(framework_sub)], check=True)
    rows = gemini_rows(root, sid=SID, cwd=sub)
    rows[0]["directories"] = [str(sub), str(framework_sub)]
    source = write_rows(tmp_path / "gemini-sub.jsonl", rows)

    result = cli.close_out(root, SID, REQUEST, source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"
    assert released(root)


def test_p4_standing_owner_authorization_releases_and_rejects_self_authored_block(
    repo, monkeypatch, tmp_path
):
    slice_rel = "docs/slices/HANDOVER-01.md"
    auth_block = (
        "# Handover slice\n\n```text\n[Owner Closeout Authorization]\n"
        "SOURCE    = https://github.com/example/repo/issues/1#issuecomment-1\n"
        "CONDITION = Session A closes out after stage 1 tests pass\n```\n"
    )
    target = repo / slice_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(auth_block, encoding="utf-8")
    git_cmd = ["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
    subprocess.run(git_cmd + ["add", "--", slice_rel], check=True)
    subprocess.run(git_cmd + ["commit", "--quiet", "-m", "pre-session owner authorization"], check=True)
    prior_oid = subprocess.run(
        git_cmd + ["rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()

    root, source, _ = _ready(repo, monkeypatch, tmp_path, start_gemini)

    # A block committed AFTER session start must be refused as AUTHORIZATION_NOT_PRIOR
    later_rel = "docs/slices/SELF-AUTHORED.md"
    (root / later_rel).write_text(auth_block, encoding="utf-8")
    subprocess.run(git_cmd + ["add", "--", later_rel], check=True)
    subprocess.run(git_cmd + ["commit", "--quiet", "-m", "self-authored after start"], check=True)
    later_oid = subprocess.run(
        git_cmd + ["rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    with pytest.raises(h.HandoffError, match="AUTHORIZATION_NOT_PRIOR"):
        cli.close_out(
            root, SID, None, source, deadline_ms=30000,
            authorization_ref=f"{later_rel}@{later_oid}",
            condition_met="stage 1 tests pass",
        )
    assert not released(root)

    # The pre-committed authorization block succeeds
    result = cli.close_out(
        root, SID, None, source, deadline_ms=30000,
        authorization_ref=f"{slice_rel}@{prior_oid}",
        condition_met="stage 1 tests pass",
    )
    assert result["status"] == "FINALIZED"
    assert result["authorization_kind"] == "standing_owner_authorization"
    assert released(root)


# ── Negative controls ───────────────────────────────────────────────────────

def test_n1_missing_owner_request_rejected_without_side_effects(ready):
    root, source, _ = ready
    before = owner(root)
    code = cli.main(["--project-root", str(root), "--session-id", SID, "--transcript-path", str(source)])
    assert code == 1
    assert owner(root) == before
    assert no_release_residue(root)
    assert not (root / attestation.AREA).exists()
    assert not (root / "artifacts/runtime/closeout-requests").exists()


@pytest.mark.parametrize("bad_request", ["", "   \n\t  ", "x" * 5000])
def test_n2_blank_or_oversized_owner_request_rejected(ready, bad_request):
    root, source, _ = ready
    before = owner(root)
    with pytest.raises(h.HandoffError, match="INVALID_ATTESTATION"):
        cli.close_out(root, SID, bad_request, source)
    assert owner(root) == before
    assert no_release_residue(root)


@pytest.mark.parametrize("other_start", [start_codex, start_claude], ids=["codex", "claude"])
def test_n3_provider_isolation_against_codex_and_claude(repo, monkeypatch, tmp_path, other_start):
    root, _, payload = _ready(repo, monkeypatch, tmp_path, other_start)
    with pytest.raises(h.HandoffError, match="ENVELOPE_PROVIDER_MISMATCH"):
        gp.publish(root, payload, deadline_ms=30000)
    assert no_release_residue(root)


def test_n4_wrong_session_id_rejected(ready):
    root, source, _ = ready
    start_gemini(root, SID_B)
    with pytest.raises(r2.OwnershipError, match="OWNER_CONFLICT"):
        cli.close_out(root, SID_B, REQUEST, source)
    assert (owner(root)["session_id"], owner(root)["state"]) == (SID, "OWNED")
    assert no_release_residue(root)


def test_n5_unprepared_session_rejected(repo, tmp_path):
    start_gemini(repo, SID)
    source = write_rows(tmp_path / "gemini.jsonl", gemini_rows(repo))
    with pytest.raises(r2.OwnershipError, match="INVALID_OWNER"):
        cli.close_out(repo, SID, REQUEST, source)
    assert not (repo / attestation.AREA).exists()


def test_n6_unattested_handoff_consumption_refused_and_recoverable(ready):
    root, _, payload = ready
    published = gp.publish(root, payload, deadline_ms=30000)
    assert published["status"] == "REQUESTED"
    with pytest.raises(h.HandoffError, match="CLOSEOUT_NOT_ATTESTED"):
        h.consume_exact_request(
            root, published["request_id"], session_id=SID,
            provider=h.GeminiTranscriptProvider(root),
        )
    assert no_release_residue(root)

    # Attesting afterwards allows the same request to complete without stranding
    attestation.record(root, SID, REQUEST)
    final = h.consume_exact_request(
        root, published["request_id"], session_id=SID,
        provider=h.GeminiTranscriptProvider(root),
    )
    assert final["status"] == "FINALIZED"
    assert released(root)


def test_n7_unattested_direct_session_closeout_entry_refused(ready, monkeypatch, capsys):
    root = ready[0]
    assert attestation.find(root, owner(root)) is None
    monkeypatch.setattr(
        "sys.argv",
        ["closeout", "--project-root", str(root), "--session-id", SID,
         "--agent-id", "gemini", "--trigger-mode", "wrapper", "--format", "json",
         "--no-ledger-write"],
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    code = entry.main()
    out = capsys.readouterr().out
    assert code != 0 or "CLOSEOUT_NOT_ATTESTED" in out
    assert not released(root)
    assert no_release_residue(root)


def test_n8_manual_fallback_stays_rejected_even_with_attestation(ready, monkeypatch, capsys):
    root = ready[0]
    attestation.record(root, SID, REQUEST)
    monkeypatch.setattr(
        "sys.argv",
        ["closeout", "--project-root", str(root), "--session-id", SID,
         "--agent-id", "gemini", "--trigger-mode", "manual_fallback", "--format", "json",
         "--no-ledger-write"],
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    code = entry.main()
    out = capsys.readouterr().out
    assert code == 1 or "RELEASE_PROOF_INVALID" in out
    assert owner(root)["state"] == "OWNED"
    assert no_release_residue(root)


def test_n9_tampered_attestation_rejected_at_release(ready):
    root, _, payload = ready
    stored = attestation.record(root, SID, REQUEST)
    path = root / attestation.AREA / SID / f'{stored["attestation_id"]}.json'
    record = json.loads(path.read_bytes())
    record["attestation"]["owner_statement"] = "something the owner never said"
    path.write_bytes(h.canonical_bytes(record))

    published = gp.publish(root, payload, deadline_ms=30000)
    with pytest.raises(h.HandoffError, match="CLOSEOUT_NOT_ATTESTED"):
        h.consume_exact_request(
            root, published["request_id"], session_id=SID,
            provider=h.GeminiTranscriptProvider(root),
        )
    assert not released(root)


def test_n10_replayed_attestation_from_older_generation_cannot_release(ready):
    root, _, payload = ready
    stale = attestation.record(root, SID, REQUEST)
    first_gen = owner(root)["generation"]

    prepare(root, SID, version=2, session_start=lambda *_a, **_k: None)
    assert owner(root)["generation"] == first_gen + 1

    published = gp.publish(root, payload, deadline_ms=30000)
    with pytest.raises(h.HandoffError, match="CLOSEOUT_NOT_ATTESTED"):
        h.consume_exact_request(
            root, published["request_id"], session_id=SID,
            provider=h.GeminiTranscriptProvider(root),
        )
    assert not released(root)
    assert (root / attestation.AREA / SID / f'{stale["attestation_id"]}.json').is_file()


def test_n11_reconcile_release_cannot_release_unattested_gemini_session(ready):
    root = ready[0]
    record = owner(root)
    with pytest.raises((r2.OwnershipError, ValueError)):
        r2.reconcile_release(root, SID, record["generation"], record["receipt_identity"] or "x" * 64)
    assert not released(root)


def test_n12_transcript_negative_controls_wrong_session_project_hash_nested_repo_and_tampered_bytes(
    ready, tmp_path
):
    root, _, payload = ready

    # Wrong sessionId in transcript
    bad_sid = write_rows(tmp_path / "bad-sid.jsonl", gemini_rows(root, sid=SID_B))
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_SESSION_MISMATCH"):
        gp.publish(root, {**payload, "transcript_path": str(bad_sid)}, deadline_ms=30000)

    # Foreign repo projectHash
    foreign = tmp_path / "foreign-repo"
    foreign.mkdir()
    subprocess.run(["git", "init", "--quiet", str(foreign)], check=True)
    bad_proj = write_rows(tmp_path / "bad-proj.jsonl", gemini_rows(foreign, sid=SID))
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_SESSION_MISMATCH"):
        gp.publish(root, {**payload, "transcript_path": str(bad_proj)}, deadline_ms=30000)

    # Unregistered nested git repository inside consumer
    nested = root / "vendor" / "nested"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(nested)], check=True)
    bad_nested = write_rows(tmp_path / "bad-nested.jsonl", gemini_rows(root, sid=SID, cwd=nested))
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_SESSION_MISMATCH"):
        gp.publish(root, {**payload, "transcript_path": str(bad_nested)}, deadline_ms=30000)

    # Valid publish, then tamper with snapshot bytes before consume
    attestation.record(root, SID, REQUEST)
    published = gp.publish(root, payload, deadline_ms=30000)
    req = h._read(r2._closeout_request_slot(root, SID))
    snap = root / req["binding"]["transcript"]["immutable_locator"]
    snap.write_bytes(snap.read_bytes() + b"\n")
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_BYTES_MISMATCH"):
        h.consume_exact_request(
            root, published["request_id"], session_id=SID,
            provider=h.GeminiTranscriptProvider(root),
        )


def test_n13_uningestable_transcript_without_gemini_turn_rejected_before_request_or_hold(
    ready, tmp_path
):
    root, valid_source, _ = ready
    header_only = gemini_rows(root, sid=SID)[:2]  # header + user message only, no gemini turn
    bad_source = write_rows(tmp_path / "header-only.jsonl", header_only)

    with pytest.raises(h.HandoffError, match="TRANSCRIPT_INGESTION_UNCONFIRMED"):
        cli.close_out(root, SID, REQUEST, bad_source, deadline_ms=30000)

    # Request was NOT published and R2 was NOT stranded in HOLD
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] == "OWNED"
    assert no_release_residue(root)

    # Operator can now supply the valid transcript and complete formal closeout
    result = cli.close_out(root, SID, REQUEST, valid_source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"
    assert released(root)


def test_p5_cached_tokens_subtracted_from_prompt_tokens(ready, tmp_path):
    root, _, _ = ready
    rows = gemini_rows(root, sid=SID)
    rows[2]["tokens"] = {
        "input": 100,
        "output": 20,
        "cached": 60,
        "thoughts": 5,
        "tool": 0,
        "total": 125,
    }
    source = write_rows(tmp_path / "gemini-cached.jsonl", rows)

    result = cli.close_out(root, SID, REQUEST, source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"

    db = root / "artifacts/codeburn_closeout_ingest.db"
    with sqlite3.connect(db) as conn:
        ingested = conn.execute(
            "SELECT s.prompt_tokens, s.completion_tokens "
            "FROM step_ingestion_provenance p JOIN steps s ON p.step_id=s.step_id "
            "WHERE s.session_id=?",
            (SID,),
        ).fetchall()
    assert ingested == [(40, 20)]


def test_n14_overflow_tokens_and_unbound_set_directories_rejected_before_hold(
    ready, tmp_path
):
    root, valid_source, _ = ready

    # 1. SQLite INTEGER overflow in tokens.input rejected before request freeze or HOLD
    overflow_rows = gemini_rows(root, sid=SID)
    overflow_rows[2]["tokens"]["input"] = 1 << 63
    overflow_source = write_rows(tmp_path / "overflow.jsonl", overflow_rows)
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_INGESTION_UNCONFIRMED"):
        cli.close_out(root, SID, REQUEST, overflow_source, deadline_ms=30000)
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] == "OWNED"

    # 2. cached > input rejected before request freeze or HOLD
    bad_cache_rows = gemini_rows(root, sid=SID)
    bad_cache_rows[2]["tokens"] = {"input": 10, "output": 5, "cached": 20}
    bad_cache_source = write_rows(tmp_path / "bad-cache.jsonl", bad_cache_rows)
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_INGESTION_UNCONFIRMED"):
        cli.close_out(root, SID, REQUEST, bad_cache_source, deadline_ms=30000)
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] == "OWNED"

    # 3. $set.directories pointing outside the consumer worktree rejected before request freeze or HOLD
    foreign = tmp_path / "foreign-set-dir"
    foreign.mkdir()
    subprocess.run(["git", "init", "--quiet", str(foreign)], check=True)
    bad_set_rows = [*gemini_rows(root, sid=SID), {"$set": {"directories": [str(foreign)]}}]
    bad_set_source = write_rows(tmp_path / "bad-set.jsonl", bad_set_rows)
    with pytest.raises(h.HandoffError, match="TRANSCRIPT_SESSION_MISMATCH"):
        cli.close_out(root, SID, REQUEST, bad_set_source, deadline_ms=30000)
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] == "OWNED"

    # Valid transcript still closes out cleanly
    result = cli.close_out(root, SID, REQUEST, valid_source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"
    assert released(root)


def test_p6_duplicate_message_id_updates_coalesced_and_crlf_byte_offsets_exact(
    ready, tmp_path
):
    root, _, _ = ready
    base_rows = gemini_rows(root, sid=SID)
    # Simulate Gemini CLI recordToolCalls re-appending msg-gemini-1 with the same id & tokens,
    # followed by a second distinct model turn msg-gemini-2.
    updated_turn_1 = {
        **base_rows[2],
        "toolCalls": [{"id": "call-1", "name": "run_shell_command"}],
    }
    turn_2 = {
        "id": "msg-gemini-2",
        "timestamp": "2026-11-20T00:00:03.000Z",
        "type": "gemini",
        "model": "gemini-2.5-pro",
        "content": "all done",
        "tokens": {"input": 15, "output": 5, "cached": 0, "thoughts": 0, "tool": 0, "total": 20},
    }
    rows = [base_rows[0], base_rows[1], base_rows[2], updated_turn_1, turn_2]
    encoded_lines = [json.dumps(r).encode("utf-8") + b"\r\n" for r in rows]
    crlf_source = tmp_path / "gemini-crlf.jsonl"
    crlf_source.write_bytes(b"".join(encoded_lines))

    expected_offset_turn_1_update = sum(len(line) for line in encoded_lines[:3])
    expected_offset_turn_2 = sum(len(line) for line in encoded_lines[:4])

    result = cli.close_out(root, SID, REQUEST, crlf_source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"

    db = root / "artifacts/codeburn_closeout_ingest.db"
    with sqlite3.connect(db) as conn:
        ingested = conn.execute(
            "SELECT s.command, s.prompt_tokens, s.completion_tokens, "
            "p.source_record_line, p.source_record_offset "
            "FROM step_ingestion_provenance p JOIN steps s ON p.step_id=s.step_id "
            "WHERE s.session_id=? ORDER BY p.source_record_line",
            (SID,),
        ).fetchall()
    assert ingested == [
        ("gemini-log-ingestion:msg-gemini-1", 25, 10, 4, expected_offset_turn_1_update),
        ("gemini-log-ingestion:msg-gemini-2", 15, 5, 5, expected_offset_turn_2),
    ]
