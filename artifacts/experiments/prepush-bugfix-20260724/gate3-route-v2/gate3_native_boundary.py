"""Native directory-handle boundary — tranche N1: declarations and the layout gate.

Design authority:
`docs/governance/gate3-native-handle-boundary-design-candidate-20260815.md`
revision 16, SHA-256
72946b3f06ffe2b506fbdde0c0cd62984b6d02e289834de0a970d0ea96931ebb, with
`docs/adr/0001-gate3-native-directory-handle-boundary.md`.

Two tranches so far.

**N1** declares the eleven `ctypes` types the Windows backend will use and gates
them against the independently derived expected-layout artifact. It makes no
native call at all and runs offline.

**N2** loads `ntdll` and `kernel32` under the four compensating controls the
owner attached to the accepted `NATIVE-INTEROP.md` §3.3 deviation, and binds
every signature the backend will need.

The claim, stated exactly: **N2 loads two System32 libraries and binds eleven
target exports, and calls none of those eleven.** Binding a signature is not
calling it.

That is the whole property, and it stops there. Native code does run:
`ctypes.WinDLL` enters the Windows loader. Stretching a narrow, testable fact
about eleven exports into a statement about native execution generally would
claim something this code does not have.

That boundary is narrower than the tranche originally proposed, and the
narrowing was forced. The approved design says that once binding completes, any
exception escaping a `ctypes` call must reach fail-fast rather than return to
Python — because a measured `EXCEPTION_ACCESS_VIOLATION` surfaces as an
ordinary catchable `OSError`, and no reliable way to tell the two apart was
established. The first draft of N2 called `GetModuleFileNameW` and
`RtlGetVersion` after binding with no such protection, so a hostile probe
walked an `OSError` straight out of both. Reading runtime facts therefore
belongs to the tranche that builds the fail-fast boundary first, not to this
one.

**N3a** builds that fail-fast boundary, so a later tranche has somewhere for an
unexplained fault to go. It is the exit, not a user of it.

**N3b** is the first tranche that calls bound exports, and every call goes
through that exit. It reads the OS build with `RtlGetVersion` and the load
paths with `GetModuleFileNameW`, and assembles the runtime facts obtainable
without a handle.

The distinction that governs every call here: a **documented failure** is a
value the boundary read itself — a negative `NTSTATUS`, a zero return with
`GetLastError`, a truncation — and becomes an ordinary closed `NativeError`. An
**exception escaping the ctypes call** is not explained by any value, cannot be
told apart from an ABI fault, and terminates.

A documented failure must also collect the evidence the design requires before
it is reported: an `NTSTATUS` goes through `RtlNtStatusToDosError`, and a Win32
zero return has `ctypes.get_last_error()` read immediately, before any other
call can overwrite it. The status mapping is itself a post-bind ctypes call and
goes through the same guard.

The closed codes here are the design's own. An earlier draft introduced
`RUNTIME_FACTS_UNAVAILABLE`, which appears nowhere in the approved mapping —
an implementation does not get to add a fourth semantic. These failures occur
during the identity stage, so they report `ROOT_IDENTITY_UNAVAILABLE`, which is
the approved code for an unknown status there.

Still deferred: `GetVolumeInformationByHandleW` for the filesystem, which reads
from a held base handle that does not exist yet. It is absent from the facts
rather than substituted from a path, because a fact from a different source is
a different fact wearing the same name.

`handle_boundary_available()` returns False, as it has since the interim gate
landed. Nothing in this module changes that: an admission registry does not
exist yet, no backend exists to probe, and the platform-admission machinery is
a later tranche.

Why the gate is the first thing built. The declarations below decide how every
later native call reads and writes memory; a field off by one byte corrupts
silently. The approved characterization only measured what these declarations
produce, which proves the Python side is self-consistent and nothing else. The
expected-layout artifact was derived from the official SDK headers by a
separate program, so comparing against it is the first check that is not the
declarations judging themselves.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import pathlib
import platform
import re
import sys
from types import MappingProxyType
from ctypes import (
    POINTER,
    Structure,
    Union,
    c_int,
    c_long,
    c_longlong,
    c_size_t,
    c_ubyte,
    c_ulong,
    c_ulonglong,
    c_ushort,
    c_void_p,
    c_wchar,
    c_wchar_p,
)


ACTIVE = False
"""No production path uses this module. M4 is what switches that."""

# --- expected-layout artifact authority ------------------------------------
#
# Digest-bearing constants live here, in the hashed backend, and the artifact
# does not reference this module, so the chain has no cycle.

EXPECTED_LAYOUT_PATH = (
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3-native-expected-layout.json"
)
EXPECTED_LAYOUT_SHA256 = (
    "503e29ffd7c7ab3d5f05612288b73f14378d7cace9484f31cbdf256503fe616b"
)
EXTRACTOR_PATH = (
    "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
    "gate3_native_expected_layout_extract.py"
)
EXTRACTOR_SHA256 = (
    "877e7fee5f7b382e3e3fe1331b1112cd1e2b24f4e1d3c09f6f570aecef6e64c0"
)

EXPECTED_LAYOUT_SCHEMA = "gate3.native-expected-layout.v1"
MAX_ARTIFACT_BYTES = 1_048_576
ADMITTED_ABI = "64/win64/WinDLL"
ADMITTED_PACK = 8
# amd64 only.  The design marks arm64 UNVERIFIED — no layout was ever measured
# there — and the expected-layout artifact is derived from x64 ABI inputs, so
# running this gate on arm64 would compare against an oracle that does not
# describe it.  Admitting arm64 needs its own characterization first.
SUPPORTED_MACHINES = ("AMD64",)

PROVENANCE_KEYS = frozenset(
    {
        "abi",
        "extraction_method",
        "extractor_path",
        "extractor_sha256",
        "fundamental_type_table",
        "header_digests",
        "measurement_class",
        "pack",
        "package_id",
        "package_sha256",
        "package_source_url",
        "package_version",
        "preprocessor_dependent_type_table",
        "sdk_version",
    }
)
EXTRACTION_METHODS = frozenset(
    {"headers-parsed", "headers-preprocessed", "vendor-published"}
)
MEASUREMENT_CLASSES = frozenset({"computed-not-compiled", "compiled"})
HEADER_DIGEST_KEYS = frozenset({"path", "bytes", "sha256"})
TYPE_KEYS = frozenset({"kind", "size", "alignment", "fields"})
FIELD_KEYS = frozenset({"name", "offset", "size"})
HEX = frozenset("0123456789abcdef")
# Matched with `fullmatch`, and deliberately unanchored: Python's `$` also
# matches just before a trailing newline, so `re.match(r"^...$", "1.2\n")`
# succeeds.  A version carrying a newline was accepted that way.
VERSION_PATTERN = re.compile(r"[0-9]+(\.[0-9]+){1,3}")

ADMITTED_PACKAGE_ID = "Microsoft.Windows.SDK.CPP"

# The closed nine-entry header inventory.  "Some path shaped like a header" is
# not an inventory: without this, an artifact could name any file it liked and
# still satisfy the path grammar.
HEADER_INVENTORY = (
    "c/Include/10.0.26100.0/shared/basetsd.h",
    "c/Include/10.0.26100.0/shared/minwindef.h",
    "c/Include/10.0.26100.0/shared/ntdef.h",
    "c/Include/10.0.26100.0/shared/windef.h",
    "c/Include/10.0.26100.0/um/WinBase.h",
    "c/Include/10.0.26100.0/um/fileapi.h",
    "c/Include/10.0.26100.0/um/minwinbase.h",
    "c/Include/10.0.26100.0/um/winnt.h",
    "c/Include/10.0.26100.0/um/winternl.h",
)

# The ABI input tables are the values the headers do not settle, so their key
# sets are fixed too.  A table of the right *size* but different names would
# otherwise pass while describing a different ABI.
FUNDAMENTAL_KEYS = frozenset(
    {
        "POINTER",
        "__int64",
        "char",
        "double",
        "float",
        "int",
        "long",
        "long long",
        "short",
        "signed char",
        "unsigned __int64",
        "unsigned char",
        "unsigned int",
        "unsigned long",
        "unsigned long long",
        "unsigned short",
        "void",
        "wchar_t",
    }
)
PREPROCESSOR_KEYS = frozenset(
    {
        "DWORDLONG",
        "DWORD_PTR",
        "INT_PTR",
        "LONGLONG",
        "LONG_PTR",
        "SIZE_T",
        "SSIZE_T",
        "UINT_PTR",
        "ULONGLONG",
        "ULONG_PTR",
    }
)


class LayoutError(ValueError):
    """Closed failure. No native message, path or artifact content is rendered."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# --- type aliases -----------------------------------------------------------

NTSTATUS = c_long  # SIGNED; success is status >= 0, never a truthiness test
HANDLE = c_void_p  # never c_int, which truncates on 64-bit
ACCESS_MASK = c_ulong
ULONG = c_ulong
DWORD = c_ulong
USHORT = c_ushort
BOOL = c_int
ULONG_PTR = c_size_t
LARGE_INTEGER = c_longlong
LPWSTR = c_wchar_p
PVOID = c_void_p


# --- structures and unions --------------------------------------------------
#
# `_pack_ = 8` is declared per NATIVE-INTEROP.md §1.1, which forbids relying on
# inference. That it happens to equal natural alignment for these types on
# amd64 was measured, not assumed, and is not the reason it is declared.


class UNICODE_STRING(Structure):
    _pack_ = 8
    _fields_ = [("Length", USHORT), ("MaximumLength", USHORT), ("Buffer", LPWSTR)]
    # Length and MaximumLength are BYTE counts, not character counts.


class OBJECT_ATTRIBUTES(Structure):
    _pack_ = 8
    _fields_ = [
        ("Length", ULONG),
        ("RootDirectory", HANDLE),
        ("ObjectName", POINTER(UNICODE_STRING)),
        ("Attributes", ULONG),
        ("SecurityDescriptor", PVOID),
        ("SecurityQualityOfService", PVOID),
    ]


class IO_STATUS_BLOCK_UNION(Union):
    _pack_ = 8
    _fields_ = [("Status", NTSTATUS), ("Pointer", PVOID)]


class IO_STATUS_BLOCK(Structure):
    _pack_ = 8
    _anonymous_ = ("u",)
    _fields_ = [("u", IO_STATUS_BLOCK_UNION), ("Information", ULONG_PTR)]


class FILE_ID_INFO(Structure):
    _pack_ = 8
    _fields_ = [("VolumeSerialNumber", c_ulonglong), ("FileId", c_ubyte * 16)]


class FILE_ATTRIBUTE_TAG_INFO(Structure):
    _pack_ = 8
    _fields_ = [("FileAttributes", DWORD), ("ReparseTag", DWORD)]


class FILE_DISPOSITION_INFO(Structure):
    _pack_ = 8
    _fields_ = [("DeleteFile", c_ubyte)]  # BOOLEAN, one byte — not BOOL


class FILE_DISPOSITION_INFO_EX(Structure):
    _pack_ = 8
    _fields_ = [("Flags", DWORD)]


class FILE_BASIC_INFO(Structure):
    _pack_ = 8
    _fields_ = [
        ("CreationTime", LARGE_INTEGER),
        ("LastAccessTime", LARGE_INTEGER),
        ("LastWriteTime", LARGE_INTEGER),
        ("ChangeTime", LARGE_INTEGER),
        ("FileAttributes", DWORD),
    ]


class EXCEPTION_RECORD(Structure):
    _pack_ = 8
    _fields_ = [
        ("ExceptionCode", DWORD),
        ("ExceptionFlags", DWORD),
        ("ExceptionRecord", PVOID),
        ("ExceptionAddress", PVOID),
        ("NumberParameters", DWORD),
        ("ExceptionInformation", ULONG_PTR * 15),
    ]
    # EXCEPTION_MAXIMUM_PARAMETERS is 15. Only the first two are ever set, and
    # both are ordinals from closed sets, so no path, handle, status or message
    # can be placed in this record at all.


class OSVERSIONINFOEXW(Structure):
    _pack_ = 8
    _fields_ = [
        ("dwOSVersionInfoSize", ULONG),
        ("dwMajorVersion", ULONG),
        ("dwMinorVersion", ULONG),
        ("dwBuildNumber", ULONG),
        ("dwPlatformId", ULONG),
        ("szCSDVersion", c_wchar * 128),
        ("wServicePackMajor", USHORT),
        ("wServicePackMinor", USHORT),
        ("wSuiteMask", USHORT),
        ("wProductType", c_ubyte),
        ("wReserved", c_ubyte),
    ]
    # dwOSVersionInfoSize MUST be set to sizeof(OSVERSIONINFOEXW) before
    # RtlGetVersion is called. That call belongs to a later tranche.


DECLARED_TYPES: dict[str, type] = {
    "UNICODE_STRING": UNICODE_STRING,
    "OBJECT_ATTRIBUTES": OBJECT_ATTRIBUTES,
    "IO_STATUS_BLOCK_UNION": IO_STATUS_BLOCK_UNION,
    "IO_STATUS_BLOCK": IO_STATUS_BLOCK,
    "FILE_ID_INFO": FILE_ID_INFO,
    "FILE_ATTRIBUTE_TAG_INFO": FILE_ATTRIBUTE_TAG_INFO,
    "FILE_DISPOSITION_INFO": FILE_DISPOSITION_INFO,
    "FILE_DISPOSITION_INFO_EX": FILE_DISPOSITION_INFO_EX,
    "FILE_BASIC_INFO": FILE_BASIC_INFO,
    "EXCEPTION_RECORD": EXCEPTION_RECORD,
    "OSVERSIONINFOEXW": OSVERSIONINFOEXW,
}


# --- artifact loading -------------------------------------------------------


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Refuse ambiguous JSON.

    `json.loads` keeps the last value for a repeated key, silently, before any
    exact-field check can see the first. An artifact carrying `size` twice must
    be rejected, not resolved — the same rule the M1 bootstrap chain applies to
    the owner pin.
    """

    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise LayoutError("EXPECTED_LAYOUT_DUPLICATE_KEY")
        seen[key] = value
    return seen


def _reject_constants(_token: str) -> object:
    raise LayoutError("EXPECTED_LAYOUT_INVALID")


def _integer(value: object, low: int, high: int) -> int:
    # `type(...) is int`, never isinstance: bool subclasses int, so `true`
    # would otherwise pass as 1.
    if type(value) is not int or not low <= value <= high:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return value


def _ascii_text(value: object) -> str:
    # `isprintable()` also excludes control characters, so a value cannot smuggle
    # in a newline or tab and still read as ordinary ASCII.
    if (
        type(value) is not str
        or not value
        or not value.isascii()
        or not value.isprintable()
    ):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return value


def _version(value: object) -> str:
    text = _ascii_text(value)
    if not VERSION_PATTERN.fullmatch(text):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return text


def _hex64(value: object) -> str:
    if type(value) is not str or len(value) != 64 or not set(value) <= HEX:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return value


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[4]


def read_expected_layout(root: pathlib.Path | None = None) -> dict[str, object]:
    """Read, verify and validate the expected-layout artifact.

    Order is fixed and matters: raw bytes, then digest, then parse. Parsing
    first would mean interpreting an artifact that has not been shown to be the
    one this module trusts.
    """

    base = _repo_root() if root is None else pathlib.Path(root)
    path = base / EXPECTED_LAYOUT_PATH
    try:
        payload = path.read_bytes()
    except OSError:
        raise LayoutError("EXPECTED_LAYOUT_UNREADABLE") from None
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise LayoutError("EXPECTED_LAYOUT_TOO_LARGE")
    if hashlib.sha256(payload).hexdigest() != EXPECTED_LAYOUT_SHA256:
        raise LayoutError("EXPECTED_LAYOUT_DIGEST_MISMATCH")
    if payload.startswith(b"\xef\xbb\xbf"):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")

    # Exactly one final LF and nothing else.  `json.loads` accepts arbitrary
    # trailing whitespace, so the rule has to be enforced on the bytes rather
    # than assumed from the parser.  One LF is required rather than forbidden
    # because every digest-pinned artifact in this tree is LF-terminated; the
    # design said "no trailing bytes", which the committed artifact itself did
    # not satisfy, and that contradiction is resolved here in favour of the
    # convention the files actually follow.
    if not payload.endswith(b"\n") or payload[-2:-1] in (b"\n", b" ", b"\t", b"\r"):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")

    try:
        text = payload[:-1].decode("utf-8")
        decoder = json.JSONDecoder(
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constants,
        )
        document, consumed = decoder.raw_decode(text)
    except LayoutError:
        raise
    except Exception:
        raise LayoutError("EXPECTED_LAYOUT_INVALID") from None
    if consumed != len(text):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if not isinstance(document, dict):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return document


def verify_extractor(root: pathlib.Path | None = None) -> str:
    """Hash the extractor as data.

    `extractor_sha256` inside the artifact is self-described provenance until
    something reads the named file and checks it. The extractor is never
    imported or executed here; it is read as bytes.
    """

    base = _repo_root() if root is None else pathlib.Path(root)
    try:
        payload = (base / EXTRACTOR_PATH).read_bytes()
    except OSError:
        raise LayoutError("EXTRACTOR_UNREADABLE") from None
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXTRACTOR_SHA256:
        raise LayoutError("EXTRACTOR_DIGEST_MISMATCH")
    return digest


def _validate_path(value: object) -> str:
    _ascii_text(value)
    if not value.startswith("c/Include/") or "\\" in value:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return value


def _validate_type_table(
    table: object, keys: frozenset[str]
) -> dict[str, list[int]]:
    if not isinstance(table, dict) or set(table) != keys:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    # The design fixes bytewise key order; an exact key *set* does not imply it,
    # and a reversed table validated cleanly until this check existed.
    if list(table) != sorted(table):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    for name, pair in table.items():
        _ascii_text(name)
        if not isinstance(pair, list) or len(pair) != 2:
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        width = _integer(pair[0], 1, 65535)
        alignment = _integer(pair[1], 1, 16)
        if alignment & (alignment - 1):
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        del width
    return table  # type: ignore[return-value]


def validate_expected_layout(document: dict[str, object]) -> dict[str, object]:
    """Enforce the closed schema before any value is trusted."""

    if set(document) != {"schema", "provenance", "types"}:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if document.get("schema") != EXPECTED_LAYOUT_SCHEMA:
        raise LayoutError("EXPECTED_LAYOUT_SCHEMA_INVALID")

    provenance = document["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_KEYS:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if provenance["extraction_method"] not in EXTRACTION_METHODS:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if provenance["measurement_class"] not in MEASUREMENT_CLASSES:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if provenance["abi"] != ADMITTED_ABI:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if _integer(provenance["pack"], 8, 8) != ADMITTED_PACK:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if provenance["extractor_path"] != EXTRACTOR_PATH:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    # Three values must agree, not two: the artifact's field, this module's
    # frozen constant, and the digest of the file on disk.  Checking only the
    # last pair left the artifact free to claim any extractor it liked, which
    # is precisely the self-described provenance the design rules out.
    if _hex64(provenance["extractor_sha256"]) != EXTRACTOR_SHA256:
        raise LayoutError("EXPECTED_LAYOUT_EXTRACTOR_MISMATCH")
    _hex64(provenance["package_sha256"])

    package_id = _ascii_text(provenance["package_id"])
    if package_id != ADMITTED_PACKAGE_ID:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    package_version = _version(provenance["package_version"])
    _version(provenance["sdk_version"])
    lowered = package_id.lower()
    expected_url = (
        f"https://api.nuget.org/v3-flatcontainer/{lowered}/"
        f"{package_version}/{lowered}.{package_version}.nupkg"
    )
    if provenance["package_source_url"] != expected_url:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")

    digests = provenance["header_digests"]
    if not isinstance(digests, list) or not digests:
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    paths: list[str] = []
    for record in digests:
        if not isinstance(record, dict) or set(record) != HEADER_DIGEST_KEYS:
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        paths.append(_validate_path(record["path"]))
        _integer(record["bytes"], 1, 16_777_216)
        _hex64(record["sha256"])
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        raise LayoutError("EXPECTED_LAYOUT_INVALID")
    if tuple(paths) != HEADER_INVENTORY:
        raise LayoutError("EXPECTED_LAYOUT_INVENTORY_MISMATCH")

    _validate_type_table(provenance["fundamental_type_table"], FUNDAMENTAL_KEYS)
    _validate_type_table(
        provenance["preprocessor_dependent_type_table"], PREPROCESSOR_KEYS
    )

    types = document["types"]
    if not isinstance(types, dict) or set(types) != set(DECLARED_TYPES):
        raise LayoutError("EXPECTED_LAYOUT_TYPE_SET_MISMATCH")
    for spec in types.values():
        if not isinstance(spec, dict) or set(spec) != TYPE_KEYS:
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        if spec["kind"] not in ("structure", "union"):
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        _integer(spec["size"], 1, 65535)
        alignment = _integer(spec["alignment"], 1, 16)
        if alignment & (alignment - 1):
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        fields = spec["fields"]
        if not isinstance(fields, list) or not fields:
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
        names: list[str] = []
        for field in fields:
            if not isinstance(field, dict) or set(field) != FIELD_KEYS:
                raise LayoutError("EXPECTED_LAYOUT_INVALID")
            names.append(_ascii_text(field["name"]))
            _integer(field["offset"], 0, 65535)
            _integer(field["size"], 1, 65535)
        if len(set(names)) != len(names):
            raise LayoutError("EXPECTED_LAYOUT_INVALID")
    return document


# --- the layout gate --------------------------------------------------------


def declared_layout(declared: type) -> dict[str, object]:
    """What this module's declarations actually produce, per `ctypes`."""

    fields = []
    for name, _ in declared._fields_:
        descriptor = getattr(declared, name)
        fields.append(
            {"name": name, "offset": descriptor.offset, "size": descriptor.size}
        )
    return {
        "kind": "union" if issubclass(declared, Union) else "structure",
        "size": ctypes.sizeof(declared),
        "alignment": ctypes.alignment(declared),
        "fields": fields,
    }


def platform_supported() -> bool:
    """OS, pointer width and architecture. No library is loaded to answer it."""

    return (
        sys.platform == "win32"
        and ctypes.sizeof(c_void_p) == 8
        and platform.machine().upper() in SUPPORTED_MACHINES
    )


def verify_layout(root: pathlib.Path | None = None) -> dict[str, object]:
    """Compare every declaration against the independently derived artifact.

    Exact equality on kind, size, alignment and each field's name, offset and
    size, in declaration order. No tolerance and no skipping: a field the
    artifact omits has already failed validation.

    Refuses off-platform rather than reporting a mismatch. `c_wchar` is two
    bytes on Windows and four elsewhere, so an off-platform run would compare
    layouts that were never meant to match and call it an ABI defect.
    """

    if not platform_supported():
        raise LayoutError("LAYOUT_PLATFORM_UNSUPPORTED")

    verify_extractor(root)
    document = validate_expected_layout(read_expected_layout(root))
    expected = document["types"]

    for name, declared in DECLARED_TYPES.items():
        actual = declared_layout(declared)
        wanted = expected[name]  # type: ignore[index]
        if actual["kind"] != wanted["kind"]:
            raise LayoutError("LAYOUT_KIND_MISMATCH")
        if actual["size"] != wanted["size"]:
            raise LayoutError("LAYOUT_SIZE_MISMATCH")
        if actual["alignment"] != wanted["alignment"]:
            raise LayoutError("LAYOUT_ALIGNMENT_MISMATCH")
        if [f["name"] for f in actual["fields"]] != [
            f["name"] for f in wanted["fields"]
        ]:
            raise LayoutError("LAYOUT_FIELD_SEQUENCE_MISMATCH")
        for got, want in zip(actual["fields"], wanted["fields"]):
            if got["offset"] != want["offset"] or got["size"] != want["size"]:
                raise LayoutError("LAYOUT_FIELD_MISMATCH")
    return document


# ===========================================================================
# Tranche N2 — loading, binding, and handle-free runtime facts
# ===========================================================================

LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800
ALLOWED_LIBRARIES = ("kernel32.dll", "ntdll.dll")
"""Exactly two, with no exception of any kind.

An earlier tool in this work stream carved out one extra name for a probe and
the carve-out had to be deleted rather than re-described. The set is closed.
"""


class NativeError(ValueError):
    """Closed native-phase error. Carries no path, handle, message or status."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _load(name: str) -> "ctypes.WinDLL":
    """Private and unsupported. Not reachable through the production API.

    Python has no enforced privacy, so this does not claim to be unreachable —
    the tests call it directly. What the control actually rests on is that the
    supported entry point, `load_bindings()`, takes no arguments: on the
    production route there is no parameter for a caller-supplied name to enter
    through. An allowlist checked *after* a name is handed over would not
    implement that control, because it still leaves a reusable
    string-to-loader primitive exposed. The allowlist here is defence in depth.
    """

    if name not in ALLOWED_LIBRARIES:
        raise NativeError("LIBRARY_NOT_ALLOWED")
    return ctypes.WinDLL(
        name, use_last_error=True, winmode=LOAD_LIBRARY_SEARCH_SYSTEM32
    )


class _Bindings:
    """Loaded libraries with every signature declared before first call.

    `argtypes` and `restype` are set for every function, without exception: an
    undeclared call marshals through the default `int`, which truncates a
    handle on 64-bit and would corrupt exactly the values this boundary exists
    to keep intact.
    """

    def __init__(self) -> None:
        # One translation for the whole phase. An earlier draft had three
        # different behaviours inside a stage the design defines as uniformly
        # recoverable: the probe sat outside any `try`, the load caught only
        # `OSError`, and only the declaration step translated broadly. The
        # boundary is *where execution is*, not what class was raised.
        try:
            if not platform_supported():
                raise NativeError("HANDLE_BOUNDARY_UNAVAILABLE")
            self.kernel32 = _load("kernel32.dll")
            self.ntdll = _load("ntdll.dll")
            self._declare()
        except NativeError:
            raise
        except Exception:
            # `Exception`, not `BaseException`. KeyboardInterrupt, SystemExit
            # and GeneratorExit are the interpreter's control flow, not a
            # probe, load or binding failure, and restating them as "this
            # platform is unavailable" would be a false answer to a question
            # nobody asked. They propagate untouched.
            raise NativeError("HANDLE_BOUNDARY_UNAVAILABLE") from None

    def _declare(self) -> None:
        k32, nt = self.kernel32, self.ntdll

        nt.NtCreateFile.restype = NTSTATUS
        nt.NtCreateFile.argtypes = [
            POINTER(HANDLE),
            ACCESS_MASK,
            POINTER(OBJECT_ATTRIBUTES),
            POINTER(IO_STATUS_BLOCK),
            POINTER(LARGE_INTEGER),
            ULONG,
            ULONG,
            ULONG,
            ULONG,
            PVOID,
            ULONG,
        ]
        nt.NtOpenFile.restype = NTSTATUS
        nt.NtOpenFile.argtypes = [
            POINTER(HANDLE),
            ACCESS_MASK,
            POINTER(OBJECT_ATTRIBUTES),
            POINTER(IO_STATUS_BLOCK),
            ULONG,
            ULONG,
        ]
        nt.RtlNtStatusToDosError.restype = ULONG
        nt.RtlNtStatusToDosError.argtypes = [NTSTATUS]
        nt.RtlGetVersion.restype = NTSTATUS
        nt.RtlGetVersion.argtypes = [POINTER(OSVERSIONINFOEXW)]

        k32.CloseHandle.restype = BOOL
        k32.CloseHandle.argtypes = [HANDLE]
        k32.WriteFile.restype = BOOL
        k32.WriteFile.argtypes = [HANDLE, PVOID, DWORD, POINTER(DWORD), PVOID]
        k32.GetFileInformationByHandleEx.restype = BOOL
        k32.GetFileInformationByHandleEx.argtypes = [HANDLE, c_int, PVOID, DWORD]
        k32.SetFileInformationByHandle.restype = BOOL
        k32.SetFileInformationByHandle.argtypes = [HANDLE, c_int, PVOID, DWORD]
        k32.GetVolumeInformationByHandleW.restype = BOOL
        k32.GetVolumeInformationByHandleW.argtypes = [
            HANDLE,
            LPWSTR,
            DWORD,
            POINTER(DWORD),
            POINTER(DWORD),
            POINTER(DWORD),
            LPWSTR,
            DWORD,
        ]
        k32.GetModuleFileNameW.restype = DWORD
        k32.GetModuleFileNameW.argtypes = [HANDLE, LPWSTR, DWORD]
        k32.RaiseFailFastException.restype = None
        k32.RaiseFailFastException.argtypes = [
            POINTER(EXCEPTION_RECORD),
            PVOID,
            DWORD,
        ]
        # Bound so the backend cannot later call it undeclared. Never invoked
        # in this tranche: invoking it terminates the process.

    BOUND = (
        ("ntdll", "NtCreateFile"),
        ("ntdll", "NtOpenFile"),
        ("ntdll", "RtlNtStatusToDosError"),
        ("ntdll", "RtlGetVersion"),
        ("kernel32", "CloseHandle"),
        ("kernel32", "WriteFile"),
        ("kernel32", "GetFileInformationByHandleEx"),
        ("kernel32", "SetFileInformationByHandle"),
        ("kernel32", "GetVolumeInformationByHandleW"),
        ("kernel32", "GetModuleFileNameW"),
        ("kernel32", "RaiseFailFastException"),
    )

    # All eleven, and N2 calls none of them: nothing in this tranche sits
    # behind a fail-fast boundary, so nothing here may cross one.  This says
    # nothing about the loader itself, which does run native code.
    NEVER_CALLED_IN_N2 = frozenset(name for _, name in BOUND)


def load_bindings() -> _Bindings:
    """The only public entry: no arguments, so no name can be supplied.

    Load and bind, and nothing else. Every failure in this phase is recoverable
    by design, because it is answered before any handle is held or any object
    exists — nothing is half-done to be uncertain about.
    """

    return _Bindings()


# ===========================================================================
# Tranche N3a — the fail-fast boundary
# ===========================================================================
#
# Why this exists before anything calls a bound export. The characterization
# measured a raised EXCEPTION_ACCESS_VIOLATION arriving as an ordinary
# catchable OSError, and established no reliable way to tell an SEH fault from
# a recoverable Win32 error. So an exception escaping a ctypes call after
# binding is unexplained, and translating it would mean reporting a possible
# ABI fault as something a caller may retry. It terminates instead.

FAIL_FAST_EXCEPTION_CODE = 0xE3A70001
"""Application-defined. Bits 31-30 are 0b11 (error severity) and bit 29 — the
customer bit — is set, so the value cannot collide with a Microsoft-defined
status. Bit 28 is 0, as reserved."""

EXCEPTION_NONCONTINUABLE = 0x0001
FAIL_FAST_GENERATE_EXCEPTION_ADDRESS = 0x0001
EXCEPTION_MAXIMUM_PARAMETERS = 15

# Frozen, and immutable at runtime rather than by convention. Assigned once and
# never renumbered; a new entry appends at the next free value. Renumbering
# would silently change the meaning of every record already captured in a dump.
#
# The mapping is built from a dict literal passed straight into the proxy, so
# nothing else holds a reference to it. An earlier revision kept the backing
# dicts bound as `_FAIL_FAST_STAGES` and `_FAIL_FAST_CODES`, and a probe wrote
# through them into the public proxies — a leading underscore is a naming
# convention, not an access boundary.
FAIL_FAST_STAGES = MappingProxyType(
    {
        "CHAIN": 1,
        "CREATE_DIRECTORY": 2,
        "CREATE_FILE": 3,
        "WRITE": 4,
        "IDENTITY": 5,
        "REVALIDATE": 6,
        "REMOVE": 7,
        "PROBE": 8,
        "ABSENCE_PROBE": 9,
        "CLOSE": 10,
    }
)
FAIL_FAST_CODES = MappingProxyType(
    {
        "UNEXPECTED_EXCEPTION": 1,
        "MATERIALIZE_PATH_EXISTS": 2,
        "MATERIALIZE_WRITE_FAILED": 3,
        "PATH_IS_REPARSE_POINT": 4,
        "PATH_INVALID": 5,
        "ROOT_IDENTITY_UNAVAILABLE": 6,
        "ROOT_IDENTITY_CHANGED": 7,
        "CLEANUP_INCOMPLETE": 8,
        "CLOSE_FAILED": 9,
        "HANDLE_BOUNDARY_UNAVAILABLE": 10,
    }
)


def build_fail_fast_record(
    bindings: _Bindings, stage: str, code: str
) -> EXCEPTION_RECORD:
    """The record carrying the diagnostic.

    The payload is two integers from closed sets, so the content boundary is
    structural rather than a rule: a path, handle, status or message cannot be
    placed in this record at all.

    Raises on an unknown stage or code, which is what puts the caller on the
    fallback path — a diagnostic that invented an ordinal would be worse than
    none.
    """

    record = EXCEPTION_RECORD()
    record.ExceptionCode = FAIL_FAST_EXCEPTION_CODE
    record.ExceptionFlags = EXCEPTION_NONCONTINUABLE
    record.ExceptionRecord = None
    # Non-NULL, always: supplying a record obliges the caller to specify
    # ExceptionCode *and* ExceptionAddress, and a NULL there does not satisfy
    # that however dwFlags is set. FAIL_FAST_GENERATE_EXCEPTION_ADDRESS asks
    # the OS to substitute the caller's return address, which is the more
    # useful value; this entry-point address is what remains if it does not.
    record.ExceptionAddress = ctypes.cast(
        bindings.kernel32.RaiseFailFastException, PVOID
    )
    record.NumberParameters = 2
    for index in range(EXCEPTION_MAXIMUM_PARAMETERS):
        record.ExceptionInformation[index] = 0
    record.ExceptionInformation[0] = FAIL_FAST_STAGES[stage]
    record.ExceptionInformation[1] = FAIL_FAST_CODES[code]
    return record


def fail_fast(bindings: _Bindings, stage: str, code: str) -> None:
    """Terminate the process. Never returns.

    Claim ceiling, per owner ruling 8's slice-specific `NATIVE-INTEROP.md` §4.1
    exception: **if** the record is constructed, the two ordinals accompany the
    fail-fast call as inputs to that call; **if** construction fails, the
    parameterless fallback still terminates and carries no payload. Whether any
    consumer preserves either outcome — a crash dump, WER, an attached debugger
    — is outside this design and is not claimed. This slice does not produce an
    independent durable diagnostic record.

    There is no sink and no pre-fail-fast I/O, so nothing here can stall on a
    reader. That is the whole property: it says nothing about whether the OS
    termination path, a debugger or WER can stall afterwards.
    """

    record = None
    try:
        record = build_fail_fast_record(bindings, stage, code)
    except Exception:
        record = None
    finally:
        # From the `finally`, so a path that raises before the record exists
        # still terminates. The fallback takes no argument derived from the
        # failure, so it cannot itself fail on bad input.
        raise_fail_fast = bindings.kernel32.RaiseFailFastException
        if record is None:
            raise_fail_fast(None, None, FAIL_FAST_GENERATE_EXCEPTION_ADDRESS)
        else:
            raise_fail_fast(
                ctypes.byref(record), None, FAIL_FAST_GENERATE_EXCEPTION_ADDRESS
            )


# ===========================================================================
# Tranche N3b — runtime facts, behind the fail-fast boundary
# ===========================================================================


def _guarded(bindings: _Bindings, stage: str, call, *args):
    """Invoke a bound export with the fail-fast exit attached.

    `Exception`, not `BaseException`: an SEH fault surfaces through ctypes as an
    `OSError`, which this catches, while `KeyboardInterrupt`, `SystemExit` and
    `GeneratorExit` are the interpreter's control flow and propagate untouched.
    Terminating on a Ctrl-C would make the boundary uninterruptible and would
    report a keystroke as an ABI fault.

    Nothing is translated. The characterization established no reliable way to
    tell an SEH fault from a recoverable error, so an exception arriving here is
    unexplained by construction and the only honest response is to stop.
    """

    try:
        return call(*args)
    except Exception:
        fail_fast(bindings, stage, "UNEXPECTED_EXCEPTION")
        raise  # unreachable in production; reachable only if fail_fast is spied


def os_build(bindings: _Bindings) -> int:
    """The OS build, from `RtlGetVersion`.

    `GetVersionEx`-family reporting is manifest-shimmed and can under-report;
    `RtlGetVersion` is not. The design names it as the admission record's build
    source, so it is the one that must be read.
    """

    info = OSVERSIONINFOEXW()
    # Required before the call; the result is undefined without it.
    info.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFOEXW)
    status = _guarded(
        bindings, "IDENTITY", bindings.ntdll.RtlGetVersion, ctypes.byref(info)
    )
    # NTSTATUS success is `>= 0`. A negative status is truthy, so a truthiness
    # test here would read every failure as success.
    if status < 0:
        # The design requires an NTSTATUS to be mapped through
        # RtlNtStatusToDosError before the mapping table is consulted. That
        # mapping is itself a post-bind ctypes call, so it goes through the
        # guard like any other.
        _guarded(
            bindings,
            "IDENTITY",
            bindings.ntdll.RtlNtStatusToDosError,
            status,
        )
        raise NativeError("ROOT_IDENTITY_UNAVAILABLE")
    return int(info.dwBuildNumber)


def library_paths(bindings: _Bindings) -> dict[str, str]:
    """Where the loader actually found each library — evidence, not assumption.

    `GetModuleFileNameW` returning exactly the buffer size means the path was
    **truncated**, not that it fitted. A truncated path is a different path, and
    accepting one as loader provenance would evidence the wrong file.
    """

    capacity = 32768  # the NT path maximum; a short buffer would truncate
    result: dict[str, str] = {}
    for name, library in (
        ("kernel32.dll", bindings.kernel32),
        ("ntdll.dll", bindings.ntdll),
    ):
        buffer = ctypes.create_unicode_buffer(capacity)
        written = _guarded(
            bindings,
            "IDENTITY",
            bindings.kernel32.GetModuleFileNameW,
            library._handle,
            buffer,
            capacity,
        )
        if written == 0:
            # Read immediately, before any other call can overwrite it. This
            # reads thread-local state rather than invoking an export, so it
            # needs no guard of its own.
            ctypes.get_last_error()
            raise NativeError("ROOT_IDENTITY_UNAVAILABLE")
        if written >= capacity:
            # Documented truncation: the value equals the buffer size only when
            # the path did not fit. The disposition is complete from the return
            # value alone, so this path does not read the last error — current
            # Windows does set ERROR_INSUFFICIENT_BUFFER here, and an earlier
            # comment claiming otherwise was wrong.
            raise NativeError("ROOT_IDENTITY_UNAVAILABLE")
        result[name] = buffer.value
    return result


def runtime_facts(bindings: _Bindings) -> dict[str, object]:
    """The facts obtainable without a handle, each from its own source.

    Four sources, not one. An earlier draft attributed all of them to a held
    base handle, which is true only of the filesystem — and the filesystem is
    exactly the one this tranche cannot read.
    """

    if not platform_supported():
        raise NativeError("HANDLE_BOUNDARY_UNAVAILABLE")
    return {
        "arch": platform.machine().upper(),
        "pointer_bits": ctypes.sizeof(c_void_p) * 8,
        "abi": ADMITTED_ABI,
        "os_build": os_build(bindings),
        "os_build_source": "RtlGetVersion",
        "filesystem": None,
        "filesystem_reason": "requires a held base handle; not this tranche",
    }


def handle_boundary_available() -> bool:
    """Still False, and this tranche does not move it.

    The design makes availability the conjunction of a frozen admission record
    and a runtime capability probe. Neither exists: there is no admission
    registry, and no backend to probe. A passing layout gate says the
    declarations match the SDK-derived oracle, and a successful load says the
    libraries resolved — neither says a handle-bound backend exists or has been
    admitted.
    """

    return False
