"""Tranche 1 admission tests for the Claude formal closeout path (#233).

Negative-first by design: this path is only meaningful if it fails closed.
Synthetic payloads are not evidence that a Claude hook fired, and a passing
test here is not evidence of completeness or anti-forgery authority.

Coverage is deliberately split, and the split is the honest state of the work:

- Live: the structural admission rules (N1, N1b, N3, N15), the transcript
  record-shape rules reached during capture (N5, N6, N12, N13), the missing
  envelope case (N7), the manual_fallback regression guard (N14) and the
  envelope-provider binding (N16).
- Strict xfail on P1-a: everything that needs a SUCCESSFULLY PUBLISHED Claude
  request (N2, N4, N8, N9, N10, N11) and the end-to-end P1/P2. See
  BLOCKED_ON_P1A. These are not "known failures to ignore"; strict xfail means
  the suite fails if they start passing, which is the signal that P1-a landed
  and this coverage must be reinstated.

Nothing in this module asserts that the envelope leg works. It cannot: a
qualified Claude envelope is unrepresentable in the current canonical contract.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from governance_tools import claude_closeout_publisher as c
from governance_tools import closeout_handoff as h
from governance_tools import native_closeout_publisher as n
from governance_tools import session_closeout_entry as entry
from governance_tools import shared_closeout_ownership as r2
from tests.test_shared_closeout_ownership import repo, prepare, owner

BLOCKED_ON_P1A = (
    "blocked on P1-a: R1 requires a root-bound schema 1.1 envelope, and the canonical "
    "reader only recognises providers codex and github-copilot-vscode "
    "(_ROOT_BOUND_SOURCE_BY_PROVIDER), binding provider to repo_binding.source. A "
    "qualified Claude envelope is therefore unrepresentable, so no Claude request can "
    "be published and these cases cannot be set up honestly. They passed before only "
    "because the request bound a non-Claude envelope, which N16 now rejects. Strict "
    "xfail is the tripwire for P1-a landing; its fix is in #232's file set."
)

SID = "session-A"
ENVELOPE = f"artifacts/runtime/sessions/{SID}/session-envelope.json"


def claude_rows(root, *, sid=SID, cwd=None):
    """A Claude-shaped transcript: queue-operation first, cwd on a later record."""
    return [
        {"type": "queue-operation", "operation": "enqueue", "sessionId": sid,
         "timestamp": "2026-10-23T04:19:15.518Z", "content": "do the thing"},
        {"type": "user", "sessionId": sid, "cwd": str(cwd or root),
         "message": {"role": "user", "content": "do the thing"}},
        {"type": "assistant", "sessionId": sid, "cwd": str(cwd or root),
         "message": {"role": "assistant", "content": "done"}},
    ]


def write_rows(path, rows):
    path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in rows))
    return path




@pytest.fixture
def ready(repo, monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    # Unit registration boundary; real Git qualification/drift runs separately.
    framework = repo / "SubModule/framework"
    framework.mkdir(parents=True)
    (framework / ".git").write_text("unit metadata")
    (repo / ".gitmodules").write_text("unit registration")
    (repo / "governance/framework.lock.json").write_text('{"adopted_commit":"' + "a" * 40 + '"}')
    monkeypatch.setattr(h, "FRAMEWORK", framework)
    monkeypatch.setattr(h, "_framework_identity", lambda root: {
        "relative_path": "SubModule/framework", "gitlink_oid": "a" * 40,
        "checkout_head": "a" * 40, "adopted_commit": "a" * 40,
        "registration_blob": "b" * 40, "lock_blob": "c" * 40})

    def git(root, *args):
        if args[0] == "ls-files":
            return ("160000 " + "a" * 40 + " 0\tSubModule/framework\0"
                    + "100644 " + "b" * 40 + " 0\t.gitmodules\0"
                    + "100644 " + "c" * 40 + " 0\tgovernance/framework.lock.json\0")
        if args == ("rev-parse", "--show-toplevel"):
            return str(framework)
        if args[0] == "rev-parse":
            return "a" * 40
        if args[0] == "status":
            return "# branch.oid " + "a" * 40 + "\n# branch.head main"
        raise AssertionError(args)

    monkeypatch.setattr(h, "_git", git)
    prepare(repo)
    source = write_rows(tmp_path / "claude.jsonl", claude_rows(repo))
    payload = dict(hook_event_name="SessionEnd", session_id=SID, cwd=str(repo),
                   transcript_path=str(source), reason="other")
    return repo, source, payload


def publish(ready, **kwargs):
    return c.publish(ready[0], ready[2], deadline_ms=30000, **kwargs)


def request_of(root):
    return h._read(r2._closeout_request_slot(root, SID))


def claude_request(root, **overrides):
    """A structurally valid Claude request built without publishing one.

    Publication is blocked while P1-a stands, so the structural admission tests
    must not depend on it. Nothing here touches the filesystem beyond the
    envelope digest, and _validate_request checks shapes and digests rather
    than file existence.
    """
    sid = overrides.pop("session_id", SID)
    o = owner(root)
    base = f"artifacts/runtime/handoff-transcripts/{sid}"
    sha, manifest_sha = "a" * 64, "b" * 64
    ref = dict(schema_version="1.0", source_kind=h.CLAUDE_SOURCE_KIND, session_id=sid,
               immutable_locator=f"{base}/snapshots/{sha}.jsonl", sha256=sha, size_bytes=10,
               manifest_locator=f"{base}/manifests/{manifest_sha}.json",
               manifest_sha256=manifest_sha,
               ref_locator=f"{base}/refs/{manifest_sha}.json",
               retention_contract="owned-sessionend-snapshot", retention_version="1.0",
               readable_after_hook=True, **h.AUTHORITY)
    ref.update(overrides.pop("transcript", {}))
    binding = {k: o[k] for k in ("consumer_root", "session_id", "generation",
                                 "candidate_identity", "text_digest")}
    binding["session_id"] = sid
    binding.update(
        envelope_sha256=r2._digest(root / ENVELOPE),
        framework=h._framework_identity(root), transcript=ref,
        native_event={"provider": "claude", "event": "SessionEnd", "reason": "other"})
    binding.update(overrides.pop("binding", {}))
    publication = dict(first_published_at="2026-10-23T00:00:00+00:00",
                       publisher_version=h.CLAUDE_PUBLISHER)
    publication.update(overrides.pop("publication", {}))
    return dict(schema_version=overrides.pop("schema_version", "1.2"), binding=binding,
                publication=publication, request_id=h._sha(h.canonical_bytes(binding)))


def error(excinfo):
    return str(excinfo.value)


# --------------------------------------------------------------------------
# P1 / P2 — the scenario #233 exists for
# --------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_p1_claude_request_is_admitted_and_releases_ownership(ready):
    root, source, _ = ready
    before = owner(root)
    result = publish(ready)
    assert result["status"] == "REQUESTED"

    req = request_of(root)
    ref = req["binding"]["transcript"]
    assert req["schema_version"] == "1.2"
    assert req["publication"]["publisher_version"] == h.CLAUDE_PUBLISHER
    assert req["binding"]["native_event"] == {"provider": "claude", "event": "SessionEnd",
                                              "reason": "other"}
    assert ref["source_kind"] == h.CLAUDE_SOURCE_KIND
    assert (root / ref["immutable_locator"]).read_bytes() == source.read_bytes()
    assert all(ref[k] == v for k, v in h.AUTHORITY.items())
    # Publication alone must not move ownership.
    assert owner(root) == before

    provider = h.ClaudeTranscriptProvider(root)
    final = h.consume_exact_request(root, req["request_id"], session_id=SID, provider=provider)
    assert final["status"] == "FINALIZED"
    assert final["transcript_ingestion"] == "VERIFIED"
    assert owner(root)["state"] == "RELEASED"

    receipt = json.loads(Path(final["closeout_result"]["closeout_receipt_artifact"]).read_bytes())
    # The whole point: a real release proof on an allowed trigger mode.
    assert receipt["trigger_mode"] == "wrapper"
    assert receipt["trigger_mode"] != "manual_fallback"
    assert receipt["entrypoint"] == "governance_tools.closeout_handoff"


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_p2_next_session_acquires_after_release(ready):
    root = ready[0]
    req = publish(ready)
    h.consume_exact_request(root, req["request_id"], session_id=SID,
                            provider=h.ClaudeTranscriptProvider(root))
    released = owner(root)
    assert released["state"] == "RELEASED"

    from tests.test_shared_closeout_ownership import prepare as prepare_next
    record = prepare_next(root, "session-B")
    assert record["session_id"] == "session-B"
    assert record["generation"] == released["generation"] + 1


# --------------------------------------------------------------------------
# N1-N15 — fail-closed admission
# --------------------------------------------------------------------------

def test_n1_unlisted_event_provider_rejected(ready):
    root = ready[0]
    bad = claude_request(root, binding={"native_event": {"provider": "gemini",
                                                         "event": "SessionEnd",
                                                         "reason": "other"}})
    with pytest.raises(h.HandoffError) as excinfo:
        h._validate_request(bad, root)
    assert "INVALID_EVENT" in error(excinfo)


def test_n1b_claude_request_cannot_claim_codex(ready):
    root = ready[0]
    bad = claude_request(root, binding={"native_event": {"provider": "codex",
                                                         "event": "SessionEnd",
                                                         "reason": "other"}})
    with pytest.raises(h.HandoffError) as excinfo:
        h._validate_request(bad, root)
    assert "INVALID_EVENT" in error(excinfo)


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_n2_claude_request_with_native_provider_rejected(ready):
    root = ready[0]
    req = publish(ready)
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, req["request_id"], session_id=SID,
                                provider=h.NativeTranscriptProvider(root))
    assert "TRANSCRIPT_RETENTION_UNQUALIFIED" in error(excinfo)
    assert owner(root)["state"] != "RELEASED"


def test_n3_wrong_publisher_version_rejected(ready):
    root = ready[0]
    bad = claude_request(root, publication={"publisher_version": "native-publisher-v1"})
    with pytest.raises(h.HandoffError) as excinfo:
        h._validate_request(bad, root)
    assert "INVALID_PUBLISHER" in error(excinfo)


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_n4_snapshot_bytes_altered_after_manifest_rejected(ready):
    root = ready[0]
    req = publish(ready)
    ref = request_of(root)["binding"]["transcript"]
    (root / ref["immutable_locator"]).write_bytes(b'{"type":"queue-operation"}\n')
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, req["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert "TRANSCRIPT_BYTES_MISMATCH" in error(excinfo)
    assert owner(root)["state"] != "RELEASED"


def test_n5_snapshot_session_id_mismatch_rejected(ready, tmp_path):
    root, _, payload = ready
    other = write_rows(tmp_path / "other.jsonl", claude_rows(root, sid="session-Z"))
    payload = {**payload, "transcript_path": str(other)}
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, payload, deadline_ms=30000)
    assert "TRANSCRIPT_SESSION_MISMATCH" in error(excinfo)


def test_n6_snapshot_cwd_mismatch_rejected(ready, tmp_path):
    root, _, payload = ready
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    other = write_rows(tmp_path / "wrongroot.jsonl", claude_rows(root, cwd=elsewhere))
    payload = {**payload, "transcript_path": str(other)}
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, payload, deadline_ms=30000)
    assert "TRANSCRIPT_SESSION_MISMATCH" in error(excinfo)


def test_n7_missing_session_envelope_rejected(ready):
    """Rejected at the R1 owner-binding layer, earlier than ENVELOPE_DRIFT."""
    root = ready[0]
    (root / ENVELOPE).unlink()
    with pytest.raises(r2.OwnershipError) as excinfo:
        publish(ready)
    assert "INVALID_OWNER" in error(excinfo)
    assert not r2._closeout_request_slot(root, SID).exists()


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_n8_envelope_changed_after_publication_rejected(ready):
    """Also rejected at the R1 layer; the release never completes either way."""
    root = ready[0]
    req = publish(ready)
    path = root / ENVELOPE
    path.write_bytes(path.read_bytes().replace(b'"provider"', b'"Provider"'))
    with pytest.raises((h.HandoffError, r2.OwnershipError)) as excinfo:
        h.consume_exact_request(root, req["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert "INVALID_OWNER" in error(excinfo) or "ENVELOPE_DRIFT" in error(excinfo)
    assert owner(root)["state"] != "RELEASED"


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_n9_binding_session_not_current_owner_rejected(ready):
    root = ready[0]
    publish(ready)
    bad = craft(root, binding={"session_id": "session-B"})
    with r2.execution_exclusion(root) as lease:
        with pytest.raises((h.HandoffError, r2.OwnershipError)) as excinfo:
            h._live(lease, bad, h.ClaudeTranscriptProvider(root))
    assert "MISMATCH" in error(excinfo) or "INVALID" in error(excinfo)
    assert owner(root)["state"] != "RELEASED"


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_n10_generation_mismatch_rejected(ready):
    root = ready[0]
    req = publish(ready)
    record = request_of(root)
    record["binding"]["generation"] = record["binding"]["generation"] + 1
    record["request_id"] = h._sha(h.canonical_bytes(record["binding"]))
    with r2.execution_exclusion(root) as lease:
        with pytest.raises(h.HandoffError) as excinfo:
            h._live(lease, record, h.ClaudeTranscriptProvider(root))
    assert "GENERATION_MISMATCH" in error(excinfo) or "MISMATCH" in error(excinfo)


@pytest.mark.xfail(strict=True, reason=BLOCKED_ON_P1A)
def test_n11_consumed_session_cannot_republish(ready):
    root = ready[0]
    req = publish(ready)
    h.consume_exact_request(root, req["request_id"], session_id=SID,
                            provider=h.ClaudeTranscriptProvider(root))
    # An immutable finalized request answers a repeat; it never re-opens one.
    assert publish(ready)["status"] == "ALREADY_FINALIZED"


def test_n12_empty_snapshot_rejected(ready, tmp_path):
    root, _, payload = ready
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"\n   \n")
    payload = {**payload, "transcript_path": str(empty)}
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, payload, deadline_ms=30000)
    assert "EMPTY_TRANSCRIPT" in error(excinfo)


def test_n13_oversized_snapshot_rejected(ready, monkeypatch):
    root = ready[0]
    monkeypatch.setattr(h, "MAX_SNAPSHOT_BYTES", 8)
    with pytest.raises(h.HandoffError) as excinfo:
        publish(ready)
    assert "SOURCE_SIZE_OR_TYPE" in error(excinfo) or "SNAPSHOT_CAP_EXCEEDED" in error(excinfo)


def test_n14_manual_fallback_still_rejected_by_both_guards(repo, monkeypatch, capsys):
    """The regression guard: this work must not have relaxed R2."""
    monkeypatch.setattr("sys.argv", ["closeout", "--project-root", str(repo),
                                     "--session-id", SID, "--agent-id", "claude",
                                     "--trigger-mode", "manual_fallback", "--format", "json"])
    assert entry.main() == 1
    assert "RELEASE_PROOF_INVALID" in capsys.readouterr().out
    # The inner library guard rejects independently of the CLI early exit.
    with r2.execution_exclusion(repo) as lease:
        with pytest.raises(Exception) as excinfo:
            entry._run_protected_closeout_with_lease(
                lease, session_id=SID, transcript_path=None, agent_id="claude",
                trigger_mode="manual_fallback", ledger_write_allowed=False)
    assert "RELEASE_PROOF_INVALID" in str(excinfo.value)


@pytest.mark.parametrize("key,value", [
    ("immutable_locator", "artifacts/elsewhere/x.jsonl"),
    ("manifest_locator", "../outside.json"),
    ("ref_locator", "artifacts/runtime/handoff-transcripts/session-A/refs/../x.json"),
])
def test_n15_locator_outside_the_handoff_area_rejected(ready, key, value):
    root = ready[0]
    ref = dict(claude_request(root)["binding"]["transcript"])
    ref[key] = value
    with pytest.raises(h.HandoffError):
        h._validate_claude_ref(ref, SID)


def test_n16_claude_request_cannot_bind_another_providers_envelope(ready):
    """P1-b: a matching digest is not an identity. Verified, not assumed."""
    root = ready[0]
    envelope = json.loads((root / ENVELOPE).read_bytes())
    assert envelope["provider"] != "claude"
    with pytest.raises(h.HandoffError) as excinfo:
        publish(ready)
    assert "ENVELOPE_PROVIDER_MISMATCH" in error(excinfo)
    # Rejection plus side-effect absence, not a code name.
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] != "RELEASED"
