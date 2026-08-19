"""Framed transport for historical evidence reconstruction (M3-a).

Authority: `docs/governance/gate3-m3-child-transport-design-candidate-20260818.md`
revision 5, subordinate to
`docs/governance/gate3-historical-evidence-materialization-design-candidate-20260815.md`
revision 10, which is where the framing table, the bounds and the authority
chain are specified.  This module implements them; it restates none of them as
new policy.

**One file, two roles.**  The parent imports `encode_stream`.  The child will
later execute this same file by absolute path under `-I -S -B`, as `__main__`.
That second role is M3-b and is not implemented here: this module defines no
`__main__` behaviour, spawns nothing, compiles nothing and imports no historical
module.

The two roles are why this file imports only the standard library.  A child
started with `-I -S -B` has nothing but the interpreter's own stdlib roots on
`sys.path` — measured on CPython 3.12.10, four entries, with even this file's
own directory excluded — so a repo-local import here would fail at the point
where the child is already running.  A test asserts the property from this
module's AST rather than trusting this paragraph.

Being one file is also what makes the encoder and the decoder *share* the wire
grammar rather than agree about it.  `_wire_path` is called by both, so
"applied identically by both sides" is a property of the code.

Not active.  `ACTIVE` is `False`, nothing calls into this module from the
verification flow, and a test asserts that.
"""

from __future__ import annotations

import collections.abc
import hashlib
import json
from typing import Mapping


# --- frozen authority -------------------------------------------------------
#
# These literals are the child's authority and they are duplicated from
# `gate3_historical_bootstrap` deliberately.  The child cannot import that
# module — see the docstring — and a child that received the parent's derivation
# would be trusting the parent's runtime state, which is the one thing the
# re-derivation exists not to do.
#
# This is *not* independent verification in the strong sense: both copies come
# from one author and one design, so a mistake in the design is made identically
# in both.  What it defends against is the parent's transport and data state
# being wrong.  Two tests bind the pair: an equality test against the bootstrap
# constants, and a differential test running both derivations over a named
# corpus.
CANDIDATE_SET_SHA256 = (
    "db86a97b36a2e80e43e9e0765f07f20cb00e07aa813cbf54bea2b587f3c02baa"
)

RUNTIME_MODULE_ALLOWLIST = (
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_ab.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_ab_live.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_route_v2_codex.py",
)

ACTIVE = False
"""M3-a is not wired into anything.  M3-b starts the child; M4 switches the
production path."""


# --- the wire ---------------------------------------------------------------

MAGIC = b"\x47\x41\x54\x45\x33\x48\x4d\x00"
VERSION = 1

HEADER_BYTES = 20
"""magic 8 + version 2 + record count 2 + aggregate payload length 8."""

# Bounds, as exact byte counts, because "4 MiB" is a unit and a limit has to be
# a number.
MAX_RECORDS = 64
MAX_PATH_BYTES = 512
MAX_CANDIDATE_SET_BYTES = 1_048_576
MAX_PAYLOAD_BYTES = 4_194_304
MAX_AGGREGATE_PAYLOAD_BYTES = 33_554_432

DERIVED_MAX_STREAM_BYTES = 34_638_232
"""Not a gate, and nothing compares against it.

It is the largest stream that satisfies every bound above:
`20 + (4 + 1,048,576) + (64 * 550) + 33,554,432`.  A cap above it could never
fire and one below it would have been the real limit under another name.  It is
recorded so the arithmetic is checkable; a test recomputes it from the bounds so
that changing a bound without changing this constant fails.
"""

_RECORD_FRAMING_BYTES = 550
"""path length 2 + path 512 + payload length 4 + digest 32, at maximum."""


class TransportError(ValueError):
    """Closed transport error that never renders stream or artifact content.

    The code is the whole message.  A rejection that quoted the bytes it
    rejected would put attacker-chosen content into a log.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# --- the wire path grammar --------------------------------------------------


def _decode_utf8(raw: bytes) -> str:
    """Strict UTF-8, and a seam the round-trip postcondition can be tested at.

    Separated from `_wire_path` for one reason: the postcondition below cannot
    be reached by any legal input, so the only way to evidence it is to mutate
    the decode and watch it fire.  A test does exactly that, with
    `errors="replace"`, with a normalizing decode and with a lenient codec.
    """

    return raw.decode("utf-8")


def _wire_path(raw: bytes) -> str:
    """The one grammar, applied by the encoder and by the decoder.

    This is **not** `gate3_historical_materialize._checked_relative`.  That one
    answers whether a path can escape a materialized root when joined to it;
    nothing here ever joins a path.  This one answers whether a byte sequence is
    a legal repo-relative path to compare against an inventory.  It accepts a
    subset of what the containment check accepts, and a differential test
    asserts that direction over a named corpus — that direction only, because
    claiming equivalence would be false.

    Defined positively rather than by exclusion, so that a form nobody thought
    of is refused rather than admitted by default.
    """

    if type(raw) is not bytes:
        raise TransportError("PATH_INVALID")
    if len(raw) > MAX_PATH_BYTES:
        raise TransportError("PATH_LENGTH_EXCEEDED")
    if not raw:
        raise TransportError("PATH_INVALID")
    try:
        text = _decode_utf8(raw)
    except UnicodeDecodeError:
        raise TransportError("PATH_INVALID") from None
    if text.encode("utf-8") != raw:
        # A postcondition, and unreachable by any legal input: strict UTF-8 is
        # canonical, so bytes that decode at all re-encode to themselves, and
        # the non-canonical forms that would break that — overlong sequences,
        # encoded surrogates, five-byte forms, anything above U+10FFFF — are
        # refused at the decode above.  What it defends against is *this
        # decoder* changing: an errors mode that replaces rather than raises, a
        # normalization step added for tidiness, a codec swapped for a lenient
        # one.  Any of those would let two byte sequences claim one path while
        # the record order is defined on the bytes.  Evidenced as a
        # decoder-mutation sensitivity test, not as an input case.
        raise TransportError("PATH_NOT_ROUND_TRIP")
    if "\x00" in text or "\\" in text or ":" in text:
        raise TransportError("PATH_INVALID")
    if "﻿" in text:
        raise TransportError("PATH_INVALID")
    if text.startswith("/") or text.endswith("/"):
        raise TransportError("PATH_INVALID")
    for segment in text.split("/"):
        if segment in ("", ".", ".."):
            raise TransportError("PATH_INVALID")
    return text


# --- the child's own derivation of the expected inventory -------------------


def _reject_duplicate_keys(pairs: list) -> dict:
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise TransportError("CANDIDATE_SET_DUPLICATE_KEY")
        seen[key] = value
    return seen


def _parse_candidate_set(payload: bytes) -> dict:
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except TransportError:
        raise
    except (UnicodeDecodeError, ValueError):
        raise TransportError("CANDIDATE_SET_INVALID") from None
    if not isinstance(value, dict):
        raise TransportError("CANDIDATE_SET_INVALID")
    return value


def _retained_inventory(candidate_set: Mapping) -> dict:
    records = candidate_set.get("files")
    if not isinstance(records, list) or not records:
        raise TransportError("FILE_INVENTORY_INVALID")
    inventory: dict = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"bytes", "path", "sha256"}:
            raise TransportError("FILE_INVENTORY_INVALID")
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
            raise TransportError("FILE_INVENTORY_INVALID")
        if path in inventory:
            raise TransportError("FILE_INVENTORY_DUPLICATE")
        inventory[path] = digest
    return inventory


def derive_inventory(candidate_set_bytes: bytes) -> dict:
    """The child's authority: expected paths and digests, from verified bytes.

    The frozen literal is what makes this more than a restatement of whatever
    the stream said.  The stream carries the candidate-set bytes, but it cannot
    reach the digest they are checked against, so it cannot make itself
    authoritative.

    Reading the expected digest out of the bytes under verification would be
    circular and is not done anywhere in this module.
    """

    if type(candidate_set_bytes) is not bytes:
        raise TransportError("CANDIDATE_SET_INVALID")
    if len(candidate_set_bytes) > MAX_CANDIDATE_SET_BYTES:
        raise TransportError("CANDIDATE_SET_EXCEEDED")
    if _sha256(candidate_set_bytes) != CANDIDATE_SET_SHA256:
        raise TransportError("CANDIDATE_SET_DIGEST_MISMATCH")
    retained = _retained_inventory(_parse_candidate_set(candidate_set_bytes))
    selected: dict = {}
    for path in RUNTIME_MODULE_ALLOWLIST:
        if path not in retained:
            raise TransportError("RUNTIME_MODULE_MISSING")
        selected[path] = retained[path]
    return selected


# --- encoding ---------------------------------------------------------------


def encode_stream(candidate_set_bytes: bytes, payloads: Mapping) -> bytes:
    """Build the framed stream.

    The bounds are enforced here as well as in the decoder.  Not because the
    decoder's checks are insufficient — those are the ones that matter, and they
    stay — but because a parent that can emit an illegal stream has a bug whose
    first symptom would otherwise be a child failing after a process spawn, far
    from the cause.  This is a diagnosis mechanism, not a second line of
    defence, and the decoder must not be relaxed on the strength of it.

    The digest of each payload is computed here, and the decoder recomputes it
    rather than trusting it.  It travels because the framing table says it does,
    not because anything downstream believes it.
    """

    if type(candidate_set_bytes) is not bytes:
        raise TransportError("CANDIDATE_SET_INVALID")
    if len(candidate_set_bytes) > MAX_CANDIDATE_SET_BYTES:
        raise TransportError("CANDIDATE_SET_EXCEEDED")
    if not isinstance(payloads, collections.abc.Mapping):
        raise TransportError("PAYLOADS_INVALID")
    if len(payloads) > MAX_RECORDS:
        raise TransportError("RECORD_COUNT_EXCEEDED")

    records = []
    for path, payload in payloads.items():
        if type(path) is not str or type(payload) is not bytes:
            raise TransportError("PAYLOADS_INVALID")
        try:
            raw_path = path.encode("utf-8")
        except UnicodeEncodeError:
            # A `str` can hold what UTF-8 cannot carry — a lone surrogate is the
            # everyday case, and `surrogateescape` decoding of a filesystem name
            # is where one comes from.  Without this the encoder would raise
            # `UnicodeEncodeError` instead of a closed code, which is a
            # different failure contract for the same class of bad path.
            raise TransportError("PATH_INVALID") from None
        # The same call the decoder makes, on the same bytes the decoder will
        # see.  Checking the str instead would be a different check.
        _wire_path(raw_path)
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise TransportError("PAYLOAD_EXCEEDED")
        records.append((raw_path, payload))

    # Bytewise on the UTF-8 path bytes: not code point order, not any locale
    # collation, and not the decoded string.  Two runs over the same module set
    # therefore produce byte-identical streams.
    records.sort(key=lambda record: record[0])
    for earlier, later in zip(records, records[1:]):
        if earlier[0] == later[0]:
            raise TransportError("RECORD_DUPLICATE_PATH")

    aggregate = sum(len(payload) for _, payload in records)
    if aggregate > MAX_AGGREGATE_PAYLOAD_BYTES:
        raise TransportError("AGGREGATE_EXCEEDED")

    parts = [
        MAGIC,
        VERSION.to_bytes(2, "little"),
        len(records).to_bytes(2, "little"),
        aggregate.to_bytes(8, "little"),
        len(candidate_set_bytes).to_bytes(4, "little"),
        candidate_set_bytes,
    ]
    for raw_path, payload in records:
        parts.append(len(raw_path).to_bytes(2, "little"))
        parts.append(raw_path)
        parts.append(len(payload).to_bytes(4, "little"))
        parts.append(hashlib.sha256(payload).digest())
        parts.append(payload)
    return b"".join(parts)


# --- decoding ---------------------------------------------------------------


class _Cursor:
    """A reader that refuses to slice past the end.

    Every `take` states the code its own truncation produces, so a short stream
    fails where it ran out rather than somewhere later with a borrowed error.
    """

    __slots__ = ("_data", "_offset")

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    def take(self, count: int, code: str) -> bytes:
        if count < 0 or count > self.remaining:
            raise TransportError(code)
        chunk = self._data[self._offset : self._offset + count]
        self._offset += count
        return chunk

    def take_int(self, width: int, code: str) -> int:
        return int.from_bytes(self.take(width, code), "little")


def decode_stream(stream: bytes) -> dict:
    """Verify a framed stream and return its payloads.

    The order is the security property.  The candidate-set block is checked
    against the frozen digest and the inventory derived from it **before any
    record is parsed**, so a stream that has no right to name these modules is
    refused before it can describe any of them.  Nothing is allocated from a
    number that has not been checked against its bound.

    Returns the payload bytes keyed by path.  Nothing is compiled, imported or
    executed here; selecting what runs is M3-b's problem and this function
    hands it verified buffers, not decisions.
    """

    if type(stream) is not bytes:
        raise TransportError("STREAM_INVALID")

    cursor = _Cursor(stream)
    if cursor.take(len(MAGIC), "STREAM_TRUNCATED") != MAGIC:
        raise TransportError("MAGIC_MISMATCH")
    if cursor.take_int(2, "STREAM_TRUNCATED") != VERSION:
        raise TransportError("VERSION_UNSUPPORTED")

    declared_count = cursor.take_int(2, "STREAM_TRUNCATED")
    declared_aggregate = cursor.take_int(8, "STREAM_TRUNCATED")
    # Checked here, before either is used to size anything.
    if declared_count > MAX_RECORDS:
        raise TransportError("RECORD_COUNT_EXCEEDED")
    if declared_aggregate > MAX_AGGREGATE_PAYLOAD_BYTES:
        raise TransportError("AGGREGATE_EXCEEDED")

    candidate_length = cursor.take_int(4, "STREAM_TRUNCATED")
    if candidate_length > MAX_CANDIDATE_SET_BYTES:
        raise TransportError("CANDIDATE_SET_EXCEEDED")
    candidate_set_bytes = cursor.take(candidate_length, "CANDIDATE_SET_TRUNCATED")

    # The authority, before anything else is read.
    expected = derive_inventory(candidate_set_bytes)

    payloads: dict = {}
    previous_raw_path = b""
    running_aggregate = 0
    for index in range(declared_count):
        path_length = cursor.take_int(2, "RECORD_TRUNCATED")
        if path_length > MAX_PATH_BYTES:
            raise TransportError("PATH_LENGTH_EXCEEDED")
        raw_path = cursor.take(path_length, "RECORD_TRUNCATED")
        path = _wire_path(raw_path)

        if index and raw_path == previous_raw_path:
            raise TransportError("RECORD_DUPLICATE_PATH")
        if index and raw_path < previous_raw_path:
            raise TransportError("RECORD_ORDER_INVALID")
        previous_raw_path = raw_path

        payload_length = cursor.take_int(4, "RECORD_TRUNCATED")
        if payload_length > MAX_PAYLOAD_BYTES:
            raise TransportError("PAYLOAD_EXCEEDED")
        # Refused at this record and before its bytes are read.  The
        # comparison is against what the header declared, not against
        # `MAX_AGGREGATE_PAYLOAD_BYTES`: the header already refused a
        # declaration above that bound, so `running > MAX` cannot happen
        # without `running > declared` happening first.  A second comparison
        # here would decide nothing and would read as though it did.
        if running_aggregate + payload_length > declared_aggregate:
            raise TransportError("AGGREGATE_MISMATCH")
        running_aggregate += payload_length

        framed_digest = cursor.take(32, "RECORD_TRUNCATED")
        payload = cursor.take(payload_length, "RECORD_TRUNCATED")

        actual = hashlib.sha256(payload)
        if actual.digest() != framed_digest:
            raise TransportError("PAYLOAD_DIGEST_MISMATCH")
        # A separate comparison against a separate authority.  The first says
        # the stream agrees with itself; only this one says the stream agrees
        # with the candidate set.  Neither substitutes for the other.
        if path not in expected:
            raise TransportError("INVENTORY_SET_MISMATCH")
        if actual.hexdigest() != expected[path]:
            raise TransportError("INVENTORY_DIGEST_MISMATCH")
        payloads[path] = payload

    if running_aggregate != declared_aggregate:
        raise TransportError("AGGREGATE_MISMATCH")
    if set(payloads) != set(expected):
        raise TransportError("INVENTORY_SET_MISMATCH")
    if cursor.remaining:
        raise TransportError("TRAILING_BYTES")
    return payloads
