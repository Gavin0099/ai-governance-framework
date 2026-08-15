# Gate 3 Native Directory-Handle Boundary Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-15

Base: `feat/gate3-historical-materialization@896bc64c006da4e40a6d5a7d8b32d462467d08f2`

Revision: 15 — fixes anonymity recognition, which revision 14 inferred from
nesting rather than from the declarator, so a named nested union was rejected as
an unmapped placeholder; and replaces two tests that asserted the right words
instead of the right behaviour — the archive is now proven unopened on a digest
mismatch, a digest-valid archive missing a closed entry is proven refused, and a
directory input is refused by the public entry point rather than by source
introspection.

Revision 14 — made the expected-layout artifact's provenance **verified
rather than declared**: the extractor now takes the `.nupkg`, checks its digest
before opening it, and reads a closed nine-entry inventory, where revision 13
accepted any header directory and stamped the official constants onto it. Also
closes the nested schema revision 13 left open — exact key sets for both ABI
tables, the exact header inventory, path components, and an exact
`package_source_url` grammar — and makes an unregistered anonymous placeholder
fail closed rather than pass through.

Revision 13 — closed the expected-layout artifact's extended `provenance`
schema, which revision 12 fixed at five keys while the extractor built against
it emits fourteen; fixes the canonical mapping for anonymous aggregate members,
without which the gate would reject `IO_STATUS_BLOCK` on a name rather than a
layout; requires the header paths to be canonical package entries plus the
package identity, so a committed artifact names its official source chain; and
requires the extractor to carry focused tests of its own.

Revision 12 — resolved the three findings raised against revision 11
(`fb76b082…`), all of them internal-consistency failures rather than new
questions: a paragraph left over from before owner ruling 8 still described the
§4.1 exception as unsought, four places still stated the diagnostic
unconditionally, and the expected-layout schema still permitted a boolean where
an integer is required while treating `extractor_sha256` as self-described
provenance.

Revision 11 applied **owner ruling 8**, the `NATIVE-INTEROP.md` §4.1
slice-specific exception, and fixed the `EXCEPTION_RECORD` calling contract.

No item is `OWNER_DECISION_REQUIRED`. The ADR follows this candidate passing
review, and native implementation remains unauthorized.

Revision 9 had resolved the findings against revision 8 (`3cc57930…`): the
`OutputDebugStringW` non-blocking claim, the expected-layout artifact's missing
authority anchor, the absent `PATH_INVALID` mapping, and `runtime_facts`
attributed entirely to the held base handle.

Revision 8 had resolved the findings against revision 7 (`0909de57…`): path
semantics in created-object names, contradictory manifest ordering, an unbounded
diagnostic, an undeclared `PVOID` and a circular SDK oracle.

Revision 7 had resolved the findings against revision 6 (`6d80eb8e…`): the
directory role's missing `FILE_WRITE_ATTRIBUTES`, layouts stated without
declarations, open canonicalization inputs, and an unbounded fail-fast
diagnostic; it also settled the two lifecycle decisions so the ADR records them
rather than making them.

Carried forward from revision 6, which was the first revision written against
**measured** platform behaviour rather than recollection: the seven owner
rulings and the approved ABI characterization
(`gate3-native-abi-characterization-20260815.md`, `47609250…`; program
`0af2cd86…`), and the four findings closed against revision 5 (`f099103d…`) —
admission's missing external authority anchor, downgraded panic-level failures,
an inexact ABI contract, and undefined runtime facts and admission bytes.

Scope: binding the creation and removal performed by historical evidence
materialization to directory handles, so that neither can be redirected outside
its intended root by a concurrent replacement of an ancestor directory.

Slice: **Windows only**, per owner ruling.

## Owner rulings incorporated

| # | Ruling | Where it lands |
| --- | --- | --- |
| 1 | Windows-only; `NATIVE-INTEROP.md` §5 two-platform exception granted **for this slice only**, not as a repo-general rule | slice statement below; POSIX section |
| 2 | Python loader deviation accepted, conditional on probe-before-load, `LOAD_LIBRARY_SEARCH_SYSTEM32`, a fixed library set and no caller-supplied name; **must be written into the ADR** | ABI contract; ADR obligations |
| 3 | `0cf5eaed…` partial-crash amendment accepted, replacing only the hard-crash row | amendment section |
| 4 | `NtCreateFile` accepted as the normative mechanism | Windows backend |
| 5 | Initial admission requires `os_build_min == os_build_max ==` the tested build; widening needs new native evidence and owner review; no automatic coverage of future cumulative updates | admission schema |
| 6 | `docs/adr/` and this slice's ADR authorized; the ADR must be complete and independently reviewed **before** native implementation is authorized | ADR obligations |
| 7 | `ADMISSION_OWNER = github:Gavin0099`, an identity label only; real authority comes from verifying an exact path and blob at a designated promotion commit | admission authority chain |
| 8 | **`NATIVE-INTEROP.md` §4.1 slice-specific exception granted**, quoted in full below | diagnostic section; compliance table; ADR obligations |

> **Owner ruling (8).** 本 Windows-only native handle-boundary slice 獲得
> `NATIVE-INTEROP.md §4.1` 的 slice-specific 例外。本切片不保證在 fail-fast 前
> 建立獨立、持久的 diagnostic record。若 `EXCEPTION_RECORD` 成功建構，封閉的
> stage/code ordinals 只被主張為伴隨 fail-fast 呼叫；若建構失敗，parameterless
> fallback 仍終止且不攜帶 diagnostic payload。此例外不得推廣至其他 native
> slices，並須記入本切片 ADR。

The exception is **slice-specific and non-generalising**: no other native slice
inherits it, and any future slice needing the same relief must obtain its own.

## Measured facts this revision is built on

Every row is from the approved characterization, not from this document's
recollection.

| Fact | Measured value | Consequence here |
| --- | --- | --- |
| `_pack_ = 8` vs unset, amd64 | identical for all nine types | `_pack_ = 8` is declared per §1.1, and the *equivalence claim* is dropped |
| arm64 layout | **`UNVERIFIED`** | arm64 must not be admitted without its own measurement |
| SDK header comparison | **`UNVERIFIED`** — no SDK on the measuring machine | no layout claim here confirms or refutes an SDK definition; verification is an implementation-review gate |
| `IO_STATUS_BLOCK_UNION` | 8 bytes, align 8, both members at offset 0 | recorded in the ABI contract |
| `FILE_DISPOSITION_INFO` under `c_ubyte` | 1 byte | declaration self-consistency only; the SDK's definition is still to be verified |
| `FILE_ATTRIBUTE_TAG_INFO` | align 4 | uniform `_pack_ = 8` is inert there; not described as if it were doing work |
| `addressof(memoryview)`, `from_buffer(bytes)`, `from_buffer(readonly memoryview)` | all rejected, `TypeError` | revision 5's write-loop buffer contract is unusable and is replaced |
| `from_buffer_copy` | `_objects is None`; address differs from a borrow of the same source | owns its storage |
| `from_buffer(bytearray)` | retains a **ctypes-constructed `memoryview`** whose `.obj` is the source | the *wrapper* must be held, and the retained object is not the source itself |
| `c_char_p(bytes)` | `_objects is` the bytes object | direct retention |
| `RaiseException(0xC0000005)` in a child | caught as an ordinary `OSError` | exceptions escaping ctypes must not be translated |
| `RaiseFailFastException` in a child | not caught by that child; exit `0xC0000602` | candidate §4.1 mechanism, on child-local evidence |
| Recoverable Win32 failure, no load | `winerror = 3`, 4-tuple, **localised message** | message text must never classify |
| Reliable SEH/Win32 classifier | **not established** | conservative panic default |
| `GetVolumeInformationW`, path-based | token `NTFS`; undersized buffer → `ERROR_BAD_LENGTH` | one volume, one host; not a general contract. The report used `casefold()`; this design specifies ASCII-lowercase instead — see canonicalization |
| `GetVolumeInformationByHandleW` | **`UNVERIFIED`** | still to be measured before admission |
| `RtlGetVersion` vs `sys.getwindowsversion()` | agreed at build 26200 | `RtlGetVersion` is the named source; 26200 is the candidate admitted build |

## Problem

`gate3_historical_materialize.py` creates and removes files by path, resolving
ancestors at the moment of each call. Exclusive creation settles the leaf name
only. A concurrent process replacing `root`, `a` or `a/b` with a junction
redirects everything that follows: bytes land elsewhere, and on the removal
side, somebody else's data is deleted. Measured on the target platform,
`os.supports_dir_fd` is empty, `O_NOFOLLOW` and `O_DIRECTORY` do not exist, and
a directory file descriptor cannot be opened at all — **there is no stdlib
construction that binds an ancestor on Windows.**

## Interim behaviour, landed and separately approved

`materialize()` and `cleanup()` refuse everywhere with
`HANDLE_BOUNDARY_UNAVAILABLE`. The path-based implementation survives only as
`_materialize_unbound` / `_cleanup_unbound`, reachable from its focused tests.
M2 is unusable, so M3 and M4 cannot proceed until this lands.

## The property being bought

**Every create and remove acts on an object this code opened, identified by
handle. No name is resolved after the object exists, except by a read-only
absence probe whose result is trusted in one direction only.**

### The absence probe

| Field | Value |
| --- | --- |
| function | `NtOpenFile`, relative to the held parent handle |
| `DesiredAccess` | `FILE_READ_ATTRIBUTES \| SYNCHRONIZE` |
| `ShareAccess` | `FILE_SHARE_READ \| FILE_SHARE_WRITE \| FILE_SHARE_DELETE` |
| `OpenOptions` | `FILE_OPEN_REPARSE_POINT \| FILE_SYNCHRONOUS_IO_NONALERT` |

Only `STATUS_OBJECT_NAME_NOT_FOUND` counts as absent. Success (handle closed
immediately), `STATUS_DELETE_PENDING`, `STATUS_ACCESS_DENIED`,
`STATUS_SHARING_VIOLATION` and anything else are **not absent** and yield
`CLEANUP_INCOMPLETE`. `FILE_SHARE_DELETE` appears here and nowhere else, so the
probe does not pin the name it asks about.

## Adapter surface

```text
DirectoryBoundary
    open_chain(absolute_base)        -> Anchor
    runtime_facts(anchor)            -> Facts    # from the HELD base handle
    probe(anchor)                    -> bool     # round trip anchored inside base
    create_directory(anchor, name)   -> Anchor   # atomic, handle-relative
    create_file(anchor, name, bytes) -> Leaf     # returns a HELD handle
    remove(held)                     -> None     # acts on the held handle only
    confirm_absent(parent, name)     -> None     # read-only probe above
    identity(held)                   -> str
    revalidate(held)                 -> None
    close(held)                      -> None
```

No operation mutates or removes by name. `base` must be absolute; symlinks and
reparse points anywhere in it are refused, never resolved; UNC and device paths
are out of scope and fail closed.

### Created-object name grammar — normative

Revision 7 asserted only that `ObjectName` carries no leading backslash. That is
not enough: with `RootDirectory` set, a name containing a separator, a `..`
segment, a stream specifier or a device name reopens the very path lookup this
boundary exists to remove. Every `name` reaching `create_directory`,
`create_file` or `confirm_absent` is validated against all of the following, and
a failure raises a closed `MaterializationError` with code `PATH_INVALID`
**before** any native call is made, so it is an ordinary recoverable result and
never reaches the fail-fast path:

| Rule | Rejected |
| --- | --- |
| exactly one component | any `/` or `\\` at any position — leading, embedded or trailing |
| character set | anything outside `[A-Za-z0-9._-]`, which also excludes `<`, `>`, `"`, `\\`, `|`, `?`, `*` and every control character |
| relative traversal | a name equal to `.` or `..` |
| stream and drive syntax | any `:` at any position — this blocks alternate data streams (`name:stream:$DATA`) and drive-relative forms |
| device names | `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, compared **case-insensitively**, both bare and with any extension (`nul.txt` is still the device) |
| trailing forms Windows silently strips | a name ending in `.` or U+0020 |
| empty or over-long | empty, or longer than 255 UTF-16 code units |

A repo-relative path from the implementation manifest is split on `/` and
**every** resulting component is validated by this same grammar, so the two
grammars cannot drift apart.

## Availability ordering

```text
1. platform probe            # OS, pointer width, machine — BEFORE any load
2. load ntdll and kernel32   # fixed names, System32 search only
3. open_chain(base)          # pins volume root … base
4. runtime_facts(anchor)     # four fields, four sources — see the table below
5. match_admission(facts)    # frozen record; refuse on any field mismatch
6. probe(anchor)             # create+remove one dir and one read-only file in base
7. proceed
```

Steps 5 and 6 are both required and neither substitutes for the other: the
record proves a human reviewed native evidence for this exact combination, the
probe proves the API works on this machine now. The zero-argument
`handle_boundary_available()` survives only as the interim gate's quick refuse.

**`runtime_facts` has four sources, not one.** Revision 8 attributed all of them
to the held base handle, which is true only of the filesystem:

| Fact | Source |
| --- | --- |
| `filesystem` | `GetVolumeInformationByHandleW` on the **held base handle** — never from the path |
| `os_build` | `RtlGetVersion`, the named source; not `GetVersionEx`, which is manifest-shimmed |
| `arch`, pointer width | the platform probe of step 1, before any load |
| `abi` | fixed for the running process; the admitted token is `64/win64/WinDLL` |

Each is compared against its own admission field, and a mismatch in any single
field refuses.

## Admission authority chain

Revision 5's pin verified only its own self-described metadata, so
`registry_sha256` could be rewritten together with the pin. Owner ruling 7 gives
the mechanism: authority comes from **an exact path and blob at a designated
promotion commit**, not from a string in a file.

| Link | Artifact | How it is obtained and bound |
| --- | --- | --- |
| 1 | constants in the **hashed backend**: `ADMISSION_PIN_PATH`, `ADMISSION_PIN_SCHEMA`, `ADMISSION_OWNER = "github:Gavin0099"`, `ADMISSION_PROMOTION_COMMIT` | reviewed, merged code. **No digest of anything in this chain appears here** |
| 2 | the owner admission pin | read as the **exact Git blob at `ADMISSION_PROMOTION_COMMIT`:`ADMISSION_PIN_PATH`** — never from the worktree. Parsed with **duplicate-key rejection**, as M1 established for a pin with no frozen whole-byte digest. Must carry the schema, the owner equal to `ADMISSION_OWNER`, state `SIGNED_AND_PROMOTED`, `registry_sha256`, and the closed backend path inventory |
| 3 | the admission registry | a **JSON data artifact**, digest-checked against `registry_sha256` **before parsing**, with duplicate-key rejection. **Never a Python module and never imported** — revision 5 made it a module, which would execute it before verifying it |
| 4 | each admission record | inside the verified registry; binds an implementation manifest digest |
| 5 | the implementation manifest | canonical serialization of `(path, sha256)` over **exactly** the closed inventory carried by the pin — not a directory listing, and not an inventory the backend supplies about itself |

**Ordering constraint, mandatory:** `ADMISSION_PROMOTION_COMMIT` must be a commit
that contains the pin and **does not contain the backend module**. Otherwise the
backend would name a commit whose tree contains the backend, and adding the
constant would change the commit it names. The pin is promoted first, in its own
commit; the backend is merged afterwards.

### Record schema

```text
schema                         = "gate3.native-handle-boundary.admission.v1"
token                          = "<platform>/<arch>/<backend>/<disposition>/<filesystem>"
threat_model                   = "windows-handle-pinned"
platform                       = win32
arch                           = amd64            # arm64 only with its own measurement
abi                            = "64/win64/WinDLL"
os_build_min                   = <the tested build>
os_build_max                   = <the same tested build>
build_source                   = "RtlGetVersion"
filesystem                     = ntfs | refs | …
backend_version                = <monotonic integer>
implementation_manifest_sha256 = <digest of the canonical manifest>
evidence_sha256                = <digest of the reviewed native-test evidence summary>
admitted_by                    = "github:Gavin0099"
admitted_at                    = <ISO date>
```

Per owner ruling 5, initial admission sets `os_build_min == os_build_max`. From
the approved characterization the candidate value is **26200**. Widening the
range requires new native evidence and owner review; nothing widens it
automatically. A manifest digest or `backend_version` mismatch invalidates the
record. `filesystem` is compared against the value derived from the held base
handle. No probe, test or code path may add a record.

### Canonical serialization — closed

Revision 6 named a shape without closing the inputs, so the same logical
manifest could still digest to different bytes. Everything below is normative,
and **any deviation is a closed failure, never normalised.**

**Encoding, both artifacts.** UTF-8, LF endings, no BOM, no trailing whitespace
on any line, no blank lines, exactly one final LF, one `name=value` line each.

**Two ordering rules, because one rule cannot serve both.** Revision 7 said every
field sorts bytewise by name and then showed a manifest with `schema` first and
numerically indexed entries. Those contradict each other: `entry` sorts before
`schema`, and `entry[10]` sorts before `entry[2]`. Settled:

| Artifact | Ordering |
| --- | --- |
| admission record | all fields sorted **bytewise ascending by field name**. It has no list-valued fields, so the rule is total |
| implementation manifest | **`schema` is the fixed first line.** Entries follow, sorted by the bytewise ascending order of the canonical path, then emitted with **numeric** indices `0..n-1`. General field-name sorting does **not** apply |

**Not JSON.** The manifest is a line-oriented text artifact, so no JSON encoding
choice — escaping, key order, separators, number formatting — can vary the
bytes. The registry remains JSON because it is a verified-by-digest data blob
whose bytes are fixed before parsing, and its parser rejects duplicate keys.

**Manifest entry lines.**

```text
schema=gate3.native-handle-boundary.implementation-manifest.v1
entry[0]=<path> <sha256>
entry[1]=<path> <sha256>
```

- exactly one U+0020 between `<path>` and `<sha256>`; no other whitespace;
- `<sha256>` is exactly 64 characters from `[0-9a-f]`, lowercase only;
- `entry[i]` indices are consecutive from `0`, rendered in decimal without
  padding.

**Path grammar.** Repo-relative, and validated before it is ever emitted or
compared:

- characters are restricted to `[A-Za-z0-9._/-]`; anything else is a closed
  failure, which excludes spaces, `\`, `:`, drive letters and every non-ASCII
  code point;
- `/` is the only separator; `\` is never accepted and never translated;
- must not begin with `/` and must not be empty;
- no segment may be empty, `.` or `..`;
- a path appearing twice is a closed failure;
- two paths that are byte-different but equal under ASCII lowercase are a
  **case collision** and are a closed failure — Windows filesystems are
  case-insensitive, so such an inventory is ambiguous about which file it names.

**Ordering.** Entries are sorted by the **bytewise ascending** order of the
UTF-8 path, never by a locale-aware or case-insensitive comparison.

**The `abi` token.** Fixed vocabulary, not a placeholder:
`<pointer-bits>/<calling-convention>/<loader>` where `pointer-bits` is `64`,
`calling-convention` is `win64` (the single x64 convention — `stdcall` exists
only on x86, which is not admitted), and `loader` is `WinDLL`. **The exact token
admitted by this slice is `64/win64/WinDLL`.**

**Filesystem token canonicalization.** The runtime value comes from
`GetVolumeInformationByHandleW` on the held base handle:

1. if any code point is outside ASCII (`>= U+0080`), fail closed — no
   transliteration is attempted;
2. map `A`–`Z` to `a`–`z` and change nothing else. `str.casefold()` is **not**
   used: it applies non-ASCII foldings such as `ß` → `ss`, so two different
   runtime tokens could canonicalize to one;
3. compare byte-equal against the record's `filesystem`, which must itself be
   lowercase ASCII.

The measured runtime token `NTFS` therefore canonicalizes to exactly `ntfs`.

## Windows backend

### `NtCreateFile`, per-role parameters

All eleven arguments are fixed per role. `FILE_DIRECTORY_FILE` and
`FILE_NON_DIRECTORY_FILE` never appear together; `FILE_ATTRIBUTE_NORMAL` never
appears with another attribute.

| Argument | Role 1: pinned ancestor | Role 2: directory we create | Role 3: file we create |
| --- | --- | --- | --- |
| `DesiredAccess` | `FILE_LIST_DIRECTORY \| SYNCHRONIZE` | `FILE_LIST_DIRECTORY \| SYNCHRONIZE \| DELETE \| FILE_WRITE_ATTRIBUTES` | `FILE_WRITE_DATA \| FILE_WRITE_ATTRIBUTES \| DELETE \| SYNCHRONIZE` |
| `RootDirectory` | previous chain handle (`NULL` at the volume root) | parent anchor | parent anchor |
| `Attributes` | `OBJ_CASE_INSENSITIVE` | `OBJ_CASE_INSENSITIVE` | `OBJ_CASE_INSENSITIVE` |
| `SecurityDescriptor` / `SecurityQoS` | `NULL` / `NULL` | `NULL` / `NULL` | `NULL` / `NULL` |
| `AllocationSize` | `NULL` | `NULL` | `NULL` |
| `FileAttributes` | `0` (ignored on open) | `FILE_ATTRIBUTE_NORMAL` | `FILE_ATTRIBUTE_READONLY` |
| `ShareAccess` | `FILE_SHARE_READ \| FILE_SHARE_WRITE` | `FILE_SHARE_READ \| FILE_SHARE_WRITE` | `FILE_SHARE_READ` |
| `CreateDisposition` | `FILE_OPEN` | `FILE_CREATE` | `FILE_CREATE` |
| `CreateOptions` | `FILE_DIRECTORY_FILE \| FILE_OPEN_REPARSE_POINT \| FILE_SYNCHRONOUS_IO_NONALERT` | `FILE_DIRECTORY_FILE \| FILE_SYNCHRONOUS_IO_NONALERT` | `FILE_NON_DIRECTORY_FILE \| FILE_SYNCHRONOUS_IO_NONALERT` |
| `EaBuffer` / `EaLength` | `NULL` / `0` | `NULL` / `0` | `NULL` / `0` |

Creating with `FILE_ATTRIBUTE_READONLY` while holding `FILE_WRITE_DATA` is
intentional: the attribute governs subsequent opens, the creating handle keeps
its granted access. `FILE_SHARE_DELETE` is omitted everywhere except the absence
probe. `DELETE` is requested only on objects this code creates.

`FILE_WRITE_ATTRIBUTES` on the **directory** role is new in this revision and
closes an inconsistency: revision 6 specified a deletion fallback that clears the
read-only attribute through `FileBasicInfo`, which needs that access, while the
directory role did not request it — the fallback could not have executed. The
alternative, dropping the attribute clear for directories on the grounds that we
create them `FILE_ATTRIBUTE_NORMAL`, was rejected: `FILE_SHARE_WRITE` is granted
on the pinned chain, so a directory acquiring the read-only attribute after
creation is a window the design leaves open rather than one it closes, and a
fallback that cannot run in that case is not a fallback.

### Chain, handles, identity

The walk starts at the volume root (`\??\C:\`), proceeds component by component
with role 1 relative to the previous handle, and holds every handle for the
tree's lifetime. Other processes keep read and write access to those directories
but cannot rename or delete them for the run — a real side effect on
user-owned directories, recorded rather than minimised.

The handle returned by `create_file` is **held until that leaf is removed**;
the leaf name is never resolved again after creation.

Identity is `GetFileInformationByHandleEx(h, FileIdInfo, …)` → `FILE_ID_INFO`
(64-bit `VolumeSerialNumber`, **128-bit** `FileId`). The 64-bit index from
`GetFileInformationByHandle` is **not** a fallback; a volume without
`FileIdInfo` is refused.

### Deletion and cleanup ordering

| Object | Preferred | Fallback |
| --- | --- | --- |
| file **and** directory | `FileDispositionInfoEx` with `DELETE \| POSIX_SEMANTICS \| IGNORE_READONLY_ATTRIBUTE` | `FileBasicInfo` setting `FILE_ATTRIBUTE_NORMAL`, then `FileDispositionInfo` with `DeleteFile = TRUE` |

Both act on the held handle. Availability is settled by the probe exercising the
disposition in use, never inferred from a version.

```text
for each leaf, deepest first:
    mark delete on the held leaf handle
    close that leaf handle
    confirm_absent(parent, name)
then for each created directory, deepest first:
    mark delete on the held directory handle
    close that directory handle
    confirm_absent(parent, name)
then close the pinned ancestor chain in reverse acquisition order
```

Reverse-order closing applies **only** to the borrowed ancestor chain. A
confirmation that is not `STATUS_OBJECT_NAME_NOT_FOUND` stops the sequence with
`CLEANUP_INCOMPLETE`; the parent is not attempted.

## Amendment to accepted design `0cf5eaed…` — accepted by the owner

Only the hard-crash row is replaced.

| | Accepted `0cf5eaed…` | Amended |
| --- | --- | --- |
| hard crash mid-run | nothing is deleted | process teardown closes handles, so an **already-marked** disposition completes; a partially removed tree can remain |
| next run finds a matching stale root | fails closed, reports local recovery required, deletes nothing | **unchanged** |
| automatic deletion or recovery of residue | never | **unchanged** |

## Error handling — no exception classification

The characterization measured a raised `EXCEPTION_ACCESS_VIOLATION` code being
caught as an ordinary `OSError`, and did **not** establish any reliable
structural classifier. It also observed that message text is localised. The
design therefore does not attempt classification:

- errors are derived **only** from values the boundary read itself: an
  `NTSTATUS` return mapped through `RtlNtStatusToDosError`, or an explicit
  `ctypes.get_last_error()` read immediately after a documented failure;
- **no exception escaping a ctypes call is ever translated** — with one
  explicitly bounded exclusion below. Such an exception is unexplained and routes
  to fail-fast via `RaiseFailFastException`, which was observed to terminate a
  child at `0xC0000602`;

**The load and bind phase is excluded, and the boundary between the two phases
is exact.** Steps 1 and 2 of the availability ordering — the platform probe, the
System32-only load of `ntdll` and `kernel32`, and the declaration of every
`argtypes`/`restype` — happen before any chain is opened, any handle is held or
any object exists. An exception there is **recoverable** and yields
`HANDLE_BOUNDARY_UNAVAILABLE`, consistent with the lifecycle decision below.
From the moment binding completes, the fail-fast rule applies without exception.
The phase is a property of where execution is, not of what the exception looks
like, so it cannot be used to smuggle a later failure into the recoverable
path;
- this is a conservative default chosen because classification was not
  established, not a claim that classification is impossible.

### Bounded diagnostic before fail-fast

`NATIVE-INTEROP.md` §4.1 requires diagnostic information to be recorded before
termination. Revision 6 routed to fail-fast without saying what is recorded,
where, or what happens if recording fails. Closed here:

| Question | Rule |
| --- | --- |
| surface | **none — there is no sink.** The diagnostic is carried inside the fail-fast exception record itself |
| mechanism | `RaiseFailFastException(&record, NULL, FAIL_FAST_GENERATE_EXCEPTION_ADDRESS)` — the full field contract is below |
| `<stage>` | one of the closed set `CHAIN`, `CREATE_DIRECTORY`, `CREATE_FILE`, `WRITE`, `IDENTITY`, `REVALIDATE`, `REMOVE`, `PROBE`, `ABSENCE_PROBE`, `CLOSE` |
| `<code>` | one of the closed `MaterializationError` codes, or `UNEXPECTED_EXCEPTION` |
| forbidden content | paths, handle values, buffer contents, `NTSTATUS` values, `GetLastError` values, exception messages, tracebacks — **nothing derived from the exception or the operands** |
| construction failure | possible, and dispositioned: building the record is pure in-memory formatting of two integers, but a `ctypes` failure or a missing ordinal is still a failure. On that path the parameterless fallback terminates and **the payload is absent** |
| control flow | building the record sits inside `try`, and `RaiseFailFastException` is called from the matching **`finally`**, with a parameterless fallback call if the record could not be built. Every path terminates. The diagnostic function returns nothing and **must not** yield a value any caller could branch on |
| what may be claimed | **conditional.** *If* the record is constructed, the two ordinals accompany the fail-fast call as inputs to that call. *If* construction fails, the parameterless fallback still terminates and carries **no** diagnostic payload. Whether any consumer preserves either outcome — a crash dump, WER, an attached debugger — is outside this design and is not claimed |

### The record's field contract

Revision 9 named only `ExceptionCode` and two `ExceptionInformation` slots. When
a non-`NULL` record is supplied, `ExceptionCode` **and** `ExceptionAddress` must
both be specified, and `dwFlags = 0` does not generate an address. Every field is
fixed here.

| Field | Value |
| --- | --- |
| `ExceptionCode` | `0xE3A70001`, fixed by this document and asserted as a literal in code. Bits 31–30 are `0b11` (error severity) and **bit 29 is set**, the customer bit, so the value cannot collide with any Microsoft-defined status. Bit 28 is `0` as reserved |
| `ExceptionFlags` | `EXCEPTION_NONCONTINUABLE` — a fail-fast is not resumable, and saying so is part of the record |
| `ExceptionRecord` | `NULL` — no chained record |
| `ExceptionAddress` | **non-`NULL`, always.** Set to the address of the `RaiseFailFastException` entry point, obtained as `cast(kernel32.RaiseFailFastException, c_void_p)`. `dwFlags` additionally carries `FAIL_FAST_GENERATE_EXCEPTION_ADDRESS`, whose documented effect is to set the exception address to the caller's return address — the more useful value. See the note below on which value survives |
| `NumberParameters` | `2` |
| `ExceptionInformation[0]` | stage ordinal |
| `ExceptionInformation[1]` | code ordinal |
| `ExceptionInformation[2..14]` | zero |
| `pContextRecord` | `NULL` |

**Why `ExceptionAddress` is not left `NULL`.** Revision 10 set it to `NULL` and
relied on the flag alone. The documented contract for supplying a non-`NULL`
record requires `ExceptionCode` **and** `ExceptionAddress` to be specified, so a
`NULL` there does not satisfy it whatever `dwFlags` says. Both are now set. Of
the two values, the flag's substitution is the meaningful one and the supplied
thunk address is what remains if no substitution occurs; the design does not
assert which of the two a given consumer will see, only that the field is never
`NULL` and never fabricated from unrelated data.

**Ordinals are frozen.** Both tables are assigned once and never renumbered; a
new stage or code appends at the next free value. Renumbering would silently
change the meaning of every previously captured record.

| Stage | Ordinal |
| --- | ---: |
| `CHAIN` | 1 |
| `CREATE_DIRECTORY` | 2 |
| `CREATE_FILE` | 3 |
| `WRITE` | 4 |
| `IDENTITY` | 5 |
| `REVALIDATE` | 6 |
| `REMOVE` | 7 |
| `PROBE` | 8 |
| `ABSENCE_PROBE` | 9 |
| `CLOSE` | 10 |

| Code | Ordinal |
| --- | ---: |
| `UNEXPECTED_EXCEPTION` | 1 |
| `MATERIALIZE_PATH_EXISTS` | 2 |
| `MATERIALIZE_WRITE_FAILED` | 3 |
| `PATH_IS_REPARSE_POINT` | 4 |
| `PATH_INVALID` | 5 |
| `ROOT_IDENTITY_UNAVAILABLE` | 6 |
| `ROOT_IDENTITY_CHANGED` | 7 |
| `CLEANUP_INCOMPLETE` | 8 |
| `CLOSE_FAILED` | 9 |
| `HANDLE_BOUNDARY_UNAVAILABLE` | 10 |

**Fallback, exactly.** If the record cannot be constructed — a `ctypes` failure
while building the structure, or an ordinal lookup that finds no entry — the
`finally` calls `RaiseFailFastException(NULL, NULL,
FAIL_FAST_GENERATE_EXCEPTION_ADDRESS)`. The process still terminates; the
diagnostic payload is simply absent. The fallback takes no arguments derived
from the failure, so it cannot itself fail on bad input, and it is never reached
by any path that could instead return to the caller.

`EXCEPTION_RECORD`'s field order matches the documented structure, and like every
other type it is bound by the SDK layout gate rather than by this document.

**Why revision 8's answer was wrong.** It chose `OutputDebugStringW` and asserted
that call cannot block on a stalled reader. That is false: the call raises an
`OUTPUT_DEBUG_STRING_EVENT`, and a debuggee thread waits for the debugger to
call `ContinueDebugEvent`, so an attached-but-stopped debugger can hold it
indefinitely — and then the `finally` is never reached. Revision 8 also claimed
both that the write could fail and that the line had been written, which cannot
both be true.

**Vocabulary, fixed.** The payload is never described with *emit*, *emitted* or
*recorded*. There is no write, so those words import a step that does not exist
and a durability this slice does not have. The only permitted statements are the
two conditional ones above: constructed → the payload accompanies the fail-fast
call; not constructed → the fallback terminates with the payload absent.

Carrying the diagnostic in the exception record removes the *sink*: there is no
reader, no buffer and no pre-fail-fast I/O of any kind, and the diagnostic
payload and the fail-fast exception are inputs to **the same API call**. It also
makes the content boundary structural rather than a rule — the payload is two
integers from closed sets, so a path, handle, status or message **cannot be
placed in it at all**.

**The claim stops there.** Revision 9 said "nothing can stall", which reached
past what is supportable: `RaiseFailFastException` itself may involve Windows
Error Reporting, an attached debugger or a JIT debugger, and no documented
guarantee says that phase terminates in bounded time. What this design supports
is narrower and is the whole of it:

> there is no independent pre-fail-fast diagnostic I/O or sink, and **when the
> record is successfully constructed** the diagnostic payload accompanies the
> fail-fast exception as an input to one call.

The conditional is load-bearing, not hedging: on the fallback path there is no
payload at all, so an unconditional "the diagnostic accompanies termination"
would be false exactly when something already went wrong. Nothing here claims
the OS termination path, a debugger or WER cannot stall, and per owner ruling 8
nothing claims an independent durable record exists.

**Why an exception was needed, and its boundary.** `NATIVE-INTEROP.md` §4.1
requires diagnostic information to be recorded before termination. This design
does not produce an independent durable record, and no sink that would produce
one can be added without reintroducing a path that may stall. **Owner ruling 8
granted a slice-specific §4.1 exception on exactly that basis.** It is granted,
not sought: nothing further is pending here. Its boundary is equally explicit —
the exception covers this Windows-only slice alone, does not generalise to any
other native slice, and must appear verbatim in this slice's ADR.

The last row is the point: a diagnostic hook that can report success or failure
is a recoverable path wearing a different name, and reintroducing one here would
undo the finding this whole section exists to answer.

### Two lifecycle semantics, settled here rather than in the ADR

Both were raised as ADR items. They are decided in the design so the ADR records
a decision rather than making one.

**A System32-only load that fails is recoverable, not a panic.** It is answered
before any chain is opened, any handle is held or any object exists — nothing is
half-done and there is nothing to be uncertain about. It yields
`HANDLE_BOUNDARY_UNAVAILABLE` and the caller refuses, exactly as an unadmitted
platform does.

**A failed `CloseHandle` never claims the handle was closed.** Ownership is
dropped so the value is never closed again, and that is all that is claimed. The
handle is *not* described as released; the OS reclaims it at process teardown.
Revision 6's "the handle is released on both paths" is withdrawn: dropping
ownership and releasing a resource are different statements, and only the first
is true.

The **public result** of a close failure is fixed rather than left to the
caller: during removal it is `CLEANUP_INCOMPLETE`, because a handle that would
not close may be exactly why a name still exists; while releasing the borrowed
ancestor chain after an otherwise successful run it is `CLOSE_FAILED`, a
distinct code so that a successful materialization is not reported as a failed
cleanup. Both appear in the mapping table. With a prior error pending, the close
failure is recorded and the prior error is what surfaces.

### Mapping

| Condition | Windows | Code |
| --- | --- | --- |
| name already taken | `STATUS_OBJECT_NAME_COLLISION` | `MATERIALIZE_PATH_EXISTS` |
| reparse point encountered | non-zero `ReparseTag` | `PATH_IS_REPARSE_POINT` |
| component unopenable | `ERROR_ACCESS_DENIED`, `ERROR_SHARING_VIOLATION` | `HANDLE_BOUNDARY_UNAVAILABLE` |
| component absent | `ERROR_PATH_NOT_FOUND`, `ERROR_FILE_NOT_FOUND` | `MATERIALIZE_WRITE_FAILED` |
| identity unsupported | `FileIdInfo` unsupported | `ROOT_IDENTITY_UNAVAILABLE` |
| held identity no longer matches | compare fails | `ROOT_IDENTITY_CHANGED` |
| handle invalid | `ERROR_INVALID_HANDLE` | `ROOT_IDENTITY_CHANGED` |
| write failed or made no progress | `WriteFile` false, or zero written | `MATERIALIZE_WRITE_FAILED` |
| directory not empty | `ERROR_DIR_NOT_EMPTY` | `CLEANUP_INCOMPLETE` |
| absence probe not name-not-found | any other status | `CLEANUP_INCOMPLETE` |
| both dispositions failed | `ERROR_ACCESS_DENIED` | `CLEANUP_INCOMPLETE` |
| `CloseHandle` failed **during removal**, no prior error | `CloseHandle` returns false | `CLEANUP_INCOMPLETE` |
| `CloseHandle` failed **while releasing the borrowed chain** after an otherwise successful run, no prior error | `CloseHandle` returns false | `CLOSE_FAILED` |
| `CloseHandle` failed with a prior error pending | — | the prior error; the close failure is recorded and never masks it |
| load, bind or platform probe failed | any | `HANDLE_BOUNDARY_UNAVAILABLE` |
| created-object name fails the grammar | no native call is made | `PATH_INVALID` |
| manifest path component fails the grammar | no native call is made | `PATH_INVALID` |
| expected-layout artifact digest mismatch, or unparseable, or duplicate keys | no native call is made | `HANDLE_BOUNDARY_UNAVAILABLE` |
| unknown **status**, chain or creation | any other | `MATERIALIZE_WRITE_FAILED` |
| unknown **status**, removal or cleanup | any other | `CLEANUP_INCOMPLETE` |
| unknown **status**, identity or revalidation | any other | `ROOT_IDENTITY_UNAVAILABLE` |
| **any exception escaping a ctypes call** | — | **fail-fast; not mapped** |

No native message, path, handle value, `NTSTATUS` or artifact content appears in
any error.

## Win32 ABI contract

Constants, structures and signatures are the design's intent. **Each is verified
against the official Windows SDK headers at implementation review** — the
characterization could not do this, since no SDK was installed on the measuring
machine, and that gate is therefore mandatory.

### Loading and types

```text
ntdll    = ctypes.WinDLL("ntdll.dll",    use_last_error=True,
                         winmode=LOAD_LIBRARY_SEARCH_SYSTEM32)
kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True,
                         winmode=LOAD_LIBRARY_SEARCH_SYSTEM32)

NTSTATUS = c_long        # SIGNED; success is status >= 0, never a truthiness test
HANDLE   = c_void_p      # never c_int
ACCESS_MASK = ULONG = DWORD = c_ulong ; USHORT = c_ushort ; BOOL = c_int
ULONG_PTR = c_size_t ; LARGE_INTEGER = c_longlong ; LPWSTR = c_wchar_p
PVOID     = c_void_p     # used by OBJECT_ATTRIBUTES and IO_STATUS_BLOCK_UNION
# ctypes names used directly and not aliased: Structure, Union, POINTER,
# c_ubyte, c_ulonglong, c_wchar
```

Per owner ruling 2 the loader controls are: platform probe (OS, pointer width,
machine) **before** any load; `LOAD_LIBRARY_SEARCH_SYSTEM32`; a fixed set of
exactly `ntdll.dll` and `kernel32.dll`; and no caller-supplied library name,
with no exception of any kind. The characterization demonstrated this control
working — both libraries resolved from `System32` and a name outside the set was
refused — and it goes into the ADR.

`argtypes`/`restype` are declared for every function before first call. Handles
are checked against `NULL` and `INVALID_HANDLE_VALUE`, closed with `CloseHandle`
only, never `NtClose`. `ctypes.get_last_error()` is read immediately.
`NtCreateFile` and `NtOpenFile` return `NTSTATUS` and do not set the last error.

### Signatures

```text
ntdll.NtCreateFile.restype  = NTSTATUS
ntdll.NtCreateFile.argtypes = [POINTER(HANDLE), ACCESS_MASK,
                               POINTER(OBJECT_ATTRIBUTES), POINTER(IO_STATUS_BLOCK),
                               POINTER(LARGE_INTEGER), ULONG, ULONG, ULONG, ULONG,
                               c_void_p, ULONG]
ntdll.NtOpenFile.restype    = NTSTATUS
ntdll.NtOpenFile.argtypes   = [POINTER(HANDLE), ACCESS_MASK,
                               POINTER(OBJECT_ATTRIBUTES), POINTER(IO_STATUS_BLOCK),
                               ULONG, ULONG]
ntdll.RtlNtStatusToDosError.restype  = ULONG
ntdll.RtlNtStatusToDosError.argtypes = [NTSTATUS]
ntdll.RtlGetVersion.restype  = NTSTATUS
ntdll.RtlGetVersion.argtypes = [POINTER(OSVERSIONINFOEXW)]

kernel32.CloseHandle.restype  = BOOL ; argtypes = [HANDLE]
kernel32.WriteFile.restype    = BOOL ; argtypes = [HANDLE, c_void_p, DWORD,
                                                   POINTER(DWORD), c_void_p]
kernel32.GetFileInformationByHandleEx.restype = BOOL
kernel32.GetFileInformationByHandleEx.argtypes = [HANDLE, c_int, c_void_p, DWORD]
kernel32.SetFileInformationByHandle.restype  = BOOL
kernel32.SetFileInformationByHandle.argtypes = [HANDLE, c_int, c_void_p, DWORD]
kernel32.GetVolumeInformationByHandleW.restype  = BOOL
kernel32.GetVolumeInformationByHandleW.argtypes = [HANDLE, LPWSTR, DWORD,
                                                   POINTER(DWORD), POINTER(DWORD),
                                                   POINTER(DWORD), LPWSTR, DWORD]
kernel32.RaiseFailFastException.restype  = None
kernel32.RaiseFailFastException.argtypes = [POINTER(EXCEPTION_RECORD), c_void_p,
                                            DWORD]
# No diagnostic sink is bound: the diagnostic travels in the fail-fast
# exception record, so there is no OutputDebugStringW, no file and no stream.
```

### Structures and unions

`_pack_ = 8` on every type, per `NATIVE-INTEROP.md` §1.1, which forbids relying
on inference. Revision 5 justified this as "equal to the SDK's natural
alignment"; **that justification is withdrawn** — the characterization showed
only that the two choices agree for these declarations on amd64.

The complete field list is normative. Revision 6 gave only the measured size,
alignment and offset table, which describes a layout without specifying the
declarations that produce it; a measurement of an unstated declaration is not an
ABI specification.

```text
class UNICODE_STRING(Structure):
    _pack_ = 8
    _fields_ = [("Length", USHORT), ("MaximumLength", USHORT), ("Buffer", LPWSTR)]
    # Length and MaximumLength are BYTE counts, not character counts

class OBJECT_ATTRIBUTES(Structure):
    _pack_ = 8
    _fields_ = [("Length", ULONG),
                ("RootDirectory", HANDLE),
                ("ObjectName", POINTER(UNICODE_STRING)),
                ("Attributes", ULONG),
                ("SecurityDescriptor", PVOID),
                ("SecurityQualityOfService", PVOID)]
    # Length is assigned sizeof(OBJECT_ATTRIBUTES) explicitly before every call

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
    _fields_ = [("DeleteFile", c_ubyte)]        # BOOLEAN, one byte

class FILE_DISPOSITION_INFO_EX(Structure):
    _pack_ = 8
    _fields_ = [("Flags", DWORD)]

class FILE_BASIC_INFO(Structure):
    _pack_ = 8
    _fields_ = [("CreationTime", LARGE_INTEGER),
                ("LastAccessTime", LARGE_INTEGER),
                ("LastWriteTime", LARGE_INTEGER),
                ("ChangeTime", LARGE_INTEGER),
                ("FileAttributes", DWORD)]

class EXCEPTION_RECORD(Structure):
    _pack_ = 8
    _fields_ = [("ExceptionCode", DWORD),
                ("ExceptionFlags", DWORD),
                ("ExceptionRecord", PVOID),
                ("ExceptionAddress", PVOID),
                ("NumberParameters", DWORD),
                ("ExceptionInformation", ULONG_PTR * 15)]
    # EXCEPTION_MAXIMUM_PARAMETERS is 15. Only the first two are ever set, and
    # both are ordinals from closed sets, so no path, handle, status or message
    # can be placed in this record at all.


class OSVERSIONINFOEXW(Structure):
    _pack_ = 8
    _fields_ = [("dwOSVersionInfoSize", ULONG),
                ("dwMajorVersion", ULONG),
                ("dwMinorVersion", ULONG),
                ("dwBuildNumber", ULONG),
                ("dwPlatformId", ULONG),
                ("szCSDVersion", c_wchar * 128),
                ("wServicePackMajor", USHORT),
                ("wServicePackMinor", USHORT),
                ("wSuiteMask", USHORT),
                ("wProductType", c_ubyte),
                ("wReserved", c_ubyte)]
    # dwOSVersionInfoSize MUST be set to sizeof(OSVERSIONINFOEXW) before
    # RtlGetVersion is called; the call is undefined otherwise.
```

Measured on amd64 (`UNVERIFIED` on arm64, `UNVERIFIED` against the SDK):

| Type | Kind | Size | Align | Offsets |
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
| `OSVERSIONINFOEXW` | structure | **not measured** | — | — |
| `EXCEPTION_RECORD` | structure | **not measured** | — | — |

`OSVERSIONINFOEXW` was used by the characterization but never declared in this
document and never measured, and `EXCEPTION_RECORD` is new in this revision and
likewise unmeasured. Both are in the SDK `sizeof`/`offsetof` gate below on the
same terms as every other type, and their absence from the measured table is
recorded rather than filled in from recollection.

`FILE_DISPOSITION_INFO.DeleteFile` is declared as a one-byte `BOOLEAN`. The
measurement shows that declaration is internally consistent; **it does not
confirm the SDK's definition**, and no claim here says a `BOOL` declaration is
wrong.

**SDK gate, mandatory at implementation review.** A contract test asserts, at
import, every `sizeof` and every `offsetof` for all eleven types above. A mismatch
is a closed failure at import and resolves in favour of the header. The
characterization could not run this gate — no SDK was installed on the measuring
machine — so nothing in this document substitutes for it.

**The oracle must not be the thing under test.** Expected sizes and offsets are
**not** computed from these ctypes declarations; that would compare the
declarations against themselves and pass whatever they happen to be.

| Element | Rule |
| --- | --- |
| artifact | `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3-native-expected-layout.json` |
| extractor | `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_native_expected_layout_extract.py`, with focused tests beside it |
| authority | two digest-bearing constants in the **hashed backend**: `EXPECTED_LAYOUT_PATH` and `EXPECTED_LAYOUT_SHA256` |
| load order | read raw bytes → **verify the digest against `EXPECTED_LAYOUT_SHA256`** → only then parse, with a duplicate-key-rejecting parser. Never parse first |
| contents | per type: `sizeof`, `alignment`, and every field's `offset` and `size`; plus provenance — SDK version, the header paths extracted from, the extraction method, and the extractor's own digest |
| closed inventory | **not** in the pin's inventory and **not** in the implementation manifest. Those cover backend *modules*; this is data, and its authority is the digest above |
| cycle check | the backend names the layout artifact's digest; the layout artifact contains nothing about the backend. The backend remains bound by the implementation manifest, so no cycle exists |

A test whose expected values move with the code under test is not a gate.

**The artifact's own schema is closed.** Without it, two implementations could
read the same anchored bytes and reach different verdicts.

| Element | Rule |
| --- | --- |
| schema token | `gate3.native-expected-layout.v1`, present as the top-level `schema` key; any other value is refused |
| top-level keys | exactly `schema`, `provenance`, `types` — no more, no fewer |
| `provenance` keys | exactly the fourteen below — no more, no fewer |
| `extractor_path` | `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_native_expected_layout_extract.py`, fixed here rather than left to a digest alone — a digest identifies bytes but does not say where to find or re-run them |

### `provenance` — the closed fourteen

Revision 12 named five keys. The extractor built against it emits more, and the
extra fields are not noise: they are the inputs a reviewer must see to judge the
oracle — the package it came from, the per-header digests, and the two type
tables that are the only values *not* derived from the headers. Widening is
therefore right, but "allow six more keys" is not a schema. Each is closed
below, on the same terms as everything else: exact key inventory, exact value
types, ranges, ordering, and unknown/duplicate keys refused at every level.

| Key | Type and constraint |
| --- | --- |
| `package_id` | exactly `Microsoft.Windows.SDK.CPP` |
| `package_version` | non-empty ASCII matching `[0-9]+(\.[0-9]+){1,3}` |
| `package_sha256` | 64 lowercase hex characters — the `.nupkg` digest |
| `package_source_url` | exactly `https://api.nuget.org/v3-flatcontainer/{lowercased package_id}/{package_version}/{lowercased package_id}.{package_version}.nupkg`. Not a prefix check: the whole string is derived from `package_id` and `package_version` and compared byte for byte, so a URL pointing somewhere else cannot satisfy it |
| `sdk_version` | the SDK **include-directory** version, distinct from `package_version`, matching `[0-9]+(\.[0-9]+){1,3}` |
| `extraction_method` | closed set: `headers-parsed`, `headers-preprocessed`, `vendor-published` |
| `measurement_class` | closed set: `computed-not-compiled`, `compiled`. Replaces revision 12's free-text `not_a_compiled_measurement`, which could not be checked |
| `extractor_path` | the fixed path above |
| `extractor_sha256` | 64 lowercase hex |
| `abi` | exactly the admitted token, `64/win64/WinDLL` |
| `pack` | integer, exactly `8`, matching `MAX_PACK` |
| `header_digests` | list of objects with **exactly** `path`, `bytes`, `sha256` and no other key; **sorted by `path` bytewise ascending**; paths unique; the path set must equal the closed nine-entry inventory below, neither more nor fewer; each `path` a canonical package entry beginning `c/Include/`, using `/` only, never absolute, never containing `\`, with **no component equal to `.`, `..` or empty**; `bytes` an integer in `1..16777216`; `sha256` 64 lowercase hex |
| `fundamental_type_table` | object whose key set is **exactly** the eighteen fundamental spellings; each value a two-element array `[size, alignment]` of integers; `size` in `1..65535`; `alignment` a power of two in `1..16`; keys sorted bytewise |
| `preprocessor_dependent_type_table` | object whose key set is **exactly** the ten preprocessor-dependent spellings; same value constraints and ordering |

Both tables are the ABI inputs the headers do not settle, so "some mapping of
strings to pairs" is not enough — an entry silently added or dropped changes
what the oracle computes. Their key sets are fixed, and a test holds them as
fixtures written independently of the extractor's constants.

**The closed header inventory** — exactly these nine entries, and the
`header_digests` path set must equal it:

```text
c/Include/10.0.26100.0/shared/basetsd.h
c/Include/10.0.26100.0/shared/minwindef.h
c/Include/10.0.26100.0/shared/ntdef.h
c/Include/10.0.26100.0/shared/windef.h
c/Include/10.0.26100.0/um/WinBase.h
c/Include/10.0.26100.0/um/fileapi.h
c/Include/10.0.26100.0/um/minwinbase.h
c/Include/10.0.26100.0/um/winnt.h
c/Include/10.0.26100.0/um/winternl.h
```

### Provenance is verified, not declared

Recording a package id, version and digest proves nothing if the extractor will
accept any directory of headers and stamp those constants onto the result. The
extractor therefore **takes the `.nupkg` itself**:

1. read the whole file and compute its SHA-256;
2. compare against the pinned `package_sha256` — **before the archive is
   opened**, so a substituted package is never even read;
3. open the archive and read exactly the nine closed entries above, by path;
4. refuse on a missing package, a digest mismatch, or any missing entry, each
   as `HANDLE_BOUNDARY_UNAVAILABLE`.

Nothing in the archive is executed; only those nine entries are extracted. A
directory-based input is not offered, because it would reintroduce exactly the
gap this closes.

**`header_paths` is removed.** Revision 12 carried both it and `header_digests`,
which duplicated the same list in two places and invited them to drift.
`header_digests` alone now carries the paths.

**Every numeric above is checked with `type(value) is int`**, per the rule
already stated, so a JSON boolean cannot pass as `1` or `0`.

### Anonymous aggregate members

The SDK spells the anonymous union inside `IO_STATUS_BLOCK` with a placeholder
macro name; the `ctypes` declaration under test names the same member `u`. The
gate compares field-name sequences exactly, so without a fixed mapping the two
would disagree on a member they both lay out identically — a false failure that
would look like an ABI defect.

**Canonical mapping, normative:** the SDK's `DUMMYUNIONNAME` maps to `u`. The
mapping is a closed table in the extractor, applied when the artifact is
written, and locked by a test; the emitted artifact must contain no occurrence
of `DUMMYUNIONNAME` anywhere.

Two properties the mapping must have, both testable:

- **anonymity is decided by the declarator, not by nesting.** A nested
  aggregate is anonymous when it has no declarator, or when its declarator is a
  placeholder matching `DUMMY(UNION|STRUCT)NAME\d*` — the SDK writes
  `union { ... } DUMMYUNIONNAME;` and this extractor does not preprocess, so it
  sees that token literally. `union { ... } named;` is an ordinary named member
  and survives untouched. An earlier revision marked *every* nested aggregate
  anonymous, so a named one was rejected as an unmapped placeholder;
- **an unregistered placeholder is a closed failure**, not a pass-through. A
  lookup that falls back to the original name would quietly make an unknown
  spelling the expected one, which is the opposite of a gate.
| `types` | an object keyed by type name; keys must equal the eleven declared types **exactly** — a missing or extra type is refused |
| each type | exactly `kind`, `size`, `alignment`, `fields`; `kind` is `structure` or `union` |
| each field | exactly `name`, `offset`, `size`, in declaration order, and the field-name sequence must equal that type's declared `_fields_` order exactly |
| value types | `size`, `alignment` and `offset` are checked with `type(value) is int` — **not** `isinstance`, because Python's `bool` is an `int` subclass and `true`/`false` would otherwise pass as `1`/`0`. Equivalently, the JSON node kind must be *number*, never *boolean*. `alignment` is a power of two in `1..16`; `size` and `offset` are in `0..65535`; strings are non-empty ASCII |
| unknown keys | **refused** at every level, never ignored |
| duplicate keys | **refused** by the parser, as with the pin and the registry |
| JSON encoding | UTF-8 without BOM; the top level is an object; no trailing bytes after it; `NaN`, `Infinity` and `-Infinity` are refused; every numeric is a JSON integer with no fractional part, no exponent, no leading `+`, and no leading zero other than `0` itself |
| artifact size | refused above 1 MiB, so a malformed or hostile artifact cannot make the gate parse unboundedly |
| `sdk_version` | non-empty ASCII matching `[0-9]+(\.[0-9]+){1,3}` |
| `header_paths` | a non-empty list of non-empty ASCII strings, each unique, in the order the extractor read them |
| `extraction_method` | one of the closed set `headers-preprocessed`, `headers-parsed`, `vendor-published` |
| `extractor_sha256` | exactly 64 lowercase hex characters |
| `fields` | a non-empty list; the field-name sequence equals that type's declared `_fields_` order exactly, and no name repeats |
| type coverage | a **bijection** with the declared types: every declared type appears exactly once, and every type present is declared. Neither a missing nor an extra entry is tolerated |
| comparison | **exact integer equality** on every `size`, `alignment` and `offset`. No tolerance, no "at least", no skipping a field the artifact happens to omit — an omission is already a refusal |
| extractor verification | `extractor_sha256` is **not** trusted as self-described provenance. At runtime the boundary reads the raw bytes at the fixed `extractor_path`, recomputes SHA-256, and compares. Order is fixed: read raw bytes → recompute → compare → only then treat the artifact as usable. The extractor is never imported or executed by this check; it is hashed as data |
| extractor verification failures | a missing or unreadable `extractor_path`, or a digest mismatch, is `HANDLE_BOUNDARY_UNAVAILABLE`, exactly as an artifact digest mismatch is |
| verdict | any refusal is `HANDLE_BOUNDARY_UNAVAILABLE`; the gate never proceeds on a partially understood artifact |

Lifetime rules: the `UNICODE_STRING`, its buffer and the `OBJECT_ATTRIBUTES` are
kept alive across the call. With `RootDirectory` set, `ObjectName` is a relative
single component that has passed the created-object name grammar above — which
rejects a leading, embedded or trailing separator, `.`, `..`, any `:`, a device
name and the trailing forms Windows strips — asserted in code.

### Writing bytes — corrected against measurement

Revision 5 held a `memoryview(payload)` and passed a pointer derived from it.
Measured: `addressof` rejects a `memoryview`, `from_buffer` rejects immutable
`bytes` and rejects a read-only `memoryview`. **That contract cannot work.** The
replacement, with the ownership property each choice actually carries:

| Choice | Property |
| --- | --- |
| `(c_char * n).from_buffer_copy(payload)` — **default** | `_objects is None`; owns its storage; no external keep-alive; costs one copy |
| `(c_char * n).from_buffer(bytearray)` | retains a **ctypes-constructed `memoryview`** whose `.obj` is the source; the **wrapper** must be held, not merely the source |

`from_buffer_copy` is the default precisely because its lifetime is
self-contained. The retained-`memoryview` detail is recorded because it is not
what an implementer would assume.

```text
buffer = (c_char * len(payload)).from_buffer_copy(payload)   # held for the loop
offset = 0
while offset < len(payload):
    chunk = min(len(payload) - offset, MAX_WRITE)     # MAX_WRITE <= 0x7FFFF000
    written = DWORD(0)
    if not WriteFile(handle, byref(buffer, offset), chunk, byref(written), None):
        -> MATERIALIZE_WRITE_FAILED
    if written.value == 0:
        -> MATERIALIZE_WRITE_FAILED                   # zero-progress guard
    offset += written.value
```

`byref(buffer, offset)` was measured to produce an address delta exactly equal
to the offset. The handle is `FILE_SYNCHRONOUS_IO_NONALERT`, so the file pointer
advances and no explicit offset management is needed.

### Handle ownership

Each `Anchor` and `Leaf` owns exactly one handle; ownership is never shared,
copied or handed out as a raw integer. `close()` calls `CloseHandle` once and
clears the stored handle **unconditionally, including on failure** — a handle
that failed to close must never be closed again. A close failure is recorded as
`CLOSE_FAILED`, never masks the original error, and **is not described as having
released the handle**; see the lifecycle semantics above. A second `close()` is a
no-op. Ownership is dropped by a context manager plus a `__del__` safety net.

## `NATIVE-INTEROP.md` compliance

| Rule | Status |
| --- | --- |
| §1.1 explicit packing | `_pack_ = 8` declared; layout asserted by contract test against SDK values at implementation review |
| §1.2 string encoding and lifetime | UTF-16 `LPWSTR`; `UNICODE_STRING`, its buffer and `OBJECT_ATTRIBUTES` explicitly kept alive; the kernel copies the name |
| §1.3 memory ownership | kernel allocates the handle, `CloseHandle` releases, ownership never transfers, no buffer needs a `FreeXXX` |
| §2.1 no raw pointer past the adapter | raw `c_void_p` never leaves the boundary module |
| §2.2 idempotent disposal with finalizer | context manager, idempotent `close()`, `__del__` safety net; a failed close drops ownership without claiming release |
| §3.1 explicit calling convention | `WinDLL` chosen deliberately; only amd64 admitted, where one convention exists |
| §3.2 probe before load | measured working; probe checks OS, pointer width, machine |
| §3.3 loading | **accepted deviation** per owner ruling 2, with the four compensating controls, demonstrated by the characterization; **goes into the ADR** |
| §4.1 Logic vs Panic | **mechanism resolved; recording requirement covered by a granted exception.** Resolved: `RaiseFailFastException` is the panic mechanism, observed to terminate a child at `0xC0000602`, and no exception escaping ctypes is ever wrapped as recoverable. The "record diagnostic info before terminating" requirement is **not met** and is covered by owner ruling 8's slice-specific exception, which does not generalise. This slice therefore claims no independent durable diagnostic record |
| §4.2 / §4.3 | no `ctypes` exception or raw `OSError` escapes; only closed codes leave the boundary |
| §5 testing | **accepted slice-limited exception** per owner ruling 1; two-platform integration testing does not apply to this Windows-only slice and the exception does not generalise |
| §6 ADR triggers | memory ownership strategy and ABI/calling convention both fire; ADR authorized by owner ruling 6 and required **before** implementation authorization |

## ADR obligations

Per owner ruling 6 the ADR must exist, be complete and be independently reviewed
before native implementation is authorized. It must record at least: the
`NtCreateFile` dependency and why the documented-API route cannot close the
creation window; the §3.3 loader deviation with its four compensating controls;
the memory-ownership strategy including that a failed `CloseHandle` drops
ownership without releasing the handle; the calling-convention decision and the
`64/win64/WinDLL` ABI token; the §5 slice-limited exception; the bounded diagnostic and its
no-recoverable-path rule; **owner ruling 8's §4.1 slice-specific exception,
quoted verbatim, with its non-generalisation stated explicitly**; that a System32-only load failure is
recoverable rather than a panic; and the admission authority chain with its
ordering constraint. This candidate does not write it, and per the review
sequence the ADR follows design approval so it cannot fossilise an undecided
ABI, canonicalization or panic semantic.

## State semantics

| Situation | Behaviour |
| --- | --- |
| reparse point at any ancestor | closed failure before any create or remove |
| held identity differs from capture | closed failure; nothing created, nothing removed |
| replacement attempt while pinned | prevented by the OS |
| absence probe not name-not-found | sequence stops; `CLEANUP_INCOMPLETE`; parent not attempted |
| hard crash | handles close on teardown; already-marked dispositions complete; residue may be partial; nothing auto-deleted next run |
| partial cleanup | root stays non-empty, root removal fails, residue reported; never a forced recursive delete |
| a name we did not create | never removed; no adapter operation could |
| exception escapes a ctypes call | fail-fast; never translated |

## Claim ceiling

The strongest claim is that **every create and remove acts on an object opened
by this code and identified by handle**, on an amd64 Windows volume matching an
admitted record and passing the runtime probe.

It does not establish: that the OS termination path, an attached debugger or
Windows Error Reporting cannot stall after `RaiseFailFastException` is called;
that any consumer preserves the diagnostic payload; that a diagnostic payload
exists at all on the fallback path, where by construction there is none; that
any independent durable diagnostic record is produced, which owner ruling 8
explicitly excepts this slice from; anything about arm64 or
POSIX; that the declared layouts
match the Windows SDK, which is `UNVERIFIED` until the implementation-review
gate; that any structural SEH classifier exists; that `RaiseFailFastException`
is uninterceptable in general, only that a measured child did not intercept it;
protection against a same-user adversary editing this module, the interpreter or
the evidence; protection against a principal privileged to force-close handles or
bypass DAC; that a crash leaves a pristine tree; that M2 is approved; or anything
about the consumed pair's result, which remains `NON_SUCCESS`.

## POSIX — specified, not admitted

`handle_boundary_available()` returns `False` on POSIX in this slice regardless
of what follows. The chain would be walked from `/` with
`O_RDONLY | O_DIRECTORY | O_NOFOLLOW`, descriptors held; files created
`O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW` at `0o400`; directories via
`mkdir(dir_fd=…)` at `0o700`. Two windows cannot be closed: `mkdirat` then
`openat` is not atomic, and there is no unlink-by-descriptor. A `0o700`
ownership contract bounds both to a same-uid or root adversary, which is weaker
than the Windows guarantee and does not satisfy the held-object requirement. Any
future POSIX record must carry `threat_model = "posix-permission-bounded"`.

## DONE for a Later Offline Implementation Tranche

`DONE = All creation and removal in historical materialization go through a
directory-boundary adapter whose remove operation takes a held handle and never
a name, with no remove-by-name operation on the surface; the materialization
module constructs no path for os.mkdir, os.open, os.unlink or os.rmdir; POSIX
returns HANDLE_BOUNDARY_UNAVAILABLE unconditionally; availability follows
platform probe, System32-only load of exactly ntdll and kernel32 with no
caller-supplied name, open_chain, runtime facts from the held base handle,
admission match and anchored probe, in that order; the Windows backend creates
every object with NtCreateFile using all eleven arguments fixed per role as
tabulated, with a relative single-component ObjectName asserted to carry no
leading backslash, pinning the ancestor chain from the volume root with
FILE_SHARE_DELETE omitted outside the absence probe and DELETE requested only on
objects it creates; it holds every created file handle until that leaf is
removed through that same handle; identity comes from FILE_ID_INFO with no
fallback; writes use from_buffer_copy held for the loop, byref offsets,
DWORD-bounded chunking, a zero-progress guard and short-write continuation;
files and directories are both deleted by FileDispositionInfoEx with POSIX
semantics and IGNORE_READONLY_ATTRIBUTE, falling back to a handle-bound
FileBasicInfo clear plus a one-byte-BOOLEAN FileDispositionInfo; cleanup marks,
closes and confirms absence per object deepest first, stopping at
CLEANUP_INCOMPLETE unless the probe returns STATUS_OBJECT_NAME_NOT_FOUND, with
the borrowed chain closed in reverse order only afterwards; close clears its
stored handle unconditionally including on failure and a second close is a
no-op; created-object names pass a normative single-component grammar rejecting
any separator, `.`, `..`, any colon, reserved device names, trailing dot or
space, empty and over-long names, with manifest paths split and each component
validated by that same grammar; errors derive only from NTSTATUS returns and
immediate GetLastError reads; an exception raised during the platform probe,
library load or symbol binding is recoverable as HANDLE_BOUNDARY_UNAVAILABLE
while any exception escaping a ctypes call after binding completes reaches
fail-fast carrying, when and only when the record is successfully constructed, a
diagnostic inside the fail-fast EXCEPTION_RECORD with ExceptionCode
0xE3A70001, EXCEPTION_NONCONTINUABLE, a NULL chained record, an
OS-generated ExceptionAddress via FAIL_FAST_GENERATE_EXCEPTION_ADDRESS, and
exactly two frozen ordinals in ExceptionInformation, with no independent
pre-fail-fast sink or I/O, reaching RaiseFailFastException from a finally and
with ExceptionAddress never NULL, falling back to the parameterless call if the
record cannot be built, and claiming only that the payload accompanies the
fail-fast call when the record was constructed and nothing at all when it was
not, under the slice-specific NATIVE-INTEROP.md §4.1 exception of owner ruling 8; a CloseHandle failure drops
ownership without claiming release and surfaces as CLEANUP_INCOMPLETE during
removal or CLOSE_FAILED while releasing the borrowed chain, and never masks a
prior error; every ctypes type, signature, structure and union
is declared with _pack_ = 8, including PVOID and OSVERSIONINFOEXW whose
dwOSVersionInfoSize is set before RtlGetVersion, and asserted by sizeof and
offsetof contract tests whose expected values come from a separately digested
expected-layout artifact extracted from the Windows SDK headers rather than from
the declarations under test, with NTSTATUS signed and success tested as
status >= 0; admission is anchored by an owner pin read as the exact Git blob at
a promotion commit that does not contain the backend, parsed with duplicate-key
rejection, naming a registry digest, where the registry is verified JSON data
that is never imported, its records bind an implementation manifest digest over
the closed inventory the pin carries, the record sorts every field bytewise by
name while the manifest instead fixes schema as its first line and emits entries
numerically indexed in canonical-path order, the abi token is exactly
64/win64/WinDLL, the filesystem token is folded ASCII-only and never by casefold,
os_build_min equals os_build_max equals the tested build with RtlGetVersion named
as the source, and no code path can add a record; the ADR required by NATIVE-INTEROP.md §6 exists and has been
independently reviewed; hard-crash residue is still never auto-deleted and
partial cleanup is still never escalated to a recursive delete; and every
retained manifest, pair-final digest, owner pin, source commit and pair identity
is byte-identical to today.`

This is a proposed later tranche, not current implementation authority.

## Focused Offline Evidence Plan

1. an injected fake drives every decision path deterministically: chain
   acquisition, atomic creation, removal by held handle, each absence-probe
   status, identity revalidation, reparse detection, short and zero-progress
   writes, chunked writes, read-only deletion for files and directories, handle
   invalidation, close failure, surviving name, crash, partial cleanup;
2. the adapter surface exposes no mutate-or-remove-by-name operation, asserted
   structurally;
3. POSIX refuses unconditionally, with the probe never reached;
4. the platform probe runs before any library load, and a name outside the fixed
   set is refused;
5. an ancestor replaced between two operations fails closed, with nothing
   created or removed outside the root;
6. a held object whose identity changes aborts before any removal, and the
   substitute's contents are proven intact;
7. a reparse point at the volume root, an intermediate ancestor and `base` each
   fail closed, tested separately;
8. a created file's handle is proven held: renaming or deleting it from another
   handle fails while we hold it;
9. `sizeof` and every `offsetof` match the **SDK header** values, asserted at
   import — the gate the characterization could not run;
10. a short write completes via the loop; a zero-progress write fails rather than
    spins; a payload exceeding the chunk bound is written in chunks;
11. a failed `CloseHandle` clears ownership and a second close is a no-op;
12. files and directories are each deleted through the preferred disposition and
    again through the fallback with the preferred one forced unavailable; with
    both failing, the object survives and `CLEANUP_INCOMPLETE` is reported;
13. cleanup ordering: a name surviving its probe stops the sequence and the
    parent removal is never attempted;
14. every mapped status produces its code; an exception injected from a ctypes
    call is proven to reach fail-fast and **not** to be translated;
15. no error rendering contains a path, handle value, `NTSTATUS` or content;
16. a relative `ObjectName` with a leading backslash is rejected in code;
17. `FileIdInfo` unavailable makes the backend unavailable rather than falling
    back;
18. the admission chain rejects, each separately: a pin read from the worktree
    instead of the promotion commit, a wrong pin path, wrong schema, wrong owner,
    unpromoted state, duplicate JSON keys, a registry digest mismatch, a registry
    supplied as an importable module, a manifest digest mismatch, a manifest
    inventory that does not match the pin's closed inventory, a build outside
    `os_build_min..os_build_max`, and a non-admitted filesystem;
19. the promotion commit is proven not to contain the backend module;
19a. manifest canonicalization rejects, each separately: a path with a
    disallowed character, a backslash, an absolute path, an empty segment, `.`,
    `..`, a duplicate path, and a pair of paths colliding under ASCII lowercase;
    and entry ordering is proven bytewise rather than locale- or
    case-insensitive;
19b. a filesystem token containing a non-ASCII code point is refused rather than
    transliterated, and `NTFS` is proven to canonicalize to exactly `ntfs`;
19c. on the record-carrying path the fail-fast sets every `EXCEPTION_RECORD`
    field to the tabulated value including `ExceptionCode 0xE3A70001`,
    `EXCEPTION_NONCONTINUABLE`, a `NULL` chained record and
    `NumberParameters = 2` with slots 2..14 zero, and carries only frozen
    ordinals; **no independent pre-fail-fast diagnostic I/O occurs**, asserted
    structurally; record construction raising is proven to reach the
    parameterless fallback with the payload absent; and the diagnostic path
    returns no value any caller could branch on;
19l. the stage and code ordinal tables are asserted against frozen literals, so
    a renumbering is a test failure rather than a silent change of meaning;
19n. `ExceptionAddress` is proven never `NULL` on the record-carrying path, and
    the fallback path is proven to pass no record at all and to carry no
    payload — the conditional claim is asserted in both directions;
19o. the expected-layout artifact is additionally rejected for: a BOM, trailing
    bytes after the top-level object, a non-object top level, `NaN` or
    `Infinity`, a fractional or exponent numeric, a leading-zero integer, a
    **boolean supplied where an integer is required** — proving the
    `type(value) is int` check rather than `isinstance` — an oversized artifact,
    a malformed `sdk_version`, an empty or duplicated `header_paths` entry, an
    `extraction_method` outside the closed set, a malformed `extractor_sha256`,
    an empty `fields` list, a repeated field name, and a types map that is not a
    bijection with the declared types;
19p. the extractor at `extractor_path` is proven to be read as raw bytes and
    hashed before the artifact is used, with a mismatched extractor and a
    missing extractor each yielding `HANDLE_BOUNDARY_UNAVAILABLE`, and the
    extractor proven never to be imported or executed by the check;
19q. the extractor has focused tests of its own, since it is a parser that
    produces authority and four real parsing defects were found while building
    it. They lock: the preprocessor-dependent typedef branches; a function
    parameter not being read as a declarator; directive lines not swallowing a
    following typedef; equivalent spellings distinguished from a real metric
    conflict; SAL annotations not read as function pointers; the anonymous-member
    canonical mapping; deterministic canonical header paths; independently
    written expected fixtures for all eleven types; and fail-closed behaviour on
    a missing header, an absent definition, an unknown typedef, an unknown
    constant and an empty aggregate;
19r. the fixtures are proven to have teeth by mutation: a changed offset, a
    reverted anonymous-member name and a non-canonical header path each fail;
19s. the extractor is proven to refuse a package whose digest does not match
    the pin, a package that does not exist, and a **digest-valid** archive
    missing one of the nine closed entries; the digest-mismatch case
    additionally proves `ZipFile` is never called, since an error-message
    assertion alone would still pass if the open were moved above the digest
    comparison; and a directory handed to the public `build()` is proven
    refused, rather than the ordering being checked by reading the source;
19t. parsed through `parse_fields`, a named nested union keeps its name, a
    placeholder declarator is recognised as anonymous and maps, and an
    unregistered placeholder spelling raises; the declarator-based recognition
    rule is asserted directly for the empty, placeholder and named cases;
19u. the package digest, source URL, SDK version, the nine entry paths, the
    per-header digests and both ABI input tables are asserted against fixtures
    written independently of the extractor's constants, so editing a constant
    and the artifact together still fails;
19m. the expected-layout artifact is rejected, each separately, for: a wrong
    schema token, a missing or extra top-level key, a missing or extra
    `provenance` key, a missing or extra type, a type whose field-name sequence
    differs from its declared `_fields_` order, a non-integer or out-of-range
    numeric, an unknown key at any level, and a duplicate key — each yielding
    `HANDLE_BOUNDARY_UNAVAILABLE`;
19d. a failed System32-only load yields `HANDLE_BOUNDARY_UNAVAILABLE` rather
    than terminating, and a failed `CloseHandle` is proven not to be reported as
    a released handle;
19e. the created-object name grammar rejects, each separately: an embedded `/`,
    an embedded backslash, a trailing separator, `.`, `..`, a name containing
    `:`, an alternate-data-stream form, each reserved device name bare and with
    an extension, a name ending in `.` or a space, an empty name, and a name
    over 255 UTF-16 code units; and a manifest path is proven to be split and
    validated component by component under this same grammar;
19f. manifest emission is proven to place `schema` first and to index entries
    numerically `0..n-1` in canonical-path order, with a ten-entry case proving
    `entry[10]` follows `entry[9]` rather than sorting near `entry[1]`;
19g. the fail-fast path terminates even when record construction raises,
    proving the `finally` placement; and the document is asserted to contain no
    use of *emit*, *emitted* or *recorded* to describe the payload, so the
    conditional wording cannot drift back;
19h. the SDK expected-layout artifact is proven to be an independent input: a
    deliberately wrong ctypes declaration fails the gate, which a self-derived
    oracle could not detect; the artifact is proven to be digest-verified
    **before** parsing, to reject duplicate keys, and to yield
    `HANDLE_BOUNDARY_UNAVAILABLE` on a digest mismatch;
19j. a name failing the grammar and a manifest component failing the grammar
    each yield `PATH_INVALID` with no native call made, proven by asserting the
    native entry points were never reached;
19k. each `runtime_facts` field is proven to come from its own source, and a
    mismatch in any single field is proven to refuse;
19i. an exception raised during load or bind yields
    `HANDLE_BOUNDARY_UNAVAILABLE`, while the same exception raised after binding
    completes is proven to reach fail-fast;
20. the canonical serialization round-trips to a stable digest, and any deviation
    fails closed rather than normalising;
21. `GetVolumeInformationByHandleW` behaviour is measured before admission — it
    is `UNVERIFIED` today;
22. real-junction tests execute on Windows and are named in the evidence summary;
    any that cannot run are listed as unverified;
23. the M2 findings already closed still hold through the adapter.

## Affected Surfaces if Later Implemented

- one native boundary module and its test;
- one admission registry **data artifact** and one owner admission pin artifact;
- the SDK expected-layout artifact, the extractor that produces it, and its
  focused tests;
- `gate3_historical_materialize.py` and `test_gate3_historical_materialize.py`;
- `docs/adr/` and this slice's ADR;
- an accepted amendment to `0cf5eaed…`.

No retained manifest, published pair artifact, owner pin for the pair, `PLAN.md`
entry, memory file or evidence path changes. **A change to any retained artifact
means this design chose wrongly and must be re-reviewed, not patched.**

## Review Questions

1. Is the closed canonicalization — line-oriented manifest, restricted path
   grammar, bytewise ordering, case-collision refusal, the fixed
   `64/win64/WinDLL` token and ASCII-only filesystem folding — sufficient to make
   the digest inputs unambiguous?
2. **Settled by owner ruling 8** — a slice-specific §4.1 exception, on the
   record that no independent durable diagnostic exists. Retained here so the
   question is visibly closed rather than dropped. Reviewers should confirm the
   exception is reproduced verbatim in the ADR and is nowhere described as
   generalising.
3. Is the admission chain accepted now that authority comes from an exact blob
   at a promotion commit, the registry is verified data rather than an imported
   module, and the closed inventory is carried by the pin?
4. Is the ordering constraint — the promotion commit must not contain the
   backend module — workable in the intended merge sequence?
5. `os_build_min == os_build_max == 26200` means the next cumulative update
   expires admission. Confirmed as intended per ruling 5?
6. Is "no exception escaping ctypes is ever translated, all such route to
   fail-fast" acceptable, given it converts an unexplained fault into process
   termination inside a verification run?
7. Does the interim refusal need a bounded lifetime — a point at which M2 being
   unusable is itself escalated?

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, historical code execution, staging, commit, push, MR, merge, manifest
update, owner-pin update, ADR creation or promotion. M2 remains
`CHANGES_REQUESTED` and must not be submitted. B-1 implementation stays paused,
Group C stays on hold, and M3 is not started. Gate 3 remains `NON_SUCCESS`.
