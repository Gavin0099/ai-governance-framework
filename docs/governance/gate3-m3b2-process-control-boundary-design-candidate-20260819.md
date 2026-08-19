# Gate 3 M3-b-2 — The Process-Control Boundary

Status: design-only candidate; not approved, not implemented, and not execution
authority. No process was started to write this, no job object was created, no
native symbol was bound and nothing was compiled. Every ABI statement below is
either derived from an artifact named here or is explicitly marked as *not yet
measured*.

Date: 2026-08-19

Revision: 1 — the design slice `BLOCKED-3` of the M3-b design requires. It
exists because naming Win32 calls is not specifying them, and because
`NATIVE-INTEROP.md` requires layouts, ownership, unwind and error translation
before a native surface is implemented.

---

## What this document closes, and what it does not

`BLOCKED-3` listed six obligations. This document closes four of them —
ownership, the unwind matrix, error translation, and the shape of the sensitivity
evidence — and closes the *specification* of the remaining two while leaving
their artifacts unproduced, for a reason stated in full below rather than
deferred to a later reader.

| Obligation | State |
| --- | --- |
| ownership, per handle | **closed here** |
| the unwind matrix | **closed here** |
| error translation | **closed here** |
| sensitivity evidence | **specified here**, produced by the implementation tranche |
| layouts and an independent oracle | **specified here, artifact not produced.** See *The oracle gap* |
| ABI declarations checked against an oracle | **specified here, artifact not produced.** Same reason |

**M3-b-2 does not begin on this document alone.** The oracle artifact is a
precondition, not a deliverable of the tranche that consumes it, because an
implementation that produces its own oracle checks its declarations against
themselves — the mistake N1 exists not to repeat.

## The first finding: the surface is larger than the blocker said

`BLOCKED-3` counted eight calls, three kinds of handle and at least six ways to
fail. Following the requirement to its end makes the count wrong in the safe
direction only if it is stated.

The child must receive the verified buffers and must not receive anything else.
`CreateProcessW` with `bInheritHandles = TRUE` and no further qualification
inherits **every** inheritable handle the parent holds — which on this path
includes the directory and file handles M2 is holding open on the materialized
root. Handing the child writable handles to the tree it is supposed to read
through a closed loader would undo the boundary from the other side.

The documented way to bound that is `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`, which
requires `STARTUPINFOEXW`, an opaque attribute list, and three more calls:

- `InitializeProcThreadAttributeList` — called twice, once to size the buffer
  and once to initialise it;
- `UpdateProcThreadAttribute`;
- `DeleteProcThreadAttributeList`.

So the surface is **fourteen calls, four kinds of owned resource** (process,
thread, job, attribute list) and the failure count rises accordingly. The
attribute list is not a handle and is not closed with `CloseHandle`; it is a
heap buffer with its own deletion call, and it is the one resource on this
surface whose leak is silent.

An alternative exists and is rejected here rather than left unmentioned:
`bInheritHandles = FALSE` with the standard handles passed through
`STARTUPINFOW`'s `hStdInput`/`hStdOutput` fields. Those fields are **only**
honoured when `bInheritHandles` is `TRUE`, so this combination does not do what
its shape suggests — it produces a child with no usable stdin. It is recorded
because it is the obvious-looking shortcut.

## The oracle gap, stated rather than absorbed

The layouts required are `STARTUPINFOW`, `STARTUPINFOEXW`,
`PROCESS_INFORMATION`, `JOBOBJECT_BASIC_LIMIT_INFORMATION`,
`JOBOBJECT_EXTENDED_LIMIT_INFORMATION`, `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION`
and the `IO_COUNTERS` embedded in the last two.

`gate3-native-expected-layout.json` covers eleven types and **none of these**.
Its extractor reads the official SDK headers out of a digest-pinned `.nupkg`:

- `package_id` `Microsoft.Windows.SDK.CPP`, version `10.0.26100.8249`;
- `package_sha256`
  `f8787b2f6678164ae789bdca6247e696c2a0f529a39ceb969d6ef3d69a987131`;
- `extraction_method` `headers-parsed`, `measurement_class`
  `computed-not-compiled`.

That package is **not present in this environment**, and no Windows SDK include
directory is installed here either — both were checked, not assumed. The oracle
therefore cannot be regenerated while writing this document.

**What this design deliberately does not do is write the offsets from memory.**
A table of sizes and offsets typed out here would become a third authority
sitting beside the declarations and the oracle, indistinguishable in the
document from a measured one, and an implementation checked against it would be
checked against somebody's recollection. `BLOCKED-3`'s own words are that these
must be *measured rather than assumed*; writing them here would satisfy the
sentence and defeat it.

The prerequisite is therefore exact and small:

1. obtain the pinned `.nupkg` at the recorded digest — the extractor verifies
   the whole-file digest before reading anything, so a substituted package fails
   closed rather than producing a plausible artifact;
2. extend `gate3_native_expected_layout_extract.py`'s type list with the seven
   types above, adding to the two explicit ABI-fact tables only if a field's
   type is genuinely not settled by the headers, and recording any such addition
   as the input it is;
3. regenerate `gate3-native-expected-layout.json` and commit it with the
   extractor digest it came from;
4. only then declare the `ctypes` structures, and gate them against the
   regenerated artifact.

`JOBOBJECT_BASIC_LIMIT_INFORMATION` is the one to watch: it is embedded as the
first member of the extended form, and the extended form's trailing members sit
at offsets that depend on both the embedded struct's size and the alignment of
`IO_COUNTERS`. An off-by-eight there is not a crash; it is a limit written into
the wrong field, which is a limit silently not applied.

## Why a job object at all

The child is started suspended and must not outlive the parent under any exit,
including a parent that is killed. Closing a process handle does not terminate
the process; neither does closing the handles of a *suspended* process, which
leaves a suspended orphan holding open handles on the materialized root, which
in turn cannot be removed. That failure was already found once in the M3-b
design review and is the reason this surface exists rather than a bare
`CreateProcessW`.

A job with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` gives the property structurally:
when the last handle to the job closes — including by the parent dying — the
kernel terminates everything in it. The accounting query exists to make the
claim checkable after the fact rather than asserted: `TotalProcesses` and
`ActiveProcesses` at return are evidence about what the job actually contained.

**The assignment window is real and is not closed by the job.** Between
`CreateProcessW` returning and `AssignProcessToJobObject` succeeding, the process
exists outside the job. `CREATE_SUSPENDED` is what makes the window harmless:
the process cannot run, spawn or open anything in it. It is narrowed by
construction, not eliminated, and this design does not claim otherwise. Assigning
via `PROC_THREAD_ATTRIBUTE_JOB_LIST` at creation would eliminate it and is
recorded as the stronger option not taken in revision 1, because it adds a second
attribute to the list that the handle-list work has to be correct for first.

## Ownership, per resource

Each resource is owned by exactly one object, ownership is never shared, copied,
or handed out as a raw integer, and the same rule the handle boundary already
carries applies unchanged: a close failure clears the stored handle
**unconditionally**, is recorded as `CLOSE_FAILED`, never masks the original
error, and **is not described as having released the resource**.

| Resource | Created by | Lifetime | Released by | Rule specific to it |
| --- | --- | --- | --- | --- |
| job handle | `CreateJobObjectW` | outlives the process handle | `CloseHandle` | closing it is what terminates the child under `KILL_ON_JOB_CLOSE`; it is therefore **closed last**, after the exit code and accounting are read, or the data is read from a job already killed |
| process handle | `CreateProcessW` | until exit code and accounting are read | `CloseHandle` | closing it releases the parent's reference and **does not terminate anything** |
| thread handle | `CreateProcessW` | until `ResumeThread` returns | `CloseHandle` | **must not outlive the resume.** It is the only handle on this surface with no post-resume use, and keeping it is how a suspended-thread reference survives a failure path |
| attribute list | `InitializeProcThreadAttributeList` | until `CreateProcessW` returns | `DeleteProcThreadAttributeList` | not a handle; `CloseHandle` on it is a category error. Its leak is silent, so its deletion is in the `finally` that owns creation, not in the success path |
| inherited handle list | the caller | for the duration of `CreateProcessW` | the caller | the array backing `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` must stay alive until `CreateProcessW` returns; `UpdateProcThreadAttribute` stores the pointer, it does not copy |

Every handle placed in the inherit list must have been created inheritable, and
**no other handle the parent holds may be inheritable at the moment of the
call**. The list restricts what is inherited; it does not make a
non-inheritable handle inheritable, and it does not retroactively make the rest
safe if a handle elsewhere was created with an inheriting security attribute.

## The unwind matrix

One row per point of failure, each stating what is terminated, what is waited
for, and what is closed, in order. "Nothing to terminate" is written explicitly
where it is true, because the row that says nothing is the row that leaks.

| Failed at | Terminate | Wait | Close / delete, in order | Code |
| --- | --- | --- | --- | --- |
| attribute list sizing or init | nothing | none | nothing exists | `PROCESS_ATTRIBUTE_LIST_FAILED` |
| `UpdateProcThreadAttribute` | nothing | none | delete attribute list | `PROCESS_ATTRIBUTE_LIST_FAILED` |
| `CreateJobObjectW` | nothing | none | delete attribute list | `PROCESS_JOB_CREATE_FAILED` |
| `SetInformationJobObject` | nothing | none | close job; delete attribute list | `PROCESS_JOB_CONFIGURE_FAILED` |
| `CreateProcessW` | nothing — no process exists | none | close job; delete attribute list | `PROCESS_CREATE_FAILED` |
| `AssignProcessToJobObject` | **`TerminateProcess` on the process handle** — it is suspended and outside the job, so closing the job does not reach it | wait for the process to signal | close thread; close process; close job; delete attribute list | `PROCESS_JOB_ASSIGN_FAILED` |
| `ResumeThread` | close the job — the process is inside it, so `KILL_ON_JOB_CLOSE` terminates it | wait for the process to signal before closing its handle | close thread; close process; close job; delete attribute list | `PROCESS_RESUME_FAILED` |
| the wait itself fails or times out | `TerminateJobObject`, which reaches the process and anything it started | wait again, bounded; a second failure is recorded and does not loop | close thread (already closed); close process; close job; delete attribute list | `PROCESS_WAIT_FAILED` / `PROCESS_TIMED_OUT` |
| `GetExitCodeProcess` | `TerminateJobObject` if the process has not signalled | none beyond the above | close process; close job; delete attribute list | `PROCESS_EXIT_CODE_UNAVAILABLE` |
| `QueryInformationJobObject` | nothing — the child has already exited | none | close process; close job; delete attribute list | `PROCESS_JOB_QUERY_FAILED` |
| success | nothing | already waited | close process; close job; delete attribute list | — |

Three properties this matrix is written to have, each of which a wrong
implementation would violate quietly:

- **the thread handle is closed on every row after `CreateProcessW` succeeds**,
  including the rows where the process is being terminated;
- **nothing is closed before the wait it is needed for.** Closing the process
  handle and then waiting on it is a use-after-close that Windows will often
  tolerate for a while;
- **the attribute list is deleted on every row**, including the ones where the
  failure had nothing to do with it.

## Error translation

`BLOCKED-3` observed that three process codes for a surface with at least six
ways to fail means five of them arrive as one. The closed set:

| Code | Raised when |
| --- | --- |
| `PROCESS_ATTRIBUTE_LIST_FAILED` | sizing, initialising or updating the attribute list |
| `PROCESS_JOB_CREATE_FAILED` | `CreateJobObjectW` |
| `PROCESS_JOB_CONFIGURE_FAILED` | `SetInformationJobObject` |
| `PROCESS_CREATE_FAILED` | `CreateProcessW` |
| `PROCESS_JOB_ASSIGN_FAILED` | `AssignProcessToJobObject` |
| `PROCESS_RESUME_FAILED` | `ResumeThread` returning `(DWORD)-1` |
| `PROCESS_WAIT_FAILED` | `WaitForSingleObject` returning `WAIT_FAILED` |
| `PROCESS_TIMED_OUT` | `WaitForSingleObject` returning `WAIT_TIMEOUT` — **distinct**, because a timeout is a fact about the child and a wait failure is a fact about the parent |
| `PROCESS_EXIT_CODE_UNAVAILABLE` | `GetExitCodeProcess` failing, **or** returning `STILL_ACTIVE` after a signalled wait |
| `PROCESS_JOB_QUERY_FAILED` | `QueryInformationJobObject` |
| `PROCESS_TERMINATE_FAILED` | `TerminateProcess` or `TerminateJobObject` on an unwind path; recorded, never masking the code that sent us there |
| `CLOSE_FAILED` | any close or delete; recorded, never masking |

Carried unchanged from the handle boundary, because the reasons are the same and
restating them weaker would be a silent relaxation:

- errors derive **only** from values the boundary read itself — a documented
  failure return followed by an immediate `ctypes.get_last_error()`;
- no exception escaping a `ctypes` call is translated; it is unexplained and
  routes to fail-fast;
- the load-and-bind phase is the one exclusion, and it is a property of where
  execution is rather than of what the exception looks like;
- no path returns a code and a live resource at the same time.

`ResumeThread`'s failure value deserves its own line: it returns the previous
suspend count, and `(DWORD)-1` is the failure. A truthiness check on that return
treats **every** success as failure and a check for zero treats failure as
success. This is the specific shape the read tranche already paid for once.

## Sensitivity evidence

Each item names what a wrong implementation would do differently, because an item
that cannot fail on a defect is not evidence.

| Item | Class | Catches |
| --- | --- | --- |
| every declared structure matches the regenerated oracle, field by field | offline | any layout typed from recollection, and any drift when the pinned SDK version moves |
| every declared signature has non-default `argtypes` and `restype`, checked against the oracle's function table rather than asserted non-empty | offline | the "asserted to be non-empty" mistake by name |
| `_pack_ = 8` declared on every structure | offline | a struct that happens to be right on this compiler and wrong on the next |
| the unwind matrix, driven by fault injection at each of the eleven failure points | in-process, no real process | a row whose terminate/wait/close order is wrong; a leaked thread handle; a deleted-nowhere attribute list |
| the thread handle is closed on the terminate rows | in-process | the leak that only appears when something has already gone wrong |
| a suspended child on the `AssignProcessToJobObject` row is terminated, not merely closed | **starts a real process** | the exact defect the M3-b review found by argument |
| accounting `ActiveProcesses` is zero and `TotalProcesses` is one at return | **starts a real process** | a job that never contained the child, which is a job that would not have killed it |
| the inherit list is exactly the intended handles | **starts a real process** | a child holding a handle on the materialized root |
| `ResumeThread` failure is detected as `(DWORD)-1` and not as falsiness | offline, mutation | the return-value shape above |
| timeout and wait failure produce different codes | offline, fault injection | the collapse `BLOCKED-3` named |

The three real-process items are the reason this tranche cannot be evidenced
entirely offline. They start a trivial interpreter child, not the historical one:
no materialized tree, no loader, no historical module.

## `NATIVE-INTEROP.md` compliance

| Rule | Status |
| --- | --- |
| §1.1 explicit packing | `_pack_ = 8` on every structure; layout gated against the regenerated oracle. **Blocked until that artifact exists** |
| §1.2 string encoding and lifetime | UTF-16 `LPWSTR` throughout; the command line buffer must be writable, since `CreateProcessW` may modify it in place, and must outlive the call |
| §1.3 memory ownership | kernel allocates process, thread and job handles; the attribute list is a caller-owned heap buffer with its own deletion call; the inherit array is caller-owned and must outlive `CreateProcessW` |
| §2.1 no raw pointer past the adapter | raw handles and the attribute-list pointer never leave the boundary module |
| §2.2 idempotent disposal with finalizer | context manager, idempotent close/delete, `__del__` safety net; a failed close drops ownership without claiming release |
| §3.1 explicit calling convention | `WinDLL`; amd64 only |
| §3.2 probe before load | shares the existing boundary's probe: OS, pointer width, machine |
| §3.3 loading | System32-only, under the same four compensating controls; **no new deviation is requested** |
| §4.1 Logic vs Panic | unchanged: unexplained exceptions route to fail-fast; the stage set gains `SPAWN`, `ASSIGN`, `RESUME`, `WAIT`, `JOB` |
| §4.2 / §4.3 | only closed codes leave the boundary |
| §5 testing | Windows-only; the existing slice-limited exception is **not** assumed to extend here and must be granted again or the item stands open |
| §6 ADR triggers | memory-ownership strategy and ABI both fire again. Whether this extends ADR-0001 or takes its own number is an open review question |

## Claim ceiling

- Nothing here is implemented. No symbol is bound, no process is started, no job
  exists, `ACTIVE` stays `False`, and no availability predicate moves.
- The layouts are **not measured**. This document specifies how they must be
  obtained and refuses to substitute a written table for the measurement.
- The job gives the child's lifetime a structural bound. It does not verify what
  the child *did*; that is the return frame's job, and the frame checks itself.
- `CREATE_SUSPENDED` narrows the assignment window. It does not eliminate it,
  and the stronger option that would is named and not taken in this revision.
- Restricting inherited handles bounds what the child receives from the parent.
  It says nothing about what the child can open for itself; that is the
  environment and the closed loader, specified elsewhere.
- The runner's trust root and its TOCTOU window remain accepted assumptions of
  M3. Nothing here narrows them.

## Authorization boundary

This document is a design candidate. It does not authorize implementation, does
not amend any authority document, and does not close `BLOCKED-3` by itself.
`BLOCKED-3` is closed when this design is reviewed and accepted **and** the
oracle artifact covering the seven types exists. Until both hold, M3-b-2 does
not begin.
