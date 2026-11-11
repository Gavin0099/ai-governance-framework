"""Owner closeout attestation: a recorded, byte-bound statement that the owner
asked this exact session to close out.

THREAT MODEL IS COOPERATIVE, AND THIS IS THE WHOLE CLAIM. Nothing here can
distinguish a command the owner typed from one an agent issued: the same process
can write this record. What it provides is a recorded operation whose bytes are
bound to exact state. It does not establish that the statement came from the
owner, nor that the owner knew of it: a record that looks like owner
authorization can be written by the same process that benefits from it. So it
does not make an unauthorized release detectable on its own, and it is not
attribution.

It is NOT authentication, NOT proof of human origin, and NOT non-repudiation.
An agent that ignores the rule can still write a well-formed attestation.
Proving human origin would need an independently authenticated confirmation
source, which this does not have and does not pretend to.

Design notes it inherits from docs/governance/claude-closeout-authorization-gate-design-candidate-20261023.md:
- the identity payload must not contain the identity, so `attestation_id` sits
  outside the `attestation` sub-object and digests that sub-object only;
- binding `generation` is what makes replay fail, and binding
  `candidate_identity`/`text_digest` means the owner authorized *these* summary
  bytes rather than closeout in general.

Two kinds of record (owner ruling 2026-11-11, #233):
- schema 1.0, `owner_statement`: what the owner asked for this session;
- schema 1.1, `authorization`: a reference to an owner authorization given in
  advance. The owner may authorize a future closeout or handover condition once,
  in a committed `[Owner Closeout Authorization]` block, instead of being asked
  again at every handover. The reference is a durable pointer, not the
  authorization itself: the block must name a verifiable original owner source
  (an https URL or a SHA-256 of the owner's record) and must already be in the
  history of `repo_head_before`, the HEAD the platform's SessionStart hook
  recorded before the agent acted. Commit dates are never used: whoever commits
  sets them. So nothing a session commits, backdated or not, can authorize that
  session. Git still proves bytes and order, not who wrote them: a block written
  by an earlier session is not stopped here, so whether SOURCE really is the
  owner's is checked by a person, and a block that fails that check makes the
  closeout invalid after the fact.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2

AREA = "artifacts/runtime/closeout-intents"
SCHEMA_VERSION = "1.0"
STANDING_SCHEMA_VERSION = "1.1"
MAX_STATEMENT = 4096
# Bound to the exact state the owner authorized. Any drift invalidates it.
_BOUND = ("consumer_root", "session_id", "generation", "candidate_identity", "text_digest")

AUTHORIZATION_HEADER = "[Owner Closeout Authorization]"
_AUTHORIZATION_FIELDS = ("SOURCE", "CONDITION")
_FIELD_LINE = re.compile(r"^([A-Z]+)\s*=\s*(.*?)\s*$")
_VERIFIABLE_SOURCE = re.compile(r"https://\S+|\b[0-9a-f]{64}\b")
_COMMIT = re.compile(r"[0-9a-fA-F]{4,64}")


def _statement(value) -> str:
    h._require(isinstance(value, str), "INVALID_ATTESTATION: statement must be text")
    text = value.strip()
    h._require(text and len(text.encode()) <= MAX_STATEMENT,
               "INVALID_ATTESTATION: statement must be non-empty and bounded")
    return text


def build(owner: dict, statement: str, *, attested_at: str | None = None) -> dict:
    """The record for one owner statement about one exact owner generation."""
    attestation = {k: owner[k] for k in _BOUND}
    attestation["owner_statement"] = _statement(statement)
    attestation["attested_at"] = attested_at or datetime.now(timezone.utc).isoformat()
    attestation["schema_version"] = SCHEMA_VERSION
    return {"attestation": attestation,
            "attestation_id": h._sha(h.canonical_bytes(attestation))}


# --------------------------------------------------------------------------
# Standing owner authorization (schema 1.1)
# --------------------------------------------------------------------------

def _git(root, *args) -> str:
    """Read-only git query against the consumer's own repository."""
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
    h._require(completed.returncode == 0,
               "AUTHORIZATION_REF_INVALID: git " + " ".join(args[:2]) + " failed")
    return completed.stdout


def _parse_ref(ref) -> tuple[str, str]:
    h._require(isinstance(ref, str) and ref.count("@") == 1,
               "AUTHORIZATION_REF_INVALID: expected <path>@<commit>")
    path, commit = ref.split("@")
    pure = PurePosixPath(path)
    h._require(bool(path) and "\\" not in path and not pure.is_absolute()
               and ".." not in pure.parts and pure.as_posix() == path,
               "AUTHORIZATION_REF_INVALID: path must be repository-relative")
    h._require(bool(_COMMIT.fullmatch(commit)), "AUTHORIZATION_REF_INVALID: commit")
    return path, commit


def authorization_block(text: str) -> dict:
    """The fields of the one authorization block in a committed file."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == AUTHORIZATION_HEADER]
    h._require(len(starts) == 1, "AUTHORIZATION_BLOCK_MISSING: exactly one "
               f"{AUTHORIZATION_HEADER} block is required")
    fields: dict[str, str] = {}
    for line in lines[starts[0] + 1:]:
        match = _FIELD_LINE.match(line.strip())
        if match is None:
            break
        h._require(match.group(1) not in fields, "AUTHORIZATION_BLOCK_INVALID: duplicate field")
        fields[match.group(1)] = match.group(2)
    for name in _AUTHORIZATION_FIELDS:
        value = fields.get(name, "")
        h._require(bool(value) and len(value.encode()) <= MAX_STATEMENT,
                   f"AUTHORIZATION_BLOCK_INVALID: {name} must be present and bounded")
    h._require(_VERIFIABLE_SOURCE.search(fields["SOURCE"]) is not None,
               "AUTHORIZATION_SOURCE_UNVERIFIABLE: SOURCE must name an https URL or "
               "a SHA-256 of the owner's original record")
    return {name.lower(): fields[name] for name in _AUTHORIZATION_FIELDS}


def resolve_authorization(root, ref, session_id: str) -> dict:
    """Resolve a reference against Git history and the closing session's start.

    Every check reads the repository and the session envelope again, so the
    stored record can never stand in for the evidence it names.
    """
    path, commit = _parse_ref(ref)
    oid = _git(root, "rev-parse", "--verify", "--quiet", commit + "^{commit}").strip()
    h._require(bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid)),
               "AUTHORIZATION_REF_INVALID: commit")
    ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", oid, "HEAD"],
                              capture_output=True)
    h._require(ancestor.returncode == 0,
               "AUTHORIZATION_REF_INVALID: commit is not in the history of HEAD")
    blob = subprocess.run(["git", "-C", str(root), "cat-file", "blob", f"{oid}:{path}"],
                          capture_output=True)
    h._require(blob.returncode == 0, "AUTHORIZATION_REF_INVALID: path not in that commit")
    block = authorization_block(blob.stdout.decode("utf-8", errors="strict"))
    # "Before the session started" is decided by history, never by commit dates,
    # which whoever commits can set. The anchor is the HEAD the platform's own
    # SessionStart hook recorded in the envelope before the agent acted; nothing
    # the session commits afterwards can become an ancestor of it.
    envelope = r2.read_session_envelope(session_id, Path(root)) or {}
    anchor = envelope.get("repo_head_before")
    h._require(isinstance(anchor, str) and bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", anchor)),
               "AUTHORIZATION_NOT_PRIOR: the closing session has no recorded starting HEAD")
    prior = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", oid, anchor],
                           capture_output=True)
    h._require(prior.returncode == 0,
               "AUTHORIZATION_NOT_PRIOR: the authorization must already be in the history "
               "the session started from")
    return {"path": path, "commit": oid, "session_start_head": anchor,
            "blob_sha256": hashlib.sha256(blob.stdout).hexdigest(), **block}


def build_standing(root, owner: dict, ref: str, condition_met: str,
                   *, attested_at: str | None = None) -> dict:
    """The record that this session met a condition the owner authorized in advance."""
    attestation = {k: owner[k] for k in _BOUND}
    attestation["authorization"] = resolve_authorization(root, ref, owner["session_id"])
    attestation["condition_met"] = _statement(condition_met)
    attestation["attested_at"] = attested_at or datetime.now(timezone.utc).isoformat()
    attestation["schema_version"] = STANDING_SCHEMA_VERSION
    return {"attestation": attestation,
            "attestation_id": h._sha(h.canonical_bytes(attestation))}


def _relative(session_id: str, attestation_id: str) -> str:
    return f"{AREA}/{session_id}/{attestation_id}.json"


def validate(record, root) -> dict:
    """Structural validation plus the identity-over-sub-object rule."""
    h._keys(record, {"attestation", "attestation_id"})
    a = record["attestation"]
    h._require(isinstance(a, dict), "INVALID_ATTESTATION: record")
    standing = a.get("schema_version") == STANDING_SCHEMA_VERSION
    kind = {"authorization", "condition_met"} if standing else {"owner_statement"}
    h._keys(a, set(_BOUND) | kind | {"attested_at", "schema_version"})
    h._require(a["schema_version"] in (SCHEMA_VERSION, STANDING_SCHEMA_VERSION),
               "INVALID_ATTESTATION: schema")
    h._require(a["consumer_root"] == str(root), "INVALID_ATTESTATION: consumer root")
    h._require(type(a["session_id"]) is str and bool(r2._ID.fullmatch(a["session_id"])),
               "INVALID_ATTESTATION: session")
    h._require(type(a["generation"]) is int and a["generation"] > 0,
               "INVALID_ATTESTATION: generation")
    h._hash(a["text_digest"])
    r2._candidate(root, a["session_id"], a["candidate_identity"])
    if standing:
        _statement(a["condition_met"])
        stored = a["authorization"]
        h._require(isinstance(stored, dict) and isinstance(stored.get("path"), str)
                   and isinstance(stored.get("commit"), str),
                   "INVALID_ATTESTATION: authorization")
        # Resolved again from Git and the envelope: a record that no longer
        # matches the history it names authorizes nothing.
        current = resolve_authorization(root, f'{stored["path"]}@{stored["commit"]}',
                                        a["session_id"])
        h._require(current == stored, "AUTHORIZATION_MISMATCH")
    else:
        _statement(a["owner_statement"])
    # fromisoformat raises TypeError on a non-str, which would escape _require
    # and propagate out of find(), so the type is checked first.
    h._require(type(a["attested_at"]) is str, "INVALID_ATTESTATION: timestamp type")
    try:
        parsed = datetime.fromisoformat(a["attested_at"])
    except ValueError as exc:
        raise h.HandoffError("INVALID_ATTESTATION: timestamp") from exc
    h._require(parsed.tzinfo is not None, "INVALID_ATTESTATION: timestamp")
    # The identity payload must not contain the identity.
    h._require(h._sha(h.canonical_bytes(a)) == record["attestation_id"],
               "ATTESTATION_ID_MISMATCH")
    return a


def publish(lease, owner: dict, statement: str) -> dict:
    """Write one attestation under the caller's existing R2 exclusion."""
    root = r2._lease(lease)
    record = build(owner, statement)
    validate(record, root)
    h._publish(lease, _relative(owner["session_id"], record["attestation_id"]), record)
    return record


def record(consumer_root, session_id: str, statement: str) -> dict:
    """Attest against whatever generation currently owns the worktree."""
    with r2.execution_exclusion(consumer_root) as lease:
        owner = r2._matching(lease, session_id)
        return publish(lease, owner, statement)


def record_standing(consumer_root, session_id: str, ref: str, condition_met: str) -> dict:
    """Record that this session met a condition the owner authorized in advance."""
    with r2.execution_exclusion(consumer_root) as lease:
        owner = r2._matching(lease, session_id)
        root = r2._lease(lease)
        record = build_standing(root, owner, ref, condition_met)
        validate(record, root)
        h._publish(lease, _relative(owner["session_id"], record["attestation_id"]), record)
        return record


def find(root, binding: dict):
    """The one attestation matching this binding exactly, or None.

    Reads only the record whose own id it recomputes, so a renamed or tampered
    file cannot be presented as a different attestation.
    """
    directory = r2._path(root, f"{AREA}/{binding['session_id']}")
    if not directory.is_dir():
        return None
    wanted = {k: binding[k] for k in _BOUND}
    for path in sorted(directory.glob("*.json")):
        relative = path.relative_to(root).as_posix()
        try:
            candidate = h._read(r2._path(root, relative))
            a = validate(candidate, root)
        except (ValueError, TypeError, KeyError, OSError):
            # A malformed record is skipped, never fatal: aborting the scan
            # would let one bad file permanently block a legitimate handover,
            # which is the half of #233 that is not about wrongful release.
            continue
        # The filename must be the identity, so the store cannot be reshuffled.
        if path.stem != candidate["attestation_id"]:
            continue
        if {k: a[k] for k in _BOUND} == wanted:
            return candidate
    return None


def require(lease, binding: dict) -> dict:
    """Fail closed unless an attestation binds this exact owner state."""
    root = r2._lease(lease)
    found = find(root, binding)
    h._require(found is not None, "CLOSEOUT_NOT_ATTESTED")
    return found
