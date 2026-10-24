"""Owner closeout attestation: an explicit, attributable record that the owner
asked this exact session to close out.

THREAT MODEL IS COOPERATIVE, AND THIS IS THE WHOLE CLAIM. Nothing here can
distinguish a command the owner typed from one an agent issued: the same process
can write this record. What it provides is an explicit operation and a record
bound to exact state, so an unauthorized release cannot happen silently and can
be attributed after the fact.

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
"""
from __future__ import annotations

from datetime import datetime, timezone

from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2

AREA = "artifacts/runtime/closeout-intents"
SCHEMA_VERSION = "1.0"
MAX_STATEMENT = 4096
# Bound to the exact state the owner authorized. Any drift invalidates it.
_BOUND = ("consumer_root", "session_id", "generation", "candidate_identity", "text_digest")


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


def _relative(session_id: str, attestation_id: str) -> str:
    return f"{AREA}/{session_id}/{attestation_id}.json"


def validate(record, root) -> dict:
    """Structural validation plus the identity-over-sub-object rule."""
    h._keys(record, {"attestation", "attestation_id"})
    a = record["attestation"]
    h._keys(a, set(_BOUND) | {"owner_statement", "attested_at", "schema_version"})
    h._require(a["schema_version"] == SCHEMA_VERSION, "INVALID_ATTESTATION: schema")
    h._require(a["consumer_root"] == str(root), "INVALID_ATTESTATION: consumer root")
    h._require(type(a["session_id"]) is str and bool(r2._ID.fullmatch(a["session_id"])),
               "INVALID_ATTESTATION: session")
    h._require(type(a["generation"]) is int and a["generation"] > 0,
               "INVALID_ATTESTATION: generation")
    h._hash(a["text_digest"])
    r2._candidate(root, a["session_id"], a["candidate_identity"])
    _statement(a["owner_statement"])
    h._require(datetime.fromisoformat(a["attested_at"]).tzinfo is not None,
               "INVALID_ATTESTATION: timestamp")
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
        except (ValueError, OSError):
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
