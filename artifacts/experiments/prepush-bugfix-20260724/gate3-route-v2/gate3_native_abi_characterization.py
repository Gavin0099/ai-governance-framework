"""Windows native ABI characterization for the Gate 3 handle boundary.

Measurement only.  This program exists because successive revisions of the
native boundary design candidate specified ABI details from memory and a
reviewer found an error in each round.  It measures what the platform actually
does so the next revision can cite numbers instead of recollection.

Boundaries, per the authorizing slice:

- it never calls `NtCreateFile`;
- it creates and deletes no filesystem object;
- it touches no production path, no credentials, no preflight, no live run and
  no historical code;
- SEH and fail-fast behaviour is measured only in a disposable child process,
  through documented Windows exception APIs, with valid arguments.  No invalid
  pointer is ever passed and no memory corruption is provoked;
- **every** library load in the parent and in every child goes through
  `system_library`, which enforces the full platform probe, a fixed name set and
  a System32-only search, per the compensating control attached to the accepted
  `NATIVE-INTEROP.md` §3.3 deviation;
- anything this machine cannot answer is reported `UNVERIFIED`, never guessed.

A note this program repeats because it keeps mattering: the structure and union
declarations below were transcribed from the design document under review.
Measuring them establishes that the *declarations* are self-consistent.  It does
not establish the Windows ABI, and no result here may be read as confirming or
refuting an SDK definition while section C reports `UNVERIFIED`.

Nothing here is admission evidence.  Admission needs the ADR, the next design
revision, an independent review and an owner promotion.

Run:  python gate3_native_abi_characterization.py
"""

from __future__ import annotations

import ctypes
import gc
import json
import os
import platform
import subprocess
import sys
from ctypes import (
    POINTER,
    Structure,
    Union,
    c_char,
    c_char_p,
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


UNVERIFIED = "UNVERIFIED"

SDK_HEADER_ROOTS = (
    r"C:\Program Files (x86)\Windows Kits\10\Include",
    r"C:\Program Files\Windows Kits\10\Include",
    r"C:\Program Files (x86)\Windows Kits\8.1\Include",
)
SDK_HEADERS = ("winternl.h", "ntdef.h", "winnt.h", "fileapi.h", "winbase.h")

# --- library loading control ------------------------------------------------
#
# Enforced identically in the parent and in every child.  The text below is
# duplicated into CHILD_SOURCE deliberately: a child that imports this module
# would drag the whole measurement surface into the process under test.

LOADER_CONTROL = r'''
LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800
ALLOWED_LIBRARIES = ("kernel32.dll", "ntdll.dll")
SUPPORTED_MACHINES = ("AMD64", "ARM64")


def platform_supported():
    """Full probe: OS, pointer width and architecture, before any load."""

    return (
        sys.platform == "win32"
        and ctypes.sizeof(ctypes.c_void_p) == 8
        and platform.machine().upper() in SUPPORTED_MACHINES
    )


def system_library(name):
    """The only load path.  Fixed names, System32 search, probe first.

    There is no exception to the allowlist, not even for a name chosen to be
    absent.  An earlier revision carved one out for a negative-load measurement;
    that measurement is gone rather than the rule.
    """

    if name not in ALLOWED_LIBRARIES:
        raise ValueError("library name is not in the fixed allowlist")
    if not platform_supported():
        raise OSError("platform probe failed; refusing to load")
    return ctypes.WinDLL(
        name, use_last_error=True, winmode=LOAD_LIBRARY_SEARCH_SYSTEM32
    )
'''

exec(LOADER_CONTROL)  # noqa: S102 — one definition, shared verbatim with children


def _loaded_from(kernel32: ctypes.WinDLL, library: ctypes.WinDLL) -> str:
    """Where the loader actually found a library — evidence, not assumption."""

    kernel32.GetModuleFileNameW.restype = c_ulong
    kernel32.GetModuleFileNameW.argtypes = [c_void_p, c_wchar_p, c_ulong]
    buffer = ctypes.create_unicode_buffer(32768)
    written = kernel32.GetModuleFileNameW(library._handle, buffer, len(buffer))
    return buffer.value if written else UNVERIFIED


# --- A. environment ---------------------------------------------------------


def _os_build_from_ntdll(ntdll: ctypes.WinDLL) -> dict[str, object]:
    """RtlGetVersion reports the true build; GetVersionEx is manifest-shimmed."""

    class OSVERSIONINFOEXW(Structure):
        _fields_ = [
            ("dwOSVersionInfoSize", c_ulong),
            ("dwMajorVersion", c_ulong),
            ("dwMinorVersion", c_ulong),
            ("dwBuildNumber", c_ulong),
            ("dwPlatformId", c_ulong),
            ("szCSDVersion", c_wchar * 128),
            ("wServicePackMajor", c_ushort),
            ("wServicePackMinor", c_ushort),
            ("wSuiteMask", c_ushort),
            ("wProductType", c_ubyte),
            ("wReserved", c_ubyte),
        ]

    ntdll.RtlGetVersion.restype = c_long
    ntdll.RtlGetVersion.argtypes = [POINTER(OSVERSIONINFOEXW)]
    info = OSVERSIONINFOEXW()
    info.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFOEXW)
    if ntdll.RtlGetVersion(ctypes.byref(info)) < 0:
        return {"source": "RtlGetVersion", "result": UNVERIFIED}
    return {
        "source": "RtlGetVersion",
        "major": info.dwMajorVersion,
        "minor": info.dwMinorVersion,
        "build": info.dwBuildNumber,
    }


def environment() -> dict[str, object]:
    supported = platform_supported()
    reported = sys.getwindowsversion() if sys.platform == "win32" else None
    result: dict[str, object] = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_probe_passed": supported,
        "platform_probe_checks": ["sys.platform", "pointer width", "machine"],
        "machine": platform.machine(),
        "processor_architecture": os.environ.get("PROCESSOR_ARCHITECTURE", UNVERIFIED),
        "pointer_size_bytes": ctypes.sizeof(c_void_p),
        "ctypes_abi_marker": "WinDLL/stdcall-on-x86" if supported else UNVERIFIED,
        "sys_getwindowsversion_build": reported.build if reported else UNVERIFIED,
    }
    if not supported:
        result["ntdll_version"] = UNVERIFIED
        result["library_paths"] = UNVERIFIED
        return result

    kernel32 = system_library("kernel32.dll")
    ntdll = system_library("ntdll.dll")
    result["ntdll_version"] = _os_build_from_ntdll(ntdll)
    result["library_paths"] = {
        "kernel32.dll": _loaded_from(kernel32, kernel32),
        "ntdll.dll": _loaded_from(kernel32, ntdll),
    }
    try:
        system_library("not-in-the-allowlist.dll")
        result["allowlist_enforced"] = False
    except ValueError:
        result["allowlist_enforced"] = True
    return result


# --- B. structure and union layout ------------------------------------------


def _types(pack: int | None) -> list[type]:
    """Every structure AND union the design candidate declares."""

    class UNICODE_STRING(Structure):
        if pack:
            _pack_ = pack
        _fields_ = [
            ("Length", c_ushort),
            ("MaximumLength", c_ushort),
            ("Buffer", c_wchar_p),
        ]

    class OBJECT_ATTRIBUTES(Structure):
        if pack:
            _pack_ = pack
        _fields_ = [
            ("Length", c_ulong),
            ("RootDirectory", c_void_p),
            ("ObjectName", POINTER(UNICODE_STRING)),
            ("Attributes", c_ulong),
            ("SecurityDescriptor", c_void_p),
            ("SecurityQualityOfService", c_void_p),
        ]

    class IO_STATUS_BLOCK_UNION(Union):
        if pack:
            _pack_ = pack
        _fields_ = [("Status", c_long), ("Pointer", c_void_p)]

    class IO_STATUS_BLOCK(Structure):
        if pack:
            _pack_ = pack
        _anonymous_ = ("u",)
        _fields_ = [("u", IO_STATUS_BLOCK_UNION), ("Information", c_size_t)]

    class FILE_ID_INFO(Structure):
        if pack:
            _pack_ = pack
        _fields_ = [("VolumeSerialNumber", c_ulonglong), ("FileId", c_ubyte * 16)]

    class FILE_ATTRIBUTE_TAG_INFO(Structure):
        if pack:
            _pack_ = pack
        _fields_ = [("FileAttributes", c_ulong), ("ReparseTag", c_ulong)]

    class FILE_DISPOSITION_INFO(Structure):
        if pack:
            _pack_ = pack
        # Declared BOOLEAN-as-one-byte by the design under review.  Whether the
        # SDK agrees is section C's question, not this measurement's.
        _fields_ = [("DeleteFile", c_ubyte)]

    class FILE_DISPOSITION_INFO_EX(Structure):
        if pack:
            _pack_ = pack
        _fields_ = [("Flags", c_ulong)]

    class FILE_BASIC_INFO(Structure):
        if pack:
            _pack_ = pack
        _fields_ = [
            ("CreationTime", c_longlong),
            ("LastAccessTime", c_longlong),
            ("LastWriteTime", c_longlong),
            ("ChangeTime", c_longlong),
            ("FileAttributes", c_ulong),
        ]

    return [
        UNICODE_STRING,
        OBJECT_ATTRIBUTES,
        IO_STATUS_BLOCK_UNION,
        IO_STATUS_BLOCK,
        FILE_ID_INFO,
        FILE_ATTRIBUTE_TAG_INFO,
        FILE_DISPOSITION_INFO,
        FILE_DISPOSITION_INFO_EX,
        FILE_BASIC_INFO,
    ]


def _layout(declared: type) -> dict[str, object]:
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


def layouts() -> dict[str, object]:
    natural = {t.__name__: _layout(t) for t in _types(None)}
    packed = {t.__name__: _layout(t) for t in _types(8)}
    differences = {
        name: {"natural": natural[name], "pack8": packed[name]}
        for name in natural
        if natural[name] != packed[name]
    }
    return {
        "architecture": platform.machine(),
        "natural": natural,
        "pack8": packed,
        "identical": not differences,
        "differences": differences,
        "establishes": (
            "self-consistency of the ctypes declarations transcribed from the "
            "design under review, on this architecture and ctypes build"
        ),
        "does_not_establish": (
            "the Windows SDK ABI. While section C is UNVERIFIED, no size, "
            "alignment or offset here confirms or refutes an SDK definition, "
            "and no alternative declaration can be called wrong on this basis."
        ),
    }


# --- C. SDK header comparison -----------------------------------------------


def sdk_headers() -> dict[str, object]:
    found: dict[str, str] = {}
    roots_present = [root for root in SDK_HEADER_ROOTS if os.path.isdir(root)]
    for root in roots_present:
        for directory, _, names in os.walk(root):
            for name in names:
                if name.lower() in SDK_HEADERS and name.lower() not in found:
                    found[name.lower()] = os.path.join(directory, name)
    return {
        "roots_searched": list(SDK_HEADER_ROOTS),
        "roots_present": roots_present,
        "headers_found": found,
        "comparison": "AVAILABLE" if found else UNVERIFIED,
        "consequence": (
            "Section B is declaration self-consistency only."
            if not found
            else "Headers located; per-field comparison is a reviewer step."
        ),
    }


# --- D. ctypes buffer semantics ---------------------------------------------


def _address(obj: object) -> int:
    return ctypes.cast(obj, c_void_p).value or 0


def _retained_objects(obj: object) -> tuple[str, list[object]]:
    """Flatten `_objects` into the concrete objects the wrapper holds."""

    retained = getattr(obj, "_objects", None)
    if retained is None:
        return "none", []
    if isinstance(retained, dict):
        return "dict", list(retained.values())
    return "object", [retained]


def _retention(obj: object, source: object) -> dict[str, object]:
    """Whether a wrapper holds a reference that reaches `source`, by identity.

    An earlier revision reported only that `_objects` was non-empty and its
    type or keys, then described that as keeping the source alive.  Non-empty is
    not an identity chain.  This resolves the chain explicitly and reports which
    link, if any, actually *is* the source.
    """

    kind, retained = _retained_objects(obj)
    direct = any(item is source for item in retained)
    indirect: str | None = None
    for item in retained:
        if item is source:
            continue
        if isinstance(item, memoryview) and item.obj is source:
            indirect = "memoryview.obj is source"
        elif getattr(item, "_objects", None) is not None:
            _, nested = _retained_objects(item)
            if any(inner is source for inner in nested):
                indirect = "nested _objects contains source"
    return {
        "objects_kind": kind,
        "retained_types": sorted({type(item).__name__ for item in retained}),
        "retains_source_directly": direct,
        "reaches_source_indirectly": indirect,
        "identity_chain_resolved": direct or indirect is not None,
        "caveat": (
            "shows a reference is held at this instant; it is not a complete "
            "lifetime proof, which would need a use-after-free this slice "
            "forbids"
        ),
    }


def buffer_semantics() -> dict[str, object]:
    """Three separate questions, reported separately.

    Revision 2 collapsed address aliasing into an ownership claim.  They are not
    the same thing: two wrappers can alias one address while only one of them
    keeps the source alive, and a copy's address being stable while it is
    strongly referenced says nothing about who owns the storage.
    """

    payload = b"gate3-characterization-payload"
    size = len(payload)
    mutable = bytearray(payload)

    rejected: dict[str, str] = {}
    for label, thunk in (
        ("addressof_memoryview_bytes", lambda: ctypes.addressof(memoryview(payload))),
        ("from_buffer_on_bytes", lambda: (c_char * size).from_buffer(payload)),
        (
            "from_buffer_on_readonly_memoryview",
            lambda: (c_char * size).from_buffer(memoryview(payload)),
        ),
    ):
        try:
            thunk()
            rejected[label] = "accepted"
        except Exception as error:
            rejected[label] = f"rejected: {type(error).__name__}"

    # Borrow and copy are compared over the SAME mutable source.  An earlier
    # revision copied from immutable `payload` and then compared the copy's
    # address against a view over a different `bytearray`, which relates two
    # unconnected objects and settles nothing.
    view_a = (c_char * size).from_buffer(mutable)
    view_b = (c_char * size).from_buffer(mutable)
    writable_view = memoryview(mutable)
    view_c = (c_char * size).from_buffer(writable_view)
    copy_of_mutable = (c_char * size).from_buffer_copy(mutable)
    copy_of_mutable_again = (c_char * size).from_buffer_copy(mutable)
    pointer_a = c_char_p(payload)
    pointer_b = c_char_p(payload)

    aliasing = {
        "two_from_buffer_views_of_one_bytearray": {
            "same_address": ctypes.addressof(view_a) == ctypes.addressof(view_b)
        },
        "from_buffer_of_writable_memoryview_vs_bytearray": {
            "same_address": ctypes.addressof(view_c) == ctypes.addressof(view_a)
        },
        "two_from_buffer_copies_of_one_bytearray": {
            "same_address": ctypes.addressof(copy_of_mutable)
            == ctypes.addressof(copy_of_mutable_again)
        },
        "copy_vs_borrow_of_the_same_bytearray": {
            "same_address": ctypes.addressof(copy_of_mutable)
            == ctypes.addressof(view_a),
            "source": "both derived from the same bytearray",
        },
        "two_c_char_p_over_one_bytes": {
            "same_address": _address(pointer_a) == _address(pointer_b)
        },
    }

    retention = {
        "from_buffer_bytearray": _retention(view_a, mutable),
        "from_buffer_writable_memoryview": _retention(view_c, mutable),
        "from_buffer_writable_memoryview_vs_the_view": _retention(
            view_c, writable_view
        ),
        "from_buffer_copy": _retention(copy_of_mutable, mutable),
        "c_char_p_over_bytes": _retention(pointer_a, payload),
    }

    ownership = {
        "from_buffer_copy_of_mutable": {
            "objects_is_none": _retained_objects(copy_of_mutable)[0] == "none",
            "address_differs_from_borrow_of_same_source": ctypes.addressof(
                copy_of_mutable
            )
            != ctypes.addressof(view_a),
            "two_copies_of_same_source_differ": ctypes.addressof(copy_of_mutable)
            != ctypes.addressof(copy_of_mutable_again),
            "contents_match_source": bytes(copy_of_mutable) == bytes(mutable),
            "address_stable_across_gc_while_referenced": _address_survives_gc(
                copy_of_mutable
            ),
            "note": (
                "address stability while strongly referenced establishes nothing "
                "on its own; the same-source address difference and the empty "
                "_objects are what distinguish a copy from a borrow"
            ),
        },
        "c_char_p_objects_is_the_payload_object": (
            getattr(pointer_a, "_objects", None) is payload
        ),
    }

    offsets = [
        {
            "offset": offset,
            "address_delta": _address(
                ctypes.cast(ctypes.byref(copy_of_mutable, offset), POINTER(c_char))
            )
            - ctypes.addressof(copy_of_mutable),
        }
        for offset in (0, 1, size - 1)
    ]

    return {
        "rejections": rejected,
        "address_aliasing": aliasing,
        "wrapper_retention": retention,
        "copy_ownership": ownership,
        "byref_offset_arithmetic": offsets,
        "not_measured": (
            "what happens if a borrowed source is released while the pointer is "
            "in use; that requires a use-after-free this slice forbids"
        ),
    }


def _address_survives_gc(obj: object) -> bool:
    before = ctypes.addressof(obj)
    gc.collect()
    return ctypes.addressof(obj) == before


# --- E. runtime-fact canonicalization ---------------------------------------


def volume_facts(probe_path: str) -> dict[str, object]:
    if not platform_supported():
        return {"result": UNVERIFIED, "reason": "platform probe failed"}

    kernel32 = system_library("kernel32.dll")
    kernel32.GetVolumeInformationW.restype = c_int
    kernel32.GetVolumeInformationW.argtypes = [
        c_wchar_p,
        c_wchar_p,
        c_ulong,
        POINTER(c_ulong),
        POINTER(c_ulong),
        POINTER(c_ulong),
        c_wchar_p,
        c_ulong,
    ]

    drive = os.path.splitdrive(os.path.abspath(probe_path))[0] + "\\"
    capacity = 261  # MAX_PATH + 1, in characters
    name = ctypes.create_unicode_buffer(capacity)
    filesystem = ctypes.create_unicode_buffer(capacity)
    serial = c_ulong(0)
    component = c_ulong(0)
    flags = c_ulong(0)

    ok = kernel32.GetVolumeInformationW(
        drive,
        name,
        capacity,
        ctypes.byref(serial),
        ctypes.byref(component),
        ctypes.byref(flags),
        filesystem,
        capacity,
    )
    if not ok:
        return {"result": UNVERIFIED, "last_error": ctypes.get_last_error()}

    token = filesystem.value
    undersized = ctypes.create_unicode_buffer(2)
    small_ok = kernel32.GetVolumeInformationW(
        drive, None, 0, None, None, None, undersized, 2
    )
    return {
        "drive": drive,
        "filesystem_token": token,
        "filesystem_token_utf8_bytes": list(token.encode("utf-8")),
        "casefold": token.casefold(),
        "buffer_capacity_chars": capacity,
        "max_component_length": component.value,
        "flags": flags.value,
        "volume_serial_present": serial.value != 0,
        "undersized_fs_buffer_succeeded": bool(small_ok),
        "undersized_fs_buffer_last_error": 0 if small_ok else ctypes.get_last_error(),
        "sample_size": "one volume, one filesystem; not a general API contract",
        "handle_based_variant": UNVERIFIED,
        "handle_based_reason": (
            "GetVolumeInformationByHandleW needs a directory handle; opening one "
            "is outside this slice"
        ),
    }


# --- F. exception and fail-fast behaviour, disposable child only ------------

CHILD_SOURCE = (
    "import ctypes, json, platform, sys\n"
    + LOADER_CONTROL
    + r'''
mode = sys.argv[1]

k32 = system_library("kernel32.dll")
# Suppress the Windows Error Reporting dialog so an unhandled fault cannot block.
k32.SetErrorMode(0x0001 | 0x0002)   # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX
k32.RaiseException.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
                               ctypes.c_void_p]
k32.RaiseException.restype = None
k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
k32.GetFileAttributesW.restype = ctypes.c_ulong

def describe(error):
    return {
        "type": type(error).__name__,
        "args_len": len(error.args),
        "winerror": getattr(error, "winerror", None),
        "errno": getattr(error, "errno", None),
        "message_head": (str(error)[:70] if error.args else ""),
    }

try:
    if mode == "application":
        # Application-defined code, bit 29 set as the convention requires.
        k32.RaiseException(0x20000001, 0, 0, None)
    elif mode == "access_violation_code":
        # The ACCESS_VIOLATION *code*, raised through the documented API with
        # valid arguments.  No pointer is dereferenced, no memory is corrupted.
        # This measures how a raised code is surfaced -- NOT how a real
        # hardware fault is surfaced, which this slice forbids producing.
        k32.RaiseException(0xC0000005, 0, 0, None)
    elif mode == "recoverable_win32_no_load":
        # An ordinary recoverable Win32 failure that loads nothing: a read-only
        # attribute query on a path that cannot exist.  Nothing is created,
        # nothing is deleted.
        INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
        result = k32.GetFileAttributesW("\\\\?\\Z:\\gate3-absent-path-probe")
        if result != INVALID_FILE_ATTRIBUTES:
            print(json.dumps({"outcome": "probe_unexpectedly_succeeded"}), flush=True)
            raise SystemExit(0)
        raise ctypes.WinError(ctypes.get_last_error())
    elif mode == "failfast":
        k32.RaiseFailFastException.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                               ctypes.c_ulong]
        k32.RaiseFailFastException.restype = None
        k32.RaiseFailFastException(None, None, 0)
    print(json.dumps({"outcome": "returned_normally"}), flush=True)
except SystemExit:
    raise
except BaseException as error:
    print(json.dumps({"outcome": "python_exception", **describe(error)}), flush=True)
'''
)


def _run_child(mode: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", CHILD_SOURCE, mode],
        capture_output=True,
        text=True,
        timeout=60,
    )
    code = completed.returncode
    try:
        observed = json.loads(completed.stdout.strip() or "{}")
    except ValueError:
        observed = {"outcome": "unparseable", "raw": completed.stdout.strip()[:200]}
    return {
        "mode": mode,
        "exit_code_signed": code,
        "exit_code_hex": hex(code & 0xFFFFFFFF),
        "observed": observed,
        "stderr_tail": completed.stderr.strip()[-300:],
    }


def exception_behaviour() -> dict[str, object]:
    if not platform_supported():
        return {"result": UNVERIFIED, "reason": "platform probe failed"}
    return {
        "measurements": {
            mode: _run_child(mode)
            for mode in (
                "application",
                "access_violation_code",
                "recoverable_win32_no_load",
                "failfast",
            )
        },
        "establishes": [
            "the specified synthetic codes raised through RaiseException were "
            "caught as ordinary Python exceptions on this interpreter and build",
            "the RaiseFailFastException child was not caught by that child's "
            "except BaseException and exited with the observed code",
        ],
        "does_not_establish": [
            "that a genuine hardware access violation surfaces identically",
            "that no safe structural classifier exists — only that the "
            "winerror/args-length discriminator proposed earlier fails",
            "that RaiseFailFastException is uninterceptable in general; only "
            "that this child did not intercept it",
            "that message text or args tuple shape is a stable ABI rather than "
            "a CPython implementation detail",
        ],
    }


# --- report -----------------------------------------------------------------


def report() -> dict[str, object]:
    return {
        "schema": "gate3.native-abi-characterization.v3",
        "a_environment": environment(),
        "b_layout": layouts(),
        "c_sdk_headers": sdk_headers(),
        "d_buffer_semantics": buffer_semantics(),
        "e_volume_facts": volume_facts(__file__),
        "f_exception_behaviour": exception_behaviour(),
        "not_admission_evidence": (
            "A measurement is an input to admission, never admission itself. "
            "Admission requires the ADR, the next design revision, an "
            "independent review and an owner promotion."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
