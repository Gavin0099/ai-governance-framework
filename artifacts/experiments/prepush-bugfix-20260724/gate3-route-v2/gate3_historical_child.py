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
import importlib.machinery
import os.path
import json
import sys
import types
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
"""Not wired into anything.  M3-b-2 starts the child; M4 switches the production
path."""


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


# ===========================================================================
# M3-b-1: the closed loader and the return frame
#
# Authority: `docs/governance/gate3-m3b-closed-loader-design-candidate-20260819.md`
# revision 5.  This tranche is in-process only.  It starts no process, makes no
# native call, imports no historical module and builds no parent-side result
# object — the result object and its "not asserted" markers belong to that
# document's `BLOCKED-2`, which is not authorized.
#
# What runs here is the machinery M3-b-2 and M3-b-3 both sit on top of.
# ===========================================================================


# --- the return frame -------------------------------------------------------

RESULT_MAGIC = b"\x47\x41\x54\x45\x33\x48\x52\x00"
"""`GATE3HR\0`.  Deliberately not the inbound magic.

Two channels carrying different things through one decoder is how a confused
deputy is built; the formats are separate so a frame cannot be replayed into the
wrong reader.
"""

RESULT_VERSION = 1
RESULT_HEADER_BYTES = 12
"""magic 8 + version 2 + entry count 2."""

MAX_RESULT_ENTRIES = 16
MAX_RESULT_LABEL_BYTES = 64
MAX_RESULT_VALUE_BYTES = 1_048_576
MAX_RESULT_AGGREGATE_BYTES = 4_194_304

DERIVED_MAX_RESULT_BYTES = 4_195_436
"""Not a gate.  `12 + 16 * (2 + 64 + 4) + 4,194,304`, recomputed by a test."""

_RESULT_ENTRY_FRAMING_BYTES = 70

RESULT_LABELS = (
    "candidate_set",
    "candidate_set_sha256",
    "contract_manifest",
    "contract_manifest_sha256",
)
"""Exactly these, all required.

A partial result is not a result: a frame carrying a manifest but not its digest
would leave the reader choosing which of two things to believe.
"""

_RESULT_DIGEST_OF = {
    "candidate_set_sha256": "candidate_set",
    "contract_manifest_sha256": "contract_manifest",
}


def _result_label(raw: bytes) -> str:
    """The label grammar: `[a-z][a-z0-9_]*`, one to sixty-four bytes.

    Carries the same byte-round-trip postcondition as the wire path grammar and
    for the same reason — see `_wire_path`.  Unreachable by any legal input;
    evidenced by mutating the decode.
    """

    if type(raw) is not bytes:
        raise TransportError("RESULT_LABEL_INVALID")
    if len(raw) > MAX_RESULT_LABEL_BYTES:
        raise TransportError("RESULT_LABEL_LENGTH_EXCEEDED")
    if not raw:
        raise TransportError("RESULT_LABEL_INVALID")
    try:
        text = _decode_utf8(raw)
    except UnicodeDecodeError:
        raise TransportError("RESULT_LABEL_INVALID") from None
    if text.encode("utf-8") != raw:
        raise TransportError("RESULT_LABEL_NOT_ROUND_TRIP")
    if not ("a" <= text[0] <= "z"):
        raise TransportError("RESULT_LABEL_INVALID")
    for character in text[1:]:
        if not ("a" <= character <= "z" or "0" <= character <= "9" or character == "_"):
            raise TransportError("RESULT_LABEL_INVALID")
    return text


def encode_result(values: Mapping) -> bytes:
    """Build the return frame.  Bounds enforced here as well as in the decoder.

    Same rationale as `encode_stream`: a producer that can emit an illegal frame
    has a bug whose first symptom would otherwise appear in another process.
    """

    if not isinstance(values, collections.abc.Mapping):
        raise TransportError("RESULT_INVALID")
    if len(values) > MAX_RESULT_ENTRIES:
        raise TransportError("RESULT_ENTRY_COUNT_EXCEEDED")
    if set(values) != set(RESULT_LABELS):
        raise TransportError("RESULT_INCOMPLETE")

    entries = []
    aggregate = 0
    for label, value in values.items():
        if type(label) is not str or type(value) is not bytes:
            raise TransportError("RESULT_INVALID")
        raw_label = label.encode("utf-8")
        _result_label(raw_label)
        if len(value) > MAX_RESULT_VALUE_BYTES:
            raise TransportError("RESULT_VALUE_EXCEEDED")
        aggregate += len(value)
        entries.append((raw_label, value))
    if aggregate > MAX_RESULT_AGGREGATE_BYTES:
        raise TransportError("RESULT_AGGREGATE_EXCEEDED")

    entries.sort(key=lambda entry: entry[0])
    parts = [
        RESULT_MAGIC,
        RESULT_VERSION.to_bytes(2, "little"),
        len(entries).to_bytes(2, "little"),
    ]
    for raw_label, value in entries:
        parts.append(len(raw_label).to_bytes(2, "little"))
        parts.append(raw_label)
        parts.append(len(value).to_bytes(4, "little"))
        parts.append(value)
    return b"".join(parts)


def decode_result(stream: bytes) -> dict:
    """Verify a return frame and return its values.

    The digest labels are recomputed here rather than trusted.  A producer
    agreeing with itself proves nothing; what the recomputation buys is that a
    frame cannot claim a digest for bytes it did not carry.
    """

    if type(stream) is not bytes:
        raise TransportError("RESULT_INVALID")

    cursor = _Cursor(stream)
    if cursor.take(len(RESULT_MAGIC), "RESULT_TRUNCATED") != RESULT_MAGIC:
        raise TransportError("RESULT_MAGIC_MISMATCH")
    if cursor.take_int(2, "RESULT_TRUNCATED") != RESULT_VERSION:
        raise TransportError("RESULT_VERSION_UNSUPPORTED")
    declared_count = cursor.take_int(2, "RESULT_TRUNCATED")
    if declared_count > MAX_RESULT_ENTRIES:
        raise TransportError("RESULT_ENTRY_COUNT_EXCEEDED")

    values: dict = {}
    previous_raw_label = b""
    aggregate = 0
    for index in range(declared_count):
        label_length = cursor.take_int(2, "RESULT_TRUNCATED")
        if label_length > MAX_RESULT_LABEL_BYTES:
            raise TransportError("RESULT_LABEL_LENGTH_EXCEEDED")
        raw_label = cursor.take(label_length, "RESULT_TRUNCATED")
        label = _result_label(raw_label)
        if index and raw_label == previous_raw_label:
            raise TransportError("RESULT_DUPLICATE_LABEL")
        if index and raw_label < previous_raw_label:
            raise TransportError("RESULT_LABEL_ORDER_INVALID")
        previous_raw_label = raw_label

        value_length = cursor.take_int(4, "RESULT_TRUNCATED")
        if value_length > MAX_RESULT_VALUE_BYTES:
            raise TransportError("RESULT_VALUE_EXCEEDED")
        if aggregate + value_length > MAX_RESULT_AGGREGATE_BYTES:
            raise TransportError("RESULT_AGGREGATE_EXCEEDED")
        aggregate += value_length
        values[label] = cursor.take(value_length, "RESULT_TRUNCATED")

    if set(values) != set(RESULT_LABELS):
        raise TransportError("RESULT_INCOMPLETE")
    for digest_label, byte_label in _RESULT_DIGEST_OF.items():
        if values[digest_label] != _sha256(values[byte_label]).encode("ascii"):
            raise TransportError("RESULT_DIGEST_MISMATCH")
    if cursor.remaining:
        raise TransportError("RESULT_TRAILING_BYTES")
    return values


# --- the closed loader ------------------------------------------------------


def module_name_for(relative: str) -> str:
    """The top-level module name a repo-relative path answers.

    Derived from the final component with `.py` removed.  Not from package
    structure: the historical modules import each other by bare absolute name,
    so every module the loader serves is top-level.
    """

    _wire_path(relative.encode("utf-8"))
    tail = relative.rsplit("/", 1)[-1]
    if not tail.endswith(".py"):
        raise TransportError("MODULE_NAME_INVALID")
    stem = tail[:-3]
    if not stem.isidentifier() or stem != stem.strip():
        raise TransportError("MODULE_NAME_INVALID")
    return stem


class BufferFinder:
    """A `MetaPathFinder` over verified buffers, answering names and nothing else.

    Returns `None` for every name outside its map, so the ordinary finders
    behind it resolve the standard library normally.  A whitelist of stdlib
    names is deliberately not used: it would have to be maintained against a
    standard library older than the code importing from it, and being wrong
    would fail closed somewhere with no useful diagnosis.
    """

    __slots__ = ("_modules", "_origins", "_root", "_loaders")

    def __init__(self, buffers: Mapping, root: str) -> None:
        # `root` is the materialized root, supplied by whoever knows it. The
        # loader will not invent it: `__file__` has to be the path the
        # historical code resolves its own data inputs from, and a repo-relative
        # string would resolve against the child's working directory, which is
        # the scratch directory and holds nothing.
        #
        # How the child *receives* this root is not decided here and is not
        # decidable here — argv, environment and the inbound frame all carry no
        # field for it. That is an open item for M3-b-2 and may need a bounded
        # amendment; this tranche makes the dependency explicit by requiring the
        # argument rather than defaulting it to something convenient.
        root = _checked_root(root)
        modules: dict = {}
        origins: dict = {}
        for relative, payload in buffers.items():
            if type(payload) is not bytes:
                raise TransportError("MODULE_SOURCE_INVALID")
            name = module_name_for(relative)
            if name in modules:
                raise TransportError("MODULE_NAME_DUPLICATE")
            modules[name] = payload
            origins[name] = _under_root(root, relative)
        self._modules = modules
        self._origins = origins
        self._root = root
        self._loaders: dict = {}

    @property
    def root(self) -> str:
        return self._root

    def loader_for(self, name: str):
        """The one loader this finder made for this name, or `None`.

        Per name rather than "any of ours": a loader is authority for the module
        it was created for, and accepting it for a different name would let one
        legitimate object vouch for something it never loaded.
        """

        return self._loaders.get(name)

    @property
    def names(self) -> tuple:
        return tuple(sorted(self._modules))

    def origin_of(self, name: str) -> str:
        return self._origins[name]

    def source_of(self, name: str) -> bytes:
        return self._modules[name]

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self._modules:
            return None
        loader = self._loaders.get(fullname)
        if loader is None:
            loader = BufferLoader(self)
            self._loaders[fullname] = loader
        spec = importlib.machinery.ModuleSpec(
            fullname, loader, origin=self._origins[fullname]
        )
        spec.has_location = True
        # No packages: `submodule_search_locations` stays `None`, so no
        # submodule search can occur under any of these names.
        return spec


class BufferLoader:
    """Compiles and executes one verified buffer.  It resolves no path."""

    __slots__ = ("_finder",)

    def __init__(self, finder: BufferFinder) -> None:
        self._finder = finder

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        name = module.__spec__.name
        module.__file__ = self._finder.origin_of(name)
        module.__package__ = ""
        module.__cached__ = None
        source = self._finder.source_of(name)
        try:
            code = compile(
                source, module.__file__, "exec", dont_inherit=True
            )
        except SyntaxError:
            raise TransportError("MODULE_COMPILE_FAILED") from None
        try:
            exec(code, module.__dict__)
        except TransportError:
            raise
        except BaseException:
            # The module name is already in the frozen inventory; a traceback
            # would carry source, which no closed code may do.
            raise TransportError("MODULE_EXEC_FAILED") from None


def _checked_root(root) -> str:
    """The materialized root must be absolute and normalized before it is used.

    A relative root makes containment meaningless: it resolves against the
    child's working directory, which is the scratch directory, so a path under
    it is under the wrong tree. Normalizing here rather than at every comparison
    means the stored root is the one thing every check agrees on.
    """

    if type(root) is not str or not root:
        raise TransportError("MATERIALIZED_ROOT_INVALID")
    if not os.path.isabs(root):
        raise TransportError("MATERIALIZED_ROOT_NOT_ABSOLUTE")
    normalized = os.path.normpath(root)
    if normalized in ("", os.path.sep) or normalized != os.path.normpath(normalized):
        raise TransportError("MATERIALIZED_ROOT_INVALID")
    return normalized


def _under_root(root: str, relative: str) -> str:
    return os.path.normpath(os.path.join(root, relative.replace("/", os.path.sep)))


def _is_under(root: str, candidate) -> bool:
    """Containment with the platform's own path semantics.

    A bare `startswith` on raw strings is wrong twice on Windows: it treats a
    case variant of the same directory as a different one, and it treats a
    separator difference as a different path. `normcase` folds both, and
    `commonpath` refuses the sibling-prefix case that `startswith` accepts —
    `C:/root-of-something-else` starts with `C:/root` and is not under it.
    """

    if type(candidate) is not str or not candidate:
        return False
    try:
        resolved = os.path.normcase(os.path.normpath(candidate))
        base = os.path.normcase(root)
        if resolved == base:
            return False
        return os.path.commonpath([resolved, base]) == base
    except ValueError:
        # Different drives, or a mix of absolute and relative: not under it.
        return False


def loaded_outside_loader(finder: BufferFinder, loaded: Mapping = None) -> tuple:
    """Modules under the materialized root that are not the ones we loaded.

    Root-scoped rather than origin-scoped: a module loaded from some *other*
    file under the materialized root is the case an origin comparison cannot
    see. Being in the map is not what makes a module ours; being under the root
    is what makes it our business.

    **Loader metadata is not evidence.** An earlier revision accepted any module
    whose `spec.loader` was one of ours, and a module can read its own
    `__loader__` and hand it to another module's spec — a probe copied it and
    the escape went unseen. A module is accepted only when all four hold: its
    name is one we loaded, `sys.modules[name]` is the object we created, its
    `__file__` is the origin we assigned that name, and its spec's loader is the
    loader we made for that name. Every one of those is something we recorded;
    none is something the module can grant itself.
    """

    loaded = {} if loaded is None else loaded
    escaped = []

    # Pass one: every module we loaded is audited unconditionally.
    #
    # An earlier revision gated the whole audit on the module's *current*
    # `__file__` being under the root, which a module can rewrite from its own
    # top-level body. Setting `__file__` to somewhere outside skipped the gate
    # and every check behind it, so the one module the audit exists for was the
    # one able to opt out of it. Position is not what makes a module in scope;
    # having loaded it is.
    for name, module in loaded.items():
        spec = getattr(module, "__spec__", None)
        if (
            sys.modules.get(name) is not module
            or name not in finder.names
            or getattr(module, "__file__", None) != finder.origin_of(name)
            or spec is None
            or getattr(spec, "loader", None) is not finder.loader_for(name)
        ):
            escaped.append(name)

    # Pass two: anything else claiming a place under the materialized root,
    # by either its `__file__` or its spec's origin.
    for name, module in list(sys.modules.items()):
        if name in loaded:
            continue
        spec = getattr(module, "__spec__", None)
        claims = (
            getattr(module, "__file__", None),
            getattr(spec, "origin", None) if spec is not None else None,
        )
        if any(_is_under(finder.root, claim) for claim in claims):
            escaped.append(name)
    return tuple(sorted(escaped))


def load_buffers(buffers: Mapping, root: str) -> dict:
    """Install the finder, load every buffer, check for bypass, uninstall.

    Registration goes into `sys.modules` and nowhere else. An earlier revision
    took a `modules` mapping so tests could pass a private dict; that is not a
    substitution the import system honours — `import` consults `sys.modules`
    regardless — so a private registry produced a *second* module object for
    every circular import and leaked it into the global table anyway. The
    parameter is gone; tests snapshot and restore the real one.

    The finder is removed before returning on every path, including failure.
    Leaving it installed would mean a later import in this interpreter could be
    answered by a map nobody expects to still be live.
    """

    modules = sys.modules
    finder = BufferFinder(buffers, root)
    for name in finder.names:
        if name in modules:
            raise TransportError("MODULE_NAME_OCCUPIED")

    sys.meta_path.insert(0, finder)
    loaded: dict = {}
    try:
        for name in finder.names:
            module = types.ModuleType(name)
            spec = finder.find_spec(name)
            module.__spec__ = spec
            module.__loader__ = spec.loader
            # In `sys.modules` before `exec_module`, as the import protocol
            # requires, so the circular absolute imports between these modules
            # resolve to the same objects.
            modules[name] = module
            loaded[name] = module
        for name in finder.names:
            spec = loaded[name].__spec__
            spec.loader.exec_module(loaded[name])
        escaped = loaded_outside_loader(finder, loaded)
        if escaped:
            raise TransportError("LOADER_BYPASSED")
    except BaseException as error:
        for name in loaded:
            modules.pop(name, None)
        _remove_finder(finder, error)
        raise
    _remove_finder(finder, None)
    return loaded


def _remove_finder(finder: BufferFinder, error) -> None:
    """Uninstall, without letting the uninstall replace what went wrong.

    A module body that removes the finder and then raises used to surface as
    `LOADER_INSTALL_FAILED`: the cleanup failure took the place of the execution
    failure that caused it. Same rule M2's teardown already carries — a failure
    while unwinding is attached to the error that caused the unwind and never
    replaces it.
    """

    removed = 0
    while finder in sys.meta_path:
        sys.meta_path.remove(finder)
        removed += 1
    if removed == 1:
        return
    # Zero means a module body removed it; more than one means a module body
    # appended it again, and an earlier revision removed only the first, leaving
    # a live finder behind on the success path. Both are the same defect: the
    # meta path is not what it was left as.
    note = "finder occurrences on sys.meta_path at cleanup: " + str(removed)
    if error is None:
        raise TransportError("LOADER_INSTALL_FAILED") from None
    if hasattr(error, "add_note"):
        error.add_note(note)
