"""Bounded SessionEnd snapshot publication; no runner or activation.

The payload is deployment provenance, not authentication. Owned bytes have no
completeness or decision authority. A timeout may leave a complete request.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import stat
import sys
import time
import uuid

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2

MAX_PAYLOAD_BYTES = 65536
CHUNK = 1024 * 1024
# Format qualification provenance, not an assertion about the executing binary.
FORMAT_VERSION = "codex-0.154.0-alpha.6.2-session-meta"


class DeadlineExpired(TimeoutError):
    pass


class Budget:
    def __init__(self, milliseconds):
        h._require(type(milliseconds) is int and milliseconds > 0, "INVALID_DEADLINE")
        try:
            self.end = time.monotonic() + milliseconds / 1000
        except OverflowError as exc:
            raise h.HandoffError("INVALID_DEADLINE") from exc
        h._require(math.isfinite(self.end), "INVALID_DEADLINE")

    def check(self):
        if time.monotonic() >= self.end:
            raise DeadlineExpired("UNCONFIRMED: deadline expired")


def _stat(value):
    return {"dev": value.st_dev, "ino": value.st_ino, "size": value.st_size,
            "mtime_ns": value.st_mtime_ns, "ctime_ns": value.st_ctime_ns}


def _payload(value, root):
    h._require(type(value) is dict and len(h.canonical_bytes(value)) <= MAX_PAYLOAD_BYTES,
               "INVALID_PAYLOAD")
    for key in ("hook_event_name", "session_id", "cwd", "transcript_path", "reason"):
        h._string(value.get(key))
    h._require(value["hook_event_name"] == "SessionEnd", "INVALID_EVENT")
    h._require(bool(r2._ID.fullmatch(value["session_id"])), "INVALID_SESSION")
    h._require(Path(value["cwd"]).is_absolute() and Path(value["cwd"]).resolve() == root,
               "CONSUMER_ROOT_MISMATCH")
    h._require(Path(value["transcript_path"]).is_absolute(), "INVALID_SOURCE_PATH")


def _binding(lease, sid, reason, qualified_context):
    root = r2._lease(lease)
    r2._identity(root, sid)
    h._require(not r2._completion(root, sid), "CONSUMED_WITHOUT_REQUEST")
    owner = r2._matching(lease, sid)
    h._require(owner["state"] == "OWNED", "PREPARED_OWNER_REQUIRED")
    r2._payloads(lease, owner)
    result = {k: owner[k] for k in ("consumer_root", "session_id", "generation",
                                   "candidate_identity", "text_digest")}
    envelope = r2._path(root, f"artifacts/runtime/sessions/{sid}/session-envelope.json")
    result.update(envelope_sha256=r2._digest(envelope), framework=h._qualified_identity(lease, qualified_context),
                  native_event={"provider": "codex", "event": "SessionEnd", "reason": reason})
    return result


def _capture(lease, payload, binding, check):
    root = r2._lease(lease)
    sid = binding["session_id"]
    source = Path(payload["transcript_path"])
    check()
    before = source.stat()
    h._require(stat.S_ISREG(before.st_mode) and before.st_size <= h.MAX_SNAPSHOT_BYTES,
               "SOURCE_SIZE_OR_TYPE")
    directory = r2._path(root, f"{h.NATIVE_AREA}/{sid}/snapshots")
    directory.mkdir(parents=True, exist_ok=True)
    partial = r2._path(root, f"{h.NATIVE_AREA}/{sid}/snapshots/{uuid.uuid4().hex}.partial")
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as reader, partial.open("xb") as writer:
        handle_before = os.fstat(reader.fileno())
        # Compare ctime only within the same API (Windows stat/fstat differ).
        h._require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                   (handle_before.st_dev, handle_before.st_ino, handle_before.st_size,
                    handle_before.st_mtime_ns), "SNAPSHOT_UNSTABLE")
        while True:
            check()
            data = reader.read(CHUNK)
            if not data:
                break
            size += len(data)
            h._require(size <= h.MAX_SNAPSHOT_BYTES, "SOURCE_SIZE_OR_TYPE")
            writer.write(data)
            digest.update(data)
        writer.flush()
        check()
        os.fsync(writer.fileno())
        check()
        h._require(_stat(handle_before) == _stat(os.fstat(reader.fileno())), "SNAPSHOT_UNSTABLE")
    after = source.stat()
    h._require(_stat(before) == _stat(after) and size == before.st_size, "SNAPSHOT_UNSTABLE")
    sha = digest.hexdigest()
    relative = f"{h.NATIVE_AREA}/{sid}/snapshots/{sha}.jsonl"
    target = r2._path(root, relative)
    check()
    try:
        os.link(partial, target)
    except FileExistsError:
        pass
    h._sync_directory(directory)
    check()
    readback = hashlib.sha256()
    with target.open("rb") as reader:
        while True:
            check()
            data = reader.read(CHUNK)
            if not data:
                break
            readback.update(data)
    h._require(target.stat().st_size == size and readback.hexdigest() == sha, "SNAPSHOT_READBACK")
    h._require(_stat(source.stat()) == _stat(before), "SNAPSHOT_UNSTABLE")
    # Successful publication consumes its temporary name, as Core _publish does.
    # Failure paths above retain partial evidence; no published object is removed.
    partial.unlink()
    manifest = dict(schema_version="1.0", provider="owned-sessionend-snapshot", provider_version="1.0",
                    binding=binding, snapshot=dict(immutable_locator=relative, sha256=sha, size_bytes=size),
                    source=dict(path=str(source), before=_stat(before), after=_stat(after)),
                    native_payload=payload, captured_at=datetime.now(timezone.utc).isoformat(),
                    platform=dict(os=platform.platform(), python=platform.python_version(),
                                  codex_version=FORMAT_VERSION), **h.AUTHORITY)
    manifest_sha = h._sha(h.canonical_bytes(manifest))
    base = f"{h.NATIVE_AREA}/{sid}"
    ref = dict(schema_version="1.0", source_kind="codex_sessionend_observed_snapshot",
               session_id=sid, **manifest["snapshot"],
               manifest_locator=f"{base}/manifests/{manifest_sha}.json", manifest_sha256=manifest_sha,
               ref_locator=f"{base}/refs/{manifest_sha}.json", retention_contract="owned-sessionend-snapshot",
               retention_version="1.0", readable_after_hook=True, **h.AUTHORITY)
    # Validate format before making a ref consumable.
    h._validate_native_snapshot(target, sid, root, check)
    for path, value in ((ref["manifest_locator"], manifest), (ref["ref_locator"], ref)):
        check()
        h._publish(lease, path, value)
        check()
    return ref


def publish(consumer_root, payload, *, deadline_ms=None, budget=None):
    """Publish only; explicit invocation is not evidence of native hook firing."""
    if budget is None:
        budget = Budget(deadline_ms)
    check = budget.check
    check()
    root = Path(consumer_root).resolve(strict=True)
    _payload(payload, root)
    sid, reason = payload["session_id"], payload["reason"]
    check()
    # Cheap authority preflight precedes even lock-directory creation. Repeat
    # under exclusion below; an existing immutable request has its own retry path.
    if not r2._closeout_request_slot(root, sid).exists():
        r2._identity(root, sid)
        h._require(not r2._completion(root, sid), "CONSUMED_WITHOUT_REQUEST")
        h._framework_preflight(root)
        check()
    with r2.execution_exclusion(root) as lease:
        check()
        provider = h.NativeTranscriptProvider(root, check=check)
        slot = r2._closeout_request_slot(root, sid)
        if slot.exists():
            request = h._decode(h._read_native_metadata(slot))
            bound = h._validate_request(request, root)
            h._require(request["schema_version"] == "1.1" and bound["session_id"] == sid
                       and bound["native_event"]["reason"] == reason, "REQUEST_CONFLICT")
            # Never read the native path or current owner for finalized duplicates.
            provider.validate(root, bound["transcript"])
            h._require(provider.manifest["binding"] == {k: v for k, v in bound.items() if k != "transcript"},
                       "MANIFEST_BINDING_MISMATCH")
            if h._finalized_path(root, bound).exists():
                result = h._finalize(lease, request)
            else:
                # Existing request freezes preparation, including a later HOLD.
                # Validation of recovery belongs to Core, never re-execute it here.
                h._live(lease, request, provider)
                result = {"status": "ALREADY_REQUESTED", "request_id": request["request_id"]}
            check()
            return result
        with h._qualified_framework(lease) as qualified_context:
            binding = _binding(lease, sid, reason, qualified_context)
            check()
            refs = r2._path(root, f"{h.NATIVE_AREA}/{sid}/refs")
            existing = None
            for path in refs.glob("*.json"):
                check()
                h._require(existing is None, "AMBIGUOUS_ORPHAN_REFS")
                ref = h._decode(h._read_native_metadata(r2._path(root, path.relative_to(root).as_posix())))
                h._require(ref.get("ref_locator") == path.relative_to(root).as_posix(), "REF_PATH_MISMATCH")
                provider.validate(root, ref)
                h._require(provider.manifest["binding"] == binding, "ORPHAN_BINDING_MISMATCH")
                existing = ref
            ref = existing if existing is not None else _capture(lease, payload, binding, check)
            check()
            result = h._publish_request_with_lease(lease, sid, ref, provider, reason=reason, check=check,
                                                        qualified_context=qualified_context)
            check()
            return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--deadline-ms", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        budget = Budget(args.deadline_ms)
        raw = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
        h._require(len(raw) <= MAX_PAYLOAD_BYTES, "PAYLOAD_TOO_LARGE")
        def pairs(items):
            obj = {}
            for key, value in items:
                h._require(key not in obj, "DUPLICATE_PAYLOAD_KEY")
                obj[key] = value
            return obj
        payload = json.loads(raw, object_pairs_hook=pairs)
        result = publish(args.consumer_root, payload, budget=budget)
        budget.check()
        print(json.dumps(result))
        return 0
    except (ValueError, TypeError, KeyError, OSError, TimeoutError, RuntimeError) as exc:
        # Even a post-publication read-back failure cannot establish absence.
        print(json.dumps({"status": "UNCONFIRMED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
