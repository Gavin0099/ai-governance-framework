# Gate 3 M3-b — The Isolated Child and the Closed Loader

Status: design-only candidate; not approved, not implemented, and not execution
authority. No child process was started to write this, no historical module was
imported, nothing was compiled and nothing was materialized. Every statement
about the historical modules below comes from reading their bytes at
`SOURCE_COMMIT`, not from running them.

Date: 2026-08-19

Revision: 6 — puts `f26` and `f27` where the work actually is.

Revision 5 excluded `f26`, `f27` and `f28` from M3-b-1 together, on the ground
that they belong to the parent-side result object and therefore to `BLOCKED-2`.
That is true of `f28` and false of the other two. `f26` is the frame's label
set — completeness, grammar, ordering, duplicates — and `f27` is the frame's own
internal consistency, a digest label against the bytes it travels with. Both are
decisions the decoder has to make before it can return anything at all, so an
M3-b-1 that omitted them would return a frame it had not finished checking.

The distinction the exclusion was reaching for is real and is now stated
directly: **the verified frame is not the reconstruction result.** `decode_result`
returns four verified values; what a passing reconstruction *means* — including
the two `"not asserted"` markers recording checks that were retired — is the
result object, and that stays behind `BLOCKED-2`.

`f28` is unchanged and still excluded.

Revision 5 — retires the scratch rules revision 4 replaced but left standing,
and corrects two evidence items.

Revision 4 wrote the new two-branch scratch rule and left three older statements
requiring unconditional removal — in the teardown order, in the
`SCRATCH_RESIDUE` anchor and in `f23`. That is the same shape this work stream
has now produced several times: **a specification that does not retire beside
the thing that replaced it.** The document said both, so it specified neither.
Both branches are now written as transactions, and the non-empty one states its
handle release explicitly, because preserving disk evidence while leaking native
handles would be a different leak rather than none.

`f24` asserted a directory was "byte-identical", which is not an observable a
directory has. It now names identity and immediate inventory. `M3-b-1`'s
boundary now says in words that the parent-side result object and its two
markers wait for `BLOCKED-2`, so nobody builds an unauthorized verification
contract early.

Revision 4 — closes four blocking findings and one warning. Two of them were
places where revision 3 specified an action that would leave a real resource
behind.

- a non-empty scratch directory could not be cleaned as specified. The boundary
  deletes objects it holds handles for; it cannot enumerate, open and adopt
  whatever the child created. "Non-empty is not a failure", "no path-based
  cleanup" and "the directory confirms absent" cannot all hold. Non-empty is now
  `SCRATCH_RESIDUE`: the directory is preserved and no absence is claimed.
- closing the handles of a suspended process does not terminate it. Revision 3's
  unwind would have left a live process nobody holds. The unwind now terminates
  first and waits, and its evidence asserts the process is gone rather than
  counting handles.
- the second native boundary is not closed by naming its calls. It needs
  layouts, ownership, unwind and error translation of its own, and
  `NATIVE-INTEROP.md` requires those before implementation. It is now
  `BLOCKED-3`, and M3-b-2 does not begin without its own design slice.
- `f19` called itself the only out-of-process item while `f21` and `f21b` start
  processes. Reclassified.
- `f28`'s "not asserted" markers had nowhere to live. A parent-side result type
  is defined, and the markers are constructed there and never derived from the
  child's stream.

Revision 3 — closes four review findings, two of which were errors of fact in
revision 2 rather than gaps.

- "the two repository checks move to the parent" was not a resolution. Run
  against the real repository they compare the **live worktree** to the pinned
  commit, which is exactly the coupling B-1 is blocked on and M4 exists to
  remove; run against the materialized tree they compare a git blob to bytes
  materialized from that blob. Neither is worth doing. They are **retired**,
  and retiring a check is a change to the verification contract, so it is
  marked `BLOCKED-2` with the literal amendment rather than described as a
  relocation.
- state 5 was called the first execution of historical code. It is not:
  `exec_module` runs each module's top-level code, so **state 4** is where
  historical code first executes. Three places also hard-coded "the four
  modules" while `BLOCKED-1` proposes a fifth; they now name the runtime
  inventory.
- the job object could not be implemented as written. Closing the last handle
  terminates the processes *and destroys the job*, so nothing remains to query
  for the active count the design required as its observation. Kill and
  observation are now ordered, `KILL_ON_JOB_CLOSE` is demoted to a crash
  backstop, and the native adapter it needs is named in the affected surfaces.
- the scratch directory was created and deleted by path under the platform
  temporary root, reintroducing the hostile-name and replacement class that
  N3c-2 already closed. It is now created, held and removed through the
  boundary under a pre-existing pinned scratch base.

Revision 2 — closes five review findings, one of which changes what the child
is for.

- `BLOCKED-2` was written as though the isolation table's wording were the
  obstacle. It is not. The historical verifier runs `git show` and
  `git check-attr` with `cwd=REPO_ROOT`, and a materialized tree contains
  retained files and no `.git`, so those calls cannot succeed there whatever the
  table says. Reading the bytes again showed the two git calls live only in
  `_verify_source_commit_inputs` and `_verify_byte_preservation_attributes`,
  which `verify_candidate()` composes — **not** in the two builders. The child
  now calls the builders and nothing else, and the two repository checks are
  retired rather than relocated — see `BLOCKED-2`.
- Teardown reclaimed only the direct child while the design permitted historical
  code to start git. A surviving grandchild falsifies the premise that no
  process is reading through a name when handles are released. A job object now
  owns the tree.
- The child's working directory was the borrowed `base`, three sections before
  a claim that `base` is never touched. `-I` constrains imports, not writes.
  M3-b now creates and owns a scratch directory, and owes its removal.
- `PYTHONHASHSEED=0` cannot do what it was there for: `-I` implies `-E`, so
  every `PYTHON*` variable is ignored. Measured — under `-I -S -B` with the
  variable set, `sys.flags.hash_randomization` is `1`, and without `-I` it is
  `0`. The determinism claim is withdrawn and re-grounded.
- `stderr` bytes were to be attached to failures while `f18` forbade failures
  carrying source text or tracebacks. `stderr` is the channel most likely to
  carry both. Only its length, truncation flag and digest survive.

Revision 1 — initial candidate.

Base: `feat/gate3-historical-materialization@62da7b6f63de297b0400683d83fec2d841456d08`

Subordinate to:

- `docs/governance/gate3-m3-child-transport-design-candidate-20260818.md`
  revision 5 — the transport, the wire grammar, the trusted computing base;
- `docs/governance/gate3-historical-evidence-materialization-design-candidate-20260815.md`
  revision 10 — the framing table, the bounds, the authority chain, the
  isolation table;
- the delivered M3-a, commit `daf4ec5e`, implementation SHA-256
  `4c47710923f951c474e4c332850e9aa31b6ee9015886b3efaa617a96fe6cdd86`.

**This document restates none of them, and amends none of them.** Two places
where it cannot be implemented without an amendment are marked `BLOCKED`, each
with the literal amendment written out so it can be reviewed as a diff. Neither
is made here. `BLOCKED-2` is not the one revision 1 carried under that name:
that one dissolved once the entrypoint was split, and a different, larger one
took its place — retiring two checks changes what verification means.

---

## Problem

Gate 3's historical evidence is verified today by rebuilding the retained
contract manifest and candidate set and comparing them byte-for-byte. That
rebuild runs the *active* modules in the *active* interpreter. The consequence
is recorded in `PLAN.md` and is the reason this work stream exists: the
historical artifacts only reconstruct while the implementing source never
moves, so an ordinary improvement to `gate3_route_v2.py` breaks the record of
something that already happened. B-1 is blocked on exactly this.

M1 established the authority chain, M2 materializes the pinned commit behind
held handles, and M3-a carries verified bytes over a bounded framed stream. The
gap left is the one that actually runs the historical code, and it is the gap
with the largest blast radius in the work stream: **M3-b is the first tranche
that executes bytes selected by something other than the active worktree.**

The narrow problem it must solve: give the reconstruction its historical
dependencies without giving it, or anything it calls, a path back to the
present.

## Current repository truth

Read rather than assumed:

- `gate3_historical_bootstrap.RUNTIME_MODULE_ALLOWLIST` names exactly four
  modules — `gate3_route_v2.py`, `gate3_route_v2_ab.py`,
  `gate3_route_v2_ab_live.py`, `gate3_route_v2_codex.py`. The retained
  candidate set records eleven files; the other seven are data, a design
  document, a test module and the candidate verifier itself.
- The reconstruction entrypoints are
  `gate3_route_v2_ab_candidate.build_contract_manifest()` and
  `build_candidate_set(contract)`, with `verify_candidate()` composing them.
  **That module is not in the allowlist.** See `BLOCKED-1`.
- That module resolves its inputs by path: `HERE = Path(__file__).resolve()
  .parent`, `REPO_ROOT = HERE.parents[3]`, and it reads at least the preflight
  JSON, the contract manifest, the candidate set, `.gitattributes` and the
  treatment packet from those roots. It also imports `subprocess` and runs
  `git show` and `git check-attr` with `cwd=REPO_ROOT` — but only from
  `verify_candidate()`, not from the two builders. See *The split entrypoint*.
- M3-a's public surface is `encode_stream(candidate_set_bytes, payloads)`,
  `decode_stream(stream) -> {path: bytes}`, `derive_inventory(bytes)`,
  `ACTIVE = False`, and `TransportError(code)`. It defines no `__main__` and a
  test asserts that.
- Measured on this interpreter (CPython 3.12.10): a script run by path under
  `-I -S -B` sees exactly four `sys.path` entries, all under the interpreter's
  own installation, with `site-packages` absent and the script's own directory
  absent.
- `handle_boundary_available()` reports `False`, so M2 cannot materialize
  anything today. M3-b is therefore specified against a materialized tree that
  does not yet exist at runtime, and its evidence plan is built accordingly.

## Target outcome

A parent that can hand a disposable child interpreter the verified bytes of the
historical runtime inventory — four modules today, five if `BLOCKED-1` is
resolved by amendment — have the reconstruction run there, and receive
back nothing but canonical bytes and digests — with every step that could
reintroduce the present named and refused, and with the steps that *cannot* be
refused named as accepted assumptions rather than quietly omitted.

## Scope

1. The spawn: executable, arguments, working directory, environment, standard
   streams, handle inheritance.
2. Stream-in: how the M3-a frame reaches the child and where authority
   validation sits relative to everything else the child does.
3. The closed loader: a `MetaPathFinder`/`Loader` pair over the verified buffer
   map, and the exact module identity it produces.
4. The execution state machine: what runs, in what order, and what each state
   is allowed to touch.
5. The return channel: framing, bounds, and every way it can fail.
6. Teardown ordering against M2 cleanup.
7. The closed failure codes and, for each, the observable that anchors it.
8. An evidence plan with mutation sensitivity.

## Non-goals

- No amendment to M3 revision 5 or historical revision 10. Where this design
  cannot proceed without one, it stops and quotes the amendment.
- No implementation, no tests, no spawn, no compile, no historical execution.
- No M4 wiring, no change to `ACTIVE` or to any availability predicate.
- No change to the owner pin, the retained manifest, the candidate set,
  `SOURCE_COMMIT` or the consumed pair's `NON_SUCCESS` result.
- No attempt to solve the runner trust root or its TOCTOU window. Those remain
  accepted assumptions of M3 — see *Trust boundaries carried forward*.
- Nothing about B-1, the `Two tranches so far` docstring, the session closeout,
  or any other dirty path.

## Affected surfaces

| Surface | Change |
| --- | --- |
| `gate3_historical_child.py` | gains a `__main__` role: decode, derive, install the loader, run, emit. The importable surface M3-a delivered is unchanged |
| a new parent-side spawn module | builds the argument vector, writes the stream, reads the result, maps every failure to a closed code |
| `gate3_historical_materialize` | no change; M3-b consumes `MaterializedTree` through the existing read surface, and must materialize all eleven retained files rather than the runtime inventory alone |
| the verification contract | two checks retired, not reimplemented — `BLOCKED-2` |
| `gate3_historical_bootstrap` | no change unless `BLOCKED-1` is resolved by amendment |
| a new native process-control adapter | a **second native boundary**, and not something this document closes. See `BLOCKED-3` |

Architecture-impact preview for the touched module, run at proposal time:
`recommended_risk=medium`, `recommended_oversight=review-required`,
`expected_validators=architecture_drift_checker`,
`required_evidence=architecture-review`. It is **provisional**: the parent-side
spawn module does not exist yet, so the estimate covers only the file that does.

---

## 1. The spawn

**Executable.** `sys.executable` of the parent, resolved once and passed as an
absolute path. Not `python`, not a `PATH` lookup, not a shell. A `PATH` lookup
is a name resolution, and name resolution is what this design removes; a shell
adds a second interpreter of the argument vector.

If `sys.executable` is empty — it can be, in embedded interpreters — the parent
refuses with `CHILD_EXECUTABLE_UNAVAILABLE` rather than substituting a guess.

**Arguments.** Exactly `[executable, "-I", "-S", "-B", runner_path]`. No `-c`,
no `-m`, no module search. `runner_path` is `gate3_historical_child.__file__`
resolved to an absolute path in the parent.

Why by path and not `-c` with the source inlined: `-c` would mean the parent
reads the runner's bytes and hands them over, which makes the parent the
selector of the trusted code as well as of the untrusted code, and puts the
runner's text inside a command line whose length and quoting are platform
business. The path form keeps one selector.

`-I` is what removes the script's directory from `sys.path` — measured, and the
measurement is the reason this is safe to do by path. `-S` removes
`site-packages`. `-B` stops the child writing bytecode next to files it is
reading, which would be a write into a tree the design says nothing writes to.

**Working directory.** An **M3-b-owned scratch directory**, created for this
run and removed by this design. Not the repository, not the materialized tree,
and — corrected from revision 1 — **not `base`**.

`base` is borrowed. Revision 1 made it the child's cwd and then asserted three
sections later that `base` is never touched, which cannot both be true once
anything in the child writes a relative path. `-I` constrains the import path;
it does not stop a `open("out.txt", "w")` anywhere in historical code or in
anything it starts.

The scratch directory is therefore an object M3-b creates, and creating it means
owing its deletion. **It is created through the native boundary, not by path.**
Revision 2 put it under the platform temporary root with an ordinary `mkdir` and
an ordinary `rmtree`, which reintroduces the whole class N3c-2 already closed: a
pre-existing name, a junction planted at the name, a replacement between the
check and the delete. "M3-b owns it" is not evidence that what gets deleted is
what got created.

The lifecycle mirrors the materialized root's, because it has the same problem:

- a **scratch base** that already exists and is supplied by the caller, pinned
  by the boundary as a role 1 borrowed ancestor. It is never created, deleted or
  marked here — the same obligation split `base` carries;
- the scratch directory is created **handle-relative** under that pinned base,
  as a role 2 created directory, so no name is resolved between the check and
  the use;
- its absence is confirmed through the boundary's absence probe before creation,
  and a name that is already present fails closed rather than being adopted;
- its **identity** is captured, not just its path, so a replacement is
  detectable;
- it is removed through the handle that created it — mark, close, confirm
  absent — which is why removal deletes the object it created and not whatever
  now answers to the name;
- a reparse point at any position fails closed, which is what a junction planted
  by the child would produce;
- `TEMP` and `TMP` in the child's environment point at it, so a library reaching
  for a temporary file lands inside the thing that will be removed rather than
  somewhere nobody is watching;
- removal, when it happens, is after the tree is confirmed gone and before the
  M2 cleanup begins;
- **an empty scratch directory is removed; a non-empty one is not.** Revision 3
  said non-empty was merely recorded and removal still confirmed absence. That
  cannot be built. The boundary removes objects it holds handles for, and it has
  no handle on anything the child created; adopting those objects would mean
  enumerating and opening by name, which is the resolution this design removed.
  Adding a handle-relative enumerate-open-delete surface is a tranche of its own
  and is not proposed here.

  So the rule is the one that can actually be executed:

  | Observed | Behaviour |
  | --- | --- |
  | scratch directory empty | removed through the creating handle, absence confirmed |
  | scratch directory non-empty | **`SCRATCH_RESIDUE`**. Nothing is deleted, the directory is preserved as it stands, and no absence is claimed |

  Preserving it is not a fallback, it is the point: a reconstruction that wrote
  files is a fact, and the residue is the evidence of it. Removing what we
  cannot enumerate safely, or claiming an absence nobody confirmed, are the two
  failures this work stream keeps being built to avoid;
- on a hard crash it is not removed automatically, matching revision 10's
  policy for the materialized root.

**Environment.** A constructed mapping, not a filtered copy. The child receives
only what the platform requires to start a process — on Windows, `SYSTEMROOT`,
`COMSPEC`, `PATHEXT`, `NUMBER_OF_PROCESSORS`, and `TEMP` and `TMP` pointing at
the scratch directory above. `PATH` is **absent**, which is deliberate now that
nothing the child runs is supposed to find an executable: see *The split
entrypoint*.
`PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP` and every `GATE3_*` variable are
absent by construction. Filtering a copy is rejected: it fails open on any
variable nobody thought of.

**No `PYTHONHASHSEED`, and the claim it supported is withdrawn.** Revision 1 set
it to `0` so that two reconstructions would be comparable. It cannot do that:
`-I` implies `-E`, so the interpreter ignores every `PYTHON*` variable.
Measured on this interpreter — under `-I -S -B` with `PYTHONHASHSEED=0` set,
`sys.flags.ignore_environment` is `1` and `sys.flags.hash_randomization` is
`1`; without `-I`, the same variable gives `0`. The variable would have been
visible in `os.environ` and inert, which is the worst kind of setting: it reads
as a guarantee and provides none.

What actually makes two reconstructions comparable is that the historical code
canonicalizes its own output — the manifest and candidate set are built through
a canonical JSON serializer with sorted keys, which is why they can be compared
byte-for-byte at all. That property belongs to the historical code and is not
something M3-b establishes. If a future measurement shows the reconstruction is
in fact hash-order sensitive, the answer is `-R`'s opposite on the command line,
not an environment variable, and it would need its own evidence.

**Handle inheritance.** `close_fds=True`, and on Windows no handle is added to
the inheritable set. No native handle from the boundary is passed. This is what
makes the statement "the child holds no capability over the materialized tree"
true of the *handles*; it is not a claim that the child could not open a
materialized file by name, and the measurement in M3 revision 5 shows a native
reader sharing read, write and delete can.

**Standard streams.** `stdin` is a pipe carrying the framed stream; `stdout` is
a pipe carrying the framed result; `stderr` is a pipe, drained to a bounded
buffer so the child cannot block on a full pipe, and **never parsed**. A channel
that is parsed is a channel that can be spoken to.

**`stderr` content does not leave the parent.** Revision 1 attached the capped
bytes to failures, which contradicted `f18` in the same document: `stderr` is
exactly where a Python traceback, a source excerpt and a filesystem path appear.
What a failure carries instead is three facts about the channel and none of its
content:

| Kept | Why |
| --- | --- |
| byte length | says something was written without saying what |
| truncated flag | distinguishes "quiet" from "capped" |
| SHA-256 of the captured bytes | two runs failing the same way are comparable, and a human with the child in front of them can confirm a match |

The digest is an **equality fingerprint**, and revision 2 over-claimed it as
revealing nothing. It does reveal equality, and against a low-entropy candidate
space — a handful of expected messages — it confirms which one occurred. The
accurate statement is narrower and is the one that holds: the failure carries no
raw bytes, so no traceback, source excerpt or filesystem path leaves the parent;
what it carries is length, truncation and an equality fingerprint.

## 2. Stream-in, and where authority sits

The parent writes the M3-a frame to the child's stdin and closes it. The child
reads stdin to end-of-file into one buffer, bounded by
`DERIVED_MAX_STREAM_BYTES + 1`; one byte past the derived maximum is enough to
distinguish "at the maximum" from "beyond it" without reading an unbounded
stream.

The child then calls `decode_stream` **before it does anything else that could
be observed** — before the loader is constructed, before any historical name
exists, before `sys.meta_path` is touched. `decode_stream` already checks the
candidate-set block against the frozen digest before parsing any record, and
M3-a evidences that with a parse spy. M3-b adds no second authority and removes
none.

Deadlock is a real failure mode here and is designed against rather than hoped
about: the parent writes stdin and reads stdout from separate threads, or uses
a single `communicate`-style call that services all three pipes. A parent that
writes the whole stream before reading stdout will hang on a child that fills
its stdout pipe first.

## 3. The closed loader

A `MetaPathFinder` inserted at `sys.meta_path[0]`, holding the verified buffer
map returned by `decode_stream`, keyed by the repo-relative paths the inventory
uses and answering on the *module names* those paths imply.

- **Name mapping.** `artifacts/.../gate3_route_v2.py` answers the top-level
  name `gate3_route_v2`. The mapping is computed from the path's final
  component with `.py` removed, and any path that does not end in `.py`, or
  whose stem is not a valid identifier, fails closed. It is not derived from
  package structure: these modules import each other by bare absolute name, as
  their bytes show.
- **No packages.** Every loaded module is top-level. `__package__` is `""` and
  `submodule_search_locations` is `None`, so no submodule search can occur.
- **`__file__`.** Set to the materialized path for the module, because the
  historical code computes digests and roots from it. **This is the point where
  the design stops being able to promise isolation** — see *The split
  entrypoint*.
- **`__spec__`.** A real `ModuleSpec` with `origin` equal to that same path and
  `has_location` true, because tooling and `inspect` will look; `loader` is this
  loader, so nothing can be reloaded through a different one.
- **`__cached__`.** `None`. With `-B` nothing writes bytecode, and an absent
  attribute is a clearer statement than a path to a file that will never exist.
- **`sys.modules`.** Populated before `exec_module`, as the import protocol
  requires, so the circular absolute imports between these four modules resolve
  to the same objects.
- **Compilation.** `compile(buffer, path, "exec", dont_inherit=True)` then
  `exec` in the module's namespace. `dont_inherit` so the parent's `__future__`
  state cannot change how historical source is compiled.

**Standard library imports pass through untouched.** The finder returns `None`
for any name not in its map, and the ordinary `sys.path` finders behind it
resolve `json`, `pathlib`, `hashlib` and the rest from the four stdlib roots.
It is not a whitelist of stdlib names: an allowlist there would have to be
maintained against a stdlib the historical code was written before, and getting
it wrong fails closed at a place with no useful diagnosis.

**A repo-local name outside the map fails closed.** The finder cannot
distinguish "repo-local" from "third-party" by name alone, so the rule is
positional rather than nominal: after the runtime inventory is loaded, the
child
asserts that `sys.modules` contains no module whose `__file__` is under the
materialized root and whose spec's loader is not this loader. That check is
observable and is where `LOADER_BYPASSED` comes from.

## 4. Execution state machine

Six states. Each names what it may touch, and the ordering is the property.

| # | State | May touch | Failure |
| --- | --- | --- | --- |
| 1 | `READ_STREAM` | stdin only | `STREAM_UNREADABLE`, `STREAM_TOO_LARGE` |
| 2 | `VERIFY` | the buffer, the frozen literals | any `TransportError` code, unchanged |
| 3 | `INSTALL_LOADER` | `sys.meta_path` | `LOADER_INSTALL_FAILED` |
| 4 | `LOAD` | the buffer map, stdlib | `MODULE_COMPILE_FAILED`, `MODULE_EXEC_FAILED`, `LOADER_BYPASSED` |
| 5 | `RECONSTRUCT` | the historical entrypoint | `RECONSTRUCTION_FAILED` |
| 6 | `EMIT` | stdout | `RESULT_TOO_LARGE`, `EMIT_FAILED` |

`VERIFY` completes before `INSTALL_LOADER` begins, and `INSTALL_LOADER` before
any historical name is resolvable. No state is re-entered; there is no retry
anywhere in the child, because a retry would mean a second execution of
historical code after a failure nobody has diagnosed.

**State 4 is the first execution of historical code in this work stream**, not
state 5. Revision 2 said state 5, which is wrong in a way worth being exact
about: `exec_module` runs each module's top-level body, and these modules do
real work there — module-level constants, path resolution, digest computation.
By the time state 4 completes, historical code has already run.

State 5 is the first *call into a reconstruction entrypoint*. That distinction
matters for the tranche split below: M3-b-1 and M3-b-2 use fixture modules
precisely so that state 4 can be evidenced without any historical top-level
body running, and only M3-b-3 executes the real ones. What state 5 calls is
`BLOCKED-1`.

## 5. The return channel

**Framing.** The same shape as the inbound stream and deliberately not the same
format, because the two carry different things and a shared decoder would make
a confused-deputy mistake possible. Magic `GATE3HR\0`, version `u16 = 1`, entry
count `u16`, then per entry: label length `u16`, label bytes, value length
`u32`, value bytes. All little-endian, unsigned, fixed width.

**Bounds.** 16 entries, 64 label bytes, 1,048,576 value bytes per entry,
4,194,304 aggregate. Derived stream maximum `4,195,436` — header 12, per-entry
framing at most `16 x 70 = 1,120`, aggregate 4,194,304 — recorded as arithmetic
and **not** enforced as a separate gate, for the reason revision 10 gives. It is
checked by the same kind of test M3-a uses, which recomputes the figure from the
bounds so that changing a bound without changing the constant fails.

**Content.** Canonical bytes and hex digests only. No pickle, no JSON of
arbitrary objects, no paths — a returned path would be a name the parent might
resolve, and resolving a name the child chose is the whole failure this design
exists to avoid.

**The frozen label set, exactly.** Revision 1 said only that labels outside a
frozen set are refused, which does not produce a unique frame. The set is four
labels and they are all required:

| Label | Value |
| --- | --- |
| `contract_manifest` | the rebuilt contract manifest bytes |
| `contract_manifest_sha256` | 64 lowercase hex characters |
| `candidate_set` | the rebuilt candidate set bytes |
| `candidate_set_sha256` | 64 lowercase hex characters |

- **Grammar.** A label is one to sixty-four bytes matching `[a-z][a-z0-9_]*`
  after strict UTF-8 decode, with the same byte-round-trip postcondition the
  wire path grammar carries and for the same reason.
- **Order.** Entries ascend by the bytewise comparison of their UTF-8 label
  bytes. Two runs producing the same result therefore produce byte-identical
  frames, which is what makes the frame itself comparable.
- **Duplicates.** Refused. Equal adjacent labels are `RESULT_DUPLICATE_LABEL`,
  distinct from an ordering failure.
- **Completeness.** The set must be exactly these four — no extra, none
  missing. A partial result is not a result: a frame carrying the manifest but
  not its digest would leave the parent choosing which of two things to
  believe.
- The parent's **result object is not the frame**, and this is where `f28`'s
  markers live. The frame carries four labels and nothing else; the parent
  constructs a result from it, and that result carries two additional fields —
  `source_commit_comparison: "not asserted"` and
  `byte_preservation_check: "not asserted"` — as literals in parent-side code,
  per `BLOCKED-2`. They are **never** read from the child's stream, are not
  labels, and a frame attempting to supply them is refused by the completeness
  rule above. A marker the child could set would be a marker the child could
  clear.

- The two digest labels are recomputed by the reader from the two byte labels
  and compared. This is the frame checking itself, not the reconstruction being
  verified: it establishes that the frame does not claim a digest for bytes it
  did not carry, and nothing more. The comparison that matters — against the
  retained artifacts — happens after the frame is accepted, in the result
  object.

**Where the boundary falls.** `decode_result` returns four verified values and
stops. Everything about what those values *mean* — whether the reconstruction
matches the retained artifacts, and the two `"not asserted"` markers recording
the checks `BLOCKED-2` retires — belongs to the result object, which does not
exist yet. The frame is finished when it is internally consistent; the result is
finished when it says something about history. A child agreeing with itself proves nothing; the comparison
  that matters is against the retained artifacts, and that happens in the
  parent after the frame is accepted.

**Failure handling.**

| Situation | Parent behaviour |
| --- | --- |
| non-zero exit | `CHILD_FAILED`, with the exit status and the `stderr` length, truncation flag and digest — never its bytes |
| exit zero, malformed frame | `RESULT_MALFORMED`. Not "assume nothing was produced" |
| exit zero, trailing bytes | `RESULT_TRAILING_BYTES`, distinct from malformed |
| timeout | `CHILD_TIMEOUT` after a wall-clock bound, then terminate, then kill after a grace period, then reap. The result is discarded even if bytes arrived |
| child killed by a signal | `CHILD_SIGNALLED`, distinct from a non-zero exit, because a crash and a refusal are different facts |
| stdout closed early | `RESULT_TRUNCATED` |

A timeout that leaves a process alive is a leak, so the parent reaps
unconditionally in a `finally`, and a failure to reap is attached to the
original error rather than replacing it — the same rule M2 already applies to
cleanup failures.

## 6. Teardown ordering, and the process tree

Revision 1 reclaimed the direct child and called that teardown. It is not.
`subprocess` remains importable in the child, so a descendant can outlive the
interpreter that started it — and a surviving grandchild falsifies the premise
the whole ordering rests on, that no process is reading through a name when
handles are released. The split entrypoint means no descendant is *expected*;
the mechanism below exists because expectation is not a containment boundary.

**The tree is owned, not just the child.**

- On Windows: a **job object**, with the child assigned to it before the
  child's main thread runs — created suspended, assigned, then resumed, so
  there is no window in which the child could spawn outside the job.

  Revision 2 then said that closing the job handle terminates the tree *and*
  that the active process count is queried to confirm it. Those two cannot both
  happen: closing the last handle terminates the processes and destroys the
  job, and a destroyed job cannot be queried. The order is now explicit:

  | Step | Call | Why |
  | --- | --- | --- |
  | 1 | `TerminateJobObject` | the handled path. It kills the tree while the job and its handle still exist |
  | 2 | wait on the child, then poll `QueryInformationJobObject` with `JobObjectBasicAccountingInformation` until `ActiveProcesses == 0` | this is the observation, and it is only possible because step 1 did not destroy the job |
  | 3 | `CloseHandle` on the job | last, once there is nothing left to observe |

  **The unwind before assignment is a different path and revision 3 got it
  wrong.** A process created with `CREATE_SUSPENDED` that never reaches
  `AssignProcessToJobObject` is in no job, so nothing kills it when a handle
  closes — and closing its process and thread handles does not terminate it. It
  is suspended, unreferenced, and alive. The failure path is therefore
  `TerminateProcess`, then `WaitForSingleObject` on the process, then
  `CloseHandle` on the thread and the process, in that order. Whether the
  assignment succeeded decides which unwind applies, so the adapter records that
  transition rather than inferring it.

  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` is still set, but **demoted to a
  crash backstop**: if the parent dies without reaching step 1, the handle
  closes with it and the tree goes with the handle. It is not the mechanism the
  handled path relies on, and it is not what any evidence item asserts.
- On POSIX: a new process group via `start_new_session`, signalled as a group.
  Recorded for completeness; this work stream runs on Windows and the job
  object is the mechanism that will be built and evidenced.

`CHILD_TREE_SURVIVED` is raised when the active process count does not reach
zero within the grace period. It is distinct from `CHILD_TIMEOUT`, because a
child that ignored a deadline and a tree that outlived its owner are different
facts with different consequences.

**The order, and the order is the property:**

1. the child exits, or is terminated; then the **job reports zero active
   processes**. Only then is step 2 allowed to begin. **No handle is released
   while any process in the tree might still be reading through a name.**
2. the parent re-reads each leaf through the handle that created it and
   re-checks its digest — revision 10's step 8. This detects; it does not
   prevent, and the design already says so.
3. the scratch directory is enumerated once, and exactly one of two
   transactions runs:

   | Observed | Transaction |
   | --- | --- |
   | empty | `remove` through the creating handle, then `confirm_absent`. Failure to confirm absence is `SCRATCH_RESIDUE` |
   | non-empty | the inventory is recorded; **nothing is marked for deletion**; the scratch handle and the borrowed chain above it are closed; `SCRATCH_RESIDUE` is reported with the directory and its contents left in place |

   The non-empty branch releases handles even though it deletes nothing.
   Preserving the evidence on disk while holding the handles open would trade a
   filesystem leak for a handle leak, and closing an unmarked handle starts no
   deletion — the same property M2's teardown already relies on.
4. M2 `cleanup(tree)` runs: mark, close, confirm absent, per object.
5. `base` is not touched. It is borrowed, and — corrected from revision 1 — it
   is not the child's working directory either.

Cleanup runs on success and on any handled failure. A failure in any teardown
step is attached to the error that caused the teardown and never replaces it,
the same rule M2 already applies. A hard crash of the parent leaves residue and
makes no completion claim, which is revision 10's chosen policy and is not
reopened here.

## 7. Closed failure codes and their anchors

Every code below is anchored to something observable, because a code whose
trigger cannot be observed cannot be tested and will not be maintained.

| Code | Anchor |
| --- | --- |
| `CHILD_EXECUTABLE_UNAVAILABLE` | `sys.executable` is empty or missing |
| `CHILD_SPAWN_FAILED` | the platform refused to create the process |
| `CHILD_TIMEOUT` | wall clock exceeded before exit |
| `CHILD_TREE_SURVIVED` | the job's active process count did not reach zero within the grace period |
| `SCRATCH_RESIDUE` | either the scratch directory was non-empty and was therefore preserved rather than removed, or it was empty and did not confirm absent after removal. Both are the same report because both mean the same thing to the caller: the directory is still there |
| `CHILD_SIGNALLED` | **POSIX only**: a negative return code, which is Python's signal convention there. Windows has no equivalent — a terminated process reports an ordinary non-zero status — so on Windows this code is never raised and `CHILD_FAILED` carries the status instead. Recorded as platform-conditional rather than left to look universal |
| `CHILD_FAILED` | non-zero exit status |
| `STREAM_UNREADABLE` / `STREAM_TOO_LARGE` | stdin read result in the child |
| `LOADER_INSTALL_FAILED` | `sys.meta_path` did not gain the finder |
| `LOADER_BYPASSED` | a module under the materialized root whose loader is not ours |
| `MODULE_COMPILE_FAILED` / `MODULE_EXEC_FAILED` | the failing module's name only |
| `RECONSTRUCTION_FAILED` | the entrypoint raised; its message is not forwarded |
| `RESULT_MALFORMED` / `RESULT_TRAILING_BYTES` / `RESULT_TRUNCATED` / `RESULT_TOO_LARGE` | the returned bytes |
| `RESULT_LABEL_INVALID` | a label failing the grammar |
| `RESULT_DUPLICATE_LABEL` / `RESULT_LABEL_ORDER_INVALID` | adjacent labels equal, or descending |
| `RESULT_INCOMPLETE` | the label set is not exactly the frozen four |
| `RESULT_DIGEST_MISMATCH` | a returned digest differs from the parent's recomputation |
| `EMIT_FAILED` | the child could not write stdout |

No code carries artifact content, source text or an exception message from
historical code. `MODULE_EXEC_FAILED` carries a module name because the name is
already in the frozen inventory; a traceback would carry source. `CHILD_FAILED`
carries the `stderr` length, truncation flag and digest, and never the bytes —
revision 1 attached the bytes, which contradicted `f18` in the same document.

---

## BLOCKED-1: the reconstruction entrypoint is not in the runtime allowlist

`RUNTIME_MODULE_ALLOWLIST` is four modules. The functions that rebuild the
retained artifacts — `build_contract_manifest()` and `build_candidate_set()` —
live in `gate3_route_v2_ab_candidate.py`, which is in the retained eleven-file
inventory but **not** in the allowlist, and is therefore not among the buffers
the child receives.

Three ways forward. The first is recommended.

**(a) Extend the allowlist to five, by amendment.** The literal change to
`gate3_historical_bootstrap.RUNTIME_MODULE_ALLOWLIST`, and to the identical
frozen tuple in `gate3_historical_child`, is to add:

> `"artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"`
> `"gate3_route_v2_ab_candidate.py",`

with the comment above it updated from "Only these four are historical *runtime
modules*" to name five and to say why the verifier is one of them: it is the
module whose execution *is* the reconstruction, and loading it from the pinned
commit is the difference between reconstructing history and re-running the
present. This widens executable authority by one module and must be reviewed as
such.

**(b) Re-implement the composition in the trusted runner.** Rejected. It would
copy roughly a hundred lines of argument assembly into present-day code, and
the copy would be the thing that decides what history was.

**(c) Have the parent call it.** Rejected outright: the parent importing a
historical module is the one thing revision 10's isolation table forbids
without qualification.

**Until an amendment is authorized, state 5 has no defined callee and M3-b
cannot be implemented.** No amendment is made in this document.

## The split entrypoint: what runs in the child, and what cannot

Revision 1 recorded this as `BLOCKED-2` and proposed to resolve it by amending
the isolation table's wording. That was wrong, and the review that said so was
right: **the wording was never the obstacle.** The historical verifier runs

- `git show SOURCE_COMMIT:<relative>` with `cwd=REPO_ROOT`, in
  `_verify_source_commit_inputs`;
- `git check-attr -z text -- <relative>` with `cwd=REPO_ROOT`, in
  `_verify_byte_preservation_attributes`;

and a materialized tree holds retained files and **no `.git`**. No amendment to
any document makes a git repository appear there. Under the environment this
design constructs there is not even a `PATH` to find the executable with. Both
calls would fail inside the child no matter what the isolation table said.

**What reading the bytes again showed.** Those two functions are called by
`verify_candidate()`. They are **not** called by `build_contract_manifest()` or
by `build_candidate_set()`, which do file reads only. So the split is available
without designing anything new:

| Runs where | What |
| --- | --- |
| child | `build_contract_manifest()` and `build_candidate_set(contract)` — pure rebuild from materialized inputs, no subprocess, no git |
| nowhere | the source-commit comparison and the `.gitattributes` check — see `BLOCKED-2` |

**Revision 2 said those two move to the parent. They cannot, and this is the
second finding revision 3 exists to correct.** Follow each option to its end:

| Semantics | Result |
| --- | --- |
| parent compares the **live worktree** to `git show SOURCE_COMMIT:path` | this is the original function unchanged, and it fails today for the B-1 divergence. It is the exact coupling M4 exists to remove; adopting it in M3-b would rebuild the defect the work stream is unwinding |
| parent compares the **materialized files** to the same git blobs | a tautology. M2 materialized those bytes *from* those blobs and verified each digest through a held handle on the way |
| the checks are **superseded** by the M1/M2 authority chain | correct, and it is a change to the verification contract rather than a relocation |

The third is chosen. It is not a smaller claim dressed up: what
`_verify_source_commit_inputs` asserts — that the bytes being reconstructed from
are the pinned commit's — is asserted more strongly by M1 and M2 together. M1
derives the expected inventory and digests from candidate-set bytes checked
against a frozen literal; M2 materializes each file from the pinned commit and
verifies its digest through the handle that created it, with no name resolved in
between. The git comparison checks the same property by shelling out to a tool
and trusting a path.

`_verify_byte_preservation_attributes` is the same story. It exists because a
*checkout* can rewrite line endings, so the worktree bytes may differ from the
committed blob. Materialization performs no checkout: M2 writes blob bytes and
reads them back through the handle. The condition the check guards against
cannot arise on this path.

**Neither is silently dropped, and neither is left implicit.** Retiring a check
is a change to what verification means, so it is `BLOCKED-2` below with a
literal amendment, and no amendment is made here.

**What is still true and still needs saying.** The remaining path behaviour is
unchanged, so this part of revision 1 stands:

1. **the child does open materialized paths.** The trusted loader does not; the
   historical builders do, by name, through ordinary `open` — the preflight
   JSON, the contract manifest, the candidate set, `.gitattributes` and the
   treatment packet. It must not be summarized as "the child opens no
   materialized path", which is false;
2. **the materialized set is larger than the executable set.** The loader gets
   the four (or five) runtime modules; M2 must materialize all eleven retained
   files, because the builders read the data ones. Two inventories, and
   conflating them turns a missing file into a mismatch;
3. **`subprocess` is still importable** in the child. Nothing this design does
   removes it, and `-I -S -B` cannot. With the split above nothing the child
   runs is expected to use it — but "expected" is not "cannot", which is why
   the job object in section 6 exists.

The literal amendment revision 10 needs, in the isolation table's `child` row,
replacing the parenthetical about `__file__`:

> `__file__` names a materialized path, and historical code resolves its own
> data inputs from it. The trusted loader opens none of those paths and selects
> no code by them; the historical code does open them, and it retains every
> capability the standard library gives it. What is established is that nothing
> the child *executes* is selected by a path, not that the child performs no
> path I/O.

**No amendment is made here.** It is smaller than revision 1's version because
the `subprocess` question is answered by the split rather than by the wording.
The evidence plan below assumes the current wording and evidences the loader's
property, not a wider one.

---

## BLOCKED-3: the process-control boundary is a design slice, not a table row

Revision 3 listed the Win32 calls M3-b-2 needs and treated naming them as
specification. It is not. `NATIVE-INTEROP.md` requires layouts, ownership,
unwind and error translation before a native surface is implemented, and this
document supplies one layout oracle and one unwind rule for a surface with eight
calls and three kinds of handle.

What a process-control design slice must close before M3-b-2 begins:

- **layouts and an independent oracle** for `STARTUPINFOW`,
  `PROCESS_INFORMATION`, `JOBOBJECT_BASIC_LIMIT_INFORMATION`,
  `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` and
  `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION` — sizes, offsets and alignment
  measured rather than assumed, in the style N1 already established;
- **ABI declarations** for `CreateProcessW`, `CreateJobObjectW`,
  `SetInformationJobObject`, `AssignProcessToJobObject`, `ResumeThread`,
  `TerminateProcess`, `TerminateJobObject`, `QueryInformationJobObject`,
  `WaitForSingleObject`, `GetExitCodeProcess` and `CloseHandle`, checked against
  an oracle rather than asserted to be non-empty — the mistake the read tranche
  already paid for;
- **ownership**, per handle: the process handle, the thread handle and the job
  handle have different lifetimes and different closing rules, and the thread
  handle in particular must not outlive the resume;
- **the unwind matrix**, one row per point of failure: job created not
  configured, configured not assigned, process created not assigned, assigned
  not resumed, resumed. Each row states what is terminated, what is waited for
  and what is closed, in order;
- **error translation**: a closed code per failure, distinguishing job creation,
  job configuration, assignment, resume, termination and query. Revision 3's
  table has three process codes for a surface with at least six ways to fail,
  which means five of them would arrive as one;
- **sensitivity evidence** for the layouts and the unwind, in the style of the
  boundary's existing battery.

Whether that slice extends `gate3_native_boundary` or stands beside it is its
own question. **M3-b-2 does not begin until it exists**, and M3-b-1 — which
starts no process — is unaffected.

---

## BLOCKED-2: retiring two checks is a change to the verification contract

`verify_candidate()` composes three things: the source-commit comparison, the
`.gitattributes` byte-preservation check, and the rebuild-and-compare. M3-b runs
the third and, for the reasons in *The split entrypoint*, retires the first two
rather than reimplementing them.

That cannot be done inside this document. It changes what a passing verification
means, and the current verifier is the authority on that. Calling it a
relocation — as revision 2 did — made a contract change look like a plumbing
decision.

The literal amendment, to revision 10's *Bootstrap validation happens before any
historical code runs*, appended after step 8:

> 9. The historical verifier's `_verify_source_commit_inputs` and
>    `_verify_byte_preservation_attributes` are **not** part of the reconstruction
>    path and are not reimplemented on it. Both require a git repository, which a
>    materialized tree is not; run against the live worktree they compare the
>    present to the pinned commit, which is the coupling this design exists to
>    remove. The property they assert is asserted by steps 2, 4 and 6: the
>    expected inventory and digests are derived from candidate-set bytes checked
>    against a frozen literal, and every materialized file is verified against
>    that inventory through the handle that created it, with no name resolved
>    between the write and the read. A reconstruction that passes therefore makes
>    no claim about the live worktree, and none is wanted.

**No amendment is made here.** Until it is authorized, M3-b-3 has no defined
verification contract, and M3-b-1 and M3-b-2 — which touch neither check —
are unaffected.

---

## Trust boundaries carried forward, unchanged

- The runner is executed by path and nothing verifies its bytes first. The
  runner path, the runner bytes and the path-to-bytes TOCTOU window remain
  **accepted trust assumptions of M3**. M3-b does not narrow them and must not
  be read as having solved them.
- "Defends against a corrupted parent" covers the parent's transport and data
  state. It does **not** cover a substituted spawn target: a parent that
  launches a different interpreter or different runner bytes has replaced the
  checker, and nothing downstream can detect what replaced it.
- The child's re-derivation of the inventory is not independent verification in
  the strong sense. Both copies come from one author and one design.
- The trusted loader opening no materialized path is a statement about that
  loader. See *The split entrypoint*.
- No current Gate 3 module may reach the child through an ordinary import
  surface. The measured `sys.path` is what makes this true, and the
  `LOADER_BYPASSED` check is what makes it observable.

## Claim ceiling

- M3-b would establish that the retained artifacts **reconstruct** from bytes
  selected by the pinned commit rather than by the active worktree. It would
  not establish that the pinned commit is what actually executed; the pin
  remains a record.
- **Reconstruction is not the whole of what `verify_candidate()` does today.**
  Two of its checks are retired rather than reimplemented: the source-commit
  comparison and the `.gitattributes` byte-preservation check. The property they
  assert is asserted by the M1/M2 chain instead, and the argument for that is in
  `BLOCKED-2`. What must not be claimed is that M3-b performs them; it does not,
  and it does not perform an equivalent of them either. It relies on an earlier
  link having done so.
- It changes no availability predicate. `handle_boundary_available()` stays
  `False` until an admission record and a capability probe exist, so nothing in
  M3-b is reachable when it lands.
- The post-execution re-check detects; it does not prevent. Revision 10 is
  explicit and this design adds nothing to it.
- The consumed A/B pair remains `NON_SUCCESS` and does not become reusable.
- Every interpreter measurement quoted here describes local CPython 3.12.10 on
  Windows.

## Evidence plan

Each item names what a wrong implementation would do differently, because an
item that cannot fail on a defect is not evidence.

**Three execution classes, because revision 3 described them wrongly.** It
called `f19` the only out-of-process item while `f21` and `f21b` start processes
of their own.

| Class | Items | What it starts |
| --- | --- | --- |
| in-process | `f5`–`f13`, `f18`, `f20`, `f26`–`f29` | nothing |
| — of those, owned by M3-b-1 | `f5`–`f13`, `f18`, `f26`, `f27` | the frame and the loader |
| — of those, waiting on `BLOCKED-2` | `f28`, and `f29`'s citation of it | the result object |
| process-control integration | `f14`–`f17`, `f21`, `f21b`, `f22`–`f25` | real processes, all fixtures — a child that sleeps, a child that spawns a grandchild, a child created suspended |
| full fixture transport run | `f19` | one end-to-end child, the only item exercising spawn, loader and return channel together |

`f1`–`f4` assert against a spawn double and start nothing. No item in any class
executes historical code; that begins in M3-b-3.

| # | Evidence |
| --- | --- |
| f1 | the argument vector is exactly `[executable, -I, -S, -B, runner]`, asserted element-wise against a spawn double; a vector with `-c`, `-m`, a shell or a bare `python` fails |
| f2 | the environment handed to the child is a constructed mapping: assert the exact key set, and that a `PYTHONPATH` set in the parent's own environment does not appear |
| f3 | cwd is neither the repository root nor the materialized root |
| f4 | `close_fds=True` and no inheritable handle is passed |
| f5 | the loader answers every name in the runtime inventory — derived from the inventory, not written out as four — and returns `None` for `json`, `pathlib` and an invented name; a whitelist-style loader that intercepts stdlib fails here, and so does a loader with the count baked in |
| f6 | module identity: `__package__ == ""`, `__spec__.loader is` the loader, `submodule_search_locations is None`, `__cached__ is None`, `__file__` equal to the materialized path |
| f7 | the circular absolute imports between the inventory's modules resolve to the same objects — assert identity, not equality |
| f8 | `LOADER_BYPASSED` fires when a module under the materialized root has a different loader, exercised by inserting one |
| f9 | state ordering, by spy: `decode_stream` is called before `sys.meta_path` is touched, and no historical name is importable before it returns |
| f10 | no retry: an entrypoint that raises is called exactly once |
| f11 | the return frame round-trips, and each of its five framing fields corrupted independently gives its own code |
| f12 | each return bound crossed by exactly one: 17 entries, 65 label bytes, 1,048,577 value bytes, 4,194,305 aggregate |
| f13 | trailing bytes, truncation, malformed frame and a valid frame after a non-zero exit each produce distinct codes |
| f14 | timeout: a child that never exits is terminated, killed after the grace period, reaped, and reported as `CHILD_TIMEOUT` with the result discarded |
| f15 | a reap failure is attached to the original error and does not replace it |
| f16 | `stderr` is never parsed: a child emitting a well-formed result frame on `stderr` changes no decision |
| f17 | teardown order, by spy: the child is reaped before any handle is released, and cleanup runs on the failure paths as well as on success |
| f18 | no failure code carries source text, artifact bytes or a historical traceback |
| f19 | the **only full fixture transport run**: one end-to-end child against a fixture tree with fixture modules — not the historical ones — proving the spawn, the loader and the return channel work together. It requires no Gate 3 artifact and executes no historical code |
| f20 | the environment handed to the child contains no `PATH` and no `PYTHON*` key, asserted against the exact key set |
| f21 | the process tree is owned: a fixture child that spawns a long-lived grandchild is fully reclaimed, and the job's `ActiveProcesses` is observed reaching zero **while the job handle is still open**, before any boundary handle is released. A direct-child-only teardown fails this, and so does an implementation that closes the job handle before querying |
| f21b | the native adapter's unwind, asserted by **process absence** and not by handle accounting: a process created suspended and never assigned is terminated, waited for, and only then are its process and thread handles closed; a process already assigned to a job is reclaimed with `TerminateJobObject` and the zero-`ActiveProcesses` observation. An implementation that only closes handles leaves a live suspended process and fails here |
| f22 | `CHILD_TREE_SURVIVED` fires when the count does not reach zero, and is distinct from `CHILD_TIMEOUT` |
| f23 | the scratch directory's lifecycle through the boundary: created handle-relative under a pinned pre-existing base, absence confirmed before creation, identity captured, enumerated once after the tree is gone and before M2 cleanup |
| f23a | the **empty** transaction: removal through the creating handle, absence confirmed, and `SCRATCH_RESIDUE` when it is not |
| f23c | the **non-empty** transaction: a fixture child writes one file, and the run reports `SCRATCH_RESIDUE`, leaves the directory and that file present and unmodified, and still releases every handle — asserted by reopening the path after the run and by handle accounting. An implementation that deletes the file, and one that keeps the handles open to preserve it, both fail |
| f23b | hostile-name mutations, not only removal failure: a pre-existing directory at the name is refused rather than adopted; a junction planted at the name fails closed; and a directory replaced between creation and removal is refused by identity rather than deleted. A path-based `mkdir`/`rmtree` implementation fails all three |
| f24 | the materialization `base` is neither the cwd nor written to: its identity and its immediate directory inventory are equal before and after a fixture run, and the child's observed cwd is not `base`. Asserted on the materialization base only — the scratch base is a different pinned ancestor and a different observation, and revision 4's "byte-identical" was not an observable a directory has |
| f25 | no failure object contains `stderr` bytes: a fixture child writing a recognizable marker to `stderr` produces a failure carrying its length and digest and not the marker |
| f26 | **M3-b-1.** The return label set: each of the four required labels missing in turn gives `RESULT_INCOMPLETE`, an extra label gives `RESULT_INCOMPLETE`, a duplicate gives `RESULT_DUPLICATE_LABEL`, a descending pair gives `RESULT_LABEL_ORDER_INVALID`, and a label failing the grammar gives `RESULT_LABEL_INVALID`. This is the frame deciding whether it is a frame, which the decoder cannot defer |
| f27 | **M3-b-1.** The reader recomputes both digests from the returned bytes: a frame whose digest label disagrees with its byte label gives `RESULT_DIGEST_MISMATCH`. Internal consistency of the frame, not verification of the reconstruction |
| f28 | **Waits on `BLOCKED-2`**, because the object it inspects does not exist until then. The retirement is visible rather than silent: a test asserts the reconstruction path calls neither `_verify_source_commit_inputs` nor `_verify_byte_preservation_attributes`; that the parent-side result object carries an explicit "not asserted" marker for both, constructed in the parent; and that a frame attempting to supply either marker as a label is refused by the completeness rule. An implementation that quietly omits them, one that quietly reintroduces a worktree comparison, and one that lets the child set the markers all fail |
| f29 | the property those checks asserted is asserted elsewhere and fails when broken: a materialized file whose bytes differ from the candidate-set digest is refused by M2's own verification before any child starts. This is M2's evidence, cited rather than duplicated, and `f28` is what stops the citation becoming a substitute for having it |

Mutation sensitivity is required for `f5`, `f8`, `f9`, `f13`, `f14`, `f17`,
`f21`, `f23` and `f26`: each must be shown to fail against an implementation
with that specific property removed, in the same style as M3-a's eighteen-defect
battery. `f21` in particular must fail against a teardown that reaps only the
direct child, because that is the implementation revision 1 specified.

There is no evidence item for `PYTHONHASHSEED`, because the claim it supported
is withdrawn. What replaced it is a measurement recorded in the changelog, and a
measurement is not a test: if a future tranche needs reconstruction determinism
as a property, it needs its own evidence and its own mechanism.

## Implementation tranche recommendation

Not one tranche. The smallest first slice that is still meaningful:

**M3-b-1 — the return channel and the loader, in-process, no spawn.** The
`MetaPathFinder`/`Loader` pair over a buffer map, the return-frame encoder and
decoder, and their failure codes. Everything in `f5`–`f13` and `f18` is
reachable without starting a process, using fixture modules rather than
historical ones. `ACTIVE` stays `False`.

**What M3-b-1 owns.** The frame, completely. That includes its label set —
completeness, grammar, ordering, duplicates — and the recomputation of its two
digest labels against the bytes they travel with, so `f26` and `f27` are
M3-b-1's. Revision 5 excluded them alongside `f28`, which was wrong: a decoder
that returned a frame without deciding whether the label set was the frozen
four, or whether a digest label matched its own bytes, would be returning
something it had not finished checking.

**What M3-b-1 must not build.** The parent-side result object and its two
`"not asserted"` markers belong to `BLOCKED-2`, which is not authorized. `f28`
therefore sits outside this tranche, and so does `f29`'s citation of it.
Building the result object early would be implementing a verification contract
that has not been agreed.

The line between them is one sentence: **`decode_result` returns verified frame
values; the result object says what a reconstruction means.** M3-b-1 owns the
first and none of the second.

**M3-b-2 — the spawn and teardown.** The parent-side process control, the
environment and argument construction, the scratch directory's lifecycle, the
job object, the timeout and reap semantics, and the ordering against M2 cleanup.
This is where `f1`–`f4`, `f14`–`f17` and `f19`–`f25` live, and where a real
child process starts for the first time. The job object is not an add-on to this
tranche; it is the part that makes the teardown ordering true.

**M3-b-3 — the historical entrypoint.** Only after **both** `BLOCKED-1` and
`BLOCKED-2` are resolved by amendment. This is the tranche whose state 4 runs
the real modules' top-level bodies and whose state 5 calls the reconstruction,
and it should be the smallest of the three by then, because everything around it
will already be evidenced.

The split is not administrative. M3-b-1 has no process and no execution;
M3-b-2 has a process but runs fixtures; only M3-b-3 runs history. Discovering a
loader defect in M3-b-3 would mean discovering it in the tranche with the
largest blast radius.

## Authorization boundary

This document proposes. It authorizes nothing. Each implementation tranche, the
two amendments quoted above, any commit, any push and any merge request need
their own owner authorization. Credentials, preflight and live remain
unauthorized, and no part of M3-b approaches them.
