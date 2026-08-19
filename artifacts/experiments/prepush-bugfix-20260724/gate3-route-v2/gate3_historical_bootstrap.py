"""Bootstrap authority chain for historical evidence reconstruction (M1).

This module validates the authority chain that must hold **before** any
historical code is materialized or executed.  It is step 1 of the historical
materialization design and is deliberately inert on its own.

Not active.  Nothing here is wired into the production candidate verifier; the
production path switches at M4.  Until then this module has no callers in the
verification flow, and a test asserts that.

It performs no filesystem lookup for its expectations, starts no child process,
materializes nothing, and imports no historical module.  Every artifact it
checks is passed in as bytes by the caller.
"""

from __future__ import annotations

import hashlib
import json
from typing import Mapping


# Frozen expected digests.  These are literals in reviewed, merged code — not
# values read from the artifacts under verification, which would be circular.
#
# The owner promotion (commit 8da68734) binds the contract manifest.  It does
# **not** bind the candidate set, and the source commit lives only inside the
# candidate set, so the candidate-set digest needs its own non-circular source.
# That source is this literal.  PLAN.md records the same value at the promoted
# milestone entry as reviewer-checkable corroboration, not as the runtime
# expectation.
CONTRACT_MANIFEST_SHA256 = (
    "fd6c75eb7e3bb7f36f85804b7b2398a07d5647d948691f2d9ff64ea094998440"
)
CANDIDATE_SET_SHA256 = (
    "db86a97b36a2e80e43e9e0765f07f20cb00e07aa813cbf54bea2b587f3c02baa"
)
SOURCE_COMMIT = "204965c94bd843d599986d9f9d0fd552ea053dff"
CANDIDATE_SET_SCHEMA = "gate3-route-v2-ab.candidate-set.v1"
OWNER_PIN_SCHEMA = "gate3-route-v2-ab.owner-manifest-pin.v1"
OWNER_PIN_PATH = (
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3-route-v2-ab-owner-pin.json"
)
OWNER_PROMOTION_COMMIT = "8da68734"
PROMOTION_STATE = "SIGNED_AND_PROMOTED"

# Only these five are historical *runtime modules*.  The candidate set retains
# eleven files, including `.gitattributes`, JSON manifests, Markdown and a test
# module; handing that whole list to a later loader would expand executable
# authority far beyond what reconstruction needs.
#
# The fifth, `gate3_route_v2_ab_candidate.py`, was added by the BLOCKED-1
# amendment of the M3-b design.  It is the module whose execution *is* the
# reconstruction: `build_contract_manifest()` and `build_candidate_set()` live
# in it, and loading it from the pinned commit rather than calling the present
# one is the difference between reconstructing history and re-running the
# present.  This widens executable authority by one module and is recorded here
# as that, not as a list that happened to grow.
RUNTIME_MODULE_ALLOWLIST = (
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_ab.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_ab_candidate.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_ab_live.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_codex.py",
)

ACTIVE = False
"""M1 is not wired into the production verifier.  M4 switches that path."""


class BootstrapError(ValueError):
    """Closed bootstrap error that never renders artifact content."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise BootstrapError("ARTIFACT_NOT_BYTES")
    return hashlib.sha256(payload).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Refuse ambiguous JSON.

    `json.loads` keeps the last value for a duplicated key, silently, before any
    exact-field check can see the first one.  The owner pin has no frozen
    whole-byte digest, so its parser *is* the authority boundary: a document
    carrying `manifest_sha256` twice must be rejected, not resolved.
    """

    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise BootstrapError("ARTIFACT_DUPLICATE_KEY")
        seen[key] = value
    return seen


def _parse(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(
            payload.decode("ascii"), object_pairs_hook=_reject_duplicate_keys
        )
    except BootstrapError:
        raise
    except Exception:
        raise BootstrapError("ARTIFACT_UNPARSEABLE") from None
    if not isinstance(value, dict):
        raise BootstrapError("ARTIFACT_UNPARSEABLE")
    return value


def verify_owner_pin(payload: bytes, path: str) -> dict[str, object]:
    """Link 1: the owner pin itself, injected as bytes and as its path.

    An earlier revision skipped this entirely and returned hard-coded promotion
    metadata, so a missing pin, a wrong schema, a wrong path, a state other than
    SIGNED_AND_PROMOTED, or a pin naming a different manifest all passed.
    """

    if type(path) is not str or path != OWNER_PIN_PATH:
        raise BootstrapError("OWNER_PIN_PATH_INVALID")
    value = _parse(payload)
    if set(value) != {"manifest_sha256", "schema", "status"}:
        raise BootstrapError("OWNER_PIN_SCHEMA_INVALID")
    if value.get("schema") != OWNER_PIN_SCHEMA:
        raise BootstrapError("OWNER_PIN_SCHEMA_INVALID")
    if value.get("status") != PROMOTION_STATE:
        raise BootstrapError("OWNER_PIN_NOT_PROMOTED")
    if value.get("manifest_sha256") != CONTRACT_MANIFEST_SHA256:
        raise BootstrapError("OWNER_PIN_MANIFEST_MISMATCH")
    return value


def verify_contract_manifest(payload: bytes, owner_pin: Mapping[str, object]) -> str:
    """Link 2: the contract manifest the verified pin names."""

    digest = _sha256(payload)
    if digest != CONTRACT_MANIFEST_SHA256:
        raise BootstrapError("CONTRACT_MANIFEST_DIGEST_MISMATCH")
    if owner_pin.get("manifest_sha256") != digest:
        raise BootstrapError("OWNER_PIN_MANIFEST_MISMATCH")
    return digest


def verify_candidate_set(payload: bytes) -> dict[str, object]:
    """Link 3: the candidate set, which the owner pin does not cover.

    Its digest is checked against the frozen literal, never against a value
    read from the payload itself.
    """

    digest = _sha256(payload)
    if digest != CANDIDATE_SET_SHA256:
        raise BootstrapError("CANDIDATE_SET_DIGEST_MISMATCH")
    value = _parse(payload)
    if value.get("schema") != CANDIDATE_SET_SCHEMA:
        raise BootstrapError("CANDIDATE_SET_SCHEMA_INVALID")
    return value


def verify_source_commit(candidate_set: Mapping[str, object]) -> str:
    """Link 4: the source commit named inside the verified candidate set."""

    named = candidate_set.get("source_base_commit")
    if type(named) is not str or named != SOURCE_COMMIT:
        raise BootstrapError("SOURCE_COMMIT_MISMATCH")
    return named


def retained_inventory(candidate_set: Mapping[str, object]) -> dict[str, str]:
    """All retained files and digests, derived only from verified bytes.

    This is the full eleven-file record.  It is **not** an executable set; see
    `runtime_module_inventory`.
    """

    records = candidate_set.get("files")
    if not isinstance(records, list) or not records:
        raise BootstrapError("FILE_INVENTORY_INVALID")
    inventory: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"bytes", "path", "sha256"}:
            raise BootstrapError("FILE_INVENTORY_INVALID")
        path = record["path"]
        digest = record["sha256"]
        size = record["bytes"]
        if (
            type(path) is not str
            or not path
            or type(digest) is not str
            or len(digest) != 64
            or not all(character in "0123456789abcdef" for character in digest)
            or type(size) is not int
            or size < 0
        ):
            raise BootstrapError("FILE_INVENTORY_INVALID")
        if path in inventory:
            raise BootstrapError("FILE_INVENTORY_DUPLICATE")
        inventory[path] = digest
    return inventory


def runtime_module_inventory(
    candidate_set: Mapping[str, object]
) -> dict[str, str]:
    """Link 5: the exact runtime modules a later loader may execute.

    Restricted to `RUNTIME_MODULE_ALLOWLIST`.  Paths and digests still come only
    from the verified candidate bytes; the allowlist decides which of those
    records carry executable authority, and every allowlisted path must be
    present exactly once.
    """

    retained = retained_inventory(candidate_set)
    selected: dict[str, str] = {}
    for path in RUNTIME_MODULE_ALLOWLIST:
        if path not in retained:
            raise BootstrapError("RUNTIME_MODULE_MISSING")
        selected[path] = retained[path]
    if len(selected) != len(RUNTIME_MODULE_ALLOWLIST):
        raise BootstrapError("RUNTIME_MODULE_INVENTORY_INVALID")
    return selected


def verify_bootstrap_chain(
    *,
    owner_pin: bytes,
    owner_pin_path: str,
    contract_manifest: bytes,
    candidate_set: bytes,
) -> dict[str, object]:
    """Run links 1 to 5 in order, on injected bytes only.

    Returns the validated facts a later step needs.  It performs no
    materialization, starts no process and executes no historical code; those
    belong to M2 and M3.
    """

    pin = verify_owner_pin(owner_pin, owner_pin_path)
    contract_digest = verify_contract_manifest(contract_manifest, pin)
    candidate_value = verify_candidate_set(candidate_set)
    source_commit = verify_source_commit(candidate_value)
    return {
        "candidate_set_sha256": CANDIDATE_SET_SHA256,
        "contract_manifest_sha256": contract_digest,
        "owner_promotion_commit": OWNER_PROMOTION_COMMIT,
        "promotion_state": str(pin["status"]),
        "retained_inventory": retained_inventory(candidate_value),
        "runtime_module_inventory": runtime_module_inventory(candidate_value),
        "source_commit": source_commit,
    }
