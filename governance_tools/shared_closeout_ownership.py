"""R2 cooperative shared-text ownership. Does not author candidates or summaries.

Only the receipt-producing main() CLI participates in protected closeout.
Direct hook/core callers and arbitrary filesystem writers are not protected.
"""
from __future__ import annotations

import argparse
import errno
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from typing import Any
import uuid

from runtime_hooks.core._canonical_closeout import (
    _consumer_worktree_root, assess_session_closeout_binding,
    pick_latest_candidate, read_session_envelope,
)

AREA = "artifacts/runtime/shared-closeout"
TEXT = "artifacts/session-closeout.txt"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RECEIPT_ID = re.compile(r"[0-9]{8}T[0-9]{12}Z_r2_[0-9a-f]{32}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_LIVE: dict[int, "Lease"] = {}
_FIELDS = {"schema_version", "consumer_root", "session_id", "generation",
           "candidate_identity", "text_digest", "state", "hold_reason",
           "receipt_identity", "receipt_sha256"}


class OwnershipError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise OwnershipError(code, detail)


def _path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    _require(not rel.is_absolute() and ".." not in rel.parts, "INVALID_OWNER", "unsafe path")
    path = root / rel
    _require(path.is_relative_to(root) and path.resolve() == path,
             "INVALID_OWNER", "redirected artifact path")
    return path


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OwnershipError("INVALID_OWNER", str(path)) from exc
    _require(isinstance(value, dict), "INVALID_OWNER", "object required")
    return value


def _bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise OwnershipError("PAYLOAD_MISMATCH", str(path)) from exc


@dataclass(eq=False)
class Lease:
    root: Path
    pid: int
    thread: int


def _lease(lease: Lease) -> Path:
    _require(_LIVE.get(id(lease)) is lease and lease.pid == os.getpid()
             and lease.thread == threading.get_ident(), "R2_BUSY", "live process lease required")
    return lease.root


@contextmanager
def execution_exclusion(consumer_root: Path, *, create: bool = True):
    """Nonblocking OS exclusion; no process-local fallback or lock-file deletion."""
    root = _consumer_worktree_root(Path(consumer_root))
    path = _path(root, AREA + "/execution.lock")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | (os.O_CREAT if create else 0), 0o600)
    locked = False
    lease = Lease(root, os.getpid(), threading.get_ident())
    try:
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            elif os.name == "posix":
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise OSError("unsupported OS lock backend")
            locked = True
        except (OSError, ImportError) as exc:
            # Diagnostic callers must distinguish contention from an unavailable
            # backend. Default execution preserves its existing fail-closed code.
            busy = isinstance(exc, OSError) and exc.errno in {errno.EACCES, errno.EAGAIN}
            code = "R2_BUSY" if create or busy else "R2_LOCK_UNKNOWN"
            raise OwnershipError(code, "OS exclusion unavailable") from exc
        _LIVE[id(lease)] = lease
        yield lease
    finally:
        _LIVE.pop(id(lease), None)
        try:
            if locked:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _publish(lease: Lease, relative: str, value: dict, *, replace: bool = False) -> Path:
    root = _lease(lease)
    path = _path(root, relative)
    data = _bytes(value)
    if path.exists() and not replace:
        _require(path.read_bytes() == data, "RELEASE_PROOF_INVALID", "conflicting published record")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _path(root, relative)
        temporary.replace(path)
        _require(path.read_bytes() == data, "RELEASE_PROOF_INVALID", "publication read-back failed")
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _identity(root: Path, sid: str) -> None:
    _require(isinstance(sid, str) and bool(_ID.fullmatch(sid)), "INVALID_OWNER", "unsafe session")
    _path(root, f"artifacts/runtime/sessions/{sid}/session-envelope.json")
    envelope = read_session_envelope(sid, root)
    _require(envelope is not None and envelope.get("schema_version") == "1.1",
             "INVALID_OWNER", "qualified R1 binding required")


def _completion(root: Path, sid: str) -> bool:
    path = _path(root, f"artifacts/runtime/closeout-completions/{sid}.json")
    if not path.exists():
        return False
    data = _json(path)
    required = data.get("required_artifacts")
    _require(data.get("session_id") == sid and isinstance(required, list) and bool(required),
             "INVALID_OWNER", "invalid consumption evidence")
    for name in required:
        _require(isinstance(name, str) and bool(name), "INVALID_OWNER")
        _require(_path(root, name).is_file(), "INVALID_OWNER", "missing consumption artifact")
    return True


def _candidate(root: Path, sid: str, value: Any) -> None:
    _require(isinstance(value, dict) and set(value) == {"relative_path", "sha256"}, "INVALID_OWNER")
    rel, sha = value["relative_path"], value["sha256"]
    _require(isinstance(rel, str) and isinstance(sha, str) and bool(_SHA.fullmatch(sha)), "INVALID_OWNER")
    path = _path(root, rel)
    directory = _path(root, f"artifacts/runtime/closeout_candidates/{sid}")
    _require(path.parent == directory and path.suffix == ".json", "INVALID_OWNER", "candidate path")


def _owner(lease: Lease) -> dict | None:
    root = _lease(lease)
    path = _path(root, AREA + "/owner.json")
    if not path.exists():
        return None
    o = _json(path)
    _require(set(o) == _FIELDS and o["schema_version"] == "1.0"
             and o["consumer_root"] == str(root), "INVALID_OWNER")
    _identity(root, o["session_id"])
    _require(type(o["generation"]) is int and o["generation"] > 0, "INVALID_OWNER")
    _candidate(root, o["session_id"], o["candidate_identity"])
    _require(isinstance(o["text_digest"], str) and bool(_SHA.fullmatch(o["text_digest"])), "INVALID_OWNER")
    _require(isinstance(o["state"], str) and (o["hold_reason"] is None or isinstance(o["hold_reason"], str))
             and o["state"] in {"OWNED", "HOLD", "RELEASED"}
             and o["hold_reason"] in {None, "preparation_pending", "closeout_pending", "failed"}, "INVALID_OWNER")
    rid, sha = o["receipt_identity"], o["receipt_sha256"]
    _require(rid is None or (isinstance(rid, str) and bool(_RECEIPT_ID.fullmatch(rid))), "INVALID_OWNER")
    _require(sha is None or (isinstance(sha, str) and bool(_SHA.fullmatch(sha))), "INVALID_OWNER")
    _require((o["state"] == "HOLD") == (o["hold_reason"] is not None), "INVALID_OWNER")
    if o["state"] == "RELEASED":
        _require(rid is not None and sha is not None, "INVALID_OWNER")
    if o["state"] == "OWNED" or o["hold_reason"] == "preparation_pending":
        _require(rid is None and sha is None, "INVALID_OWNER")
    if o["hold_reason"] == "closeout_pending":
        _require(rid is not None, "INVALID_OWNER")
    return o


def _matching(lease: Lease, sid: str, generation: int | None = None) -> dict:
    o = _owner(lease)
    if o is None:
        code = "AMBIGUOUS_LEGACY_STATE" if _path(lease.root, TEXT).exists() else "INVALID_OWNER"
        raise OwnershipError(code, "owner required")
    _require(o["session_id"] == sid, "OWNER_CONFLICT")
    if generation is not None:
        _require(type(generation) is int and o["generation"] == generation, "GENERATION_MISMATCH")
    return o


def _initial(root: Path, sid: str) -> None:
    _require(not _path(root, TEXT).exists(), "AMBIGUOUS_LEGACY_STATE")
    area = _path(root, AREA)
    _require(all(p.name == "execution.lock" for p in area.iterdir()), "AMBIGUOUS_LEGACY_STATE")
    # Unknown/orphan/active lifecycle state cannot initialize FREE.
    for directory, envelope_dir in (("sessions", True), ("closeout_candidates", True),
                                     ("closeout-completions", False), ("closeouts", False),
                                     ("candidates", False), ("curated", False),
                                     ("summaries", False), ("verdicts", False), ("traces", False)):
        parent = _path(root, "artifacts/runtime/" + directory)
        if not parent.exists():
            continue
        for item in parent.iterdir():
            _path(root, item.relative_to(root).as_posix())
            other = item.name if envelope_dir else item.stem
            if directory == "sessions" and other == sid:
                _require(item.is_dir() and all(p.name == "session-envelope.json"
                         for p in item.iterdir()), "AMBIGUOUS_LEGACY_STATE")
                continue
            _require(bool(_ID.fullmatch(other)), "AMBIGUOUS_LEGACY_STATE")
            _require(read_session_envelope(other, root) is not None and _completion(root, other),
                     "AMBIGUOUS_LEGACY_STATE", "active or orphan lifecycle evidence")
    receipts = _path(root, "artifacts/runtime/closeout-receipts")
    if receipts.exists():
        for p in receipts.iterdir():
            data = _json(_path(root, p.relative_to(root).as_posix()))
            other = data.get("session_id")
            _require(isinstance(other, str) and bool(_ID.fullmatch(other)) and _completion(root, other),
                     "AMBIGUOUS_LEGACY_STATE", "unexplained receipt")


def _payloads(lease: Lease, o: dict) -> None:
    root = _lease(lease)
    ci = o["candidate_identity"]
    candidate = _path(root, ci["relative_path"])
    files = sorted(candidate.parent.glob("*.json"))
    _require(bool(files) and files[-1] == candidate, "PAYLOAD_MISMATCH", "selected candidate changed")
    _require(_digest(candidate) == ci["sha256"] and _digest(_path(root, TEXT)) == o["text_digest"],
             "PAYLOAD_MISMATCH")


def _closeout_request_slot(root: Path, session_id: str) -> Path:
    """Existence alone freezes preparation; R2 deliberately does not parse requests."""
    _require(isinstance(session_id, str) and bool(_ID.fullmatch(session_id)),
             "INVALID_OWNER", "unsafe session")
    return _path(root, f"artifacts/runtime/closeout-requests/{session_id}/request.json")


def _require_unrequested(lease: Lease, session_id: str) -> None:
    slot = _closeout_request_slot(_lease(lease), session_id)
    _require(not slot.exists(), "CLOSEOUT_REQUESTED", "preparation is frozen")


def acquire_owner(lease: Lease, session_id: str, candidate_identity: dict, text_digest: str) -> dict:
    root = _lease(lease)
    _require_unrequested(lease, session_id)
    _identity(root, session_id)
    _require(not _completion(root, session_id), "CONSUMED_SESSION")
    _candidate(root, session_id, candidate_identity)
    _require(isinstance(text_digest, str) and bool(_SHA.fullmatch(text_digest)), "INVALID_OWNER")
    candidate = _path(root, candidate_identity["relative_path"])
    _require(not candidate.exists(), "PAYLOAD_MISMATCH", "retry must append a new candidate")
    o = _owner(lease)
    if o is None:
        _initial(root, session_id)
        generation = 1
    else:
        if o["state"] == "RELEASED":
            if _closeout_request_slot(root, o["session_id"]).exists():
                # Bounded handoff integration: validate the full immutable proof,
                # never treat finalized.json existence as permission to advance.
                # Lazy import keeps ordinary preparation independent of handoff.
                from governance_tools.closeout_handoff import validate_finalization
                validate_finalization(lease, o["session_id"], expected_owner=o)
            _verify_release(lease, o)
        else:
            _require(o["session_id"] == session_id, "OWNER_CONFLICT")
        generation = o["generation"] + 1
    new = dict(schema_version="1.0", consumer_root=str(root), session_id=session_id,
               generation=generation, candidate_identity=dict(candidate_identity), text_digest=text_digest,
               state="HOLD", hold_reason="preparation_pending", receipt_identity=None, receipt_sha256=None)
    _publish(lease, AREA + "/owner.json", new, replace=True)
    return new


def confirm_prepared(lease: Lease, session_id: str, generation: int) -> dict:
    _require_unrequested(lease, session_id)
    o = _matching(lease, session_id, generation)
    _require(o["state"] == "HOLD" and o["hold_reason"] == "preparation_pending", "INVALID_OWNER")
    _require(not _completion(lease.root, session_id), "CONSUMED_SESSION")
    _payloads(lease, o)
    binding = assess_session_closeout_binding(session_id, lease.root, pick_latest_candidate(session_id, lease.root))
    _require(binding["status"] == "valid", "PAYLOAD_MISMATCH", "candidate session binding")
    o.update(state="OWNED", hold_reason=None)
    _publish(lease, AREA + "/owner.json", o, replace=True)
    return o


def begin_closeout(lease: Lease, session_id: str, generation: int | None = None) -> dict:
    o = _matching(lease, session_id, generation)
    _require(not _completion(lease.root, session_id), "CONSUMED_SESSION")
    _require(o["state"] == "OWNED", "INVALID_OWNER", "prepared owner required")
    _payloads(lease, o)
    o.update(state="HOLD", hold_reason="closeout_pending", receipt_identity=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_r2_" + uuid.uuid4().hex)
    _publish(lease, AREA + "/owner.json", o, replace=True)
    return o


def receipt_binding(o: dict) -> dict:
    return dict(schema_version="1.0", consumer_root=o["consumer_root"], session_id=o["session_id"],
                generation=o["generation"], candidate_identity=dict(o["candidate_identity"]),
                expected_text_digest=o["text_digest"], receipt_identity=o["receipt_identity"])


def _receipt_relative(o: dict) -> str:
    return f'artifacts/runtime/closeout-receipts/closeout_receipt_{o["receipt_identity"]}.json'


def _receipt_schema(data: dict) -> None:
    """Validate this receipt schema's bounded vocabulary without core extras.

    Unknown schema keywords fail closed. JSON Schema format remains annotation,
    matching the previous validator without an opt-in format checker.
    """
    schema = _json(Path(__file__).resolve().parents[1] / "schemas/closeout_receipt.schema.json")
    allowed = {"$schema", "$id", "title", "description", "format", "type",
               "required", "properties", "additionalProperties", "items", "enum",
               "const", "minLength", "minimum", "pattern", "allOf", "if", "then"}

    def supported(node):
        _require(isinstance(node, dict) and not (set(node) - allowed),
                 "RELEASE_PROOF_INVALID", "unsupported receipt schema keyword")
        _require(node.get("type") in {None, "object", "array", "string", "integer", "boolean"},
                 "RELEASE_PROOF_INVALID", "unsupported receipt schema type")
        _require(type(node.get("additionalProperties", True)) is bool,
                 "RELEASE_PROOF_INVALID", "unsupported additionalProperties schema")
        for child in node.get("properties", {}).values():
            supported(child)
        for key in ("items", "if", "then"):
            if key in node:
                supported(node[key])
        for child in node.get("allOf", []):
            supported(child)

    def equal(a, b):
        # Python treats True == 1; JSON Schema does not.
        return a == b and (isinstance(a, bool) == isinstance(b, bool))

    def matches(value, node):
        kind = node.get("type")
        checks = {"object": isinstance(value, dict), "array": isinstance(value, list),
                  "string": isinstance(value, str),
                  "integer": type(value) is int or (type(value) is float and value.is_integer()),
                  "boolean": type(value) is bool}
        if kind is not None and not checks[kind]:
            return False
        if "const" in node and not equal(value, node["const"]):
            return False
        if "enum" in node and not any(equal(value, x) for x in node["enum"]):
            return False
        if isinstance(value, dict):
            props = node.get("properties", {})
            if not set(node.get("required", [])).issubset(value):
                return False
            if node.get("additionalProperties") is False and set(value) - set(props):
                return False
            if any(not matches(value[k], v) for k, v in props.items() if k in value):
                return False
        if isinstance(value, list) and "items" in node:
            if any(not matches(item, node["items"]) for item in value):
                return False
        if isinstance(value, str):
            if len(value) < node.get("minLength", 0):
                return False
            if "pattern" in node and re.search(node["pattern"], value) is None:
                return False
        if type(value) in (int, float) and "minimum" in node and value < node["minimum"]:
            return False
        if any(not matches(value, child) for child in node.get("allOf", [])):
            return False
        if "if" in node and matches(value, node["if"]):
            return matches(value, node.get("then", {}))
        return True

    supported(schema)
    _require(matches(data, schema), "RELEASE_PROOF_INVALID", "receipt schema invalid")


def publish_receipt(lease: Lease, receipt: dict) -> Path:
    _receipt_schema(receipt)
    o = _matching(lease, receipt.get("session_id", ""))
    _require(o["state"] == "HOLD" and o["hold_reason"] == "closeout_pending", "RELEASE_PROOF_INVALID")
    _payloads(lease, o)
    _require(receipt.get("schema_version") == "1.5" and receipt.get("exit_code") == 0
             and receipt.get("r2_binding") == receipt_binding(o)
             and receipt.get("checksum_of_cleaned_path") == o["text_digest"]
             and receipt.get("closeout_artifact_path") == str(_path(lease.root, TEXT)), "RELEASE_PROOF_INVALID")
    path = _path(lease.root, _receipt_relative(o))
    _require(not path.exists(), "RELEASE_PROOF_INVALID", "receipt already exists")
    return _publish(lease, _receipt_relative(o), receipt)


def _receipt_proof(lease: Lease, o: dict) -> str:
    _require(o["receipt_identity"] is not None and _completion(lease.root, o["session_id"]),
             "RELEASE_PROOF_INVALID", "consumed session and reserved receipt required")
    path = _path(lease.root, _receipt_relative(o))
    data = _json(path)
    _receipt_schema(data)
    _require(data.get("schema_version") == "1.5" and data.get("exit_code") == 0
             and data.get("session_id") == o["session_id"]
             and data.get("r2_binding") == receipt_binding(o)
             and data.get("checksum_of_cleaned_path") == o["text_digest"]
             and data.get("closeout_artifact_path") == str(_path(lease.root, TEXT)), "RELEASE_PROOF_INVALID")
    sha = _digest(path)
    _require(o["receipt_sha256"] in (None, sha), "RELEASE_PROOF_INVALID")
    return sha


def _release_record(o: dict, sha: str) -> dict:
    return {**receipt_binding(o), "receipt_sha256": sha, "state": "RELEASED"}


def _verify_release(lease: Lease, o: dict) -> None:
    _payloads(lease, o)
    sha = _receipt_proof(lease, o)
    release = _json(_path(lease.root, f'{AREA}/releases/{o["generation"]}.json'))
    _require(release == _release_record(o, sha), "RELEASE_PROOF_INVALID")


def finalize_release(lease: Lease, receipt: Path) -> dict:
    o = _owner(lease)
    _require(o is not None and o["state"] == "HOLD"
             and o["hold_reason"] in {"closeout_pending", "failed"}, "RELEASE_PROOF_INVALID")
    _require(receipt == _path(lease.root, _receipt_relative(o)), "RELEASE_PROOF_INVALID")
    _payloads(lease, o)
    sha = _receipt_proof(lease, o)
    _publish(lease, f'{AREA}/releases/{o["generation"]}.json', _release_record(o, sha))
    o.update(state="RELEASED", hold_reason=None, receipt_sha256=sha)
    _publish(lease, AREA + "/owner.json", o, replace=True)
    return o


def reconcile_release(consumer_root: Path, session_id: str, generation: int, receipt_identity: str) -> dict:
    with execution_exclusion(consumer_root) as lease:
        o = _matching(lease, session_id, generation)
        _require(o["receipt_identity"] == receipt_identity, "RELEASE_PROOF_INVALID")
        if o["state"] == "RELEASED":
            _verify_release(lease, o)
            return {"status": "ALREADY_RELEASED", "generation": generation}
        result = finalize_release(lease, _path(lease.root, _receipt_relative(o)))
        return {"status": result["state"], "generation": generation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["reconcile-release"])
    parser.add_argument("--consumer-root", required=True, type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--generation", required=True, type=int)
    parser.add_argument("--receipt-identity", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(reconcile_release(args.consumer_root, args.session_id,
                                           args.generation, args.receipt_identity)))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
