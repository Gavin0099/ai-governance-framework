# Gate 3 N3c-2 — Creation, Deletion and the Absence Probe

Status: design-only candidate; not approved, not implemented, and not execution
authority. No filesystem object was created, deleted or probed to write this.

Date: 2026-08-17

Revision: 7 — retires the section that still described `verify` as reading by
path. That description was correct when written and stopped being correct when
revision 21 gave role 3 a read right: byte verification now goes through the
creating handle, so `_contained` no longer guards a path-based read, because
there is no longer a path-based read to guard. Leaving both descriptions in the
document meant it specified two ways to verify the same bytes.

Revision 6 — points the read algorithm at revision 21, which is where the
fourth `ReadFile` outcome lives. Revision 5 still credited revision 20, whose
algorithm has only three, so an over-report would have fallen outside the
algorithm this document defers to.

Revision 5 — attributes byte immutability to the mechanism that actually
provides it rather than to the share mask alone, and follows design revision 21
in rejecting a `ReadFile` that reports more than it was asked for.

Revision 4 — the subordinate authority pointer in the header still named
revision 18 while the paragraph beneath it named 19, so the document deferred to
the surface that had just been corrected. Both now name revision 20, which also
closes the read state machine. Evidence `r5` is retightened to name the code it
expects rather than only that the read fails.

Revision 3 — the read surface's authority moves to design revision 19, which
settles where the expected length comes from and defines the exports, stage and
codes the read uses. Revision 2 also repeated the claim that role 3's share mask
admits no other opener; that is false, and the corrected statement is below.
Nothing else changes.

Base: `feat/gate3-historical-materialization@4eafdb80f450e5d734c75568b734d79813dcc037`

Design authority this document is subordinate to:
`docs/governance/gate3-native-handle-boundary-design-candidate-20260815.md`
revision 21, with
`docs/adr/0001-gate3-native-directory-handle-boundary.md`.

Revision 21 remains the authority on the adapter surface, the per-role
`NtCreateFile` parameter table, access masks, the deletion and cleanup ordering,
the absence-probe parameters, the created-object name grammar, the admission
chain and the fail-fast contract. **This document does not restate them, and
where anything here appears to conflict, revision 21 governs.** What this
document adds is the tranche contract: what N3c-2 owns, what it refuses, how
`base` is admitted, how M2's blocked operations map onto the surface, and what
evidence would have to exist before any of it is believed.

## Owner ruling incorporated, verbatim

> 裁定：`base` 必須預先存在，並維持 Role 1 borrowed ancestor 身分。N3c-2 不得建立、刪除或接管 `base`。

The reasoning, recorded because it is the part that generalizes: an object
created by this code carries an obligation to delete it, and a borrowed ancestor
carries an obligation never to delete it. "Create it, then treat it as borrowed"
puts both obligations on one object, and no ordering of operations discharges
them together. The refusal is therefore structural rather than a policy that
could be relaxed later under pressure.

## Ownership, stated as obligations rather than as roles

| | Role 1 — borrowed ancestor | Role 2 — directory we create | Role 3 — file we create |
| --- | --- | --- | --- |
| Who creates it | nobody in this process | N3c-2 | N3c-2 |
| Opened by | `open_chain`, N3c-1, already delivered | `create_directory` | `create_file` |
| Held for | the lifetime of the tree | until cleanup deletes it | until its bytes are written and cleanup deletes it |
| Deletion obligation | **never**; `DELETE` is not requested and cannot be | must be deleted by cleanup | must be deleted by cleanup |
| Failure to delete | not applicable | `CLEANUP_INCOMPLETE` | `CLEANUP_INCOMPLETE` |

The obligations are opposite, which is why the roles cannot merge. A reader
checking this design should be able to answer, for any handle the
implementation holds, which of the two deletion obligations applies — and if
that question has no single answer for some handle, the design is wrong there.

`base` is Role 1. The output root created under `base` is Role 2, as is every
intermediate directory. Payload files are Role 3.

## `base` admission

Normative: **the caller supplies an absolute path to a directory that already
exists.** N3c-2 creates nothing on the way to it.

Admission runs before any object is created, and fails closed on each of these:

| Condition | Closed code |
| --- | --- |
| `base` is relative, UNC, a device path, or fails the path grammar | `PATH_INVALID` |
| `base`, or any ancestor of it, does not exist | `BASE_NOT_FOUND` |
| `base`, or any ancestor, is a reparse point | `PATH_IS_REPARSE_POINT` |
| `base` exists but cannot be opened or pinned — sharing violation, access denied, anything else | `BASE_NOT_ADMISSIBLE` |
| a pinned component's identity no longer matches at revalidation | `ROOT_IDENTITY_CHANGED` |
| a required metadata query fails | `ROOT_IDENTITY_UNAVAILABLE` |

### Why two new codes rather than reusing `HANDLE_BOUNDARY_UNAVAILABLE`

`HANDLE_BOUNDARY_UNAVAILABLE` means the boundary itself cannot be used on this
platform or build — a property of the process, identical for every caller,
unfixable by changing an argument. A missing or unusable `base` is a property of
one call, and the caller can act on it. Collapsing them would tell a caller to
go looking for a platform problem when the actual fault is a path they passed.

`FAIL_FAST_CODES` is frozen and appends at the next free value; revision 17
forbids renumbering because a renumber silently changes the meaning of every
ordinal already captured in a dump. The two additions are therefore:

```text
BASE_NOT_FOUND       = 11
BASE_NOT_ADMISSIBLE  = 12
```

No existing entry moves. `FAIL_FAST_STAGES` needs no addition: base admission
happens in `CHAIN`, which already exists.

## Phase ordering — normative, and the reason it is not the obvious one

```text
1. read every blob through the injected reader, and verify every digest
2. open and pin the pre-existing base; revalidate the pinned chain
3. runtime admission and the capability probe, from the held base handle
4. create and write — no injected code runs in this phase
5. handle-bound cleanup, one object at a time: for each object, deepest first,
   mark delete on its held handle, close that handle, then confirm the name is
   absent before moving to the next object
6. release whatever handles are still held
```

Step 5 is deliberately not written as "delete everything, then confirm
everything". Revision 17 makes confirmation part of each object's transaction,
and a design that batches it loses the property that makes the stop rule work: a
parent must not be attempted while its child may still exist. Confirming only
after the whole sweep would mean the parent was already attempted by the time
the child's failure surfaced.

The ordering that looks safer — pin first, then read the blobs — is wrong, and
the reason is worth stating because it inverts the usual instinct. `read_blob`
is injected, caller-supplied and untrusted. Pinning before it runs means holding
directory handles *across* a call into untrusted code, which is both a resource
held for an unbounded time and a window in which that code can act while our
handles are open. Reading first costs nothing: phase 1 touches no filesystem
state of ours, so there is nothing of ours to race.

What phase 4 buys is the property M2 already claims and must keep: between the
last injected call and the last create, no external code runs, so no checked
parent of ours exists for the injected reader to swap. Any redesign that
reintroduces a callback into phase 4 — a progress hook, a lazy byte source, a
logging callback that a caller can supply — voids that property, and this
document treats such a change as a new safety trade-off rather than a detail.

## M2's blocked operations, mapped

M2 currently fails closed on eight operations. Each maps to the revision 17
adapter surface, and one is deleted rather than mapped.

| M2 today | Maps to | Note |
| --- | --- | --- |
| `os.makedirs(base_dir, exist_ok=True)` | **removed** | the owner ruling: `base` pre-exists, and creating it here is what the ruling forbids |
| `os.mkdir(root)`, must fail if the name is taken | `create_directory(base_anchor, root_name)` | `FILE_CREATE` fails on an occupied name, which is the same refusal without the lookup |
| `os.mkdir(root / parent)` for intermediates | `create_directory(parent_anchor, component)` | each relative to the anchor above it, never to a path |
| `_create_exclusively` — `O_CREAT｜O_EXCL｜O_WRONLY`, mode `S_IREAD` | `create_file(parent_anchor, name, payload)` | `FILE_CREATE` supplies the exclusivity; `FILE_ATTRIBUTE_READONLY` supplies born-read-only |
| `os.write(descriptor, payload)` | inside `create_file` | written through the held handle, before it is released |
| `stale_root` via `os.path.lexists` | `confirm_absent(base_anchor, root_name)` | the probe is handle-relative and only `STATUS_OBJECT_NAME_NOT_FOUND` counts as absent |
| `_drop_name` — `chmod` then `unlink` then `rmdir` | `remove(held)` | acts on the held object, so the `rmdir` fallback for "our name now answers as a directory" has nothing left to disambiguate |
| `_identity_of(root)` and its re-check | `identity(held)` / `revalidate(held)` | already delivered by N3c-1 |

### Born read-only, and still deletable

`create_file` requests `FILE_ATTRIBUTE_READONLY` while holding `FILE_WRITE_DATA`:
the attribute governs later opens, the creating handle keeps its granted access,
so there is no interval in which the materialized bytes are writable through
their path. Deletion then needs `FileDispositionInfoEx` with
`IGNORE_READONLY_ATTRIBUTE`, which is why role 3 carries `FILE_WRITE_ATTRIBUTES`
and `DELETE`. This is one mechanism, not three independent choices, and changing
any part of it breaks the other two.

### Reading a created file back

Role 3 carries `FILE_READ_DATA` from design revision 18, and `read_all(leaf)` is
how this code reads a materialized byte back. Design revision 21 owns the
algorithm — the rewind on every call with its checked postcondition, the sealed
length, the one-byte end-of-file probe, and the mapping of all four `ReadFile`
outcomes, including a count larger than the request, onto
`MATERIALIZE_READ_FAILED` and `MATERIALIZED_BYTES_CHANGED` — and this section
does not restate it.

The share mask is not total exclusion. Measured against a held role 3 handle, a
native reader sharing only read is refused, one sharing read and write is
refused, and one sharing read, write and delete succeeds. What the mask excludes
is any opener unwilling to tolerate our write and delete access — ordinary
writers, deleters and CPython's `open()` — and not a deliberate reader. Reading
through the creating handle is chosen because it resolves no name and adds no
second ownership path, not because nothing else could get in.

The contract, because "read the file" is not a specification:

| Question | Answer |
| --- | --- |
| where it starts | the file pointer is set to zero before the first chunk, every call — a read that continued from wherever the last write left it would return nothing and look like an empty file |
| who says how long | the `Leaf`, sealed at creation. `read_all` takes no length argument, so the expected answer cannot be adjusted by whoever is asking |
| short reads | continued, exactly as writes are; a read returning fewer bytes than asked for is legal and is not the end of the file |
| end of file | a read returning **zero** bytes is the only end-of-file signal, and it is expected exactly once, when the sealed length has already been read. Before that point the same event is a file shorter than recorded, not a failure of the call |
| repeated calls | permitted and independent; each call rewinds, so two calls on one handle return the same bytes |
| how much | `expected_length` exactly. Fewer bytes at end-of-file, or any byte beyond it, is `MATERIALIZED_BYTES_CHANGED` |
| upper bound | `expected_length` is the bound. There is no "read until EOF" mode, so a file that grew cannot make this allocate without limit |
| chunking | `DWORD`-bounded, like writes. There is no zero-progress guard: for a read, zero bytes *is* end of file, so the case needs a code rather than a guard — which is where the write loop and the read loop genuinely differ |

The length is sealed into the `Leaf` at creation, so "how many bytes should be
here" is answered by what this code wrote rather than by what is on disk now, or
by what a caller would prefer.

What this does **not** establish is that the bytes cannot change. They cannot,
but the read is not what stops them and neither is the share mask on its own —
the creating handle holds `FILE_WRITE_DATA` for the life of the object, so
something in this process could write through it if a path to doing so existed.
Three things together are what close it:

- the **share mask** refuses any external opener unwilling to tolerate our write
  and delete access, which is every writer and deleter;
- the **opaque handle** never leaves the module, so no caller can obtain the raw
  capability to write through;
- the **call census** over the module's own source proves there is no second
  `WriteFile` reachable after `create_file` returns.

Remove any one and the claim fails, which is why evidence `r6` has to rest on
all three rather than on the mask.

### What M2 must delete, not adapt

These are path-based fallbacks that exist only because ancestors were not bound.
Keeping them alongside a handle-bound path would leave two ways to remove an
object, one of which resolves by name:

- `_drop_name`'s `os.chmod` / `os.unlink` / `os.rmdir` sequence, including the
  comment about a junction planted over one of our own names;
- `_remove`'s `root / PurePosixPath(relative)` construction and the final
  `os.rmdir(root)`;
- `_create_exclusively` in full, including the `getattr(os, "O_NOFOLLOW", 0)`
  that contributes nothing on Windows;
- `stale_root`'s `os.path.lexists`;
- `os.makedirs(base_dir, exist_ok=True)`;
`_contained` **is** on this list, and the reason it was kept off it for two
revisions is worth recording. It existed to stop `verify` reading outside the
root while `verify` resolved `root / relative` by path — a real risk that a
digest comparison does not cover, because a digest says nothing when an external
location happens to hold exactly the expected bytes and the unauthorized read
has already happened by then. That argument was sound for as long as the
read-back was path-based. Revision 21 gave role 3 a read right, byte
verification now goes through the creating handle, and an escape check on a read
that no longer resolves a name is guarding nothing.

`verify` keeps one path-based operation: enumerating the tree to compare the
observed path set against the record. That walk reads no bytes and refuses to
descend through a reparse point, so the escape `_contained` guarded has no route
left. What is **not** claimed is that the enumeration is handle-bound — it is
not, and the adapter offers no directory enumeration to make it so. A path walk
observing a set that a handle-based walk would not remains possible in
principle; closing it is a later step and is not claimed here.

## Cleanup failure never masks a prior failure

Settled in N3c-1 and carried forward unchanged, because it was got wrong three
times there and the same shape recurs wherever an unwind path exists:

- a failure during cleanup is attached to the error that caused the cleanup, and
  the original error is what propagates;
- with no prior error, a cleanup failure is raised normally — a caller closing
  deliberately is asking to be told;
- both directions are tested, so "does not mask" is not implemented as "always
  swallows".

### Deletion attempts and handle release are separate rules

An earlier revision of this document ran these together and contradicted itself
within three lines. They are different sequences with opposite continuation
rules, and conflating them is how a "keep going" rule for closing handles turns
into deleting past a failure.

**Deletion attempts stop.** Per revision 17: on a confirmation that is not
`STATUS_OBJECT_NAME_NOT_FOUND`, the sequence stops at that object with
`CLEANUP_INCOMPLETE` and the parent is **not** attempted. Deleting a parent
whose child may still exist is exactly the operation that must not be guessed
at.

**Handle release continues.** Every handle still held after deletion stops is
closed in reverse acquisition order, and every one is attempted even if an
earlier close fails, because stopping there leaks the handles beneath it.

The set matters, and "closing a handle removes no object" is not true in
general — on Windows, closing the last handle to an object already marked
delete-pending is what completes the deletion. It is true of *this* set: the
handles reaching the release pass are created objects that were never reached by
the deletion sequence, and therefore never marked, plus the borrowed ancestor
chain, which is never marked by construction. Closing that set starts no
deletion, which is why continuing through it costs nothing the stopping rule
protects. An object that *was* marked has already had its handle closed inside
its own transaction, per revision 17's `mark delete → close → confirm` order.

**Precedence.** `CLEANUP_INCOMPLETE` is the reported failure when deletion
stopped and there was no prior error. A close failure during the release pass is
attached as a note and never replaces `CLEANUP_INCOMPLETE`; and if a prior error
caused the cleanup, that error is what propagates, with both cleanup outcomes
attached to it.

## Evidence plan

The tranche is not believable on passing tests alone; each item below names what
would be false if the mechanism were absent.

**Hostile, offline:**

1. `base` missing yields `BASE_NOT_FOUND` and not
   `HANDLE_BOUNDARY_UNAVAILABLE`, asserted by code equality;
2. `base` present but unopenable yields `BASE_NOT_ADMISSIBLE`;
3. a relative, UNC or device `base` yields `PATH_INVALID` before any open;
4. every refusal above happens with **zero** objects created. "List the base
   before and after" is not executable for most of these — a missing base cannot
   be listed, an unopenable one may not be, and an invalid path has no directory
   to list — so the anchor is chosen per refusal:
   - invalid path, including UNC and device forms: prove no native open or
     create export was invoked at all, so the refusal precedes any native call;
   - missing base: enumerate a controlled, pre-existing parent that the test
     created, and confirm the base name is still absent under it afterwards;
   - unopenable base: enumerate that same controlled parent, taking a full
     inventory before and after, and additionally prove the create surface was
     never invoked;
5. an occupied name yields the creation refusal rather than an open of whatever
   occupies it, proven by a pre-planted file, directory and reparse point in
   turn;
6. the new codes are appended, not renumbered: the ordinals of all ten existing
   codes are asserted individually;
7. an injected reader that tries to create our root during phase 1 finds phase 4
   still refuses, and the ordering test asserts the reader ran before any create
   — the property, not the sequence of lines;
8. a callback supplied anywhere reachable from phase 4 fails a structural check,
   so the callback-free property is enforced rather than documented.

**The read surface:**

r1. a file written and read back through the same held handle returns exactly
    the bytes written, for a payload spanning several chunks;
r2. two consecutive `read_all` calls on one handle return identical bytes,
    which is the rewind observed rather than assumed;
r3. a `read_all` immediately after `create_file` — that is, with the file
    pointer left wherever writing put it — returns the payload rather than
    nothing, which is the same rewind seen from the case that would silently
    return an empty file;
r4. a short read is continued: an injected reader returning a fraction of each
    request still yields the whole payload, and the request sizes show more
    passes than chunks;
r4b. a rewind that reports success without moving the pointer is refused with
    `MATERIALIZE_READ_FAILED`, so the returned position is shown to be checked
    rather than the boolean alone;
r5. a `ReadFile` that succeeds while returning zero bytes before the sealed
    length is reached yields `MATERIALIZED_BYTES_CHANGED`, asserted by code and
    not merely as "it failed" — the same event maps to a different code once
    the sealed length has been read, and a test that only checked for failure
    would pass with the two confused;
r6. a file whose bytes were changed underneath is rejected as
    `MATERIALIZED_BYTES_CHANGED`. Reaching that state needs a fixture owning
    its own object, and the reason it cannot happen to a real one is asserted
    as all three of its parts: an external writer is refused by the share mask,
    the raw handle is unreachable from outside the module, and the call census
    shows no `WriteFile` after creation. A test resting on the mask alone would
    leave the other two unasserted;
r6b. a `ReadFile` reporting more bytes than were requested is rejected as
    `MATERIALIZE_READ_FAILED`, in the read loop and in the one-byte probe
    separately — an over-report is a broken call, not a changed file;
r7. `expected_length` comes from the record: a test that alters the recorded
    length and leaves the file alone must fail closed, proving the length is
    not re-derived from the object being checked;
r8. the share behaviour, measured rather than asserted: a native reader sharing
    only read is refused, one sharing read and write is refused, and one sharing
    read, write and delete succeeds. The claim under test is the narrow one —
    the mask excludes openers unwilling to tolerate our write and delete access
    — and explicitly not that nothing can open the file.

**Real Windows, and the part that cannot be faked:**

9. born-read-only, established with a control rather than by a confounded
   probe. A second write-open while the creating handle is still held proves
   nothing: role 3's `ShareAccess` is `FILE_SHARE_READ` alone, so that open
   fails on the share mask whether or not `FILE_ATTRIBUTE_READONLY` was ever
   requested, and the test would pass against an implementation that dropped the
   attribute entirely. The evidence is therefore two-part, each part paired with
   a fixture that must behave differently:
   An earlier revision specified the observation "after creation, before the
   first write". That point is not reachable. `create_file(anchor, name, bytes)`
   takes the payload and returns a held `Leaf`, so creation and writing both
   complete before control returns; reaching between them would mean splitting
   the adapter surface, adding a callback into phase 4, or putting a test query
   into the production path. The first two are forbidden by this design and the
   third has no authorization. The evidence is therefore taken at two points
   that do exist:
   - **offline, at the call boundary**: a fake binding captures role 3's
     `NtCreateFile` arguments and asserts `FileAttributes ==
     FILE_ATTRIBUTE_READONLY`. The sensitivity case is the mutation itself — an
     implementation requesting `FILE_ATTRIBUTE_NORMAL` must fail this assertion,
     and that must be demonstrated, not assumed;
   - **real Windows, after `create_file` returns**: `FileBasicInfo` on the
     production handle, which is still held, reports `FILE_ATTRIBUTE_READONLY`,
     while a test-owned control file created with `FILE_ATTRIBUTE_NORMAL`
     reports it clear. The first shows what was requested, the second shows what
     the kernel actually retained; neither alone would do, because a request
     that the filesystem ignored would pass the offline check and a query that
     returns a constant would pass the online one.
   Revision 17 requires every created file handle to be held until that leaf is
   removed through that same handle, so a probe that closes the handle early and
   reopens the name is not the role 3 lifecycle — it is a second ownership path
   for the same object, and the design refuses to grow one for the sake of a
   test.
   What this does **not** establish is the absence of a writable window. No
   measurement is taken between create and write, because no such point is
   observable through this surface. The property follows from the fixed
   parameter table and the share mask: the creating handle is the only handle,
   and role 3's `ShareAccess` excludes write. That is an argument, recorded as
   reasoning, and it is not claimed as measured;

9a. optional, and separate: an OS characterization fixture may create a file
   with `FILE_ATTRIBUTE_READONLY`, close it, and observe that a write-open then
   fails with `ERROR_ACCESS_DENIED` while an equivalent
   `FILE_ATTRIBUTE_NORMAL` file opens successfully. This fixture owns its own
   objects, creates and removes them itself, and is **not** part of the role 3
   lifecycle: it characterizes how Windows treats the attribute after close, and
   evidences nothing about the production path's ownership, holding or deletion.
   It must not be cited as role 3 evidence;
10. deletion of the production role 3 file from item 9, through its original
    held handle, succeeds via `FileDispositionInfoEx`
    with `IGNORE_READONLY_ATTRIBUTE`, and the fallback path is exercised
    separately rather than assumed available;
11. `confirm_absent` returns absent only for `STATUS_OBJECT_NAME_NOT_FOUND`;
    each of `STATUS_DELETE_PENDING`, success, and a sharing violation is shown
    to yield `CLEANUP_INCOMPLETE`;
12. no role but the absence probe requests `FILE_SHARE_DELETE`, asserted against
    the mask constants so a later widening cannot pass unnoticed;
13. no borrowed ancestor requests `DELETE`, asserted the same way;
14. after a complete cycle, `base` still exists and has the identity it was
    pinned with — the ruling's central claim, stated as a test.

Every real-Windows item runs against a caller-supplied temporary directory that
the test creates as `base` beforehand, so the tranche itself still creates no
`base`.

## Claim ceiling

This document is design bytes. It is not an implementation, not an admission,
and not authority to create or delete anything. Approving it does not move
`handle_boundary_available()` or `ACTIVE`, does not unblock M2, and does not
touch the consumed A/B pair, which remains `NON_SUCCESS` and unusable. The
evidence plan is a plan: none of it has been run, and no result from it is
claimed or predicted here.

The mapping table asserts that M2's operations *can* be expressed on the
revision 17 surface. It does not assert that the resulting M2 would be correct;
M2's own rewrite and review are a later slice.

## Authorization boundary

Authorized by this slice: writing this document.

Not authorized, and not implied by approval of it: implementing N3c-2, creating
or deleting any filesystem object, running the absence probe, modifying M2,
changing `FAIL_FAST_CODES` in the implementation, touching B-1 or any other
excluded dirty path, staging, committing or pushing.
