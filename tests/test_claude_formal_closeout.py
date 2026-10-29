"""The four safety properties #233 actually has to hold, and nothing else.

Scoped deliberately: this is not a second copy of the admission suite. The
cross-provider property the owner listed is already covered end to end by
test_n17_codex_request_cannot_bind_a_claude_envelope in
tests/test_claude_closeout_admission.py, so it is referenced rather than
duplicated here.

Every refusal asserts side-effect absence as well as the error, because a
rejection on its own is not evidence of safety.
"""
import json

import pytest

from governance_tools import claude_formal_closeout as cli
from governance_tools import closeout_attestation as attestation
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2
from tests.test_shared_closeout_ownership import prepare, owner
from tests.test_claude_closeout_admission import (  # noqa: F401 - fixtures
    ENVELOPE, SID, ready, repo, start_claude, write_rows, claude_rows)

REQUEST = "please close out this session"


def released(root):
    record = owner(root)
    return record["state"] == "RELEASED"


def no_release_residue(root, *, sid=SID):
    """Nothing a later call could consume, and no completion claimed."""
    record = owner(root)
    releases = root / r2.AREA / "releases"
    return (record["state"] != "RELEASED"
            and record["receipt_identity"] is None
            and not (root / "artifacts/runtime/closeout-completions" / f"{sid}.json").exists()
            and not any(releases.glob("*.json")) if releases.is_dir() else True)


# --------------------------------------------------------------------------
# S1 / S2 — the product property, both directions
# --------------------------------------------------------------------------

def test_s1_next_session_cannot_take_over_before_a_closes_out(ready):
    """A holds the worktree; B must not be able to acquire it."""
    root = ready[0]
    assert owner(root)["session_id"] == SID
    with pytest.raises(r2.OwnershipError) as excinfo:
        prepare(root, "session-B", session_start=start_claude)
    assert "OWNER_CONFLICT" in str(excinfo.value)
    assert owner(root)["session_id"] == SID


def test_s2_next_session_takes_over_after_a_formally_closes_out(ready):
    """One command: attest, publish, release. Then B acquires."""
    root, source, _ = ready
    before = owner(root)
    result = cli.close_out(root, SID, REQUEST, source, deadline_ms=30000)

    assert result["status"] == "FINALIZED"
    assert result["owner_state"] == "RELEASED"
    assert result["transcript_ingestion"] == "VERIFIED"
    assert result["attestation_id"] and result["request_id"]
    # The command must not overstate what it proved. Asserted as substance, so
    # the wording can improve but cannot quietly strengthen.
    model = result["authorization_model"]
    assert "cooperative" in model
    assert "not authentication" in model
    assert "not attribution" in model

    # The attestation is on disk, bound to the generation that was released.
    stored = attestation.find(root, {**{k: before[k] for k in
                                        ("consumer_root", "session_id", "generation",
                                         "candidate_identity", "text_digest")}})
    assert stored is not None
    assert stored["attestation_id"] == result["attestation_id"]
    assert stored["attestation"]["owner_statement"] == REQUEST

    record = prepare(root, "session-B", session_start=start_claude)
    assert record["session_id"] == "session-B"
    assert record["generation"] == before["generation"] + 1


# --------------------------------------------------------------------------
# S3 — no release without a current, matching attestation
# --------------------------------------------------------------------------

def test_s3_release_without_any_attestation_is_refused(ready):
    """The gate is in the core, so bypassing the CLI does not bypass it."""
    root, source, payload = ready
    from governance_tools import claude_closeout_publisher as publisher
    result = publisher.publish(root, payload, deadline_ms=30000)
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, result["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert "CLOSEOUT_NOT_ATTESTED" in str(excinfo.value)
    assert not released(root)


def test_s3_replayed_attestation_from_an_older_generation_cannot_release(ready):
    """An attestation authorizes one generation's exact summary bytes."""
    root, source, payload = ready
    stale = attestation.record(root, SID, REQUEST)
    first_generation = owner(root)["generation"]

    # A legitimate re-preparation advances the generation; the old attestation
    # must not carry over to it.
    # Re-prepare the same session: its envelope already exists, so no
    # SessionStart runs. Only the owner generation advances.
    prepare(root, SID, version=2, session_start=lambda *a, **k: None)
    assert owner(root)["generation"] == first_generation + 1

    from governance_tools import claude_closeout_publisher as publisher
    result = publisher.publish(root, payload, deadline_ms=30000)
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, result["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert "CLOSEOUT_NOT_ATTESTED" in str(excinfo.value)
    assert not released(root)
    # The stale record still exists; it simply does not authorize anything.
    assert (root / attestation.AREA / SID / f'{stale["attestation_id"]}.json').is_file()


def test_s3_tampered_attestation_is_not_accepted(ready):
    """Editing the bytes breaks the identity the filename asserts."""
    root, source, payload = ready
    stored = attestation.record(root, SID, REQUEST)
    path = root / attestation.AREA / SID / f'{stored["attestation_id"]}.json'
    record = json.loads(path.read_bytes())
    record["attestation"]["owner_statement"] = "something the owner never said"
    path.write_bytes(h.canonical_bytes(record))

    from governance_tools import claude_closeout_publisher as publisher
    result = publisher.publish(root, payload, deadline_ms=30000)
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, result["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert "CLOSEOUT_NOT_ATTESTED" in str(excinfo.value)
    assert not released(root)


# --------------------------------------------------------------------------
# S4 — a refusal leaves nothing usable, and does not strand the session
# --------------------------------------------------------------------------

def test_s4_refusal_leaves_no_usable_evidence_and_does_not_strand(ready):
    """The pair: no wrongful release, and no permanent block."""
    root, source, payload = ready
    from governance_tools import claude_closeout_publisher as publisher
    result = publisher.publish(root, payload, deadline_ms=30000)

    with pytest.raises(h.HandoffError):
        h.consume_exact_request(root, result["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))

    # Nothing a later call could consume, and no completion claimed. The early
    # gate refuses before begin_closeout reserves a receipt identity, so the
    # owner is untouched rather than parked in HOLD.
    record = owner(root)
    assert record["state"] == "OWNED"
    assert record["receipt_identity"] is None
    assert not (root / "artifacts/runtime/closeout-completions" / f"{SID}.json").exists()
    releases = root / r2.AREA / "releases"
    assert not releases.is_dir() or not any(releases.glob("*.json"))

    # And the session is not stranded: attesting now lets the same request
    # through, so the refusal was a gate rather than a dead end.
    attestation.record(root, SID, REQUEST)
    final = h.consume_exact_request(root, result["request_id"], session_id=SID,
                                    provider=h.ClaudeTranscriptProvider(root))
    assert final["status"] == "FINALIZED"
    assert released(root)


# --------------------------------------------------------------------------
# The claim ceiling is part of the contract, so it is asserted
# --------------------------------------------------------------------------

def test_the_attestation_does_not_claim_authentication():
    """If this wording drifts upward, the test fails rather than the docs."""
    text = attestation.__doc__
    assert "NOT authentication" in text
    assert "NOT proof of human origin" in text
    assert "NOT non-repudiation" in text
    assert "cooperative" in text.lower()


# --------------------------------------------------------------------------
# Cross-entry coverage: the gate is at the convergence point, not per entry
# --------------------------------------------------------------------------

def test_old_entry_cannot_release_an_unattested_claude_session(ready, monkeypatch, capsys):
    """session_closeout_entry does not route through consume_exact_request.

    It reaches finalize_release directly at session_closeout_entry.py:654 with a
    legal `wrapper` trigger mode, so a gate placed only in the handoff would
    leave this entry open. Checked rather than assumed.
    """
    from governance_tools import session_closeout_entry as entry
    root = ready[0]
    assert attestation.find(root, owner(root)) is None

    monkeypatch.setattr("sys.argv", ["closeout", "--project-root", str(root),
                                     "--session-id", SID, "--agent-id", "claude",
                                     "--trigger-mode", "wrapper", "--format", "json",
                                     "--no-ledger-write"])
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    code = entry.main()
    out = capsys.readouterr().out

    assert code != 0 or "CLOSEOUT_NOT_ATTESTED" in out
    record = owner(root)
    assert record["state"] != "RELEASED"
    releases = root / r2.AREA / "releases"
    assert not releases.is_dir() or not any(releases.glob("*.json"))
    assert not (root / "artifacts/runtime/closeout-completions" / f"{SID}.json").exists()


def test_old_entry_provider_comes_from_the_envelope_not_agent_id(ready, monkeypatch, capsys):
    """A caller-supplied agent_id must not decide whether the gate applies."""
    from governance_tools import session_closeout_entry as entry
    root = ready[0]
    assert json.loads((root / ENVELOPE).read_bytes())["provider"] == "claude"

    # Claim to be codex while the canonical envelope says claude.
    monkeypatch.setattr("sys.argv", ["closeout", "--project-root", str(root),
                                     "--session-id", SID, "--agent-id", "codex",
                                     "--trigger-mode", "wrapper", "--format", "json",
                                     "--no-ledger-write"])
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    code = entry.main()
    out = capsys.readouterr().out
    assert code != 0 or "CLOSEOUT_NOT_ATTESTED" in out
    assert owner(root)["state"] != "RELEASED"


def test_reconcile_release_cannot_release_an_unattested_claude_session(ready):
    """reconcile_release reaches finalize_release directly too."""
    root = ready[0]
    record = owner(root)
    with pytest.raises((r2.OwnershipError, ValueError)):
        r2.reconcile_release(root, SID, record["generation"],
                             record["receipt_identity"] or "x" * 64)
    assert owner(root)["state"] != "RELEASED"


def test_codex_release_path_is_unaffected_by_the_claude_gate(repo, monkeypatch, capsys):
    """A codex-envelope session must not start needing an attestation."""
    from governance_tools import session_closeout_entry as entry
    import io
    prepare(repo)  # the shared harness uses the Codex SessionStart
    assert json.loads((repo / ENVELOPE).read_bytes())["provider"] == "codex"
    assert attestation.find(repo, owner(repo)) is None

    monkeypatch.setattr("sys.argv", ["closeout", "--project-root", str(repo),
                                     "--session-id", SID, "--agent-id", "codex",
                                     "--trigger-mode", "synthetic_smoke",
                                     "--format", "json", "--no-ledger-write"])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    entry.main()
    # The point is only that the claude gate did not reject it.
    assert "CLOSEOUT_NOT_ATTESTED" not in capsys.readouterr().out


# --------------------------------------------------------------------------
# #245 P2 — a malformed record must not block a legitimate handover
# --------------------------------------------------------------------------

def test_malformed_attestation_sorted_first_does_not_block_a_legal_handover(ready):
    """The no-permanent-block half of #233.

    find() scans sorted(glob("*.json")), so a bad record whose id sorts first
    is seen first. Before the fix, attested_at=null raised TypeError out of
    datetime.fromisoformat — which _require never sees and find did not catch —
    so one bad file aborted the scan and a valid attestation later in the order
    could never be found. A legitimate re-authorization then failed forever.
    """
    root, source, _ = ready
    valid = attestation.record(root, SID, REQUEST)

    bad_id = "0" * 64  # sorts before any real digest
    directory = root / attestation.AREA / SID
    bad = dict(json.loads((directory / f'{valid["attestation_id"]}.json').read_bytes()))
    bad["attestation"] = {**bad["attestation"], "attested_at": None}
    (directory / f"{bad_id}.json").write_bytes(h.canonical_bytes(bad))
    assert sorted(p.stem for p in directory.glob("*.json"))[0] == bad_id

    # The valid record is still found, and the handover still completes.
    found = attestation.find(root, owner(root))
    assert found is not None and found["attestation_id"] == valid["attestation_id"]

    result = cli.close_out(root, SID, REQUEST, source, deadline_ms=30000)
    assert result["status"] == "FINALIZED"
    assert released(root)


@pytest.mark.parametrize("value", [None, 0, [], {}, True])
def test_malformed_timestamp_types_are_refused_not_raised(ready, value):
    """Each bad type yields a governed refusal, never a bare TypeError."""
    root = ready[0]
    record = attestation.build(owner(root), REQUEST)
    record["attestation"]["attested_at"] = value
    with pytest.raises(h.HandoffError) as excinfo:
        attestation.validate(record, root)
    assert "INVALID_ATTESTATION" in str(excinfo.value)
