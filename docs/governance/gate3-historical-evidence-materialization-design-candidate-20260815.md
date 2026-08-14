# Gate 3 Historical Evidence Materialization Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-15

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
| child | loads the materialized tree, where no active Gate 3 module exists, so historical modules may use their original names safely |
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

- the child reads each file once and verifies its exact digest;
- it compiles and executes **that byte buffer**, not the path;
- absolute imports resolve only from the verified module-byte map, so
  `import gate3_route_v2 as route` inside a historical module cannot reach a
  file at all;
- `__file__` may point at the materialized path for historical digest
  computation, but **no code is selected by that path**;
- the post-execution re-check judges whether the reconstruction result is
  acceptable. It no longer claims to prevent code substitution, because it
  cannot.

**AST parsing instead of execution is a rejected alternative**, recorded so it
is not revisited: it trades fidelity to what actually ran for a narrower blast
radius, and keeping it alongside executable loading as an implementation-time
choice would leave two reconstruction semantics.

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
6. verify the exact path set, the bytes and each digest, rejecting any
   additional repo-local module;
7. start the child;
8. after the child returns, re-check the materialized bytes — see the limit on
   what that check can and cannot do, below.

### Temporary root: identity, sealing and crash semantics

Calling the tree "read-only" is not a mechanism. The contract:

- the materialized root is created private to this process and its **identity**
  is captured, not just its path, so a replacement is detectable;
- every materialized path is containment-checked against that root; a symlink,
  junction or reparse point at any position fails closed;
- the digests recorded during validation are re-checked after the child
  returns. **This does not close the validation-to-use window** — the custom
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
with a fixed materialized sys.path, sanitized environment, -B and a closed
repo-local import inventory, with no comparison against worktree bytes and no
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
5. the child runs with a fixed materialized `sys.path`, sanitized environment
   and `-B`, and a repo-local import outside the closed inventory fails closed;
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
