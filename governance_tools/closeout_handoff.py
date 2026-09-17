"""Explicit durable handoff core with versioned transcript providers.

No background transport or timeout guarantee is provided by this core.
All cooperating state transitions use R2 OS exclusion. Local filesystem/Git
identity is a correctness boundary, not protection from hostile local writers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from governance_tools import shared_closeout_ownership as r2
from governance_tools.prepare_closeout_candidate import validate_framework_binding, _git

ENTRYPOINT = "governance_tools.closeout_handoff"
ORIGIN = "deferred_handoff"
FRAMEWORK = Path(__file__).resolve().parents[1]
AREA = "artifacts/runtime/closeout-requests"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_OID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_BINDING = {"consumer_root", "session_id", "envelope_sha256", "generation",
            "candidate_identity", "text_digest", "framework", "native_event", "transcript"}
_REF = {"session_id", "immutable_locator", "sha256", "retention_contract",
        "retention_version", "readable_after_hook", "source_kind"}


class HandoffError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise HandoffError(message)


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "INVALID_SCHEMA: fields")


def _string(value):
    _require(type(value) is str and bool(value) and all(ord(c) >= 32 for c in value),
             "INVALID_SCHEMA: string")


def _hash(value):
    _require(type(value) is str and bool(_SHA.fullmatch(value)), "INVALID_SCHEMA: digest")


def _relative(value):
    _string(value)
    path = Path(value)
    _require(not path.is_absolute() and not path.drive and ".." not in path.parts
             and path.as_posix() == value and value not in {"", "."}, "UNSAFE_PATH")


def _decode(data):
    def pairs(items):
        result = {}
        for k, v in items:
            _require(k not in result, "INVALID_SCHEMA: duplicate key")
            result[k] = v
        return result
    try:
        obj = json.loads(data, object_pairs_hook=pairs)
        _require(canonical_bytes(obj) == data, "NONCANONICAL_BYTES")
        return obj
    except (ValueError, TypeError, UnicodeError) as exc:
        raise HandoffError("INVALID_CANONICAL_JSON") from exc


def _read(path):
    try:
        return _decode(path.read_bytes())
    except OSError as exc:
        raise HandoffError("MISSING_PROOF: " + str(path)) from exc


def _sync_directory(path):
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _publish(lease, relative, value, *, replace=False):
    """Full temp + fsync + atomic no-clobber link. Keep failed temps as evidence.

    Windows file fsync/link/read-back is process-crash qualified by tests; this
    does not claim sudden-power-loss durability on every Windows filesystem.
    """
    root = r2._lease(lease)
    path = r2._path(root, relative)
    data = canonical_bytes(value)
    if path.exists() and not replace:
        _require(path.read_bytes() == data, "PUBLICATION_CONFLICT")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    _sync_directory(path.parent.parent)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    r2._path(root, relative)
    if replace:
        os.replace(temp, path)
    else:
        try:
            os.link(temp, path)  # Atomic create-if-absent, never os.replace(request).
        except FileExistsError:
            _require(path.read_bytes() == data, "PUBLICATION_CONFLICT")
    _sync_directory(path.parent)
    _require(path.read_bytes() == data, "PUBLISH_UNCONFIRMED")
    temp.unlink(missing_ok=True)
    _sync_directory(path.parent)
    return path


def _validate_ref(ref, sid):
    _keys(ref, _REF)
    _require(ref["session_id"] == sid and ref["retention_contract"] == "fixture-retained-transcript"
             and ref["retention_version"] == "1.0" and ref["source_kind"] == "fixture"
             and ref["readable_after_hook"] is True, "TRANSCRIPT_RETENTION_UNQUALIFIED")
    _hash(ref["sha256"])
    _relative(ref["immutable_locator"])
    expected = f'artifacts/runtime/handoff-transcript-fixtures/{sid}/{ref["sha256"]}.jsonl'
    _require(ref["immutable_locator"] == expected, "TRANSCRIPT_IDENTITY_MISMATCH")


class FixtureTranscriptProvider:
    """A test-owned retention manifest, never a native retention provider.

    The independently pre-established manifest binds consumer, session and bytes.
    Providing readable_after_hook=True alone is deliberately insufficient.
    Tests own its retention lifecycle; arbitrary local tampering is rejected.
    """
    def __init__(self, consumer_root: Path):
        self.root = Path(consumer_root).resolve()

    def validate(self, root, ref):
        _require(root == self.root, "TRANSCRIPT_ROOT_MISMATCH")
        sid = ref["session_id"]
        _validate_ref(ref, sid)
        manifest = _read(r2._path(root, f"artifacts/runtime/handoff-transcript-fixtures/{sid}/manifest.json"))
        _require(manifest == {"consumer_root": str(root), "transcript": ref},
                 "TRANSCRIPT_RETENTION_UNQUALIFIED")
        path = r2._path(root, ref["immutable_locator"])
        _require(r2._digest(path) == ref["sha256"], "TRANSCRIPT_BYTES_MISMATCH")
        records = [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]
        _require(records and records[0].get("type") == "session_meta"
                 and records[0].get("payload", {}).get("id") == sid,
                 "TRANSCRIPT_SESSION_MISMATCH")
        return path


MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024
NATIVE_AREA = "artifacts/runtime/handoff-transcripts"
AUTHORITY = dict(source_semantics="sessionend_observed_snapshot",
                 completeness="unqualified", decision_authority="none")
_NATIVE_REF = _REF | {"schema_version", "size_bytes", "manifest_locator",
                       "manifest_sha256", "ref_locator", *AUTHORITY}


def _validate_native_ref(ref, sid):
    _keys(ref, _NATIVE_REF)
    _require(type(sid) is str and bool(r2._ID.fullmatch(sid)), "INVALID_SESSION")
    _require(ref["schema_version"] == "1.0" and ref["session_id"] == sid
             and ref["source_kind"] == "codex_sessionend_observed_snapshot"
             and ref["retention_contract"] == "owned-sessionend-snapshot"
             and ref["retention_version"] == "1.0" and ref["readable_after_hook"] is True,
             "INVALID_NATIVE_REF")
    _require(all(ref[k] == v for k, v in AUTHORITY.items()), "INVALID_SNAPSHOT_AUTHORITY")
    _require(type(ref["size_bytes"]) is int and 0 <= ref["size_bytes"] <= MAX_SNAPSHOT_BYTES,
             "INVALID_SNAPSHOT_SIZE")
    _hash(ref["sha256"])
    _hash(ref["manifest_sha256"])
    base = f"{NATIVE_AREA}/{sid}"
    for key, expected in {
        "immutable_locator": f'{base}/snapshots/{ref["sha256"]}.jsonl',
        "manifest_locator": f'{base}/manifests/{ref["manifest_sha256"]}.json',
        "ref_locator": f'{base}/refs/{ref["manifest_sha256"]}.json',
    }.items():
        _relative(ref[key])
        _require(ref[key] == expected, "TRANSCRIPT_IDENTITY_MISMATCH")


def _read_native_metadata(path, limit=131072):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    _require(len(data) <= limit, "NATIVE_METADATA_TOO_LARGE")
    return data


def _validate_native_snapshot(path, sid, root, check):
    # Supported JSONL identity only. No last-record/completeness heuristic.
    with path.open("rb") as stream:
        total = 0
        first = True
        while line := stream.readline(MAX_SNAPSHOT_BYTES + 1):
            check()
            total += len(line)
            _require(total <= MAX_SNAPSHOT_BYTES, "SNAPSHOT_CAP_EXCEEDED")
            if not line.strip():
                continue
            record = json.loads(line)
            if first:
                _require(type(record) is dict and type(record.get("payload")) is dict
                         and record.get("type") == "session_meta"
                         and record.get("payload", {}).get("id") == sid
                         and record.get("payload", {}).get("cwd") == str(root), "TRANSCRIPT_SESSION_MISMATCH")
                first = False
        _require(not first, "EMPTY_TRANSCRIPT")


class NativeTranscriptProvider:
    """Owned observed bytes; neither completeness nor anti-forgery authority."""

    def __init__(self, consumer_root, *, check=lambda: None):
        self.root = Path(consumer_root).resolve()
        self.check = check

    def validate(self, root, ref):
        self.check()
        _require(root == self.root, "TRANSCRIPT_ROOT_MISMATCH")
        _validate_native_ref(ref, ref["session_id"])
        _require(_decode(_read_native_metadata(r2._path(root, ref["ref_locator"]))) == ref, "REF_BYTES_MISMATCH")
        data = _read_native_metadata(r2._path(root, ref["manifest_locator"]))
        _require(_sha(data) == ref["manifest_sha256"], "MANIFEST_HASH_MISMATCH")
        m = _decode(data)
        _keys(m, {"schema_version", "provider", "provider_version", "binding", "snapshot",
                  "source", "native_payload", "captured_at", "platform", *AUTHORITY})
        _require(m["schema_version"] == "1.0" and m["provider"] == "owned-sessionend-snapshot"
                 and m["provider_version"] == "1.0"
                 and all(m[k] == v for k, v in AUTHORITY.items()), "INVALID_MANIFEST")
        _keys(m["binding"], _BINDING - {"transcript"})
        # Reuse strict request binding validation even for an orphan ref.
        bound = {**m["binding"], "transcript": ref}
        _validate_request(dict(schema_version="1.1", binding=bound,
                               request_id=_sha(canonical_bytes(bound)),
                               publication=dict(first_published_at=m["captured_at"],
                                                publisher_version="native-publisher-v1")), root)
        _require(m["binding"]["session_id"] == ref["session_id"]
                 and m["binding"]["consumer_root"] == str(root), "MANIFEST_BINDING_MISMATCH")
        _require(m["snapshot"] == {k: ref[k] for k in ("immutable_locator", "sha256", "size_bytes")},
                 "SNAPSHOT_BINDING_MISMATCH")
        _keys(m["source"], {"path", "before", "after"})
        _require(m["source"]["before"] == m["source"]["after"], "SNAPSHOT_UNSTABLE")
        _keys(m["source"]["before"], {"dev", "ino", "size", "mtime_ns", "ctime_ns"})
        _require(all(type(v) is int for v in m["source"]["before"].values())
                 and m["source"]["before"]["size"] == ref["size_bytes"], "INVALID_SOURCE_STAT")
        payload = m["native_payload"]
        _require(type(payload) is dict and payload.get("hook_event_name") == "SessionEnd"
                 and payload.get("session_id") == ref["session_id"]
                 and payload.get("reason") == m["binding"]["native_event"]["reason"]
                 and str(Path(payload.get("cwd", "")).resolve()) == str(root)
                 and payload.get("transcript_path") == m["source"]["path"],
                 "INVALID_NATIVE_PAYLOAD")
        _require(datetime.fromisoformat(m["captured_at"]).tzinfo is not None, "INVALID_TIMESTAMP")
        _keys(m["platform"], {"os", "python", "codex_version"})
        for value in m["platform"].values():
            _string(value)
        path = r2._path(root, ref["immutable_locator"])
        _require(path.stat().st_size == ref["size_bytes"], "TRANSCRIPT_BYTES_MISMATCH")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                self.check()
                digest.update(chunk)
        _require(digest.hexdigest() == ref["sha256"], "TRANSCRIPT_BYTES_MISMATCH")
        _validate_native_snapshot(path, ref["session_id"], root, self.check)
        self.manifest = m
        self.check()
        return path


def _framework_identity(root):
    consumer, framework = validate_framework_binding(root, FRAMEWORK)
    relative = framework.relative_to(consumer).as_posix()
    return {"relative_path": relative,
            "gitlink_oid": _git(root, "rev-parse", ":" + relative),
            "checkout_head": _git(framework, "rev-parse", "HEAD"),
            "adopted_commit": json.loads((root / "governance/framework.lock.json").read_bytes())["adopted_commit"],
            "registration_blob": _git(root, "rev-parse", ":.gitmodules"),
            "lock_blob": _git(root, "rev-parse", ":governance/framework.lock.json")}


def _framework_preflight(root):
    """Structural rejection only; registration authority is established in-lease."""
    _require(not any(k.upper().startswith("GIT_") for k in os.environ), "GIT_OVERRIDE")
    framework = FRAMEWORK.resolve(strict=True)
    _require(framework != root and framework.is_relative_to(root), "FRAMEWORK_ROOT_MISMATCH")
    _require(r2._path(root, framework.relative_to(root).as_posix()) == framework,
             "FRAMEWORK_ROOT_MISMATCH")
    for rel in (".gitmodules", "governance/framework.lock.json"):
        _require(r2._path(root, rel).is_file(), "FRAMEWORK_CONTROL_MISSING")
    _require((framework / ".git").exists(), "FRAMEWORK_METADATA_MISSING")


def _control_hashes(root):
    return tuple((rel, r2._digest(r2._path(root, rel)))
                 for rel in (".gitmodules", "governance/framework.lock.json"))


@dataclass(frozen=True, eq=False)
class _QualifiedFrameworkContext:
    lease: object
    root: Path
    framework: Path
    identity_bytes: bytes
    controls: tuple


# Transient scope membership, not a cache or a persistent authority source.
_QUALIFIED = {}


@contextmanager
def _qualified_framework(lease):
    root = r2._lease(lease)
    _framework_preflight(root)
    before = _control_hashes(root)
    identity = _framework_identity(root)  # The sole full native qualification.
    _require(_control_hashes(root) == before, "FRAMEWORK_CONTROL_DRIFT")
    framework = r2._path(root, identity["relative_path"])
    _require(framework == FRAMEWORK.resolve(strict=True), "FRAMEWORK_ROOT_MISMATCH")
    context = _QualifiedFrameworkContext(lease, root, framework, canonical_bytes(identity), before)
    _QUALIFIED[id(context)] = context
    try:
        yield context
    finally:
        _QUALIFIED.pop(id(context), None)


def _qualified_identity(lease, context):
    root = r2._lease(lease)
    _require(type(context) is _QualifiedFrameworkContext
             and _QUALIFIED.get(id(context)) is context
             and context.lease is lease and context.root == root, "INVALID_QUALIFIED_CONTEXT")
    return _decode(context.identity_bytes)  # Fresh value, immutable captured bytes.


def _check_framework_drift(lease, context, check=lambda: None):
    identity = _qualified_identity(lease, context)
    root = r2._lease(lease)
    check()
    _framework_preflight(root)
    _require(root.resolve(strict=True) == root and FRAMEWORK.resolve(strict=True) == context.framework,
             "FRAMEWORK_ROOT_DRIFT")
    actual_top = Path(_git(context.framework, "rev-parse", "--show-toplevel")).resolve(strict=True)
    _require(actual_top == context.framework, "FRAMEWORK_WORKTREE_BINDING_DRIFT")
    check()
    relative = identity["relative_path"]
    expected = {relative: ("160000", identity["gitlink_oid"], "0"),
                ".gitmodules": ("100644", identity["registration_blob"], "0"),
                "governance/framework.lock.json": ("100644", identity["lock_blob"], "0")}
    raw = _git(root, "ls-files", "--stage", "-z", "--", *expected)
    actual = {}
    for entry in raw.rstrip("\0").split("\0"):
        header, sep, path = entry.partition("\t")
        _require(sep and path not in actual, "FRAMEWORK_INDEX_DRIFT")
        actual[path] = tuple(header.split())
    _require(actual == expected, "FRAMEWORK_INDEX_DRIFT")
    check()
    _require(_git(root, "rev-parse", "--verify", "HEAD:" + relative) == identity["gitlink_oid"],
             "FRAMEWORK_ADOPTION_DRIFT")
    check()
    status = _git(context.framework, "status", "--porcelain=v2", "--branch", "--untracked-files=all")
    lines = status.splitlines()
    heads = [line.removeprefix("# branch.oid ") for line in lines if line.startswith("# branch.oid ")]
    _require(heads == [identity["checkout_head"]] and all(line.startswith("# ") for line in lines),
             "FRAMEWORK_WORKTREE_DRIFT")
    _require(_control_hashes(root) == context.controls, "FRAMEWORK_CONTROL_DRIFT")
    check()


def _validate_request(request, root):
    _keys(request, {"schema_version", "request_id", "binding", "publication"})
    _require(request["schema_version"] in ("1.0", "1.1"), "UNKNOWN_REQUEST_VERSION")
    _hash(request["request_id"])
    b = request["binding"]
    _keys(b, _BINDING)
    _require(b["consumer_root"] == str(root), "CONSUMER_ROOT_MISMATCH")
    sid = b["session_id"]
    _require(type(sid) is str and bool(r2._ID.fullmatch(sid)), "INVALID_SESSION")
    _require(type(b["generation"]) is int and b["generation"] > 0, "INVALID_GENERATION")
    _hash(b["envelope_sha256"])
    _hash(b["text_digest"])
    r2._candidate(root, sid, b["candidate_identity"])
    f = b["framework"]
    _keys(f, {"relative_path", "gitlink_oid", "checkout_head", "adopted_commit", "registration_blob", "lock_blob"})
    _relative(f["relative_path"])
    for key in set(f) - {"relative_path"}:
        _require(type(f[key]) is str and bool(_OID.fullmatch(f[key])), "INVALID_FRAMEWORK_IDENTITY")
    _require(f["gitlink_oid"] == f["checkout_head"] == f["adopted_commit"], "FRAMEWORK_MISMATCH")
    e = b["native_event"]
    _keys(e, {"provider", "event", "reason"})
    _require(e["provider"] == "codex" and e["event"] == "SessionEnd", "INVALID_EVENT")
    _string(e["reason"])
    native = request["schema_version"] == "1.1"
    (_validate_native_ref if native else _validate_ref)(b["transcript"], sid)
    _keys(request["publication"], {"first_published_at", "publisher_version"})
    _require(request["publication"]["publisher_version"] == ("native-publisher-v1" if native else "core-v1-fixture"), "INVALID_PUBLISHER")
    timestamp = datetime.fromisoformat(request["publication"]["first_published_at"])
    _require(timestamp.tzinfo is not None, "INVALID_TIMESTAMP")
    _require(_sha(canonical_bytes(b)) == request["request_id"], "REQUEST_ID_MISMATCH")
    return b


def _base(root, sid):
    return r2._closeout_request_slot(root, sid).parent.relative_to(root).as_posix()


def _check_owner(owner, binding):
    for key in ("consumer_root", "session_id", "generation", "candidate_identity", "text_digest"):
        _require(owner[key] == binding[key], "OWNER_REQUEST_MISMATCH: " + key)


def _live(lease, request, provider, *, qualified_context=None):
    root = r2._lease(lease)
    b = _validate_request(request, root)
    r2._identity(root, b["session_id"])
    envelope = r2._path(root, f'artifacts/runtime/sessions/{b["session_id"]}/session-envelope.json')
    _require(r2._digest(envelope) == b["envelope_sha256"], "ENVELOPE_DRIFT")
    if qualified_context is None:
        identity = _framework_identity(root)
    else:
        _require(request["schema_version"] == "1.1", "INVALID_QUALIFIED_CONTEXT")
        identity = _qualified_identity(lease, qualified_context)
    _require(identity == b["framework"], "FRAMEWORK_DRIFT")
    expected_provider = NativeTranscriptProvider if request["schema_version"] == "1.1" else FixtureTranscriptProvider
    _require(type(provider) is expected_provider, "TRANSCRIPT_RETENTION_UNQUALIFIED")
    transcript = provider.validate(root, b["transcript"])
    if request["schema_version"] == "1.1":
        _require(provider.manifest["binding"] == {k: v for k, v in b.items() if k != "transcript"}, "MANIFEST_BINDING_MISMATCH")
    owner = r2._matching(lease, b["session_id"], b["generation"])
    _check_owner(owner, b)
    r2._payloads(lease, owner)
    return owner, transcript


def publish_request(consumer_root: Path, session_id: str, transcript_ref: dict,
                    provider: FixtureTranscriptProvider, *, reason="fixture-normal-quit") -> dict:
    """Explicit fixture core API. Does not consume, start a worker or touch text."""
    with r2.execution_exclusion(consumer_root) as lease:
        return _publish_request_with_lease(lease, session_id, transcript_ref, provider, reason=reason)


def _publish_request_with_lease(lease, session_id, transcript_ref, provider, *,
                                reason="fixture-normal-quit", check=lambda: None, qualified_context=None):
    native = type(provider) is NativeTranscriptProvider
    check()
    root = r2._lease(lease)
    if qualified_context is not None:
        _require(native, "INVALID_QUALIFIED_CONTEXT")
        _qualified_identity(lease, qualified_context)
    slot = r2._closeout_request_slot(root, session_id)
    if slot.exists():
        existing = _read(slot)
        b = _validate_request(existing, root)
        _require(b["session_id"] == session_id and b["transcript"] == transcript_ref
                 and b["native_event"]["reason"] == reason, "REQUEST_CONFLICT")
        if _finalized_path(root, b).exists():
            return _finalize(lease, existing)
        _live(lease, existing, provider)
        return {"status": "ALREADY_REQUESTED", "request_id": existing["request_id"]}
    r2._identity(root, session_id)
    _require(not r2._completion(root, session_id), "CONSUMED_WITHOUT_REQUEST")
    o = r2._matching(lease, session_id)
    _require(o["state"] == "OWNED", "PREPARED_OWNER_REQUIRED")
    envelope = r2._path(root, f"artifacts/runtime/sessions/{session_id}/session-envelope.json")
    b = {k: o[k] for k in ("consumer_root", "session_id", "generation", "candidate_identity", "text_digest")}
    identity = (_framework_identity(root) if qualified_context is None
                else _qualified_identity(lease, qualified_context))
    b.update(envelope_sha256=r2._digest(envelope), framework=identity,
             transcript=transcript_ref, native_event={"provider": "codex", "event": "SessionEnd", "reason": reason})
    request = {"schema_version": "1.1" if native else "1.0", "request_id": _sha(canonical_bytes(b)), "binding": b,
               "publication": {"first_published_at": datetime.now(timezone.utc).isoformat(),
                               "publisher_version": "native-publisher-v1" if native else "core-v1-fixture"}}
    _live(lease, request, provider, qualified_context=qualified_context)
    if qualified_context is not None:
        _check_framework_drift(lease, qualified_context, check)
    check()
    _publish(lease, slot.relative_to(root).as_posix(), request)
    check()
    _validate_request(_read(slot), root)
    check()
    return {"status": "REQUESTED", "request_id": request["request_id"]}

def _attempts(root, request):
    b = request["binding"]
    directory = r2._path(root, _base(root, b["session_id"]) + "/attempts")
    values = []
    for path in sorted(directory.glob("*.json")):
        r2._path(root, path.relative_to(root).as_posix())
        a = _read(path)
        _keys(a, {"schema_version", "attempt_id", "request_id", "request_sha256", "generation",
                  "execution_origin", "state", "receipt_identity"})
        _require(a["schema_version"] == "1.0" and a["attempt_id"] == path.stem
                 and bool(re.fullmatch(r"[0-9a-f]{32}", path.stem))
                 and a["request_id"] == request["request_id"]
                 and a["request_sha256"] == _sha(canonical_bytes(request))
                 and type(a["generation"]) is int and a["generation"] == b["generation"]
                 and a["execution_origin"] == ORIGIN and a["state"] == "RUNNING", "ATTEMPT_MISMATCH")
        rid = a["receipt_identity"]
        _require(rid is None or (type(rid) is str and bool(r2._RECEIPT_ID.fullmatch(rid))), "ATTEMPT_MISMATCH")
        values.append((path, a))
    _require(sum(a["receipt_identity"] is not None for _, a in values) <= 1, "AMBIGUOUS_ATTEMPT")
    return values


def _claim(lease, request):
    b = request["binding"]
    a = dict(schema_version="1.0", attempt_id=f"{len(_attempts(lease.root, request)) + 1:032d}",
             request_id=request["request_id"], request_sha256=_sha(canonical_bytes(request)),
             generation=b["generation"], execution_origin=ORIGIN, state="RUNNING", receipt_identity=None)
    path = _base(lease.root, b["session_id"]) + "/attempts/" + a["attempt_id"] + ".json"
    _publish(lease, path, a)
    return path, a


def _bind_attempt(lease, path, attempt, owner):
    _require(attempt["receipt_identity"] in (None, owner["receipt_identity"]), "RECEIPT_RESERVATION_CONFLICT")
    attempt = {**attempt, "receipt_identity": owner["receipt_identity"]}
    _publish(lease, path, attempt, replace=True)
    return attempt


def _release_path(root, b):
    return r2._path(root, f'{r2.AREA}/releases/{b["generation"]}.json')


def _finalized_path(root, b):
    return r2._path(root, _base(root, b["session_id"]) + "/finalized.json")


def _ingestion_record(request, attempt):
    return {"schema_version": "1.0", "request_id": request["request_id"],
            "request_sha256": _sha(canonical_bytes(request)),
            "attempt_id": attempt["attempt_id"], "receipt_identity": attempt["receipt_identity"],
            "transcript": request["binding"]["transcript"], "state": "VERIFIED"}


def _ingestion_proof(root, request, attempt):
    path = r2._path(root, _base(root, request["binding"]["session_id"])
                    + "/ingestion/" + attempt["attempt_id"] + ".json")
    _require(path.is_file() and canonical_bytes(_read(path)) == canonical_bytes(_ingestion_record(request, attempt)),
             "TRANSCRIPT_INGESTION_UNCONFIRMED")
    return path


def _finalization_record(root, request):
    """Rebuild deterministic finalization from immutable A proofs only."""
    b = _validate_request(request, root)
    attempts = [(p, a) for p, a in _attempts(root, request) if a["receipt_identity"] is not None]
    _require(len(attempts) == 1, "MISSING_RESERVED_ATTEMPT")
    attempt_path, attempt = attempts[0]
    ingestion_path = _ingestion_proof(root, request, attempt)
    expected = {"schema_version": "1.0", "consumer_root": str(root), "session_id": b["session_id"],
                "generation": b["generation"], "candidate_identity": b["candidate_identity"],
                "expected_text_digest": b["text_digest"], "receipt_identity": attempt["receipt_identity"]}
    receipt_path = r2._path(root, f'artifacts/runtime/closeout-receipts/closeout_receipt_{attempt["receipt_identity"]}.json')
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    r2._receipt_schema(receipt)
    _require(receipt_bytes == r2._bytes(receipt), "NONCANONICAL_RECEIPT")
    _require(receipt.get("r2_binding") == expected and receipt.get("exit_code") == 0
             and receipt.get("schema_version") == "1.5" and receipt.get("session_id") == b["session_id"]
             and receipt.get("trigger_mode") == "wrapper" and receipt.get("entrypoint") == ENTRYPOINT
             and receipt.get("checksum_of_cleaned_path") == b["text_digest"]
             and receipt.get("closeout_artifact_path") == str(root / r2.TEXT), "RECEIPT_PROOF_MISMATCH")
    release_path = _release_path(root, b)
    release_bytes = release_path.read_bytes()
    _require(release_bytes == r2._bytes({**expected, "receipt_sha256": _sha(receipt_bytes), "state": "RELEASED"}),
             "RELEASE_PROOF_MISMATCH")
    return {"schema_version": "1.0", "request_id": request["request_id"],
             "request_sha256": _sha(canonical_bytes(request)), "execution_origin": ORIGIN,
             "attempt_id": attempt["attempt_id"], "attempt_sha256": _sha(attempt_path.read_bytes()),
             "receipt_identity": attempt["receipt_identity"], "receipt_sha256": _sha(receipt_bytes),
             "release_sha256": _sha(release_bytes),
             "ingestion_sha256": _sha(ingestion_path.read_bytes()), "state": "FINALIZED"}


def validate_finalization(lease, session_id, *, expected_owner=None):
    """Read-only readiness gate shared by R2 next-acquire and handoff retries.

    Never reads current owner/shared text. R2 supplies its already-validated
    previous owner when deciding whether that exact generation may be replaced.
    """
    root = r2._lease(lease)
    request = _read(r2._closeout_request_slot(root, session_id))
    binding = _validate_request(request, root)
    _require(binding["session_id"] == session_id, "REQUEST_SESSION_MISMATCH")
    if expected_owner is not None:
        _check_owner(expected_owner, binding)
    expected = _finalization_record(root, request)
    if expected_owner is not None:
        _require(expected_owner["state"] == "RELEASED"
                 and expected_owner["receipt_identity"] == expected["receipt_identity"]
                 and expected_owner["receipt_sha256"] == expected["receipt_sha256"],
                 "OWNER_FINALIZATION_MISMATCH")
    actual = _read(_finalized_path(root, binding))
    _require(canonical_bytes(actual) == canonical_bytes(expected), "FINALIZATION_PROOF_MISMATCH")
    return expected


def _finalize(lease, request):
    root = r2._lease(lease)
    b = _validate_request(request, root)
    final_path = _finalized_path(root, b)
    exists = final_path.exists()
    if exists:
        # Once B may have advanced, only immutable A evidence is admissible.
        validate_finalization(lease, b["session_id"])
    else:
        # A cannot lose ownership before this publication: next-acquire checks
        # this exact proof under the same lease. A release record alone is NOT
        # evidence that the mutable owner transition completed.
        owner = r2._matching(lease, b["session_id"], b["generation"])
        _check_owner(owner, b)
        _require(owner["state"] == "RELEASED", "OWNER_NOT_RELEASED")
        r2._verify_release(lease, owner)
        final = _finalization_record(root, request)
        _require(owner["receipt_identity"] == final["receipt_identity"]
                 and owner["receipt_sha256"] == final["receipt_sha256"],
                 "OWNER_FINALIZATION_MISMATCH")
        _publish(lease, final_path.relative_to(root).as_posix(), final)
        validate_finalization(lease, b["session_id"], expected_owner=owner)
    return {"status": "ALREADY_FINALIZED" if exists else "FINALIZED", "request_id": request["request_id"],
            "execution_origin": ORIGIN, "fixture_only": request["schema_version"] == "1.0"}


def _verify_ingestion(root, sid, transcript):
    """Verify actual persisted ingestor rows, not the fail-silent bridge return."""
    db = r2._path(root, "artifacts/codeburn_closeout_ingest.db")
    _require(db.is_file(), "TRANSCRIPT_INGESTION_UNCONFIRMED")
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        count = conn.execute("SELECT COUNT(*) FROM step_ingestion_provenance p JOIN steps s ON p.step_id=s.step_id "
                             "WHERE s.session_id=? AND p.provider='codex' AND p.source_artifact_path=?",
                             (sid, str(transcript))).fetchone()[0]
    _require(count > 0, "TRANSCRIPT_INGESTION_UNCONFIRMED")


def consume_exact_request(consumer_root: Path, request_id: str, *, session_id: str,
                          provider: FixtureTranscriptProvider) -> dict:
    """Consume one explicitly addressed slot and hash; never select latest request."""
    _hash(request_id)
    with r2.execution_exclusion(consumer_root) as lease:
        root = r2._lease(lease)
        slot = r2._closeout_request_slot(root, session_id)
        request = _read(slot)
        b = _validate_request(request, root)
        _require(request["request_id"] == request_id and b["session_id"] == session_id, "REQUEST_ID_MISMATCH")
        # Only a complete finalization permits immutable-only late retry.
        if _finalized_path(root, b).exists():
            return _finalize(lease, request)
        owner, transcript = _live(lease, request, provider)
        if owner["state"] == "RELEASED":
            return _finalize(lease, request)
        attempts = _attempts(root, request)
        reserved = [(p, a) for p, a in attempts if a["receipt_identity"] is not None]
        if owner["state"] == "HOLD":
            _require(owner["hold_reason"] in {"closeout_pending", "failed"}
                     and owner["receipt_identity"] is not None, "FAILED_HOLD")
            if reserved:
                _require(reserved[0][1]["receipt_identity"] == owner["receipt_identity"], "RECEIPT_RESERVATION_CONFLICT")
            else:
                _require(bool(attempts), "MISSING_CLAIM")
                # Only one unreserved claim can be the interrupted last claim.
                p, a = attempts[-1]
                _bind_attempt(lease, p.relative_to(root).as_posix(), a, owner)
            linked = [(p, a) for p, a in _attempts(root, request) if a["receipt_identity"] is not None]
            _require(len(linked) == 1, "MISSING_RESERVED_ATTEMPT")
            _ingestion_proof(root, request, linked[0][1])
            receipt = r2._path(root, r2._receipt_relative(owner))
            _require(receipt.is_file(), "FAILED_HOLD: no receipt; core replay forbidden")
            r2.finalize_release(lease, receipt)
            return _finalize(lease, request)
        _require(owner["state"] == "OWNED" and not reserved
                 and not r2._completion(root, session_id), "FAILED_HOLD: cannot replay")
        path, attempt = _claim(lease, request)
        def verify_before_receipt(result):
            _require(result.get("session_id") == session_id, "RESULT_SESSION_MISMATCH")
            _verify_ingestion(root, session_id, transcript)
            linked = _read(r2._path(root, path))
            _publish(lease, _base(root, session_id) + "/ingestion/" + linked["attempt_id"] + ".json",
                     _ingestion_record(request, linked))

        from governance_tools.session_closeout_entry import _run_protected_closeout_with_lease
        result = _run_protected_closeout_with_lease(
            lease, session_id=session_id, transcript_path=transcript, agent_id="codex",
            trigger_mode="wrapper", entrypoint=ENTRYPOINT, ledger_write_allowed=False,
            after_begin=lambda o: _bind_attempt(lease, path, attempt, o),
            after_run=verify_before_receipt)
        final = _finalize(lease, request)
        return {**final, "transcript_ingestion": "VERIFIED", "closeout_result": result}
