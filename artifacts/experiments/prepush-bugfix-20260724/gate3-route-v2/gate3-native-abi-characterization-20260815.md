# Gate 3 Windows Native ABI Characterization Report

Status: measurement evidence; **not admission evidence**, not approved, not
implementation authority

Date: 2026-08-15

Base: `feat/gate3-historical-materialization@896bc64c006da4e40a6d5a7d8b32d462467d08f2`

Revision: 4 — revises the two blocking findings raised against revision 3: the
loader allowlist still carried an exception for a deliberately absent library,
and the buffer measurements compared a copy against an unrelated source while
reporting a non-empty `_objects` as a lifetime guarantee

## Review targets

| Artifact | Path |
| --- | --- |
| measurement program | `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_native_abi_characterization.py` |
| this report | `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3-native-abi-characterization-20260815.md` |

Neither is under `docs/governance/`. The design candidate under separate review
is `docs/governance/gate3-native-handle-boundary-design-candidate-20260815.md`
and is untouched by this slice.

## Reproduction

```bash
python artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_native_abi_characterization.py
```

## Boundaries observed

- `NtCreateFile` was never called; no filesystem object was created or deleted;
- no production path, credential, preflight, live run or historical code was
  touched;
- SEH and fail-fast were measured only in disposable children through documented
  Windows exception APIs with valid arguments. **No invalid pointer was passed
  and no memory corruption was provoked.** Raising the access-violation *code*
  through `RaiseException` is not a genuine hardware fault and is never treated
  as one here;
- children ran with `SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)`.

## A. Environment and loader control

| Fact | Value |
| --- | --- |
| Python | CPython 3.12.10 |
| Machine / `PROCESSOR_ARCHITECTURE` | `AMD64` / `AMD64` |
| Pointer size | 8 bytes |
| Platform probe | passed, **before any load** |
| Probe checks | `sys.platform`, pointer width, machine |
| `RtlGetVersion` | 10.0 build **26200** |
| `sys.getwindowsversion().build` | **26200** |

**The loader allowlist now has no exception.** Revision 2 had the child call
`ctypes.WinDLL` directly. Revision 3 routed that call through the helper but
kept a carve-out so a deliberately absent library could still be attempted —
which still attempted a load outside the fixed set the owner's ruling names, and
still contradicted this report's own description of the set as fixed.
Corrected by deleting the carve-out and the measurement that needed it, not by
re-describing them:

- the helper's source is defined once and injected verbatim into every child, so
  parent and child enforce the identical rule;
- the probe checks OS, pointer width and machine in both, before any load;
- `ALLOWED_LIBRARIES` is exactly `kernel32.dll` and `ntdll.dll`, with no second
  branch of any kind;
- the section F contrast case loads nothing at all.

| Check | Result |
| --- | --- |
| `kernel32.dll` resolved from | `C:\WINDOWS\System32\KERNEL32.DLL` |
| `ntdll.dll` resolved from | `C:\WINDOWS\SYSTEM32\ntdll.dll` |
| Name outside the fixed set | **refused** |

Paths come from `GetModuleFileNameW` on the loaded module handle.

The two build sources agree here. Per the owner ruling that initial admission
uses `os_build_min == os_build_max ==` the tested build, the candidate value
from this machine is **26200**, with `RtlGetVersion` recommended as the source.

## B. ctypes declaration layout, amd64

Measured with `_pack_` unset and with `_pack_ = 8`. All nine types are identical
between the two.

| Type | Kind | Size | Align | Field offsets |
| --- | --- | ---: | ---: | --- |
| `UNICODE_STRING` | structure | 16 | 8 | 0, 2, 8 |
| `OBJECT_ATTRIBUTES` | structure | 48 | 8 | 0, 8, 16, 24, 32, 40 |
| `IO_STATUS_BLOCK_UNION` | union | 8 | 8 | 0, 0 |
| `IO_STATUS_BLOCK` | structure | 16 | 8 | 0, 8 |
| `FILE_ID_INFO` | structure | 24 | 8 | 0, 8 |
| `FILE_ATTRIBUTE_TAG_INFO` | structure | 8 | 4 | 0, 4 |
| `FILE_DISPOSITION_INFO` | structure | 1 | 1 | 0 |
| `FILE_DISPOSITION_INFO_EX` | structure | 4 | 4 | 0 |
| `FILE_BASIC_INFO` | structure | 40 | 8 | 0, 8, 16, 24, 32 |

**What this establishes:** the ctypes declarations transcribed from the design
document under review are self-consistent on this architecture and ctypes build,
and the two packing choices agree.

**What it does not establish:** the Windows ABI. Section C is `UNVERIFIED`, the
field types came from the document being reviewed, so a wrong type there yields
a matching wrong number here. Revision 2 wrote that the 1-byte
`FILE_DISPOSITION_INFO` result "confirms that declaring `DeleteFile` as `BOOL`
would pass the wrong buffer size". **That is withdrawn.** The measurement shows
what the current `c_ubyte` declaration produces; it cannot confirm the SDK's
definition and cannot establish that any alternative declaration is wrong.

`FILE_ATTRIBUTE_TAG_INFO` aligns at 4 under these declarations, so a uniform
`_pack_ = 8` is inert there — again a statement about the declaration, not the
SDK.

## C. SDK header comparison — `UNVERIFIED`

No Windows SDK is installed. All three searched roots are absent; no headers
found. Section B is declaration self-consistency only, and closing this needs a
machine with the SDK.

## D. ctypes buffer semantics — three separate questions

Two defects in revision 3 are corrected here. The copy was built from an
immutable `bytes` and then compared against a view over a **different**
`bytearray`, so "copy vs source buffer" related two unconnected objects and
settled nothing. And retention was reported as `_objects` being non-empty, plus
its type or keys, which is not an identity chain and does not show the source is
reached at all.

### D.1 Rejections

| Attempt | Result |
| --- | --- |
| `ctypes.addressof(memoryview(bytes))` | rejected, `TypeError` |
| `(c_char*n).from_buffer(bytes)` | rejected, `TypeError` |
| `(c_char*n).from_buffer(memoryview(bytes))` — read-only | rejected, `TypeError` |

### D.2 Address aliasing — borrow and copy over the *same* `bytearray`

| Comparison | Same address? |
| --- | --- |
| two `from_buffer` views over one `bytearray` | **yes** |
| `from_buffer(memoryview(bytearray))` vs `from_buffer(bytearray)` | **yes** |
| two `from_buffer_copy` of that same `bytearray` | no |
| `from_buffer_copy` vs `from_buffer`, **same `bytearray`** | no |
| two `c_char_p` over one `bytes` | **yes** |

### D.3 Retention — identity chain resolved, not inferred

| Wrapper | `_objects` | Retained type | Reaches the source? |
| --- | --- | --- | --- |
| `from_buffer(bytearray)` | dict, 1 entry | `memoryview` | **indirectly** — the retained `memoryview.obj` **is** the `bytearray` |
| `from_buffer(memoryview(bytearray))` | dict, 1 entry | `memoryview` | **indirectly** — same relation to the `bytearray`; and the retained view is **not** the caller's `memoryview` object |
| `c_char_p(bytes)` | the object itself | `bytes` | **directly** — `pointer._objects is payload` is `True` |
| `from_buffer_copy(bytearray)` | `None` | — | no — retains nothing |

The precise result matters: `from_buffer` does **not** retain the `bytearray`
itself. It retains a `memoryview` that ctypes constructs, whose `.obj` is the
`bytearray`. Revision 3 described this as "keeps its source alive", which
happened to be true by one indirection it had not looked at.

**What this establishes:** a reference reaching the source is held **at the
moment of measurement**. It is not a complete lifetime proof, which would need a
use-after-free this slice forbids.

### D.4 Copy ownership

For a copy and a borrow taken from the same `bytearray`:
`from_buffer_copy` has `_objects is None`, its address differs from the borrow's,
two copies of that one source occupy different addresses, and its contents match.
Those together distinguish a copy from a borrow.

Its address also remained stable across `gc.collect()` **while strongly
referenced**, which on its own establishes nothing and is reported only for
completeness.

**Not measured:** what happens when a borrowed source is released while the
pointer is in use.

**Correction this forces on the design candidate:** the write loop's
`memoryview(payload)` yields no pointer at all — `addressof` rejects it and
`from_buffer` rejects a read-only view. The workable contracts are
`from_buffer_copy(payload)` (owns its storage, retains nothing) or a retained
borrow via `from_buffer(bytearray)`, `from_buffer(memoryview(bytearray))` or
`c_char_p(payload)`.

## E. Runtime-fact canonicalization

| Fact | Value |
| --- | --- |
| Drive | `D:\` |
| Filesystem token | `NTFS` (UTF-8 `4E 54 46 53`), `casefold()` → `ntfs` |
| Max component length | 255 |
| Buffer capacity used | 261 chars (`MAX_PATH + 1`) |
| Undersized buffer (2 chars) | fails, last error **24** (`ERROR_BAD_LENGTH`) |

**Sample size: one volume, one filesystem, one host.** On this NTFS volume a
261-character buffer succeeded and a 2-character buffer failed cleanly rather
than truncating. That is not a general API contract. Other filesystems remain
`UNVERIFIED`, and `GetVolumeInformationByHandleW` — the variant the design needs
— is `UNVERIFIED` because obtaining a directory handle is outside this slice.

## F. Exception and fail-fast behaviour

Four disposable children. The contrast case loads nothing: a read-only attribute
query on a path that cannot exist.

| Mode | Caught? | Exit | Type | `winerror` | `args` | Message head |
| --- | --- | --- | --- | ---: | ---: | --- |
| `RaiseException(0x20000001)` | yes | 0 | `OSError` | 536870913 | 5 | `[WinError 536870913] Windows Error 0x20000001` |
| `RaiseException(0xC0000005)` | yes | 0 | `OSError` | `None` | 1 | `exception: access violation reading 0x0…` |
| recoverable Win32, **no load** | yes | 0 | `FileNotFoundError` | **3** | 4 | `[WinError 3] 系統找不到指定的路徑。` |
| `RaiseFailFastException` | **no** | `0xC0000602` | — | — | — | terminated |

### What this run establishes

1. the specified **synthetic** codes raised through `RaiseException` were caught
   as ordinary Python exceptions under CPython 3.12.10 on build 26200;
2. the `RaiseFailFastException` child was **not** caught by that child's
   `except BaseException` and exited with code `0xC0000602`.

### What it does not establish

- that a genuine hardware access violation surfaces the same way;
- that `RaiseFailFastException` is uninterceptable in general — only that this
  child did not intercept it;
- that message text or `args` shape is a stable ABI rather than a CPython
  implementation detail;
- **that no safe structural classifier exists.** Revision 2 concluded exactly
  that and overreached. What the evidence supports is narrower and is stated
  below.

### Status of the discriminator proposed earlier

Revision 1 proposed: an `OSError` with no `winerror` and a 1-tuple `args` is an
SEH fault. This run neither establishes nor falsifies it.

The single recoverable case measured here — a failing `GetFileAttributesW` —
surfaces with `winerror = 3` and a 4-tuple, so it *is* distinguishable from the
raised access-violation shape. That is one sample and establishes nothing
general. Revision 3 reported a colliding case, but it came from a library-load
path that has been **removed from this program for allowlist compliance**, so it
is not evidence in this report and is not cited as such.

**This run did not establish a reliable classifier.** It did not search for one
either, and its absence here is not proof that none exists.

One datum does bear on the question independently: the contrast's message
arrived localised — `系統找不到指定的路徑。` — concrete evidence that message
text varies with locale and must never carry classification weight.

### Design consequence, stated conservatively

Because no reliable classifier was established, the boundary should derive its
errors only from values it read itself — an `NTSTATUS` return, an explicit
`GetLastError` after a documented failure — and should treat any *unknown*
exception escaping a ctypes call as a panic rather than translating it.
`RaiseFailFastException` is available for that path and was observed to
terminate this child at `0xC0000602`. This is a conservative default chosen
because classification was not established, not a proof that classification is
impossible.

## UNVERIFIED inventory

| Item | Reason |
| --- | --- |
| SDK header comparison for every type | no Windows SDK installed |
| arm64 sizes, alignments, offsets | no arm64 machine available |
| `GetVolumeInformationByHandleW` | needs a directory handle; outside this slice |
| Genuine (non-raised) access-violation surfacing | requires an invalid dereference; forbidden |
| Borrowed-source release behaviour | requires a use-after-free; forbidden |
| Filesystems other than NTFS | only the local volume was read |
| `FileIdInfo`, `FileDispositionInfoEx` availability | both need a file handle; outside this slice |
| Stability of message text or `args` shape | single build, single locale |
| Whether any safe structural classifier exists | not searched for |
| Whether a library-load failure collides with the SEH shape | the measurement was removed for allowlist compliance |

## Corrections this run forces on design revision 5

1. the write-loop buffer contract is unusable as written; restate as
   `from_buffer_copy` (retains nothing, owns its storage) or a borrow whose
   **wrapper** is held — noting that `from_buffer` retains a ctypes-constructed
   `memoryview` over the source, not the source object itself;
2. the `_pack_ = 8` justification is unsupported — the declarations agree on
   amd64, arm64 is unknown, and neither is confirmed against the SDK;
3. `NATIVE-INTEROP.md` §4.1 has a candidate Python mechanism,
   `RaiseFailFastException`, observed to terminate this child at `0xC0000602`;
4. the error mapping should translate only from values the boundary read itself
   and route unknown escaping exceptions to fail-fast, as a conservative default
   given that classification was not established;
5. no claim in the design may cite section B as confirming or refuting an SDK
   definition while section C is `UNVERIFIED`;
6. the admission record should name `RtlGetVersion` as its build source; the
   candidate `os_build_min == os_build_max` from this machine is `26200`;
7. `IO_STATUS_BLOCK_UNION` measures 8 bytes, aligned 8, both members at offset 0.

## Not admission evidence

A measurement is an input to admission, never admission itself. Admission still
requires the ADR, the next design revision, an independent review and an owner
promotion. Nothing here admits a platform, backend or disposition, and
`handle_boundary_available()` continues to return `False`.

Gate 3 remains `NON_SUCCESS`. M2, M3 and M4 remain blocked.
