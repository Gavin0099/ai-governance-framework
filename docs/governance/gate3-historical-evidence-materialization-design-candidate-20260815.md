# Gate 3 Historical Evidence Materialization Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-15

Revision: 8 — the isolation table's own `child` row still said the child "loads
the materialized tree", two rows above the ones stating that repo-local modules
are never found on a path. It reads equally as loading from the materialized
filesystem, which revision 7 retired, or as loading buffers that came from it,
which is what happens — and a row that supports both readings is not a
specification. Rewritten to the second.

Revision 7 — the DONE line and evidence item 5 still required the child to run
with a fixed *materialized* `sys.path`, while the isolation table had already
excluded the materialized root from the import roots and made the verified-byte
loader the only source of repo-local modules. Taken literally the two could not
both be implemented: a materialized root on `sys.path` is exactly the filesystem
import surface the loader exists to remove. Both now say stdlib-only.

Revision 6 — removes a superseded framing paragraph that revision 4 left in
place beside the exact one. It described the stream as a header followed
directly by records, which stopped being true when the candidate-set authority
block was inserted between them, so the document carried two live wire formats
in different orders. One survives.

Revision 5 — the child's expected inventory pointed at the wrong authority.
Revision 4 had it read the contract manifest from the repository at the active
head, which both mixes two versions and contradicts this document's own
authority chain: the executable inventory is derived only from the digest-pinned
candidate-set bytes, and the active head must not be able to redecide what the
history was. The candidate-set bytes now travel first on the same stream and are
checked against a digest frozen in the child runner, so the authority is a
literal in trusted code rather than anything the stream or the worktree
supplies. The whole-stream bound is also withdrawn as an independent gate — it
was unreachable, being larger than the sum of the bounds that constrain it — and
recorded as a derived maximum instead.

Revision 4 — the transport revision 3 introduced said "bounded" and "framed"
without giving a single number or field width, so two implementations of it
would not have produced the same bytes and neither could have been checked
against the other. Every bound is now a value and every field has a width, an
encoding and an order. The independent authority the child compares against is
named, because a child checking the stream's digests against the stream's own
payloads proves only that the stream agrees with itself. The claim that the
child could not read the materialized files even if it tried is withdrawn: it
has no inherited capability, which is a different and smaller statement.

Revision 3 — the child no longer opens the materialized files, and the channel
that replaces those opens is specified rather than left to the implementation.
The parent reads each file back through the handle that created it, verifies the
digest there, and passes the verified buffers over one framed transport defined
below.

Revision 2 justified this by saying the child *could not* open the files. That
overstated the share mask: measured against a held role 3 handle, a native
reader that shares read, write and delete does open it, while one sharing less
is refused. The reason the child does not read is therefore not that it is
impossible — it is that a second reader resolving the name again would be a
second path to the bytes, and the whole point of reconstructing from a pinned
tree is that exactly one capability decides what the child executes.

Base: `main@3305b640d17ca253e632093d434ae029f920c3e3` (merge of PR #70)

Scope: separating historical evidence reconstruction from the active runtime
source, so that the consumed `NON_SUCCESS` pair stays exactly reconstructable
while the implementation it once ran on may legitimately evolve

## Problem

Two responsibilities currently share one set of files:

1. `gate3_route_v2.py`, `gate3_route_v2_ab.py`, `gate3_route_v2_ab_live.py` and
   `gate3_route_v2_codex.py` are the **active implementation**, expected to
   evolve;
2. the same paths are the **promoted historical candidate source snapshot** for
   the consumed pair.

Those conflict by construction. Any lawful change to the implementation stops
the historical verifier passing, and the only ways out — freezing the code
forever, or re-pinning the old evidence to bytes it never ran — are both
unacceptable. Re-pinning would make the record describe an execution that never
happened.

B-1 was simply the first change to make the conflict visible. It is not the
cause and reverting it would not fix anything.

## How it was found

Implementing the approved B-1 rendering boundary edits `gate3_route_v2.py` and
`gate3_route_v2_codex.py`. Measured by running the directory suite with the
edits present and again with them stashed:

**Six regressions caused by B-1** — failing with the edits, passing without:

| Test | Cases |
| --- | --- |
| `test_candidate_runtime_inputs_match_source_commit` | 1 |
| `test_candidate_contract_mutation_is_rejected` | 1 |
| `test_exact_git_tree_materializes_and_reconstructs_non_success` | 1 |
| `test_materialized_runtime_residue_still_fails_closed` | 3 (parametrized) |

**One pre-existing failure, not caused by B-1**:
`test_exact_candidate_reconstructs_and_validates` fails in both runs. It is
caused by untracked evidence paths already present in the directory, and **must
not be cited as evidence of this conflict**.

The B-1 design predicted only that a measured preflight would be invalidated.
The promoted candidate reconstruction breaking was not predicted, and that claim
is corrected separately.

## Current Repository Truth

`gate3_route_v2_ab_candidate.py` couples history to the worktree **twice**, and
both couplings must be addressed:

1. **Byte equality.** `_verify_source_commit_inputs()` compares
   `path.read_bytes()` against `git show SOURCE_COMMIT:path` for
   `SOURCE_COMMIT_INPUTS`, which includes `gate3_route_v2.py` and
   `gate3_route_v2_codex.py`. `SOURCE_COMMIT` is
   `204965c94bd843d599986d9f9d0fd552ea053dff`.
2. **Live-module reconstruction.** `build_contract_manifest()` and
   `build_candidate_set()` rebuild the manifests from **currently imported**
   module attributes — `codex.PROMPT`, `codex.BASELINE_WORKSPACE`,
   `codex.OUTPUT_SCHEMA`, `codex.EXPECTED_WORKSPACE`,
   `live._implementation_sha256()` — and `_file_record()` reads worktree bytes.

Fixing only the first would leave the reconstruction silently reading today's
values. That is the more dangerous of the two, because it fails quietly rather
than loudly.

## Decision: materialize history, do not constrain the present

**The historical verifier materializes the pinned commit and reconstructs from
those bytes. It never requires the worktree to match.**

| Element | Decision |
| --- | --- |
| source of truth | `git` object store at `SOURCE_COMMIT`, materialized read-only into a temporary tree |
| what is compared | materialized bytes against the retained manifests, never worktree bytes |
| module values | read from the **materialized** modules, not from whatever is imported in the running process |
| worktree | unconstrained; the active implementation may evolve freely |

### Isolation is a child process, not a namespace

Reconstruction needs values, not just bytes: `PROMPT`, `BASELINE_WORKSPACE`,
`OUTPUT_SCHEMA`, `EXPECTED_WORKSPACE` and the live adapter digest.

An earlier revision proposed loading the historical modules under a distinct
namespace in the same process. **That does not work.** The historical modules
contain absolute imports — `import gate3_route_v2 as route`,
`import gate3_route_v2_ab as pair`, `import gate3_route_v2_codex as codex` — so
aliasing the entry module changes nothing: those imports still resolve against
the active `sys.modules`, and reconstruction would silently mix historical and
present code. That revision also left the choice open as a review question; it
is decided here.

**Historical code executes only in a disposable child interpreter.**

| Element | Rule |
| --- | --- |
| parent process | never imports a historical module, under any name |
| child | receives verified byte buffers and loads repo-local modules only through the closed loader; that loader opens nothing in the materialized tree, whose root is absent from `sys.path`. This is a statement about the loader, not about everything the child process could be made to do — `__file__` may still name a materialized path, and historical code is outside the loader's guarantees. No active Gate 3 module exists in that interpreter, so historical modules may keep their original names safely |
| interpreter flags | `-I -S -B`: isolated, no site processing, no bytecode |
| import roots | cwd, user site, `site-packages`, `PYTHONPATH` and the active repo root are all excluded. Only the interpreter's own confirmed stdlib roots remain — the historical modules need `json`, `pathlib`, `ctypes` and others, so "only the materialized root" as an earlier revision put it was not executable as written |
| repo-local modules | supplied **only** by the closed verified-byte loader below, never found on a path |
| inventories | stdlib imports and repo-local imports are verified separately; a repo-local import outside the closed inventory fails closed |
| return channel | canonical reconstructed bytes and digests only — no objects, no pickles, no paths |

### The child executes verified bytes, not a path

An earlier revision claimed that sealing before execution and re-checking
afterwards "closes the window". **It does not.** The sequence

> parent verifies file A → file is replaced by B → child executes B →
> post-check notices and rejects

still executes B. A post-check detects; it cannot prevent a side effect that
already happened.

The child therefore loads through a **closed custom loader over verified byte
buffers**:

- the **parent** reads each file once, through the handle that created it, and
  verifies its exact digest there. The child receives the resulting buffers, and
  its trusted loader opens no materialized path — a statement about that loader,
  not about everything the child process could be made to do. This is not a
  relaxation: a loader that opened the name would be
  resolving a path the parent has deliberately stopped resolving, and would be
  executing bytes selected by that path rather than by the capability the parent
  verified;
- the child compiles and executes **that byte buffer**, not the path;
- absolute imports resolve only from the verified module-byte map, so
  `import gate3_route_v2 as route` inside a historical module cannot reach a
  file at all;
- `__file__` may point at the materialized path for historical digest
  computation, but **no code is selected by that path**, and the trusted loader
  opens none of them;
- the post-execution re-check judges whether the reconstruction result is
  acceptable. It no longer claims to prevent code substitution, because it
  cannot.

**AST parsing instead of execution is a rejected alternative**, recorded so it
is not revisited: it trades fidelity to what actually ran for a narrower blast
radius, and keeping it alongside executable loading as an implementation-time
choice would leave two reconstruction semantics.

### The parent-to-child channel — normative

The child executes what it is given, so how it is given decides what it
executes. Leaving that to the implementation would put the reconstruction's
integrity in whichever mechanism was convenient.

**One transport.** A single bounded, length-framed stream on the child's
standard input. Not an environment variable, not `argv`, not a pickle, not a
temporary file, and with no fallback if the stream is unavailable — a fallback
is a second channel, and a second channel is a second thing to verify.
`pickle` is excluded by name because it executes during decode, which would put
code selection back in the transport.

**Framing, exactly.** All integers are unsigned, little-endian, fixed width.

| Position | Field | Width | Value |
| --- | --- | --- | --- |
| header | magic | 8 bytes | `47 41 54 45 33 48 4d 00` (`GATE3HM\0`) |
| header | version | 2 | `1` |
| header | record count | 2 | how many records follow |
| header | aggregate payload length | 8 | sum of every record's payload length |
| authority | candidate-set length | 4 | bytes of the candidate-set document |
| authority | candidate-set bytes | that many | verified against the frozen digest before anything else is read |
| record | path length | 2 | bytes of UTF-8, not characters |
| record | path | that many | repo-relative, `/`-separated, no BOM |
| record | payload length | 4 | bytes |
| record | digest | 32 | raw SHA-256, **not** hex |
| record | payload | that many | the bytes themselves |

The digest is 32 raw bytes rather than 64 ASCII: one encoding, no case
question, and a length that cannot be confused with the other.

**Order.** Records ascend by the bytewise comparison of their UTF-8 path bytes
— not by code point, not by any locale collation, and not by the decoded
string. Two runs reconstructing the same module set therefore produce
byte-identical streams, which is what makes the stream itself comparable across
runs.

**Bounds, as values.** Every one is an exact byte count, because "4 MiB" is a
unit and a limit has to be a number.

| Bound | Value |
| --- | --- |
| records | 64 |
| path bytes | 512 |
| candidate-set bytes | 1,048,576 |
| payload bytes, one file | 4,194,304 |
| payload bytes, aggregate | 33,554,432 |
| whole framed stream, **derived** | 34,638,232 |

The last row is not a gate. An earlier revision set an independent whole-stream
cap of 33 MiB, which no legal stream could ever reach: the header is 20 bytes,
the candidate-set block at most 1,048,580, the per-record framing at most
64 × 550 = 35,200, and the aggregate payload at most 33,554,432, so the largest
stream satisfying every other bound is 34,638,232 bytes. A cap above that can
never fire, and one below it would have been the real limit under another name.
The derived figure is recorded so the arithmetic is checkable, and enforcement
stays with the bounds that constrain it.

The header's count and aggregate are checked against their limits **before any
allocation sized from them**. A per-record length can only be checked once that
record's header has been read, so the claim is not that everything is validated
up front: it is that nothing is allocated from an unchecked number. A record
whose declared payload would push the running total past the aggregate is
refused at that record, before its bytes are read.

**The child re-verifies, against an authority the stream cannot supply.**
Receiving is not trusting, and a child comparing the framed digests to the
framed payloads would only prove the stream agrees with itself.

The authority is the candidate-set document, and the chain is:

1. the child runner carries the candidate-set SHA-256
   `db86a97b36a2e80e43e9e0765f07f20cb00e07aa813cbf54bea2b587f3c02baa` as a
   **frozen literal in trusted code** — not on the wire, not in the worktree,
   not derived from the active head;
2. the stream's first block is the candidate-set bytes; the child hashes them
   and refuses unless they equal that literal;
3. the expected executable path inventory and per-file digests are derived from
   **those verified bytes**, exactly as step 4 of the authority chain requires;
4. every following record is checked against that inventory.

The candidate-set bytes travel over the same transport as the payloads, and
that is not a circularity: what makes them authoritative is the frozen digest
in the child, which the stream cannot reach. Reading the manifest from the
active head — which an earlier revision specified — would have let the present
redecide what the history was, and that is the one thing this whole design
exists to prevent.

Before compiling anything the child checks:

- the framing consumed the stream exactly, with no trailing byte;
- the magic and version are the ones above;
- every path passes the same grammar the parent applied;
- the path set equals the inventory derived from the verified candidate-set
  bytes — no duplicate, no extra, none missing — and the records are in the
  required order;
- every payload's SHA-256 equals both the digest framed with it **and** the
  digest that derived inventory records for that path.

Any mismatch fails closed and nothing is compiled. The parent verified the bytes
against the filesystem through held handles; the child verifies them against an
inventory rooted in a digest frozen in its own code. Neither check substitutes
for the other, and the frozen digest is what makes the second one more than a
restatement of the first.

**Handles are not inherited.** No native handle from the boundary is passed to
the child, so it holds no capability over the materialized tree and cannot
write to or remove anything in it — the share mask denies those to any opener.
It is *not* claimed that the child could not read a materialized file if it set
out to: measurement shows a native reader that shares read, write and delete
succeeds against a held role 3 handle. What the design establishes is narrower
and is the part that matters: the trusted loader resolves no materialized path,
so nothing the child executes is selected by one, and execution comes only from
the verified wire buffers.

### Bootstrap validation happens before any historical code runs

The order is fixed. Executing first and validating afterwards would mean running
substituted source and reporting it too late.

**The authority chain has two links, and an earlier revision named neither.**
The owner pin binds the *contract manifest*; `SOURCE_COMMIT` lives in the
*candidate set*; and the pin does not bind the candidate set. Without stating
both links, the candidate set and the source commit could be swapped together
and the owner pin would still pass.

| Step | What is validated | Against |
| --- | --- | --- |
| 1 | owner-pin artifact: path, schema, `SIGNED_AND_PROMOTED` state | contract-manifest SHA-256 `fd6c75eb7e3bb7f36f85804b7b2398a07d5647d948691f2d9ff64ea094998440`, from owner promotion commit `8da68734` |
| 2 | candidate-set bytes | exact SHA-256 `db86a97b36a2e80e43e9e0765f07f20cb00e07aa813cbf54bea2b587f3c02baa`, held as a **frozen literal in the historical verifier module** — see below |
| 3 | the source commit named inside the verified candidate set | must equal exactly `204965c94bd843d599986d9f9d0fd552ea053dff` |
| 4 | executable path inventory and per-file digests | derived **only** from the verified `db86a97b…` bytes, never from the worktree copy |

**Where the candidate-set digest comes from, and why not from the candidate
set.** The owner pin binds only the contract manifest, so the candidate-set
digest needs its own non-circular source. An earlier revision said only that its
"stated authority source" would be recorded alongside, which specified nothing.

The expected value is a **frozen literal in the historical verifier module**,
established when this design becomes mainline authority — the same mechanism
that froze the v1 contract bytes in Group A. It is reviewed and merged code, not
a value read from the artifact under verification.

`PLAN.md` records `db86a97b…` independently at the promoted-milestone entry, and
that record is corroboration a reviewer can check. It is not the runtime source
of the expectation.

**Reading the expected digest out of the candidate bytes being verified would be
circular** and is forbidden: it would verify the artifact against itself.

Steps 1–4 execute no historical code. Only after all four:

5. materialize `SOURCE_COMMIT` read-only;
6. verify the exact path set, and read every file back through its creating
   handle to verify each digest, rejecting any additional repo-local module;
7. start the child, handing it the verified buffers;
8. after the child returns, re-read through the same handles and re-check each
   digest — see the limit on what that check can and cannot do, below.

### Temporary root: identity, sealing and crash semantics

Calling the tree "read-only" is not a mechanism. The contract:

- the materialized root is created private to this process and its **identity**
  is captured, not just its path, so a replacement is detectable;
- every materialized path is containment-checked against that root; a symlink,
  junction or reparse point at any position fails closed;
- the digests recorded during validation are re-checked after the child
  returns, through the same held handles rather than by reopening the paths. **This does not close the validation-to-use window** — the custom
  loader executing one verified byte buffer is what prevents code-selection
  substitution. The re-check only decides whether the reconstruction result is
  acceptable;
- cleanup runs on success and on any handled failure;
- **on a hard crash, residue is not deleted automatically.** An earlier
  revision left two policies open — automatic bounded recovery, or state the
  limit — which would have produced different state machines, different deletion
  authority and different tests. One is chosen:

  | Situation | Behaviour |
  | --- | --- |
  | hard crash leaves a materialized root | nothing is deleted; no completion claim is made |
  | a later run finds a matching stale root | **fails closed** and reports that local recovery is required |
  | removing it | manual, or a separately authorized bounded recovery — never a side effect of the next verification |

  What remains is a copy of public source rather than private data, but it
  remains, and claiming a cleanliness nobody observed is the failure mode this
  work stream exists to avoid.

## What must not change

None of the following may be modified, re-signed or re-derived by this work:

- the retained contract manifest and candidate-set bytes;
- the pair-final digest and every published pair artifact;
- the owner promotion and its pin;
- `SOURCE_COMMIT` = `204965c94bd843d599986d9f9d0fd552ea053dff`;
- `PAIR_ID`, the run identifiers and the consumed pair's `NON_SUCCESS` result.

**The old pair's retained authority and evidence are bound to `204965c9…`, and
nothing here may rebind them to other source bytes.** That is a statement about
the record, not about execution: as the claim ceiling below says, the pin is a
record and this design preserves it rather than proving what ran. An earlier
revision asserted that the old pair *ran* those bytes, which its own claim
ceiling contradicted.

The new B-1 source becomes a candidate for a future fresh preflight and a future
new pair only; it is never written back into the old pair's provenance.

## Fail-closed requirements

Materialization widens the attack surface from "read a file" to "materialize a
tree and load code from it", so the failure modes must be closed explicitly:

- the pinned commit is unreadable or absent → closed failure, no fallback to
  worktree bytes;
- materialized bytes differ from what the retained manifest records → closed
  failure;
- the retained manifest itself is mutated → closed failure, as today;
- materialization leaves residue, or a materialized path escapes its temporary
  root → closed failure;
- reconstruction succeeds but isolation was not achieved → closed failure;
- **no path in which a missing or broken historical input is answered by the
  active worktree.**

## Claim ceiling

The strongest claim is that **the retained historical artifacts reconstruct
exactly from the pinned commit**. That is what is verified today, minus the
accidental requirement that the present match the past.

It does not establish:

- that the pinned commit is what actually executed — the pin is a record, and
  this design preserves it rather than proving it;
- anything about the consumed pair's result, which remains `NON_SUCCESS`;
- that the active source is fit for any future execution; that needs its own
  fresh preflight and its own pair authorization.

## DONE for a Later Offline Implementation Tranche

`DONE = The historical verifier materializes SOURCE_COMMIT read-only and
reconstructs the retained contract manifest and candidate set from those bytes
and from historical modules executed only in a disposable child interpreter
with a fixed stdlib-only sys.path that does not include the materialized root,
a sanitized environment, -B and a closed repo-local import inventory supplied
solely by the verified-byte loader, with no comparison against worktree bytes and no
fallback to the active modules; the owner pin is validated against contract manifest fd6c75eb…, the
candidate set against db86a97b…, and the source commit named inside it against
204965c9…, with the executable inventory derived only from those verified bytes,
all before any historical code runs; the child executes verified byte buffers
through a closed loader rather than paths; a stale root from an earlier hard
crash fails closed and is never auto-deleted; every
retained manifest, pair-final digest, owner pin, source commit and pair identity
is byte-identical to today; the six regressions B-1 caused pass with the B-1 edits present,
while the one pre-existing failure is reported separately and never counted as
evidence of this conflict; tampering with the pinned source, the retained manifest or the
materialization fails closed; and no artifact asserts execution provenance beyond the retained binding to
204965c9….`

This is a proposed later tranche, not current implementation authority.

## Focused Offline Evidence Plan

1. reconstruction passes with the B-1 edits present in the worktree, and the
   six previously failing tests pass;
2. reconstruction passes with the worktree source deliberately altered further,
   proving independence from the present;
3. reconstruction reads historical values: an active module constant is changed
   and the reconstructed manifest is unaffected;
4. the parent imports no historical module: after reconstruction every active
   Gate 3 module in `sys.modules` is still the active one, byte-for-byte;
5. the child runs with a fixed `sys.path` holding only the interpreter's
   confirmed stdlib roots — the materialized root is asserted **absent** from
   it, so no repo-local module can be found on disk at all — with a sanitized
   environment and `-B`, and a repo-local import outside the closed inventory
   fails closed;
5a. a child failure produces a closed error and never falls back to the active
   modules;
5b. bootstrap validation rejects a tampered pin, digest, schema or path set
   **before** the child is started, asserted by proving the child never ran;
5c. the child executes byte buffers: a file substituted after verification but
   before execution is proven **not to run**, distinguishing this from a
   post-check that merely reports it;
5d. a repo-local import inside a historical module resolves from the verified
   byte map and cannot reach the filesystem;
5e. the child runs under `-I -S -B` with cwd, user site, `site-packages`,
   `PYTHONPATH` and the active repo root all absent, while stdlib imports still
   succeed;
5f. swapping the candidate set and the source commit together is rejected,
   proving the owner pin alone is not treated as covering them;
6. an unreadable or absent `SOURCE_COMMIT` fails closed;
7. mutating the retained contract manifest, the candidate set, or a materialized
   byte each fails closed;
8. no materialized path escapes the temporary root; a symlink, junction or
   reparse point at any position fails closed; the root's identity is checked,
   not only its path;
8a. cleanup runs on success and on handled failure; a simulated hard crash
   leaves the root in place, and the next run fails closed reporting that local
   recovery is required rather than deleting it;
9. the retained manifests, pair-final digest, owner pin, `SOURCE_COMMIT` and
   `PAIR_ID` are byte-identical before and after;
10. no artifact or claim token rebinds the consumed pair's retained authority to
    source other than `204965c9…`, and none asserts execution provenance the pin
    cannot establish;
11. the expected candidate-set digest is the frozen literal, proven by mutating
    the candidate set and confirming the expectation does not move with it.

### Evidence for the channel

Framing is where a "verified" buffer stops being verified if nobody checks the
frame, so each item names what would be false without it.

t1. a truncated header, and a truncated record, are both refused before
    anything is compiled;
t2. an unknown magic and an unknown version are refused, separately, so a
    future format cannot be mistaken for this one;
t3. each enforced bound is exercised at the limit and one past it: record
    count, path bytes, candidate-set bytes, per-file payload, aggregate
    payload. The derived whole-stream figure is not among them — it has no
    enforcement point, and a test written against it would either be
    unreachable or be testing one of the others under a different name;
t4. a header declaring an aggregate beyond the limit is refused **without**
    allocating from it, asserted by the refusal preceding any read of records;
t5. a duplicate path, an out-of-order pair, and a path failing the grammar are
    each refused;
t6. a payload whose digest does not match its framed digest is refused; so is
    one whose framed digest does not match the manifest, with the payload and
    framed digest mutually consistent — the case that a stream-only check would
    accept;
t7. a record whose declared length disagrees with the bytes that follow, and a
    stream with trailing bytes after the last record, are both refused;
t8. the authority chain, at each link: candidate-set bytes failing the frozen
    digest are refused before any record is read; a stream carrying a coherent
    extra module — correct framing, correct digest, absent from the derived
    inventory — is refused; and a mutation replacing the frozen literal with a
    value read from the stream must fail the suite, which is what shows the
    literal is load-bearing rather than decorative;
t9. structural: the child contains no path open of the materialized tree, no
    `pickle`, and no second transport — asserted over its source, with a
    synthetic case proving the check fires;
t10. no boundary handle is inheritable by the child;
t11. mutation: a child altered to compile bytes read from a materialized path
    instead of from the wire must fail the suite, which is what makes the rest
    of this list evidence rather than description.

## Affected Surfaces if Later Implemented

- `gate3_route_v2_ab_candidate.py` and `test_gate3_route_v2_ab_candidate.py`
- `gate3_route_v2_ab_checkout.py` and `test_gate3_route_v2_ab_checkout.py`
- possibly one small materialization helper module and its test

The retained manifests, published pair artifacts, owner pin, `PLAN.md`, memory
and every evidence path remain unchanged. **A change to any retained artifact
means this design chose wrongly and must be re-reviewed, not patched.**

## Review Questions

1. Is a disposable child interpreter acceptable, given it adds a process
   boundary to a previously in-process verifier?
2. Is the closed repo-local import inventory maintainable, or will it drift as
   the historical modules' dependencies are rediscovered?
3. The hard-crash policy is settled — no automatic deletion, next run fails
   closed reporting that local recovery is required. Confirm that choice is
   implementable as specified rather than reopening it.
4. Does removing the worktree-equality check lose a property worth keeping — for
   example, noticing that someone edited a file the old pair depended on?
5. Should this separation extend to the preflight receipts, which are pinned the
   same way and will face the same conflict at the next source change?

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, staging, commit, push, MR, merge, manifest update, owner-pin update
or promotion. B-1 implementation stays paused, Group C stays on hold, and the
consolidated contract slice is not started. Gate 3 remains `NON_SUCCESS`.
