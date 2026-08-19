# ADR-0001 — Gate 3 Native Directory-Handle Boundary (Windows-only slice)

Status: **Proposed** — awaiting independent review. Native implementation
remains unauthorized until this ADR passes that review.

Date: 2026-08-15

Slice: Gate 3 historical evidence materialization, native directory-handle
boundary, **Windows only**

Design candidate this ADR records decisions for:
`docs/governance/gate3-native-handle-boundary-design-candidate-20260815.md`,
revision 12, SHA-256
`4cbfda68947f8b066244af34c08093ee0b0a374ce74639865a304e899557c528` (APPROVED)

Measurement evidence relied on:
`artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3-native-abi-characterization-20260815.md`,
SHA-256 `476092508db8d93d94d03d83e1b62adcea57c4a219b0f879c524fedaa92dcd69`
(APPROVED); program SHA-256
`0af2cd866dc57c8387c4527d84a857ee005598558c5cbe7dac6ed5ce92b6fd22`

## Conflict check — `ARCHITECTURE.md` §6.2

Performed before writing this record, as §6.2 requires and as its closing line
makes a governance failure to omit.

| Step | Result |
| --- | --- |
| 1. related titles in `docs/adr/` | **none — the directory did not exist.** A repository-wide search for any ADR-shaped document found none |
| 2. conflicts found | none are possible; there is no prior architecture decision record to conflict with |
| 3. supersession or escalation | neither applies; nothing is superseded |
| 4. links to related ADRs | none exist yet. This is ADR-0001 and later native ADRs should link back to it |

`docs/adr/` is created by this record, under the authority of owner ruling 6.

## Triggers — `ARCHITECTURE.md` §6.1 and `NATIVE-INTEROP.md` §6

| Trigger | Fires? |
| --- | --- |
| memory ownership strategy | **yes** — handle ownership, close semantics |
| cross-platform loading strategy | **yes** — System32-only loading, Windows-only slice |
| ABI or calling convention | **yes** — `ctypes` layouts, `64/win64/WinDLL` |
| boundary partitioning | yes — the adapter replaces path-based filesystem calls |
| long-lived interface placement | no |
| `LibraryImport` vs `DllImport` | not applicable — Python, not C# |

## Context

`gate3_historical_materialize.py` created and removed filesystem objects by
path. Every such call resolves its ancestors at the moment of the call, so a
concurrent process replacing an ancestor directory with a junction redirects
what follows — writing this experiment's bytes outside its root, and on the
removal side deleting data belonging to someone else. The consequence reaching
third-party data is what made a native boundary worth its cost rather than a
documented limitation.

Measured on the target platform (CPython 3.12.10, Windows 11 build 26200):

```
os.supports_dir_fd: []
os.O_NOFOLLOW:      False
os.O_DIRECTORY:     False
os.open(<a directory>, os.O_RDONLY) -> PermissionError [Errno 13]
```

**No stdlib construction binds an ancestor on Windows.** POSIX has `dir_fd`;
Windows does not expose it, so the boundary requires native calls.

An interim state was landed and separately approved: both public entry points
refuse with `HANDLE_BOUNDARY_UNAVAILABLE`, so the path-based implementation is
unreachable in production while this boundary is designed. M2 is therefore
unusable and M3/M4 cannot proceed until the boundary lands.

## Decisions

### D1 — `NtCreateFile` is the normative creation mechanism

`CreateDirectoryW` followed by a separate handle acquisition leaves a window in
which an ordinary non-reparse directory can be substituted; it passes every
attribute and reparse check, and there is no prior identity to compare it
against, so **no signal fires**. `NtCreateFile` creates the object and returns
its handle in one operation, relative to a parent handle via
`OBJECT_ATTRIBUTES.RootDirectory`.

Accepted trade: a dependency on a semi-documented NT entry point, taken because
the documented-API route provably cannot close the window.

### D2 — the slice is Windows-only

POSIX returns `HANDLE_BOUNDARY_UNAVAILABLE` unconditionally. POSIX has no
atomic create-and-return-descriptor and no unlink-by-descriptor, so it cannot
satisfy the design's held-object requirement; a weaker POSIX backend admitted
alongside would have made a single claim cover two different guarantees. POSIX
semantics are specified in the design for a separate later slice and are not
admitted here.

### D3 — cross-platform loading strategy

`NATIVE-INTEROP.md` §3.3 prefers `LibraryImport` and
`NativeLibrary.SetDllImportResolver`, which have no Python equivalent. The
deviation is accepted with four compensating controls, all mandatory:

1. a platform probe — OS, pointer width, machine — **before** any library load;
2. `winmode=LOAD_LIBRARY_SEARCH_SYSTEM32`, so the search never leaves the
   system directory and DLL search-order hijacking does not apply;
3. a fixed library set of exactly `ntdll.dll` and `kernel32.dll`, with **no
   exception of any kind** — an earlier revision carved one out for a
   deliberately absent library and the carve-out was deleted, not re-described;
4. no caller-supplied library name.

The characterization demonstrated the control working: both libraries resolved
from `System32` and a name outside the set was refused.

A load or bind failure is **recoverable**, not a panic: it is answered before
any chain is opened, any handle held or any object created, so nothing is
half-done. It yields `HANDLE_BOUNDARY_UNAVAILABLE`.

### D4 — memory and handle ownership strategy

The kernel allocates the handle; `CloseHandle` releases it; ownership never
transfers; no buffer crosses the boundary needing a `FreeXXX`. Each `Anchor`
and `Leaf` owns exactly one handle, never shared, copied or handed out as a raw
integer. Ownership is dropped by a context manager plus a `__del__` safety net.

**A failed `CloseHandle` drops ownership without claiming the handle was
released.** The value is never closed again; the OS reclaims it at process
teardown. Its public result is fixed: `CLEANUP_INCOMPLETE` during removal,
`CLOSE_FAILED` while releasing the borrowed ancestor chain after an otherwise
successful run, and with a prior error pending the prior error surfaces while
the close failure is recorded.

Write buffers follow the measured semantics: `from_buffer_copy` is the default
because it owns its storage and retains nothing; a borrow requires the
**wrapper** to be held, and `from_buffer` retains a ctypes-constructed
`memoryview` over the source rather than the source itself.

### D5 — ABI and calling convention

`ctypes.WinDLL` is chosen deliberately; only amd64 is admitted, where a single
convention exists. The admitted ABI token is exactly **`64/win64/WinDLL`**.

`_pack_ = 8` is declared on every structure and union, per `NATIVE-INTEROP.md`
§1.1, which forbids relying on inference. The characterization measured that
`_pack_ = 8` and leaving it unset produce identical layouts for these
declarations on amd64; **it did not verify them against the Windows SDK**, and
no claim in the design or here says otherwise.

The SDK `sizeof`/`offsetof` gate is mandatory at implementation review, and its
oracle must not be the thing under test: expected values come from a separately
digested expected-layout artifact extracted from the official headers, whose
extractor is itself read as raw bytes and hashed before use and is never
imported or executed.

`arm64` is **`UNVERIFIED`** and must not be admitted without its own
measurement.

### D6 — diagnostic before fail-fast, and the §4.1 exception

No exception escaping a `ctypes` call is translated. The characterization
measured a raised `EXCEPTION_ACCESS_VIOLATION` code being caught as an ordinary
`OSError`, and established **no** reliable structural classifier; it also
observed that message text is localised. Errors are therefore derived only from
values the boundary read itself, and an unexplained escaping exception routes to
`RaiseFailFastException`. The load and bind phase is excluded and remains
recoverable.

The diagnostic is carried inside the fail-fast `EXCEPTION_RECORD` — two frozen
ordinals in `ExceptionInformation` — so there is no sink, no pre-fail-fast I/O
and nothing that can stall on a reader. The claim is conditional and stays
conditional: **if** the record is constructed, the payload accompanies the
fail-fast call; **if** construction fails, the parameterless fallback still
terminates and the payload is absent. Nothing claims the OS termination path, a
debugger or Windows Error Reporting cannot stall.

That does not produce an independent durable record, which `NATIVE-INTEROP.md`
§4.1 requires. Owner ruling 8 granted a slice-specific exception on exactly that
basis; it is reproduced verbatim below and **does not generalise**.

### D7 — admission authority chain

Authority comes from verifying an exact path and blob at a designated promotion
commit, never from a string in a file. Digest-free constants in the hashed
backend name the pin; the pin is read as the exact Git blob at
`ADMISSION_PROMOTION_COMMIT`, parsed with duplicate-key rejection, and names the
registry digest; the registry is verified JSON **data** that is never imported;
its records bind an implementation manifest digest over the closed inventory the
pin carries.

**Ordering constraint, mandatory:** the promotion commit must contain the pin
and **must not contain the backend module**, or the backend would name a commit
whose tree contains the backend and the constant would change what it names.

Initial admission sets `os_build_min == os_build_max ==` the tested build
(candidate value `26200`), with `RtlGetVersion` named as the build source.

### D8 — testing exception

`NATIVE-INTEROP.md` §5 requires L2 integration tests on two platforms. This
slice is single-platform by owner ruling 1, so the requirement cannot be met.
The exception is **slice-limited** and does not become a repo-general rule.

### D9 — amendment to accepted design `0cf5eaed…`

Only the hard-crash row changes: process teardown closes handles, so an
already-marked disposition completes and a partially removed tree can remain.
The stale-root rules are unchanged — a matching stale root still fails closed
and reports that local recovery is required, and nothing is ever auto-deleted or
auto-recovered.

## Owner rulings, verbatim

Reproduced exactly as issued. Where a ruling was issued in Traditional Chinese
it is not translated here, because a translation is a paraphrase and this record
is the authority a later reader will rely on.

> **1. 接受 Windows-only例外**
> 本切片只支援Windows；POSIX無條件`HANDLE_BOUNDARY_UNAVAILABLE`。同意對
> `NATIVE-INTEROP §5`作本切片限定例外，不擴張成repo通則。

> **2. 接受Python loader偏離**
> 以platform probe先於load、`LOAD_LIBRARY_SEARCH_SYSTEM32`、固定允許的system
> libraries及禁止caller supplied library name作補償控制。此偏離必須寫入ADR。

> **3. 接受`0cf5eaed…` partial-crash amendment**
> 僅取代hard-crash「nothing is deleted」一列：process teardown可能完成部分
> pending disposition。其他stale-root與不得自動recover/delete規則不變。

> **4. 接受`NtCreateFile`依賴**
> 作為Windows backend關閉create→open窗口的normative mechanism。

> **5. Admission expiry不採major-release粗粒度**
> 初始admission必須`os_build_min == os_build_max == 實際測試build`。日後擴張
> build range需新的native evidence與owner review；不得自動涵蓋future cumulative
> updates。

> **6. 授權建立`docs/adr/`與本切片ADR**
> ADR必須在native implementation授權前完成並獨立review。

> **7. 指定`ADMISSION_OWNER = github:Gavin0099`**
> 此token只是identity label；真正authority必須來自指定promotion commit內exact
> path/blob的驗證，不能靠字串本身。

> **8. `NATIVE-INTEROP.md §4.1` slice-specific exception**
> 本 Windows-only native handle-boundary slice 獲得 `NATIVE-INTEROP.md §4.1` 的
> slice-specific 例外。本切片不保證在 fail-fast 前建立獨立、持久的 diagnostic
> record。若 `EXCEPTION_RECORD` 成功建構，封閉的 stage/code ordinals 只被主張為
> 伴隨 fail-fast 呼叫；若建構失敗，parameterless fallback 仍終止且不攜帶
> diagnostic payload。此例外不得推廣至其他 native slices，並須記入本切片 ADR。

## Deviation register

Every deviation is **slice-specific**. None generalises, and any future native
slice needing the same relief must obtain its own ruling.

| Rule | Deviation | Compensating control | Authority |
| --- | --- | --- | --- |
| `NATIVE-INTEROP.md` §3.3 | `LibraryImport` / `SetDllImportResolver` unavailable in Python | probe before load, `LOAD_LIBRARY_SEARCH_SYSTEM32`, fixed two-library set, no caller-supplied name | owner ruling 2 |
| `NATIVE-INTEROP.md` §4.1 | no independent durable diagnostic record | payload carried in the fail-fast exception record when constructible; no pre-fail-fast I/O; conditional claim | owner ruling 8 |
| `NATIVE-INTEROP.md` §5 | no two-platform integration testing | single-platform slice by ruling; POSIX refuses unconditionally | owner ruling 1 |
| accepted design `0cf5eaed…` | hard-crash row replaced | all other stale-root rules unchanged; nothing auto-deleted | owner ruling 3 |

## Consequences

**Gained.** Creation and removal act on objects this code opened, identified by
handle, on an admitted amd64 Windows volume passing the runtime probe. Names are
never resolved after an object exists, except by a read-only absence probe whose
result is trusted only for `STATUS_OBJECT_NAME_NOT_FOUND`.

**Cost.** A native surface — NT and Win32 bindings, handle lifetimes, error
mapping — that must be maintained and re-reviewed. Pinning the ancestor chain
blocks rename and delete of user-owned directories for a run's duration. Every
Windows cumulative update expires admission until re-admitted, by ruling 5.

**Not established, and must not be read as established:**

- the declared layouts match the Windows SDK — `UNVERIFIED`, and the gate that
  would settle it runs at implementation review;
- `GetVolumeInformationByHandleW` behaviour — `UNVERIFIED`, and it must be
  measured before admission;
- arm64 anything;
- that any structural SEH classifier exists;
- that `RaiseFailFastException` is uninterceptable in general — only that one
  measured child did not intercept it;
- that any consumer preserves the diagnostic payload, or that one exists at all
  on the fallback path;
- protection against a same-user adversary editing this module, the interpreter
  or the evidence, or a principal privileged to force-close handles or bypass
  DAC;
- that a crash leaves a pristine tree.

**Risk.** High, and inherent to native ABI work and process termination rather
than incidental to these decisions.

## Authorization boundary

This ADR authorizes no implementation, credentials, preflight, live execution,
historical code execution, staging, commit, push, MR, merge, manifest update,
owner-pin update or promotion. Native implementation requires a separate
authorization after this ADR passes independent review. M2 remains
`CHANGES_REQUESTED` and unusable behind the interim refusal; B-1 implementation
stays paused; Group C stays on hold; M3 is not started. Gate 3 remains
`NON_SUCCESS`.
