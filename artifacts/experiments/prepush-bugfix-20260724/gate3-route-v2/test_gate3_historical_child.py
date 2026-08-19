"""Focused evidence for M3-a, the framed transport.

Evidence plan: `docs/governance/gate3-m3-child-transport-design-candidate-20260818.md`
revision 5, items `e1`-`e16`.  Each test names the item it discharges.

Everything here runs **in-process**.  Nothing spawns a child process, compiles
anything, imports a historical module or executes historical code.  An earlier
revision of this file read the pinned historical payloads out of git with
`subprocess`, which contradicted that sentence while the sentence was still
printed at the top of the file; the payloads are now synthetic and no
subprocess is started.

What that costs, stated rather than glossed: the round trip is evidence about
the framing and the verification, not about the four historical modules.  What
it does not cost is the authority evidence — `e6`, `e7` and `e11` still run
against the **real retained candidate-set bytes** read from disk, so the frozen
digest, the derivation and its agreement with `gate3_historical_bootstrap` are
exercised against the artifact itself.

Every rejection is asserted **by exact code**.  A test that accepts any
exception, or either of two codes, passes on the wrong rejection — and the wrong
rejection is how a grammar error becomes a length error and stops being visible.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

import pytest

import gate3_historical_bootstrap as bootstrap
import gate3_historical_child as child
import gate3_historical_materialize as materialize


HERE = Path(__file__).resolve().parent
CANDIDATE_PATH = HERE / "gate3-route-v2-ab-candidate-set.json"

MAGIC = child.MAGIC


def candidate_bytes() -> bytes:
    """The real retained candidate set, read from disk.  No process is started."""

    return CANDIDATE_PATH.read_bytes()


# --- the fixture authority --------------------------------------------------
#
# A synthetic candidate set and allowlist, so the decode tests can run without
# the pinned historical bytes.  The paths are chosen so that a wrong comparator
# produces a *different* order from the bytewise one — the real allowlist is
# entirely lower case, so casefold could not reorder it and a comparator test
# built on it would pass against a broken encoder.

FIXTURE_ALLOWLIST = (
    "pkg/Ä.py",  # decomposed: NFC normalization changes these bytes
    "pkg/B.py",
    "pkg/a.py",
    "pkg/z.py",
)

FIXTURE_PAYLOADS = {
    path: ("# fixture payload for " + path + "\n").encode("utf-8")
    for path in FIXTURE_ALLOWLIST
}


def fixture_candidate() -> bytes:
    files = [
        {
            "bytes": len(payload),
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for path, payload in sorted(FIXTURE_PAYLOADS.items())
    ]
    files.append({"bytes": 3, "path": "pkg/notes.md", "sha256": "0" * 64})
    document = {"authorization": "fixture", "files": files}
    return json.dumps(document, sort_keys=True, ensure_ascii=False).encode("utf-8")


@pytest.fixture
def authority(monkeypatch):
    """Point the module's frozen literals at the fixture set, for this test only.

    Monkeypatching here rather than adding a parameter to `derive_inventory` is
    deliberate: a production override would be a way for a caller to weaken the
    authority, which is the one thing the frozen literal exists to prevent.
    """

    monkeypatch.setattr(child, "RUNTIME_MODULE_ALLOWLIST", FIXTURE_ALLOWLIST)
    monkeypatch.setattr(
        child,
        "CANDIDATE_SET_SHA256",
        hashlib.sha256(fixture_candidate()).hexdigest(),
    )
    return fixture_candidate()


# --- a raw stream builder and an independent reader, both outside the module -
#
# The encoder has no way to emit an illegal stream, so every out-of-bounds and
# malformed-framing case below would be unreachable without the builder.  The
# reader is a second implementation of the framing walk, so `e3` observes the
# record region rather than searching the whole stream — the paths also occur
# inside the candidate-set block, and an earlier revision of `e3` was measuring
# the order of that JSON instead of the order of the records.


def record_bytes(
    raw_path: bytes,
    payload: bytes,
    *,
    path_length=None,
    payload_length=None,
    digest=None,
    omit_payload=False,
):
    parts = [
        (len(raw_path) if path_length is None else path_length).to_bytes(2, "little"),
        raw_path,
        (len(payload) if payload_length is None else payload_length).to_bytes(
            4, "little"
        ),
        hashlib.sha256(payload).digest() if digest is None else digest,
    ]
    if not omit_payload:
        parts.append(payload)
    return b"".join(parts)


def build_stream(
    *,
    magic=None,
    version=1,
    count=None,
    aggregate=None,
    candidate=None,
    candidate_length=None,
    records=(),
    trailing=b"",
):
    records = list(records)
    candidate = fixture_candidate() if candidate is None else candidate
    return b"".join(
        [
            MAGIC if magic is None else magic,
            version.to_bytes(2, "little"),
            (len(records) if count is None else count).to_bytes(2, "little"),
            (0 if aggregate is None else aggregate).to_bytes(8, "little"),
            (
                len(candidate) if candidate_length is None else candidate_length
            ).to_bytes(4, "little"),
            candidate,
            b"".join(records),
            trailing,
        ]
    )


def parse_records(stream: bytes):
    """Walk the framing independently and return the record region only."""

    offset = 0
    assert stream[offset : offset + 8] == MAGIC
    offset += 8
    offset += 2  # version
    count = int.from_bytes(stream[offset : offset + 2], "little")
    offset += 2
    declared_aggregate = int.from_bytes(stream[offset : offset + 8], "little")
    offset += 8
    candidate_length = int.from_bytes(stream[offset : offset + 4], "little")
    offset += 4 + candidate_length

    records = []
    for _ in range(count):
        path_length = int.from_bytes(stream[offset : offset + 2], "little")
        offset += 2
        raw_path = stream[offset : offset + path_length]
        offset += path_length
        payload_length = int.from_bytes(stream[offset : offset + 4], "little")
        offset += 4
        digest = stream[offset : offset + 32]
        offset += 32
        payload = stream[offset : offset + payload_length]
        offset += payload_length
        records.append((raw_path, payload, digest))
    assert offset == len(stream), "the framing did not consume the stream exactly"
    assert declared_aggregate == sum(len(record[1]) for record in records)
    return records


def ordered_records(order):
    """Records for `FIXTURE_PAYLOADS` in a caller-chosen order."""

    return [
        record_bytes(path.encode("utf-8"), FIXTURE_PAYLOADS[path]) for path in order
    ]


def fixture_aggregate() -> int:
    return sum(len(payload) for payload in FIXTURE_PAYLOADS.values())


BYTEWISE_ORDER = sorted(FIXTURE_ALLOWLIST, key=lambda path: path.encode("utf-8"))


def refuses(code):
    """Assert one exact code, never merely 'it raised' and never a choice."""

    class _Context:
        def __enter__(self):
            self._raises = pytest.raises(child.TransportError)
            self._caught = self._raises.__enter__()
            return self._caught

        def __exit__(self, *exc):
            handled = self._raises.__exit__(*exc)
            if handled:
                assert self._caught.value.code == code, (
                    "expected " + code + ", got " + self._caught.value.code
                )
            return handled

    return _Context()


# --- inertness --------------------------------------------------------------


def test_the_module_is_not_active() -> None:
    assert child.ACTIVE is False


def test_the_module_defines_no_main_entrypoint() -> None:
    """M3-b owns the `__main__` role; M3-a must not have started it."""

    source = Path(child.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.If):
            names = {
                sub.id for sub in ast.walk(node.test) if isinstance(sub, ast.Name)
            }
            assert "__name__" not in names
    for banned in ("subprocess", "compile(", "exec(", "importlib"):
        assert banned not in source


def test_this_evidence_file_starts_no_process() -> None:
    """The claim at the top of this file, asserted rather than promised.

    It was false once.  A test is the only form of that sentence that stays
    true when somebody reaches for a convenient byte source.
    """

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    for banned in ("subprocess", "os", "multiprocessing", "asyncio"):
        assert banned not in imported


def test_the_derived_stream_maximum_is_recomputed_from_the_bounds() -> None:
    """The derived figure is arithmetic, not a remembered number."""

    assert child.DERIVED_MAX_STREAM_BYTES == (
        child.HEADER_BYTES
        + 4
        + child.MAX_CANDIDATE_SET_BYTES
        + child.MAX_RECORDS * child._RECORD_FRAMING_BYTES
        + child.MAX_AGGREGATE_PAYLOAD_BYTES
    )
    assert child._RECORD_FRAMING_BYTES == 2 + child.MAX_PATH_BYTES + 4 + 32


# --- e1, e2 -----------------------------------------------------------------


def test_e1_round_trip_returns_the_same_bytes(authority) -> None:
    stream = child.encode_stream(authority, FIXTURE_PAYLOADS)
    assert child.decode_stream(stream) == FIXTURE_PAYLOADS


def test_e2_encoding_is_deterministic_and_order_insensitive(authority) -> None:
    reversed_map = dict(reversed(list(FIXTURE_PAYLOADS.items())))
    first = child.encode_stream(authority, FIXTURE_PAYLOADS)
    second = child.encode_stream(authority, FIXTURE_PAYLOADS)
    third = child.encode_stream(authority, reversed_map)
    assert first == second == third


# --- e3: the record region, against an expected raw byte sequence -----------


REAL_EXPECTED_ORDER = [
    b"artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    b"gate3_route_v2.py",
    b"artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    b"gate3_route_v2_ab.py",
    b"artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    b"gate3_route_v2_ab_live.py",
    b"artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    b"gate3_route_v2_codex.py",
]


def test_e3_record_order_matches_an_expected_raw_byte_sequence() -> None:
    """Read out of the record region by the independent walker.

    The real allowlist paths, because the order those four go in is the claim
    that matters.  `encode_stream` enforces bounds and grammar and does not
    consult the inventory, so this needs no authority fixture and no payload
    bytes beyond a marker.
    """

    payloads = {path.decode("utf-8"): b"x" for path in REAL_EXPECTED_ORDER}
    stream = child.encode_stream(candidate_bytes(), payloads)
    assert [record[0] for record in parse_records(stream)] == REAL_EXPECTED_ORDER


def test_e3_the_fixture_order_is_also_the_bytewise_one(authority) -> None:
    stream = child.encode_stream(authority, FIXTURE_PAYLOADS)
    assert [record[0] for record in parse_records(stream)] == [
        path.encode("utf-8") for path in BYTEWISE_ORDER
    ]
    assert BYTEWISE_ORDER == ["pkg/Ä.py", "pkg/B.py", "pkg/a.py", "pkg/z.py"]


# --- e3b: three wrong comparators, each producing a stream that is refused ---


def _wrong_order_stream(order):
    return build_stream(records=ordered_records(order), aggregate=fixture_aggregate())


def test_e3b_a_casefold_ordered_stream_is_refused(authority) -> None:
    casefolded = sorted(FIXTURE_ALLOWLIST, key=str.casefold)
    assert casefolded != BYTEWISE_ORDER
    with refuses("RECORD_ORDER_INVALID"):
        child.decode_stream(_wrong_order_stream(casefolded))


def test_e3b_a_normalization_ordered_stream_is_refused(authority) -> None:
    normalized = sorted(
        FIXTURE_ALLOWLIST,
        key=lambda path: unicodedata.normalize("NFC", path).encode("utf-8"),
    )
    assert normalized != BYTEWISE_ORDER
    with refuses("RECORD_ORDER_INVALID"):
        child.decode_stream(_wrong_order_stream(normalized))


def test_e3b_a_locale_collated_stream_is_refused(authority) -> None:
    import locale

    try:
        locale.setlocale(locale.LC_COLLATE, "en_US.UTF-8")
    except locale.Error:
        pytest.skip("named skip: no en_US.UTF-8 collation on this host")
    try:
        collated = sorted(FIXTURE_ALLOWLIST, key=locale.strxfrm)
    finally:
        locale.setlocale(locale.LC_COLLATE, "C")
    assert collated != BYTEWISE_ORDER
    with refuses("RECORD_ORDER_INVALID"):
        child.decode_stream(_wrong_order_stream(collated))


def test_e3b_the_bytewise_order_is_accepted(authority) -> None:
    """The counterpart: the three refusals must not be refusing everything."""

    stream = _wrong_order_stream(BYTEWISE_ORDER)
    assert child.decode_stream(stream) == FIXTURE_PAYLOADS


# --- e4: every framing field, corrupted independently -----------------------


def test_e4_magic(authority) -> None:
    with refuses("MAGIC_MISMATCH"):
        child.decode_stream(build_stream(magic=b"GATE3HM\x01"))


def test_e4_version(authority) -> None:
    with refuses("VERSION_UNSUPPORTED"):
        child.decode_stream(build_stream(version=2))


def test_e4_record_count(authority) -> None:
    with refuses("RECORD_COUNT_EXCEEDED"):
        child.decode_stream(build_stream(count=child.MAX_RECORDS + 1))


def test_e4_declared_aggregate(authority) -> None:
    with refuses("AGGREGATE_EXCEEDED"):
        child.decode_stream(
            build_stream(aggregate=child.MAX_AGGREGATE_PAYLOAD_BYTES + 1)
        )


def test_e4_candidate_set_length(authority) -> None:
    with refuses("CANDIDATE_SET_EXCEEDED"):
        child.decode_stream(
            build_stream(candidate_length=child.MAX_CANDIDATE_SET_BYTES + 1)
        )


def test_e4_candidate_set_block_truncated(authority) -> None:
    with refuses("CANDIDATE_SET_TRUNCATED"):
        child.decode_stream(
            build_stream(candidate_length=len(fixture_candidate()) + 64)
        )


def test_e4_record_path_length(authority) -> None:
    record = record_bytes(b"pkg/a.py", b"x", path_length=child.MAX_PATH_BYTES + 1)
    with refuses("PATH_LENGTH_EXCEEDED"):
        child.decode_stream(build_stream(records=[record], aggregate=1))


def test_e4_record_payload_length(authority) -> None:
    record = record_bytes(
        b"pkg/a.py", b"x", payload_length=child.MAX_PAYLOAD_BYTES + 1
    )
    with refuses("PAYLOAD_EXCEEDED"):
        child.decode_stream(build_stream(records=[record], aggregate=1))


def test_e4_record_digest(authority) -> None:
    records = ordered_records(BYTEWISE_ORDER)
    records[0] = record_bytes(
        BYTEWISE_ORDER[0].encode("utf-8"),
        FIXTURE_PAYLOADS[BYTEWISE_ORDER[0]],
        digest=b"\x00" * 32,
    )
    with refuses("PAYLOAD_DIGEST_MISMATCH"):
        child.decode_stream(
            build_stream(records=records, aggregate=fixture_aggregate())
        )


# --- e5 ---------------------------------------------------------------------


def test_e5_a_trailing_byte_is_refused(authority) -> None:
    stream = child.encode_stream(authority, FIXTURE_PAYLOADS) + b"\x00"
    with refuses("TRAILING_BYTES"):
        child.decode_stream(stream)


def test_e5_a_stream_one_byte_short_is_refused_with_a_different_code(
    authority,
) -> None:
    stream = child.encode_stream(authority, FIXTURE_PAYLOADS)[:-1]
    with refuses("RECORD_TRUNCATED"):
        child.decode_stream(stream)


def test_e5_a_header_one_byte_short_is_refused() -> None:
    with refuses("STREAM_TRUNCATED"):
        child.decode_stream(MAGIC + b"\x01")


# --- e6: the authority, before anything else --------------------------------


def test_e6_the_authority_is_checked_before_any_record_is_parsed(
    authority, monkeypatch
) -> None:
    """Proven by a parse spy, not by where the check sits in the source."""

    parsed = []
    real = child._wire_path
    monkeypatch.setattr(
        child, "_wire_path", lambda raw: parsed.append(raw) or real(raw)
    )
    forged = fixture_candidate().replace(b"pkg/z.py", b"pkg/y.py", 1)
    assert forged != fixture_candidate()
    stream = build_stream(
        candidate=forged,
        records=ordered_records(BYTEWISE_ORDER),
        aggregate=fixture_aggregate(),
    )
    with refuses("CANDIDATE_SET_DIGEST_MISMATCH"):
        child.decode_stream(stream)
    assert parsed == []


def test_e6_the_expected_digest_is_never_read_out_of_the_candidate_bytes() -> None:
    """Against the real retained artifact: the literal is not derived from it."""

    before = child.CANDIDATE_SET_SHA256
    forged = candidate_bytes() + b"\n"
    with refuses("CANDIDATE_SET_DIGEST_MISMATCH"):
        child.derive_inventory(forged)
    assert child.CANDIDATE_SET_SHA256 == before
    assert child.CANDIDATE_SET_SHA256 != hashlib.sha256(forged).hexdigest()


def test_e6_the_real_candidate_set_derives_the_real_inventory() -> None:
    inventory = child.derive_inventory(candidate_bytes())
    assert set(inventory) == set(child.RUNTIME_MODULE_ALLOWLIST)
    assert all(len(digest) == 64 for digest in inventory.values())


# --- e7: every bound crossed by exactly one ---------------------------------


def test_e7_sixty_five_records(authority) -> None:
    with refuses("RECORD_COUNT_EXCEEDED"):
        child.decode_stream(build_stream(count=child.MAX_RECORDS + 1))


def test_e7_a_five_hundred_and_thirteen_byte_path() -> None:
    raw = b"a" * (child.MAX_PATH_BYTES + 1)
    with refuses("PATH_LENGTH_EXCEEDED"):
        child._wire_path(raw)
    with refuses("PATH_LENGTH_EXCEEDED"):
        child.encode_stream(candidate_bytes(), {raw.decode(): b"x"})


def test_e7_a_five_hundred_and_twelve_byte_path_is_accepted() -> None:
    """The bound is exact: one below the refusal must pass."""

    raw = b"a" * child.MAX_PATH_BYTES
    assert child._wire_path(raw) == raw.decode()


def test_e7_a_candidate_set_one_byte_over() -> None:
    oversized = b"x" * (child.MAX_CANDIDATE_SET_BYTES + 1)
    with refuses("CANDIDATE_SET_EXCEEDED"):
        child.derive_inventory(oversized)
    with refuses("CANDIDATE_SET_EXCEEDED"):
        child.encode_stream(oversized, {})


def test_e7_a_single_payload_one_byte_over() -> None:
    with refuses("PAYLOAD_EXCEEDED"):
        child.encode_stream(
            candidate_bytes(), {"a.py": b"\x00" * (child.MAX_PAYLOAD_BYTES + 1)}
        )


def test_e7_an_aggregate_one_byte_over(authority) -> None:
    with refuses("AGGREGATE_EXCEEDED"):
        child.decode_stream(
            build_stream(aggregate=child.MAX_AGGREGATE_PAYLOAD_BYTES + 1)
        )


# --- e8: refused at the record, before the payload is read ------------------
#
# One limit decides here, not two.  An earlier revision compared the running
# total against `MAX_AGGREGATE_PAYLOAD_BYTES` as well; a mutation check showed
# that comparison could be deleted with the suite still green, because the
# header already refuses a declaration above the bound and the declared
# comparison is therefore always the tighter one.  The global bound is enforced
# where it can decide something — at the header, covered by `e4` and `e7`.


def test_e8_the_declared_aggregate_is_refused_before_the_payload_is_read(
    authority,
) -> None:
    """The header said zero; the first record declares one byte and omits it.

    The proof is the reader position, not the exception type.  A decoder that
    read the payload first would fail with `RECORD_TRUNCATED` — which is what
    this implementation produced before the check existed, and what the
    reviewer's counterexample elicited.
    """

    record = record_bytes(b"pkg/a.py", b"x", omit_payload=True)
    with refuses("AGGREGATE_MISMATCH"):
        child.decode_stream(build_stream(records=[record], count=1, aggregate=0))


def test_e8_the_global_bound_decides_at_the_header(authority) -> None:
    """Where the global bound can actually decide something.

    Once the header is accepted, `declared_aggregate <= MAX`, so a running total
    above `MAX` would have had to pass `declared_aggregate` first — which is why
    the record loop compares against the declaration alone.  A second comparison
    there could never be the one that refuses.
    """

    with refuses("AGGREGATE_EXCEEDED"):
        child.decode_stream(
            build_stream(aggregate=child.MAX_AGGREGATE_PAYLOAD_BYTES + 1)
        )
    accepted = build_stream(
        records=ordered_records(BYTEWISE_ORDER), aggregate=fixture_aggregate()
    )
    child.decode_stream(accepted)
    assert fixture_aggregate() <= child.MAX_AGGREGATE_PAYLOAD_BYTES


def test_e8_a_stream_declaring_more_than_it_carries_is_refused(authority) -> None:
    """The other direction: under-run is caught after the records."""

    stream = build_stream(
        records=ordered_records(BYTEWISE_ORDER), aggregate=fixture_aggregate() + 1
    )
    with refuses("AGGREGATE_MISMATCH"):
        child.decode_stream(stream)


# --- e9 ---------------------------------------------------------------------


def test_e9_nothing_is_allocated_from_an_unchecked_count(authority) -> None:
    with refuses("RECORD_COUNT_EXCEEDED"):
        child.decode_stream(build_stream(count=65_535))


def test_e9_nothing_is_allocated_from_an_unchecked_aggregate(authority) -> None:
    with refuses("AGGREGATE_EXCEEDED"):
        child.decode_stream(build_stream(aggregate=2**63))


# --- e10: the two digest comparisons are separate ---------------------------


def test_e10_a_payload_agreeing_with_the_stream_but_not_the_inventory(
    authority,
) -> None:
    target = BYTEWISE_ORDER[0]
    replacement = b"# not the recorded bytes\n"
    records = ordered_records(BYTEWISE_ORDER)
    records[0] = record_bytes(target.encode("utf-8"), replacement)
    aggregate = fixture_aggregate() - len(FIXTURE_PAYLOADS[target]) + len(replacement)
    with refuses("INVENTORY_DIGEST_MISMATCH"):
        child.decode_stream(build_stream(records=records, aggregate=aggregate))


def test_e10_a_payload_agreeing_with_the_inventory_but_not_the_framed_digest(
    authority,
) -> None:
    target = BYTEWISE_ORDER[0]
    records = ordered_records(BYTEWISE_ORDER)
    records[0] = record_bytes(
        target.encode("utf-8"), FIXTURE_PAYLOADS[target], digest=b"\xff" * 32
    )
    with refuses("PAYLOAD_DIGEST_MISMATCH"):
        child.decode_stream(
            build_stream(records=records, aggregate=fixture_aggregate())
        )


# --- e11: the two bindings of Decision 2 ------------------------------------


def test_e11_the_frozen_literals_match_the_bootstrap_module() -> None:
    assert child.CANDIDATE_SET_SHA256 == bootstrap.CANDIDATE_SET_SHA256
    assert child.RUNTIME_MODULE_ALLOWLIST == bootstrap.RUNTIME_MODULE_ALLOWLIST


NAMED_CORPUS = {
    "unmodified": lambda raw: raw,
    "a flipped byte inside a recorded digest": lambda raw: raw.replace(
        b"53f2ba2d", b"53f2ba2e", 1
    ),
    "a duplicated top-level key": lambda raw: raw.replace(
        b"{", b'{"files": [], ', 1
    ),
    "a runtime module renamed out of the inventory": lambda raw: raw.replace(
        b"gate3_route_v2_ab_live.py", b"gate3_route_v2_ab_dead.py", 1
    ),
    "a non-hexadecimal digest": lambda raw: raw.replace(
        b"53f2ba2d", b"53f2ba2z", 1
    ),
    "a truncated document": lambda raw: raw[: len(raw) // 2],
    "a top-level array instead of an object": lambda raw: b"[]",
    "files replaced by a string": lambda raw: raw.replace(
        b'"files"', b'"files_was"', 1
    ),
}


@pytest.mark.parametrize("name", sorted(NAMED_CORPUS))
def test_e11_both_derivations_agree_over_the_named_corpus(name, monkeypatch) -> None:
    """Agreement on what is accepted and on what is refused.

    Both frozen digests are pointed at the mutant so the comparison reaches the
    derivations themselves; otherwise every mutation would be refused at the
    digest and the test would prove only that both modules can hash.

    The corpus is a finite enumerated list.  It establishes nothing about inputs
    outside it, and this test does not claim otherwise.
    """

    mutant = NAMED_CORPUS[name](candidate_bytes())
    digest = hashlib.sha256(mutant).hexdigest()
    monkeypatch.setattr(child, "CANDIDATE_SET_SHA256", digest)
    monkeypatch.setattr(bootstrap, "CANDIDATE_SET_SHA256", digest)

    try:
        expected = bootstrap.runtime_module_inventory(
            bootstrap.verify_candidate_set(mutant)
        )
    except bootstrap.BootstrapError:
        with pytest.raises(child.TransportError):
            child.derive_inventory(mutant)
        return
    assert child.derive_inventory(mutant) == expected


def test_e11_a_mutant_is_refused_at_the_digest_when_the_literals_stand() -> None:
    mutant = candidate_bytes().replace(b"53f2ba2d", b"53f2ba2e", 1)
    assert mutant != candidate_bytes()
    with refuses("CANDIDATE_SET_DIGEST_MISMATCH"):
        child.derive_inventory(mutant)
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.verify_candidate_set(mutant)


# --- e12 --------------------------------------------------------------------


def test_e12_the_production_module_imports_only_the_standard_library() -> None:
    """Load-bearing: a repo-local import here fails inside the running child."""

    tree = ast.parse(Path(child.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError("relative import in the child module")
            imported.add((node.module or "").split(".")[0])
    imported.discard("__future__")
    outside = sorted(name for name in imported if name not in sys.stdlib_module_names)
    assert outside == []


def test_e12_rejects_a_repo_local_import(tmp_path) -> None:
    """Sensitivity: the AST check must fail on the thing it is named after."""

    sample = tmp_path / "sample.py"
    sample.write_text("import gate3_historical_bootstrap\n", encoding="utf-8")
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(sample.read_text(encoding="utf-8")))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert any(name not in sys.stdlib_module_names for name in imported)


# --- e13 --------------------------------------------------------------------


def test_e13_a_duplicate_path_is_refused(authority) -> None:
    path = BYTEWISE_ORDER[0]
    records = ordered_records([path, path])
    with refuses("RECORD_DUPLICATE_PATH"):
        child.decode_stream(
            build_stream(
                records=records, aggregate=len(FIXTURE_PAYLOADS[path]) * 2
            )
        )


def test_e13_a_path_absent_from_the_derived_inventory_is_refused(authority) -> None:
    extra = b"pkg/zz_extra.py"
    records = ordered_records(BYTEWISE_ORDER) + [record_bytes(extra, b"x")]
    with refuses("INVENTORY_SET_MISMATCH"):
        child.decode_stream(
            build_stream(records=records, aggregate=fixture_aggregate() + 1)
        )


def test_e13_records_out_of_order_are_refused(authority) -> None:
    with refuses("RECORD_ORDER_INVALID"):
        child.decode_stream(_wrong_order_stream(list(reversed(BYTEWISE_ORDER))))


# --- e14 --------------------------------------------------------------------


def test_e14_an_encoder_that_drops_the_last_record_must_fail_the_round_trip(
    authority,
) -> None:
    """A mutation check on `e1`: the round trip has to be load-bearing."""

    kept = BYTEWISE_ORDER[:-1]
    dropped = BYTEWISE_ORDER[-1]
    stream = build_stream(
        records=ordered_records(kept),
        aggregate=fixture_aggregate() - len(FIXTURE_PAYLOADS[dropped]),
    )
    with refuses("INVENTORY_SET_MISMATCH"):
        child.decode_stream(stream)


# --- e15: the wire grammar, each form with its own exact code ---------------


GRAMMAR_REJECTIONS = {
    "an overlong sequence": (b"a\xc0\xaf.py", "PATH_INVALID"),
    "an encoded surrogate": (b"a\xed\xa0\x80.py", "PATH_INVALID"),
    "a truncated multi-byte sequence": (b"a\xc3.py", "PATH_INVALID"),
    "a five-byte form": (b"a\xf8\x88\x80\x80\x80.py", "PATH_INVALID"),
    "a code point above U+10FFFF": (b"a\xf4\x90\x80\x80.py", "PATH_INVALID"),
    "a NUL": (b"a\x00.py", "PATH_INVALID"),
    "a backslash": (b"a\\b.py", "PATH_INVALID"),
    "a colon": (b"C:file.py", "PATH_INVALID"),
    "a leading slash": (b"/a.py", "PATH_INVALID"),
    "a trailing slash": (b"a/", "PATH_INVALID"),
    "an empty segment": (b"a//b.py", "PATH_INVALID"),
    "a dot segment": (b"a/./b.py", "PATH_INVALID"),
    "a dot dot segment": (b"a/../b.py", "PATH_INVALID"),
    "a byte order mark": ("﻿a.py".encode("utf-8"), "PATH_INVALID"),
    "an empty path": (b"", "PATH_INVALID"),
    "five hundred and thirteen bytes": (
        b"a" * (child.MAX_PATH_BYTES + 1),
        "PATH_LENGTH_EXCEEDED",
    ),
}


@pytest.mark.parametrize("name", sorted(GRAMMAR_REJECTIONS))
def test_e15_the_wire_grammar_rejects_each_form_with_its_own_code(name) -> None:
    """One code per form.

    Accepting either `PATH_INVALID` or `PATH_LENGTH_EXCEEDED` would pass on an
    implementation that reported a NUL as a length overrun, which is how a
    grammar failure stops being distinguishable from a bounds failure.
    """

    raw, code = GRAMMAR_REJECTIONS[name]
    with refuses(code):
        child._wire_path(raw)


def test_e15_the_wire_grammar_accepts_the_real_inventory() -> None:
    for path in child.RUNTIME_MODULE_ALLOWLIST:
        assert child._wire_path(path.encode("utf-8")) == path


CONTAINMENT_CORPUS = (
    "a.py",
    "a/b.py",
    "artifacts/experiments/x.py",
    "/a.py",
    "a/../b.py",
    "../a.py",
    "a//b.py",
    "a\\b.py",
    "C:a.py",
    "",
    "a/",
    "a/./b.py",
    "./a.py",
)


@pytest.mark.parametrize("path", CONTAINMENT_CORPUS)
def test_e15_the_wire_grammar_rejects_everything_containment_rejects(path) -> None:
    """One direction only, over a named corpus.

    Claiming equivalence would be false: the wire grammar rejects strictly more,
    and a test written to prove equivalence would have to be wrong in one
    direction to pass.  A finite corpus establishes nothing about inputs outside
    it either, which is why the claim is stated as a direction over this list.
    """

    try:
        materialize._checked_relative(path)
    except materialize.MaterializationError:
        with pytest.raises(child.TransportError):
            child._wire_path(path.encode("utf-8"))


def test_e15_the_reverse_inclusion_is_false_and_has_witnesses() -> None:
    """Named witnesses that the containment check accepts and the wire refuses."""

    for witness in ("a/", "a/./b.py"):
        materialize._checked_relative(witness)
        with refuses("PATH_INVALID"):
            child._wire_path(witness.encode("utf-8"))


def test_e15_an_unencodable_path_is_a_closed_refusal() -> None:
    """A `str` can hold what UTF-8 cannot carry.

    A lone surrogate — what `surrogateescape` produces from an undecodable
    filesystem name — made `path.encode("utf-8")` raise `UnicodeEncodeError`
    straight out of the encoder, past the closed error contract.  This test
    fails against that implementation.
    """

    with refuses("PATH_INVALID"):
        child.encode_stream(candidate_bytes(), {"pkg/\ud800.py": b"x"})


# --- e16: the round-trip postcondition, as sensitivity ----------------------


def test_e16_no_legal_input_reaches_the_round_trip_postcondition() -> None:
    """Stated in the test, so nobody goes looking for the byte sequence.

    Strict UTF-8 is canonical.  Every sequence that decodes re-encodes to
    itself, so `PATH_NOT_ROUND_TRIP` is unreachable from the wire and can only
    be evidenced by mutating the decoder — which the three tests below do.
    """

    for length in (1, 2, 3):
        for value in range(0, 256**length, 1 if length == 1 else 2_557):
            raw = value.to_bytes(length, "big")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            assert text.encode("utf-8") == raw


def test_e16_a_replacing_decoder_trips_the_postcondition(monkeypatch) -> None:
    monkeypatch.setattr(
        child, "_decode_utf8", lambda raw: raw.decode("utf-8", errors="replace")
    )
    with refuses("PATH_NOT_ROUND_TRIP"):
        child._wire_path(b"a\xff.py")


def test_e16_a_normalizing_decoder_trips_the_postcondition(monkeypatch) -> None:
    monkeypatch.setattr(
        child,
        "_decode_utf8",
        lambda raw: unicodedata.normalize("NFC", raw.decode("utf-8")),
    )
    with refuses("PATH_NOT_ROUND_TRIP"):
        child._wire_path("Ä.py".encode("utf-8"))


def test_e16_a_lenient_codec_trips_the_postcondition(monkeypatch) -> None:
    monkeypatch.setattr(child, "_decode_utf8", lambda raw: raw.decode("latin-1"))
    with refuses("PATH_NOT_ROUND_TRIP"):
        child._wire_path("é.py".encode("utf-8"))


def test_e16_the_unmutated_decoder_never_trips_it() -> None:
    """The counterpart: the sensitivity tests must not pass for free."""

    for path in child.RUNTIME_MODULE_ALLOWLIST:
        assert child._wire_path(path.encode("utf-8")) == path


# --- one grammar, both sides ------------------------------------------------


def test_both_sides_call_the_same_grammar_function(authority, monkeypatch) -> None:
    """'Applied identically by both sides' as a property of the code."""

    seen = []
    real = child._wire_path
    monkeypatch.setattr(
        child, "_wire_path", lambda raw: seen.append(raw) or real(raw)
    )
    stream = child.encode_stream(authority, FIXTURE_PAYLOADS)
    encoded_calls = len(seen)
    assert encoded_calls == len(FIXTURE_PAYLOADS)
    child.decode_stream(stream)
    assert len(seen) == encoded_calls * 2


def test_the_candidate_set_json_rejects_duplicate_keys(monkeypatch) -> None:
    """A second `authorization` key, which `json.loads` would silently keep."""

    duplicated = candidate_bytes().replace(
        b'"authorization"', b'"authorization": "x", "authorization"', 1
    )
    assert duplicated != candidate_bytes()
    assert json.loads(duplicated.decode("utf-8"))
    monkeypatch.setattr(
        child, "CANDIDATE_SET_SHA256", hashlib.sha256(duplicated).hexdigest()
    )
    with refuses("CANDIDATE_SET_DUPLICATE_KEY"):
        child.derive_inventory(duplicated)


def test_a_transport_error_never_renders_content() -> None:
    """The code is the whole message."""

    error = child.TransportError("PATH_INVALID")
    assert str(error) == "PATH_INVALID"
    assert error.code == "PATH_INVALID"
