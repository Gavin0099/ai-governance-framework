"""Native directory-handle boundary — tranche N1: declarations and the layout gate.

Design authority:
`docs/governance/gate3-native-handle-boundary-design-candidate-20260815.md`
revision 21, SHA-256
f1d7d8160c307ad656ec96d6089e9eb216272d9faf9068e923eb41bac01714df, with
`docs/adr/0001-gate3-native-directory-handle-boundary.md`.

Two tranches so far.

**N1** declares the eleven `ctypes` types the Windows backend will use and gates
them against the independently derived expected-layout artifact. It makes no
native call at all and runs offline.

**N2** loads `ntdll` and `kernel32` under the four compensating controls the
owner attached to the accepted `NATIVE-INTEROP.md` §3.3 deviation, and binds
every signature the backend will need.

The claim, stated exactly: **N2 loads two System32 libraries and binds the
target exports, and calls none of them.** Binding a signature is not calling
it. There were eleven when N2 landed; design revision 21 added `ReadFile` and
`SetFilePointerEx` for the held-handle read, so there are thirteen — the count
belongs in `BOUND` rather than in prose that has to be remembered.

That is the whole property, and it stops there. Native code does run:
`ctypes.WinDLL` enters the Windows loader. Stretching a narrow, testable fact
about a fixed export list into a statement about native execution generally
would claim something this code does not have.

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

**N3c-1** pins the ancestor chain: every component from the volume root down to
`base` is opened and held for the tree's lifetime. It opens directories and
creates nothing.

**N3c-2** adds creation, deletion and the absence probe, so `NtCreateFile`,
`WriteFile` and `SetFileInformationByHandle` are now called — on objects this
module creates, under a `base` it only borrows. `base` is never created, never
deleted and never marked.

Pinning is what stops a component being swapped mid-run. Each handle is opened
with `FILE_SHARE_DELETE` omitted, so while it is held no other process can
rename or delete that directory; and each open is **handle-relative** to the one
above it, so no component is ever re-resolved by name.

Still deferred: `GetVolumeInformationByHandleW` for the filesystem. It reads
from a held base handle, which exists, so nothing technical stops it — it is
absent because it belongs to a later tranche, and the absence is a choice.

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
    c_char,
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
        k32.ReadFile.restype = BOOL
        k32.ReadFile.argtypes = [HANDLE, PVOID, DWORD, POINTER(DWORD), PVOID]
        k32.SetFilePointerEx.restype = BOOL
        k32.SetFilePointerEx.argtypes = [
            HANDLE,
            LARGE_INTEGER,
            POINTER(LARGE_INTEGER),
            DWORD,
        ]
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
        ("kernel32", "ReadFile"),
        ("kernel32", "SetFilePointerEx"),
        ("kernel32", "GetFileInformationByHandleEx"),
        ("kernel32", "SetFileInformationByHandle"),
        ("kernel32", "GetVolumeInformationByHandleW"),
        ("kernel32", "GetModuleFileNameW"),
        ("kernel32", "RaiseFailFastException"),
    )

    # All of them, and N2 calls none: nothing in that tranche sits behind a
    # fail-fast boundary, so nothing there may cross one.  Derived from BOUND
    # rather than counted in a comment, so adding an export cannot leave a
    # stale number behind.  This says nothing about the loader itself, which
    # does run native code.
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
        "READ": 11,
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
        # Appended for N3c-2, never renumbered. `HANDLE_BOUNDARY_UNAVAILABLE`
        # says the boundary cannot be used on this platform at all — the same
        # answer for every caller, unfixable by changing an argument. These two
        # are properties of one call, which the caller can act on.
        "BASE_NOT_FOUND": 11,
        "BASE_NOT_ADMISSIBLE": 12,
        # Two codes rather than one: "the read call failed" and "the read
        # succeeded and returned something other than what was written" send a
        # reader to different places, and one code for both would report a
        # changed file as a broken API.
        "MATERIALIZE_READ_FAILED": 13,
        "MATERIALIZED_BYTES_CHANGED": 14,
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


# ===========================================================================
# Tranche N3c-1 — pinning the ancestor chain
# ===========================================================================
#
# Every constant below was read out of the pinned SDK headers rather than
# recalled. The `FILE_INFO_BY_HANDLE_CLASS` ordinals in particular are position
# dependent: the enum body is bracketed by `NTDDI_VERSION` blocks, so the values
# are only these when every block is active. The admission record pins the SDK
# and the OS build, which is what makes that assumption checkable.

SYNCHRONIZE = 0x00100000
FILE_LIST_DIRECTORY = 0x0001
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OBJ_CASE_INSENSITIVE = 0x00000040
FILE_OPEN = 0x00000001
FILE_DIRECTORY_FILE = 0x00000001
FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
FILE_OPEN_REPARSE_POINT = 0x00200000

FILE_READ_ATTRIBUTES = 0x0080
FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002
FILE_WRITE_ATTRIBUTES = 0x0100
DELETE = 0x00010000

FILE_ATTRIBUTE_READONLY = 0x00000001
FILE_ATTRIBUTE_NORMAL = 0x00000080

FILE_CREATE = 0x00000002
FILE_NON_DIRECTORY_FILE = 0x00000040

FILE_DISPOSITION_DELETE = 0x00000001
FILE_DISPOSITION_POSIX_SEMANTICS = 0x00000002
FILE_DISPOSITION_IGNORE_READONLY_ATTRIBUTE = 0x00000010

FILE_BEGIN = 0

FILE_BASIC_INFO_CLASS = 0
FILE_DISPOSITION_INFO_CLASS = 4
FILE_DISPOSITION_INFO_EX_CLASS = 21

# Signed, because NTSTATUS is signed here and success is `>= 0`.
STATUS_OBJECT_NAME_NOT_FOUND = -1073741772  # 0xC0000034
STATUS_OBJECT_NAME_COLLISION = -1073741771  # 0xC0000035
STATUS_OBJECT_PATH_NOT_FOUND = -1073741766  # 0xC000003A
STATUS_DELETE_PENDING = -1073741738  # 0xC0000056
STATUS_SHARING_VIOLATION = -1073741757  # 0xC0000043

# Not NULL. On 64-bit this is 0xFFFFFFFFFFFFFFFF, so a `if not handle.value`
# test passes it straight through to the next metadata query. The design
# requires both sentinels to be rejected, and one of them is truthy.
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
FILE_ID_INFO_CLASS = 18

# Role 1 from design revision 17: a borrowed ancestor. DELETE is *not*
# requested — the pin comes from omitting FILE_SHARE_DELETE, not from asking for
# delete access on a directory this code did not create.
#
# FILE_READ_ATTRIBUTES is not decoration. Revision 16 required a reparse-tag
# check on every pinned ancestor while granting a mask that cannot perform one:
# measured on the volume root, GetFileInformationByHandleEx with
# FileAttributeTagInfo failed with ERROR_ACCESS_DENIED under
# FILE_LIST_DIRECTORY | SYNCHRONIZE alone. It is an independent right from
# FILE_WRITE_ATTRIBUTES (0x0100), so holding the write right would not have
# granted the read.
ANCESTOR_ACCESS = FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES | SYNCHRONIZE
ANCESTOR_SHARE = FILE_SHARE_READ | FILE_SHARE_WRITE
ANCESTOR_OPTIONS = (
    FILE_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT
)

# Role 2 from the design: a directory this code creates and must delete. DELETE
# is requested precisely because the obligation here is the opposite of role 1's.
CREATED_DIRECTORY_ACCESS = (
    FILE_LIST_DIRECTORY
    | FILE_READ_ATTRIBUTES
    | SYNCHRONIZE
    | DELETE
    | FILE_WRITE_ATTRIBUTES
)
CREATED_DIRECTORY_SHARE = FILE_SHARE_READ | FILE_SHARE_WRITE
CREATED_DIRECTORY_OPTIONS = FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT

# Role 3: a file this code creates, writes once and must delete. Born read-only
# — the attribute governs later opens while this handle keeps the write access
# it was granted, so the bytes are never writable through their path.
CREATED_FILE_ACCESS = (
    FILE_READ_DATA
    | FILE_WRITE_DATA
    | FILE_READ_ATTRIBUTES
    | FILE_WRITE_ATTRIBUTES
    | DELETE
    | SYNCHRONIZE
)
CREATED_FILE_SHARE = FILE_SHARE_READ
CREATED_FILE_OPTIONS = FILE_NON_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT

# The absence probe, and the only place FILE_SHARE_DELETE appears: the probe
# must not pin the name it is asking about.
ABSENCE_ACCESS = FILE_READ_ATTRIBUTES | SYNCHRONIZE
ABSENCE_SHARE = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
ABSENCE_OPTIONS = FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT

# One megabyte, far inside DWORD. Chunking exists because the count argument is
# a DWORD; the loop exists because a short write is legal and not an error.
WRITE_CHUNK = 1 << 20

# The same bound for reads, kept as its own name so the two can diverge without
# one silently changing the other.
READ_CHUNK = 1 << 20

_DRIVE_ROOT = re.compile(r"^([A-Za-z]):[\\/]$")

_CREATED_NAME = re.compile(r"^[A-Za-z0-9._-]{1,255}$")
_DEVICE_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{digit}" for digit in range(1, 10)]
    + [f"LPT{digit}" for digit in range(1, 10)]
)


def _validate_created_name(name: str) -> str:
    """The normative grammar for a name this code creates or probes.

    Stricter than `_validate_component`, which governs *borrowed* ancestors and
    has to tolerate whatever already exists on disk. Nothing here has to be
    tolerated: this code chooses these names, so anything that could reopen a
    path lookup under `RootDirectory` is refused outright.

    Raises before any native call, so a bad name is an ordinary recoverable
    result and never reaches the fail-fast path.
    """

    if type(name) is not str or not _CREATED_NAME.fullmatch(name):
        # The character class already excludes separators, colons, wildcards
        # and control characters; length is bounded by the same match.
        raise NativeError("PATH_INVALID")
    if name in (".", ".."):
        raise NativeError("PATH_INVALID")
    if name.endswith(".") or name.endswith(" "):
        # Windows strips these silently, so the name asked for is not the name
        # created — a difference this boundary must not paper over.
        raise NativeError("PATH_INVALID")
    stem = name.split(".", 1)[0].upper()
    if stem in _DEVICE_NAMES:
        # `nul.txt` is still the device.
        raise NativeError("PATH_INVALID")
    return name


class _Held:
    """One held kernel handle and the identity the object had when opened.

    Anchor and Leaf share this rather than each carrying a copy: the ownership
    rules here were got wrong three separate times during N3c-1, and two
    independent implementations of them would drift.

    Opaque on purpose: the raw handle never leaves this module, so no caller can
    keep one past `close` or hand one to something that resolves names.
    """

    __slots__ = ("_bindings", "_handle", "_identity", "_closed", "_removing")

    def __init__(self, bindings: "_Bindings", handle: int, identity: str) -> None:
        self._bindings = bindings
        self._handle = handle
        self._identity = identity
        self._closed = False
        # Set once the object is marked for deletion. It changes what a failed
        # close *means*: releasing a borrowed handle that will not close is a
        # leak, while failing to close a handle whose object is delete-pending
        # means the removal did not complete.
        self._removing = False

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Drop ownership. A failed close is not a released handle.

        The stored handle is cleared unconditionally, including on failure,
        because a handle that would not close must never be closed again — the
        value may already have been recycled. What is *not* claimed is that it
        was released; the OS reclaims it at process teardown.
        """

        if self._closed:
            return  # a second close is a no-op, not an error
        handle = self._handle
        removing = self._removing
        self._handle = 0
        self._closed = True
        if not _close_handle(self._bindings, handle):
            ctypes.get_last_error()
            # Per the design's mapping: during removal the finding is that the
            # removal did not complete; releasing the borrowed chain after an
            # otherwise successful run, it is a close failure.
            raise NativeError("CLEANUP_INCOMPLETE" if removing else "CLOSE_FAILED")

    def __enter__(self) -> "Anchor":
        return self

    def __exit__(self, _exc_type, exc_value, _traceback) -> bool:
        """Close, and never let the closing become the failure.

        `return False` only runs if `close()` returned. Calling it
        unconditionally meant that a body error plus a failing `CloseHandle`
        propagated `CLOSE_FAILED` and lost the body error entirely — the same
        masking already fixed in the `_anchor` and `open_chain` unwinds, left
        behind here because this path exits through a different door.
        """

        if exc_value is None:
            self.close()  # nothing to mask: the caller wants to be told
            return False
        failure = _close_chain_quietly([self])
        if failure is not None:
            _note_cleanup_failure(exc_value, failure.args[0])
        return False  # never swallow the exception that is unwinding

    def __del__(self) -> None:
        """Leak backstop, not a reporting path.

        A caller that forgets `close()` still releases the handle here. Errors
        are swallowed because raising from a finalizer only prints and is
        ignored, and because at interpreter shutdown the module globals this
        needs may already be gone. Deterministic reporting is what the context
        manager is for. An unexplained fault inside `CloseHandle` still reaches
        fail-fast through `_guarded`: suppressing an ABI fault would be worse
        than terminating.
        """

        try:
            self.close()
        except Exception:
            pass


class Anchor(_Held):
    """A directory handle this code holds.

    Role 1 when it was borrowed and merely pinned, role 2 when this code
    created it. The distinction is not in the object: it is in whether cleanup
    is obliged to delete it, which the caller tracks by keeping created anchors
    in a separate list.
    """

    __slots__ = ()


class PinnedChain:
    """The volume root down to `base`, every component held.

    Pinning one directory is not enough: renaming an ancestor moves everything
    under it. The chain terminates at the volume root, which cannot be renamed
    or deleted.
    """

    __slots__ = ("anchors",)

    def __init__(self, anchors: list[Anchor]) -> None:
        self.anchors = anchors

    @property
    def base(self) -> Anchor:
        return self.anchors[-1]

    def close(self) -> None:
        """Release every anchor, and report the first failure.

        Every anchor is attempted before raising: stopping at the first failure
        would leak the handles beneath it.
        """

        failure = _close_chain_quietly(self.anchors)
        if failure is not None:
            raise failure

    def __enter__(self) -> "PinnedChain":
        return self

    def __exit__(self, _exc_type, exc_value, _traceback) -> bool:
        """Same rule as `Anchor.__exit__`, over the whole chain."""

        if exc_value is None:
            self.close()
            return False
        failure = _close_chain_quietly(self.anchors)
        if failure is not None:
            _note_cleanup_failure(exc_value, failure.args[0])
        return False

    def __del__(self) -> None:
        """Same backstop as `Anchor`, for a chain the caller never closed."""

        try:
            self.close()
        except Exception:
            pass


class Leaf(_Held):
    """A file this code created and still holds, with the length it was written at.

    Role 3. Held until it is removed through this same handle — reopening the
    name to delete it would be a second ownership path for one object.

    `length` is sealed here at creation and is what `read_all` reads to. It is
    deliberately not a parameter of the read: "how many bytes should be here"
    must not be answerable by whoever is asking the question, or the expected
    answer could be adjusted to fit the observation.
    """

    __slots__ = ("_length",)

    def __init__(
        self, bindings: "_Bindings", handle: int, identity: str, length: int
    ) -> None:
        super().__init__(bindings, handle, identity)
        if type(length) is not int or length < 0:
            raise NativeError("MATERIALIZE_WRITE_FAILED")
        self._length = length

    @property
    def length(self) -> int:
        return self._length


def _unicode_string(text: str):
    """A UNICODE_STRING plus the buffer it points at.

    Both are returned so the caller can keep them alive across the call. The
    kernel reads the buffer during `NtOpenFile`; a temporary freed beforehand
    is a use-after-free that usually looks like it worked.
    """

    buffer = ctypes.create_unicode_buffer(text)
    encoded = len(text) * ctypes.sizeof(c_wchar)
    name = UNICODE_STRING()
    name.Length = encoded
    name.MaximumLength = encoded + ctypes.sizeof(c_wchar)
    name.Buffer = ctypes.cast(buffer, LPWSTR)
    return name, buffer


def _validate_component(component: str) -> str:
    """A single path component of a *borrowed* ancestor.

    Looser than the created-object grammar deliberately: a directory this code
    did not create may legitimately contain spaces, and refusing
    a path like Program Files would be refusing reality. What must still be
    anything that changes how the name is parsed — a separator would smuggle in
    extra components, and `..` would walk back out of the chain.
    """

    if type(component) is not str or not component:
        raise NativeError("PATH_INVALID")
    if "/" in component or "\\" in component or "\x00" in component:
        raise NativeError("PATH_INVALID")
    if component in (".", ".."):
        raise NativeError("PATH_INVALID")
    return component


def split_base_path(base: str) -> tuple[str, list[str]]:
    """Split an absolute drive path into its NT volume root and components.

    UNC and device paths are out of scope by design and are refused rather than
    partially handled.
    """

    if type(base) is not str or not base:
        raise NativeError("PATH_INVALID")
    normalised = base.replace("/", "\\")
    if normalised.startswith("\\\\"):
        raise NativeError("PATH_INVALID")  # UNC or device path
    if len(normalised) < 3 or normalised[1] != ":" or normalised[2] != "\\":
        raise NativeError("PATH_INVALID")
    if not normalised[0].isascii() or not normalised[0].isalpha():
        raise NativeError("PATH_INVALID")
    drive = normalised[0].upper()
    rest = [part for part in normalised[3:].split("\\") if part]
    return f"\\??\\{drive}:\\", [_validate_component(part) for part in rest]


def _open_directory(
    bindings: _Bindings, name: str, parent: "Anchor | None"
) -> int:
    """Open one directory, relative to `parent` when there is one.

    `FILE_OPEN_REPARSE_POINT` opens a reparse point as itself rather than
    following it, so a junction becomes something to detect instead of
    something to traverse.
    """

    handle = HANDLE()
    unicode_name, buffer = _unicode_string(name)
    attributes = OBJECT_ATTRIBUTES()
    attributes.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
    attributes.RootDirectory = None if parent is None else parent._handle
    attributes.ObjectName = ctypes.pointer(unicode_name)
    attributes.Attributes = OBJ_CASE_INSENSITIVE
    attributes.SecurityDescriptor = None
    attributes.SecurityQualityOfService = None
    status_block = IO_STATUS_BLOCK()

    status = _guarded(
        bindings,
        "CHAIN",
        bindings.ntdll.NtOpenFile,
        ctypes.byref(handle),
        ANCESTOR_ACCESS,
        ctypes.byref(attributes),
        ctypes.byref(status_block),
        ANCESTOR_SHARE,
        ANCESTOR_OPTIONS,
    )
    # Keep the name alive until the call has returned.
    del unicode_name, buffer, attributes

    if status < 0:
        _guarded(
            bindings, "CHAIN", bindings.ntdll.RtlNtStatusToDosError, status
        )
        # Not `HANDLE_BOUNDARY_UNAVAILABLE`. That code means the boundary
        # cannot be used on this platform at all — the same answer for every
        # caller, unfixable by changing an argument. A component that is missing
        # or unopenable is a property of this call, and the caller can act on
        # it; collapsing the two sends them looking for a platform problem when
        # the fault is the path they passed.
        if status in (
            STATUS_OBJECT_NAME_NOT_FOUND,
            STATUS_OBJECT_PATH_NOT_FOUND,
        ):
            raise NativeError("BASE_NOT_FOUND")
        raise NativeError("BASE_NOT_ADMISSIBLE")
    if not handle.value or handle.value == INVALID_HANDLE_VALUE:
        # A success status with an unusable handle is not something to reason
        # about; it is refused. Closing is not attempted either, because
        # neither sentinel is a handle this process owns.
        raise NativeError("HANDLE_BOUNDARY_UNAVAILABLE")
    return handle.value


def _query_failed(detail: str) -> NativeError:
    """The closed error code, with the OS error attached as a note.

    The last error was already being read immediately after the failing call —
    and then discarded, which made the read pointless. Attaching it keeps the
    error code closed while letting a caller distinguish `ERROR_ACCESS_DENIED`
    from a genuinely unavailable object. It is a note, not a code: the closed
    set that the fail-fast payload draws from is unaffected.
    """

    error = NativeError("ROOT_IDENTITY_UNAVAILABLE")
    error.add_note(f"{detail}: last_error={ctypes.get_last_error()}")
    return error


def _reparse_tag(bindings: _Bindings, handle: int) -> int:
    info = FILE_ATTRIBUTE_TAG_INFO()
    ok = _guarded(
        bindings,
        "IDENTITY",
        bindings.kernel32.GetFileInformationByHandleEx,
        handle,
        FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        raise _query_failed("FileAttributeTagInfo")
    return int(info.ReparseTag)


def _identity_of(bindings: _Bindings, handle: int) -> str:
    """A durable identity for the object behind the handle.

    `FILE_ID_INFO` carries a 64-bit volume serial and a 128-bit file id. The
    64-bit index from `GetFileInformationByHandle` is not unique on every
    filesystem and is deliberately not used as a fallback.
    """

    info = FILE_ID_INFO()
    ok = _guarded(
        bindings,
        "IDENTITY",
        bindings.kernel32.GetFileInformationByHandleEx,
        handle,
        FILE_ID_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        raise _query_failed("FileIdInfo")
    payload = bytes(info.FileId)
    return hashlib.sha256(
        f"{info.VolumeSerialNumber}:{payload.hex()}".encode("ascii")
    ).hexdigest()


def _close_handle(bindings: _Bindings, handle: int) -> bool:
    """Close one raw handle through the guarded boundary.

    `CloseHandle` is a bound export like any other, so an exception escaping it
    after binding is unexplained and must reach fail-fast. Two earlier call
    sites invoked it directly; being inside a cleanup path does not make a
    bound call exempt, and the structural test that was supposed to catch this
    only inspected a hand-written list of two functions.

    Returns the call's own success flag. A zero here is an ordinary failed
    close, not an unexplained fault, and is left for the caller to interpret.
    """

    return bool(
        _guarded(bindings, "CLOSE", bindings.kernel32.CloseHandle, handle)
    )


def _note_cleanup_failure(error: BaseException, detail: str) -> None:
    """Attach a cleanup failure to the error that caused the cleanup.

    A failure while unwinding must not become the failure that is reported.
    The original exception is what explains why the unwind is happening; a
    `CLOSE_FAILED` raised over the top of it destroys that explanation and
    sends the reader after the wrong fault.
    """

    error.add_note(f"cleanup after this error also failed: {detail}")


def _anchor(bindings: _Bindings, name: str, parent: "Anchor | None") -> Anchor:
    handle = _open_directory(bindings, name, parent)
    try:
        if _reparse_tag(bindings, handle) != 0:
            raise NativeError("PATH_IS_REPARSE_POINT")
        return Anchor(bindings, handle, _identity_of(bindings, handle))
    except BaseException as error:
        if not _close_handle(bindings, handle):
            ctypes.get_last_error()
            _note_cleanup_failure(error, "CLOSE_FAILED")
        raise


def open_chain(bindings: _Bindings, base: str) -> PinnedChain:
    """Pin every component from the volume root down to `base`.

    Each open is relative to the handle above it, so no component is resolved
    by name twice, and every handle is held for the chain's lifetime.
    """

    if not platform_supported():
        raise NativeError("HANDLE_BOUNDARY_UNAVAILABLE")

    volume_root, components = split_base_path(base)
    anchors: list[Anchor] = []
    try:
        anchors.append(_anchor(bindings, volume_root, None))
        for component in components:
            anchors.append(_anchor(bindings, component, anchors[-1]))
    except BaseException as error:
        # The quiet variant, deliberately: `close_chain` raises, and raising
        # from here would replace the failure that is being unwound with a
        # `CLOSE_FAILED` about a handle nobody asked about.
        cleanup_failure = _close_chain_quietly(anchors)
        if cleanup_failure is not None:
            _note_cleanup_failure(error, cleanup_failure.args[0])
        raise
    return PinnedChain(anchors)


def revalidate(bindings: _Bindings, anchor: Anchor) -> None:
    """Confirm the held object is still the one that was opened."""

    if anchor.closed:
        raise NativeError("ROOT_IDENTITY_CHANGED")
    if _reparse_tag(bindings, anchor._handle) != 0:
        raise NativeError("PATH_IS_REPARSE_POINT")
    if _identity_of(bindings, anchor._handle) != anchor.identity:
        raise NativeError("ROOT_IDENTITY_CHANGED")


def _close_chain_quietly(anchors: "list[Anchor]") -> "NativeError | None":
    """Close in reverse acquisition order and *return* the first failure.

    Returning rather than raising is what lets an unwinding caller keep its own
    error. Every anchor is still attempted: stopping at the first failure would
    leak the handles below it.
    """

    failure: NativeError | None = None
    for anchor in reversed(anchors):
        try:
            anchor.close()
        except NativeError as error:
            failure = failure or error
    return failure


def close_chain(bindings: _Bindings, chain: PinnedChain) -> None:
    """Release the borrowed chain in reverse acquisition order.

    Kept as a function for callers that hold `bindings` rather than the chain;
    the ownership lives on `PinnedChain` itself. Nothing here is deleted —
    these are directories the run borrowed, not objects it created.
    """

    chain.close()


# ===========================================================================
# Tranche N3c-2 — creation, deletion and the absence probe
# ===========================================================================
#
# Everything below acts on objects this code creates, under a `base` it only
# borrowed. `base` is never created, never deleted and never marked; N3c-1's
# `open_chain` is the only way it is touched.


def _create(
    bindings: _Bindings,
    parent: Anchor,
    name: str,
    access: int,
    share: int,
    attributes: int,
    options: int,
) -> int:
    """Create one object relative to `parent`, or refuse.

    `FILE_CREATE` is what makes an occupied name a refusal rather than an open
    of whatever is sitting there — the same guarantee `O_EXCL` gave the path
    version, without the path.
    """

    _validate_created_name(name)
    if parent.closed:
        raise NativeError("ROOT_IDENTITY_CHANGED")

    handle = HANDLE()
    unicode_name, buffer = _unicode_string(name)
    object_attributes = OBJECT_ATTRIBUTES()
    object_attributes.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
    object_attributes.RootDirectory = parent._handle
    object_attributes.ObjectName = ctypes.pointer(unicode_name)
    object_attributes.Attributes = OBJ_CASE_INSENSITIVE
    object_attributes.SecurityDescriptor = None
    object_attributes.SecurityQualityOfService = None
    status_block = IO_STATUS_BLOCK()

    stage = "CREATE_FILE" if options & FILE_NON_DIRECTORY_FILE else "CREATE_DIRECTORY"
    status = _guarded(
        bindings,
        stage,
        bindings.ntdll.NtCreateFile,
        ctypes.byref(handle),
        access,
        ctypes.byref(object_attributes),
        ctypes.byref(status_block),
        None,
        attributes,
        share,
        FILE_CREATE,
        options,
        None,
        0,
    )
    # Keep the name alive until the call has returned.
    del unicode_name, buffer, object_attributes

    if status < 0:
        _guarded(bindings, stage, bindings.ntdll.RtlNtStatusToDosError, status)
        # Only a collision is a collision. Reporting every creation failure as
        # `MATERIALIZE_PATH_EXISTS` would tell a caller a name is taken when the
        # volume is full, the parent was deleted underneath us, or access was
        # refused — three different problems with three different responses.
        if status == STATUS_OBJECT_NAME_COLLISION:
            raise NativeError("MATERIALIZE_PATH_EXISTS")
        raise NativeError("MATERIALIZE_WRITE_FAILED")
    if not handle.value or handle.value == INVALID_HANDLE_VALUE:
        raise NativeError("MATERIALIZE_WRITE_FAILED")
    return handle.value


def create_directory(bindings: _Bindings, parent: Anchor, name: str) -> Anchor:
    """Role 2: a directory this code creates and cleanup must delete."""

    handle = _create(
        bindings,
        parent,
        name,
        CREATED_DIRECTORY_ACCESS,
        CREATED_DIRECTORY_SHARE,
        FILE_ATTRIBUTE_NORMAL,
        CREATED_DIRECTORY_OPTIONS,
    )
    try:
        return Anchor(bindings, handle, _identity_of(bindings, handle))
    except BaseException as error:
        _rollback_created(bindings, parent, name, handle, error)
        raise


def _write_all(bindings: _Bindings, handle: int, payload: bytes) -> None:
    """Write every byte, or refuse.

    The buffer is created once and held for the whole loop: a temporary freed
    between chunks is a use-after-free that usually looks like it worked.
    Offsets go through `byref(buffer, offset)` rather than pointer arithmetic.

    A short write is legal and is continued, but a write reporting **zero**
    bytes is not progress — looping on it would spin forever, so it is a
    failure.
    """

    if type(payload) is not bytes:
        raise NativeError("MATERIALIZE_WRITE_FAILED")
    if not payload:
        return

    total = len(payload)
    block = (c_char * total).from_buffer_copy(payload)
    written_total = 0
    while written_total < total:
        chunk = min(WRITE_CHUNK, total - written_total)
        written = DWORD(0)
        ok = _guarded(
            bindings,
            "WRITE",
            bindings.kernel32.WriteFile,
            handle,
            ctypes.byref(block, written_total),
            chunk,
            ctypes.byref(written),
            None,
        )
        if not ok:
            ctypes.get_last_error()
            raise NativeError("MATERIALIZE_WRITE_FAILED")
        if written.value == 0 or written.value > chunk:
            # Zero is no progress; more than asked for is a contract violation.
            raise NativeError("MATERIALIZE_WRITE_FAILED")
        written_total += written.value
    del block


def create_file(
    bindings: _Bindings, parent: Anchor, name: str, payload: bytes
) -> Leaf:
    """Role 3: create the file read-only, write it, and keep holding it.

    `FILE_ATTRIBUTE_READONLY` at creation while this handle holds
    `FILE_WRITE_DATA` is deliberate: the attribute governs *later* opens, this
    handle keeps the access it was granted, so there is no interval in which the
    bytes are writable through their path.

    The handle is not released here. Revision 17 requires a created file to be
    removed through the same handle that created it; reopening the name to
    delete it would be a second ownership path for one object.
    """

    handle = _create(
        bindings,
        parent,
        name,
        CREATED_FILE_ACCESS,
        CREATED_FILE_SHARE,
        FILE_ATTRIBUTE_READONLY,
        CREATED_FILE_OPTIONS,
    )
    try:
        _write_all(bindings, handle, payload)
        return Leaf(bindings, handle, _identity_of(bindings, handle), len(payload))
    except BaseException as error:
        _rollback_created(bindings, parent, name, handle, error)
        raise


def _rewind(bindings: _Bindings, handle: int) -> None:
    """Set the file pointer to zero, and confirm it went there.

    Every read starts with this. Without it the first read after `create_file`
    would begin where writing stopped and return nothing — and an empty result
    is exactly the failure that passes unnoticed.

    The returned position is checked rather than only the boolean: a rewind
    reporting success without moving the pointer would surface later as a short
    read and be reported as a changed file, which sends the reader after the
    wrong fault.
    """

    position = LARGE_INTEGER(0)
    ok = _guarded(
        bindings,
        "READ",
        bindings.kernel32.SetFilePointerEx,
        handle,
        LARGE_INTEGER(0),
        ctypes.byref(position),
        FILE_BEGIN,
    )
    if not ok or position.value != 0:
        ctypes.get_last_error()
        raise NativeError("MATERIALIZE_READ_FAILED")


def read_all(bindings: _Bindings, leaf: Leaf) -> bytes:
    """Read the whole file back through the handle that created it.

    Takes no length: the leaf carries the one it was written at.

    A path-based read is not the alternative this replaces. Role 3's share mask
    refuses any opener unwilling to tolerate our write and delete access — every
    ordinary reader, including CPython's `open()` — while an opener that shares
    all three does get in. Reading through the creating handle is chosen because
    it resolves no name and adds no second ownership path, not because nothing
    else could read the file.

    `ReadFile`'s outcomes are mapped exhaustively. A count larger than the one
    requested is a broken call rather than a changed file, and is refused rather
    than trusted: a fake binding can return it, and treating it as a short read
    would advance past what was written.
    """

    if leaf.closed:
        raise NativeError("ROOT_IDENTITY_CHANGED")

    expected = leaf.length
    _rewind(bindings, leaf._handle)

    if expected == 0:
        chunks: list[bytes] = []
    else:
        buffer = (c_char * expected)()
        read_total = 0
        while read_total < expected:
            request = min(READ_CHUNK, expected - read_total)
            got = DWORD(0)
            ok = _guarded(
                bindings,
                "READ",
                bindings.kernel32.ReadFile,
                leaf._handle,
                ctypes.byref(buffer, read_total),
                request,
                ctypes.byref(got),
                None,
            )
            if not ok:
                ctypes.get_last_error()
                raise NativeError("MATERIALIZE_READ_FAILED")
            if got.value > request:
                # Not a short read. Nothing legitimate returns more than it was
                # asked for, and continuing would write past `request`.
                raise NativeError("MATERIALIZE_READ_FAILED")
            if got.value == 0:
                # End of file before the recorded length: the file is shorter
                # than what was written.
                raise NativeError("MATERIALIZED_BYTES_CHANGED")
            read_total += got.value
        chunks = [bytes(buffer)]

    # One byte past the recorded length. A read to the end would let a file that
    # grew decide how much this allocates; one byte answers the only question
    # being asked.
    probe = (c_char * 1)()
    got = DWORD(0)
    ok = _guarded(
        bindings,
        "READ",
        bindings.kernel32.ReadFile,
        leaf._handle,
        ctypes.byref(probe),
        1,
        ctypes.byref(got),
        None,
    )
    if not ok:
        ctypes.get_last_error()
        raise NativeError("MATERIALIZE_READ_FAILED")
    if got.value > 1:
        raise NativeError("MATERIALIZE_READ_FAILED")
    if got.value == 1:
        raise NativeError("MATERIALIZED_BYTES_CHANGED")

    return chunks[0] if chunks else b""


def file_attributes(bindings: _Bindings, held: "_Held") -> int:
    """The attribute word the kernel actually retained for a held object.

    Separate from `_reparse_tag` because the question is different: that one
    asks what kind of object this is, this one asks what was kept of what was
    requested. Role 3's born-read-only claim is checked here, against a control
    object, because a request the filesystem ignored would still look correct
    at the call boundary.
    """

    info = FILE_BASIC_INFO()
    ok = _guarded(
        bindings,
        "IDENTITY",
        bindings.kernel32.GetFileInformationByHandleEx,
        held._handle,
        FILE_BASIC_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        raise _query_failed("FileBasicInfo")
    return int(info.FileAttributes)


def _mark_deleted(bindings: _Bindings, handle: int) -> None:
    """Mark one raw handle's object for deletion, preferred class then fallback.

    Split out from `remove` so the post-create rollback path can use exactly the
    same marking code. A rollback that deleted by some other means would be a
    second deletion path, and the two would drift.
    """

    disposition = FILE_DISPOSITION_INFO_EX()
    disposition.Flags = (
        FILE_DISPOSITION_DELETE
        | FILE_DISPOSITION_POSIX_SEMANTICS
        | FILE_DISPOSITION_IGNORE_READONLY_ATTRIBUTE
    )
    ok = _guarded(
        bindings,
        "REMOVE",
        bindings.kernel32.SetFileInformationByHandle,
        handle,
        FILE_DISPOSITION_INFO_EX_CLASS,
        ctypes.byref(disposition),
        ctypes.sizeof(disposition),
    )
    if ok:
        return
    ctypes.get_last_error()

    basic = FILE_BASIC_INFO()
    # Zero means "leave this timestamp alone"; only the attribute word changes.
    basic.CreationTime = 0
    basic.LastAccessTime = 0
    basic.LastWriteTime = 0
    basic.ChangeTime = 0
    basic.FileAttributes = FILE_ATTRIBUTE_NORMAL
    ok = _guarded(
        bindings,
        "REMOVE",
        bindings.kernel32.SetFileInformationByHandle,
        handle,
        FILE_BASIC_INFO_CLASS,
        ctypes.byref(basic),
        ctypes.sizeof(basic),
    )
    if not ok:
        ctypes.get_last_error()
        raise NativeError("CLEANUP_INCOMPLETE")

    legacy = FILE_DISPOSITION_INFO()
    legacy.DeleteFile = 1
    ok = _guarded(
        bindings,
        "REMOVE",
        bindings.kernel32.SetFileInformationByHandle,
        handle,
        FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(legacy),
        ctypes.sizeof(legacy),
    )
    if not ok:
        ctypes.get_last_error()
        raise NativeError("CLEANUP_INCOMPLETE")


def _rollback_created(
    bindings: _Bindings,
    parent: Anchor,
    name: str,
    handle: int,
    error: BaseException,
) -> None:
    """Undo a create that succeeded before a later step failed.

    Without this, a failure between `FILE_CREATE` and the returned ownership
    object leaves the name on disk with nothing holding it: the caller never
    received an object to clean up, so nothing ever would. The object is marked,
    closed and confirmed gone, in that order — the same transaction cleanup
    uses.

    Every failure here is attached to `error` and none replaces it. The reason
    the rollback is happening is what the caller needs to see.
    """

    try:
        _mark_deleted(bindings, handle)
    except NativeError as failure:
        _note_cleanup_failure(error, f"rollback mark failed: {failure.args[0]}")
        if not _close_handle(bindings, handle):
            ctypes.get_last_error()
            _note_cleanup_failure(error, "rollback close failed")
        return

    if not _close_handle(bindings, handle):
        ctypes.get_last_error()
        _note_cleanup_failure(error, "rollback close failed")
        return

    try:
        confirm_absent(bindings, parent, name)
    except NativeError as failure:
        _note_cleanup_failure(error, f"rollback residue: {failure.args[0]}")


def remove(bindings: _Bindings, held: "_Held") -> None:
    """Mark the held object for deletion. Deletion completes when it closes.

    Acts on the handle, never on a name, so nothing here can be redirected by
    replacing a directory. `IGNORE_READONLY_ATTRIBUTE` is why role 3 can be born
    read-only and still be removable; POSIX semantics is why the name is gone
    when the last handle closes rather than lingering as delete-pending.

    The fallback exists because `FileDispositionInfoEx` is not available on
    every filesystem. It clears the read-only attribute first, because the older
    disposition class has no flag that ignores it.
    """

    if held.closed:
        raise NativeError("ROOT_IDENTITY_CHANGED")

    # Set before the call, not after: if marking raises, this handle's object
    # may still be delete-pending, and a later close must report that the
    # removal did not complete rather than that a handle would not close.
    held._removing = True
    _mark_deleted(bindings, held._handle)


def confirm_absent(bindings: _Bindings, parent: Anchor, name: str) -> None:
    """Read-only: the name is gone under this parent, or cleanup is incomplete.

    Only `STATUS_OBJECT_NAME_NOT_FOUND` counts as absent. A success, a
    delete-pending, a sharing violation and an access denial are all *not*
    absent — each means something is still there, or that we cannot tell, and
    neither is a reason to proceed to the parent.

    `FILE_SHARE_DELETE` appears here and nowhere else in this module, so the
    probe does not pin the name it is asking about.
    """

    _validate_created_name(name)
    if parent.closed:
        raise NativeError("ROOT_IDENTITY_CHANGED")

    handle = HANDLE()
    unicode_name, buffer = _unicode_string(name)
    object_attributes = OBJECT_ATTRIBUTES()
    object_attributes.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
    object_attributes.RootDirectory = parent._handle
    object_attributes.ObjectName = ctypes.pointer(unicode_name)
    object_attributes.Attributes = OBJ_CASE_INSENSITIVE
    object_attributes.SecurityDescriptor = None
    object_attributes.SecurityQualityOfService = None
    status_block = IO_STATUS_BLOCK()

    status = _guarded(
        bindings,
        "ABSENCE_PROBE",
        bindings.ntdll.NtOpenFile,
        ctypes.byref(handle),
        ABSENCE_ACCESS,
        ctypes.byref(object_attributes),
        ctypes.byref(status_block),
        ABSENCE_SHARE,
        ABSENCE_OPTIONS,
    )
    del unicode_name, buffer, object_attributes

    if status == STATUS_OBJECT_NAME_NOT_FOUND:
        return
    if status >= 0 and handle.value and handle.value != INVALID_HANDLE_VALUE:
        # It opened, so it is still there. Close what we just opened before
        # reporting, or the probe leaks the handle it proved exists.
        _close_handle(bindings, handle.value)
    raise NativeError("CLEANUP_INCOMPLETE")


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
