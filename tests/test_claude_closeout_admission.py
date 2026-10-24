"""Tranche 1 admission tests for the Claude formal closeout path (#233).

Negative-first by design: this path is only meaningful if it fails closed.
Synthetic payloads are not evidence that a Claude hook fired, and a passing
test here is not evidence of completeness or anti-forgery authority.

Two session-start fixtures, deliberately separate:

- ``ready``: Claude's normal flow. Claude's own SessionStart
  (runtime_hooks/adapters/claude_code/session_lifecycle.py) issued the
  root-bound envelope, so a Claude request can be published and consumed.
- ``codex_ready``: a Claude SessionEnd for a session Codex's SessionStart
  bound. Only N16 uses it; that borrowed identity must stay rejected.

Rejections assert the one code that names the gate under test, not a family of
codes: a strict xfail never checked why a case failed, so every case taken off
it states its reason. The cwd cases pin the worktree-root contract Claude
shares with its SessionStart binding: the root and its subdirectories are
admitted, another worktree and a nested repository are not.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from governance_tools import claude_closeout_publisher as c
from governance_tools import closeout_handoff as h
from governance_tools import native_closeout_publisher as n
from governance_tools import session_closeout_entry as entry
from governance_tools import shared_closeout_ownership as r2
from runtime_hooks.adapters.claude_code.session_lifecycle import session_start as claude_session_start
from tests.test_shared_closeout_ownership import repo, prepare, owner, start_session as start_codex

SID = "session-A"
ENVELOPE = f"artifacts/runtime/sessions/{SID}/session-envelope.json"
GIT = ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]


def start_claude(root, sid=SID):
    """Claude's own SessionStart: the normal flow issues a claude root-bound envelope."""
    claude_session_start(dict(hook_event_name="SessionStart", source="startup",
                              session_id=sid, cwd=str(root)), root)


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


def place(root, tmp_path, name):
    """One cwd for the worktree-root contract.

    Another worktree and a nested repository each have their own Git worktree
    root, whether they sit beside root or inside it.
    """
    if name == "subdirectory":
        path = root / "src" / "deep"
        path.mkdir(parents=True)
    elif name == "other_worktree":
        path = tmp_path / "other worktree"
        subprocess.run(GIT + ["-C", str(root), "worktree", "add", "--quiet", "--detach", str(path)],
                       check=True, capture_output=True)
    elif name == "nested_repo":
        path = root / "vendor" / "nested"
        path.mkdir(parents=True)
        subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)
    else:
        raise AssertionError(name)
    return path


def _ready(repo, monkeypatch, tmp_path, session_start):
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
    prepare(repo, session_start=session_start)
    source = write_rows(tmp_path / "claude.jsonl", claude_rows(repo))
    payload = dict(hook_event_name="SessionEnd", session_id=SID, cwd=str(repo),
                   transcript_path=str(source), reason="other")
    return repo, source, payload


@pytest.fixture
def ready(repo, monkeypatch, tmp_path):
    """Claude's normal flow: Claude's own SessionStart issued the envelope."""
    return _ready(repo, monkeypatch, tmp_path, start_claude)


@pytest.fixture
def codex_ready(repo, monkeypatch, tmp_path):
    """A Claude SessionEnd for a session Codex's SessionStart bound (N16 only)."""
    return _ready(repo, monkeypatch, tmp_path, start_codex)


def publish(ready, **kwargs):
    return c.publish(ready[0], ready[2], deadline_ms=30000, **kwargs)


def request_of(root):
    return h._read(r2._closeout_request_slot(root, SID))


def claude_request(root, **overrides):
    """A structurally valid Claude request built without publishing one.

    The structural admission tests must not depend on publication. Nothing here
    touches the filesystem beyond the envelope digest, and _validate_request
    checks shapes and digests rather than file existence.
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


def forge_chain(root, sid, binding, source, **payload):
    """Write a snapshot, manifest and ref with real digests, without the publisher.

    The publisher refuses a non-owner or an out-of-worktree cwd before it writes
    a manifest, so a case that must reach a later gate builds the chain here.
    The layout mirrors native_closeout_publisher._capture. Returns the ref.
    """
    data = source.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    base = f"{h.NATIVE_AREA}/{sid}"
    snapshot = dict(immutable_locator=f"{base}/snapshots/{sha}.jsonl", sha256=sha,
                    size_bytes=len(data))
    target = root / snapshot["immutable_locator"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    observed = n._stat(source.stat())
    native_payload = dict(hook_event_name="SessionEnd", session_id=sid, cwd=str(root),
                          transcript_path=str(source), reason=binding["native_event"]["reason"])
    native_payload.update(payload)
    manifest = dict(schema_version="1.0", provider="owned-sessionend-snapshot",
                    provider_version="1.0", binding=binding, snapshot=snapshot,
                    source=dict(path=str(source), before=observed, after=observed),
                    native_payload=native_payload, captured_at="2026-10-23T00:00:00+00:00",
                    platform={"os": "fixture", "python": "fixture",
                              "claude_version": c.FORMAT_VERSION}, **h.AUTHORITY)
    manifest_sha = h._sha(h.canonical_bytes(manifest))
    ref = dict(schema_version="1.0", source_kind=h.CLAUDE_SOURCE_KIND, session_id=sid,
               **snapshot, manifest_locator=f"{base}/manifests/{manifest_sha}.json",
               manifest_sha256=manifest_sha, ref_locator=f"{base}/refs/{manifest_sha}.json",
               retention_contract="owned-sessionend-snapshot", retention_version="1.0",
               readable_after_hook=True, **h.AUTHORITY)
    with r2.execution_exclusion(root) as lease:
        h._publish(lease, ref["manifest_locator"], manifest)
        h._publish(lease, ref["ref_locator"], ref)
    return ref


def forge_request(root, tmp_path, sid=SID, **binding):
    """A request for sid that is self-consistent through every gate before ownership."""
    bound = {k: v for k, v in claude_request(root)["binding"].items() if k != "transcript"}
    bound.update(
        session_id=sid,
        envelope_sha256=r2._digest(root / f"artifacts/runtime/sessions/{sid}/session-envelope.json"),
        candidate_identity=dict(bound["candidate_identity"],
                                relative_path=f"artifacts/runtime/closeout_candidates/{sid}/000001.json"))
    bound.update(binding)
    source = write_rows(tmp_path / f"{sid}-forged.jsonl", claude_rows(root, sid=sid))
    bound["transcript"] = forge_chain(root, sid, bound, source)
    return dict(schema_version="1.2", binding=bound,
                publication=dict(first_published_at="2026-10-23T00:00:00+00:00",
                                 publisher_version=h.CLAUDE_PUBLISHER),
                request_id=h._sha(h.canonical_bytes(bound)))


def runtime_state(root):
    """Every runtime artifact's bytes, except the OS lock the caller may hold."""
    area = root / "artifacts/runtime"
    return {p.relative_to(area).as_posix(): p.read_bytes() for p in sorted(area.rglob("*"))
            if p.is_file() and p.name != "execution.lock"}


def error(excinfo):
    return str(excinfo.value)


# --------------------------------------------------------------------------
# P1 / P2 — the scenario #233 exists for
# --------------------------------------------------------------------------

def test_p1_claude_request_is_admitted_and_releases_ownership(ready):
    root, source, _ = ready
    assert json.loads((root / ENVELOPE).read_bytes())["provider"] == "claude"
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


def test_p2_next_session_acquires_after_release(ready):
    root = ready[0]
    req = publish(ready)
    h.consume_exact_request(root, req["request_id"], session_id=SID,
                            provider=h.ClaudeTranscriptProvider(root))
    released = owner(root)
    assert released["state"] == "RELEASED"

    record = prepare(root, "session-B", session_start=start_claude)
    assert record["session_id"] == "session-B"
    assert record["generation"] == released["generation"] + 1


# --------------------------------------------------------------------------
# N1-N16 — fail-closed admission
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


def test_n2_claude_request_with_native_provider_rejected(ready):
    root = ready[0]
    req = publish(ready)
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, req["request_id"], session_id=SID,
                                provider=h.NativeTranscriptProvider(root))
    assert error(excinfo) == "TRANSCRIPT_RETENTION_UNQUALIFIED"
    assert owner(root)["state"] != "RELEASED"


def test_n3_wrong_publisher_version_rejected(ready):
    root = ready[0]
    bad = claude_request(root, publication={"publisher_version": "native-publisher-v1"})
    with pytest.raises(h.HandoffError) as excinfo:
        h._validate_request(bad, root)
    assert "INVALID_PUBLISHER" in error(excinfo)


def test_n4_snapshot_bytes_altered_after_manifest_rejected(ready):
    root = ready[0]
    req = publish(ready)
    ref = request_of(root)["binding"]["transcript"]
    (root / ref["immutable_locator"]).write_bytes(b'{"type":"queue-operation"}\n')
    with pytest.raises(h.HandoffError) as excinfo:
        h.consume_exact_request(root, req["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert error(excinfo) == "TRANSCRIPT_BYTES_MISMATCH"
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


def test_n8_envelope_changed_after_publication_rejected(ready):
    """Rejected at the R1 layer: the changed envelope is no longer a qualified one."""
    root = ready[0]
    req = publish(ready)
    path = root / ENVELOPE
    path.write_bytes(path.read_bytes().replace(b'"provider"', b'"Provider"'))
    with pytest.raises(r2.OwnershipError) as excinfo:
        h.consume_exact_request(root, req["request_id"], session_id=SID,
                                provider=h.ClaudeTranscriptProvider(root))
    assert excinfo.value.code == "INVALID_OWNER"
    assert owner(root)["state"] != "RELEASED"


def test_n9_binding_session_not_current_owner_rejected(ready, tmp_path):
    """A request for a session that does not own the closeout.

    Session B has its own Claude envelope, candidate path, snapshot, manifest
    and ref, all with real digests, so every gate before ownership passes and
    the rejection can only come from the owner check. Rejection alone is not
    enough: the owner and every runtime artifact, release records and receipts
    included, must be exactly as they were.
    """
    root = ready[0]
    publish(ready)
    start_claude(root, "session-B")
    request = forge_request(root, tmp_path, "session-B")
    before = owner(root)
    with r2.execution_exclusion(root) as lease:
        state = runtime_state(root)
        with pytest.raises(r2.OwnershipError) as excinfo:
            h._live(lease, request, h.ClaudeTranscriptProvider(root))
        assert runtime_state(root) == state
    assert excinfo.value.code == "OWNER_CONFLICT"
    assert owner(root) == before
    assert not (root / r2.AREA / "releases").exists()
    assert not (root / "artifacts/runtime/closeout-receipts").exists()


def test_n10_generation_mismatch_rejected(ready, tmp_path):
    """Self-consistent through the manifest, so only the owner's generation differs."""
    root = ready[0]
    request = forge_request(root, tmp_path, generation=owner(root)["generation"] + 1)
    with r2.execution_exclusion(root) as lease:
        with pytest.raises(r2.OwnershipError) as excinfo:
            h._live(lease, request, h.ClaudeTranscriptProvider(root))
    assert excinfo.value.code == "GENERATION_MISMATCH"
    assert owner(root)["state"] != "RELEASED"


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


def test_n16_claude_request_cannot_bind_another_providers_envelope(codex_ready):
    """P1-b: a matching digest is not an identity. Verified, not assumed."""
    root = codex_ready[0]
    assert json.loads((root / ENVELOPE).read_bytes())["provider"] == "codex"
    with pytest.raises(h.HandoffError) as excinfo:
        publish(codex_ready)
    assert error(excinfo) == "ENVELOPE_PROVIDER_MISMATCH"
    # Rejection plus side-effect absence, not a code name.
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] != "RELEASED"


# --------------------------------------------------------------------------
# cwd — Claude's worktree-root contract at all three places; Codex unchanged
# --------------------------------------------------------------------------

def test_same_worktree_root_is_the_session_start_rule(tmp_path, monkeypatch):
    """Root and its subdirectory match; nothing with another worktree root does."""
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)

    def git(*args):
        subprocess.run(GIT + list(args), check=True, capture_output=True)

    root = tmp_path / "consumer"
    git("init", "--quiet", str(root))
    git("-C", str(root), "commit", "--quiet", "--allow-empty", "-m", "root")
    root = root.resolve()
    library = tmp_path / "library"
    git("init", "--quiet", str(library))
    git("-C", str(library), "commit", "--quiet", "--allow-empty", "-m", "library")
    git("-C", str(root), "-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
        library.as_posix(), "vendor/library")
    plain = tmp_path / "plain"
    plain.mkdir()

    assert h._same_worktree_root(str(root), root)
    assert h._same_worktree_root(str(place(root, tmp_path, "subdirectory")), root)
    for cwd in (place(root, tmp_path, "other_worktree"), place(root, tmp_path, "nested_repo"),
                root / "vendor" / "library", plain, tmp_path / "missing"):
        assert not h._same_worktree_root(str(cwd), root), cwd
    assert not h._same_worktree_root("src", root)
    assert not h._same_worktree_root(None, root)


def test_subdirectory_cwd_is_admitted_end_to_end_and_kept_raw(ready, tmp_path):
    """Publish entry, transcript and manifest read-back all admit a subdirectory."""
    root, _, payload = ready
    sub = place(root, tmp_path, "subdirectory")
    source = write_rows(tmp_path / "sub.jsonl", claude_rows(root, cwd=sub))
    result = c.publish(root, {**payload, "cwd": str(sub), "transcript_path": str(source)},
                       deadline_ms=30000)
    assert result["status"] == "REQUESTED"
    ref = request_of(root)["binding"]["transcript"]
    manifest = json.loads((root / ref["manifest_locator"]).read_bytes())
    # The raw cwd stays as evidence; it is never rewritten to the root.
    assert manifest["native_payload"]["cwd"] == str(sub)
    final = h.consume_exact_request(root, result["request_id"], session_id=SID,
                                    provider=h.ClaudeTranscriptProvider(root))
    assert final["status"] == "FINALIZED"
    assert owner(root)["state"] == "RELEASED"


@pytest.mark.parametrize("name", ["other_worktree", "nested_repo"])
def test_payload_cwd_outside_the_worktree_rejected_at_publish_entry(ready, tmp_path, name):
    root, _, payload = ready
    cwd = place(root, tmp_path, name)
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, {**payload, "cwd": str(cwd)}, deadline_ms=30000)
    assert error(excinfo) == "CONSUMER_ROOT_MISMATCH"
    assert not r2._closeout_request_slot(root, SID).exists()
    assert not (root / h.NATIVE_AREA / SID).exists()


@pytest.mark.parametrize("name", ["other_worktree", "nested_repo"])
def test_transcript_cwd_outside_the_worktree_rejected(ready, tmp_path, name):
    root, _, payload = ready
    rows = claude_rows(root)
    rows[2]["cwd"] = str(place(root, tmp_path, name))
    source = write_rows(tmp_path / "wandered.jsonl", rows)
    with pytest.raises(h.HandoffError) as excinfo:
        c.publish(root, {**payload, "transcript_path": str(source)}, deadline_ms=30000)
    assert error(excinfo) == "TRANSCRIPT_SESSION_MISMATCH"
    assert not r2._closeout_request_slot(root, SID).exists()
    assert not (root / h.NATIVE_AREA / SID / "refs").exists()


@pytest.mark.parametrize("name,admitted", [
    ("subdirectory", True), ("other_worktree", False), ("nested_repo", False),
])
def test_manifest_readback_applies_the_worktree_root_rule(ready, tmp_path, name, admitted):
    """The publisher never writes such a manifest, so the read-back is checked on its own."""
    root, source, _ = ready
    binding = {k: v for k, v in claude_request(root)["binding"].items() if k != "transcript"}
    cwd = str(place(root, tmp_path, name))
    ref = forge_chain(root, SID, binding, source, cwd=cwd)
    provider = h.ClaudeTranscriptProvider(root)
    if admitted:
        provider.validate(root, ref)
        assert provider.manifest["native_payload"]["cwd"] == cwd
    else:
        with pytest.raises(h.HandoffError) as excinfo:
            provider.validate(root, ref)
        assert error(excinfo) == "INVALID_NATIVE_PAYLOAD"


def test_codex_payload_cwd_rule_stays_exact(ready, tmp_path):
    """The cwd change is Claude-only: Codex still requires the root itself."""
    root, _, payload = ready
    moved = {**payload, "cwd": str(place(root, tmp_path, "subdirectory"))}
    with pytest.raises(h.HandoffError) as excinfo:
        n._payload(moved, root)
    assert error(excinfo) == "CONSUMER_ROOT_MISMATCH"
    n._payload(moved, root, c.CLAUDE)
    n._payload(payload, root)


# --------------------------------------------------------------------------
# #242 — provider identity isolation in both directions
# --------------------------------------------------------------------------

def test_n17_codex_request_cannot_bind_a_claude_envelope(ready, tmp_path):
    """The mirror of N16. Owner decision 2026-10-24: identity is isolated.

    N16 covered only Claude-request-on-Codex-envelope. While codex mapped to
    None this direction was unchecked, and it became reachable as soon as
    Claude SessionStart began issuing envelopes.
    """
    root = ready[0]
    assert json.loads((root / ENVELOPE).read_bytes())["provider"] == "claude"
    source = write_rows(tmp_path / "codex.jsonl", [
        {"type": "session_meta", "payload": {"id": SID, "cwd": str(root)}},
        {"type": "event_msg", "timestamp": "2026-10-24T00:00:00Z",
         "payload": {"type": "token_count", "info": {}}},
    ])
    payload = dict(hook_event_name="SessionEnd", session_id=SID, cwd=str(root),
                   transcript_path=str(source), reason="other")
    with pytest.raises(h.HandoffError) as excinfo:
        n.publish(root, payload, deadline_ms=30000, profile=n.CODEX)
    assert "ENVELOPE_PROVIDER_MISMATCH" in error(excinfo)
    # Rejection plus side-effect absence, not a code name.
    assert not r2._closeout_request_slot(root, SID).exists()
    assert owner(root)["state"] != "RELEASED"
    assert not (root / "artifacts/runtime/closeout-completions" / f"{SID}.json").exists()


def test_every_request_provider_has_an_explicit_envelope_mapping():
    """A new provider must fail closed, never default-allow.

    This is the development-time control for the runtime
    ENVELOPE_PROVIDER_UNMAPPED guard: adding a provider to _VERSIONS without
    adding it here fails this test rather than silently skipping the envelope
    leg.
    """
    declared = {provider for _, provider in h._VERSIONS.values()}
    assert declared == set(h._ENVELOPE_PROVIDERS), (declared, set(h._ENVELOPE_PROVIDERS))
    # No None escape hatch, and no empty set that would reject everything by
    # accident rather than by decision.
    for provider, allowed in h._ENVELOPE_PROVIDERS.items():
        assert isinstance(allowed, frozenset) and allowed, (provider, allowed)
    # github-copilot-vscode issues root-bound envelopes but has no request
    # provider, so nothing may bind one. Recorded so a future widening is a
    # deliberate edit to this assertion.
    assert "github-copilot-vscode" not in h._ENVELOPE_PROVIDERS
    assert all("github-copilot-vscode" not in allowed
               for allowed in h._ENVELOPE_PROVIDERS.values())
