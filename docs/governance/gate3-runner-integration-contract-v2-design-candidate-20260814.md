# Gate 3 Runner Integration Contract v2 Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-14

Revision: supersedes the first revision at SHA-256
`73d681093112703c2d8895bfbc5d6ced6537799fc463101f8e12af41f04f9257`, which
received `CHANGES_REQUESTED` with four blocking findings and one warning, and
the second revision at SHA-256
`a286a2307a343b39504f4818ef6a51665369b4dff655e40bb094f6bc0fb4d656`, which
received `CHANGES_REQUESTED` with two blocking findings and one warning, and the
third revision at SHA-256
`3b76e4a60f0e015561478594baf688ad7b86568829fb59e59975a21062c48eab`, which
received `CHANGES_REQUESTED` with two blocking findings. All are applied here.

Three rounds found one underlying defect in four places: a guarantee asserted
over a seam that cannot enforce it.

- `evidence_class = PRODUCTION` is caller intent, because `invoke` is an
  injected callable.
- An admission builder does not constrain a coordinator field that accepts any
  callable.
- An import guard does not constrain what an author ran before pasting a
  literal.
- A private token is an API structural constraint, not a boundary against a
  hostile in-process caller.

Two of those were stated in direct contradiction to a correct sentence one or
two paragraphs earlier in the same document. Where this revision withdraws a
claim, the withdrawal is recorded in place rather than silently deleted.

Base: `main@a1d74069a7b19ed0cdc3c93d20425384a19e7af6` (merge of PR #65)

Scope: a versioned reopening of the runner integration contract that admits a
bridge-source runtime identity and a workspace-baseline authority, and defines
what happens to every artifact produced under the current contract

## Problem

Two of the five production-wiring preconditions named by the accepted bridge
design require fields that `RuntimeAuthority` does not have. Adding them changes
`RUNNER_INTEGRATION_CONTRACT_BYTES`, and that digest is pinned by the merged
runner/capture integration milestone. This is not an additive change; it reopens
a sealed contract.

Doing it carelessly has a specific failure mode that matters more than the
schema work: every artifact produced under the current contract is **synthetic**,
and a version bump is exactly the moment at which synthetic evidence could be
silently re-read as production evidence.

## Current Repository Truth

Verified against the merged sources at the base commit. Field inventories are
quoted from the code, not from prior design documents.

1. `RuntimeAuthority` (`gate3_final_message_runner_integration.py:120`) has
   exactly: `action_sha256`, `arm`, `git_commit`, `runner_blob`,
   `integration_blob`, `integration_contract_sha256`, `capture_bindings_sha256`,
   `runtime_sha256`. There is no bridge-source field and no workspace-baseline
   field.
2. `public_value()` emits those plus fixed `capture_ordinal`, `launch_ordinal`,
   `replacement`, `retry`, `schema`. `_validate_authority_artifact` compares the
   retained artifact for **equality** with `public_value()`, so any added key
   changes every authority artifact.
3. `RuntimeAuthority.validate()` rejects any `runtime_sha256` whose key set is
   not exactly `RUNTIME_SUBJECTS`, and `_check_runtime` additionally requires
   `set(runtime_readers) == set(authority.runtime_sha256)`.
4. `RUNNER_INTEGRATION_CONTRACT_BYTES` is **computed at import** from the live
   module constants `CHECKPOINTS`, `PROFILES` and `RUNTIME_SUBJECTS`.
5. `_validate_contract_artifact` compares the retained contract artifact
   byte-for-byte against that module constant and against
   `authority.integration_contract_sha256`. **The verifier is therefore
   single-version by construction**: it cannot verify any package whose contract
   bytes differ from the currently imported ones.
6. `_validate_runtime_binding` cross-checks only five of the seven runtime
   subjects against `CaptureBindings` (`adapter_source`, `adapter_contract`,
   `raw_contract`, `projector_contract`, `public_schemas`). `runner_source` and
   `integration_source` are authority-only, with no second source of truth.
7. `test_gate3_final_message_runner_integration.py` pins
   `EXPECTED_INTEGRATION_CONTRACT_BYTES` and a full
   `EXPECTED_PUBLIC_CHAIN_BYTES` map as literal byte strings, including the
   seal, authority, receipt and finalization digests. A contract change
   invalidates all of them.
8. Every runner-integration and bridge artifact in the repository today was
   produced from injected synthetic inputs. No package was produced by a real
   runner.

### Two consequences worth stating plainly

**Fact 4 is a latent defect, stated precisely.** The pinned SHA-256 is a
constant; nothing can change it. What drifts is the **module constant the
shipped verifier accepts as v1**: because `RUNNER_INTEGRATION_CONTRACT_BYTES` is
recomputed at import from live constants, editing `CHECKPOINTS`, `PROFILES` or
`RUNTIME_SUBJECTS` changes the bytes the verifier will accept, so previously
valid v1 packages stop verifying while the recorded pin still reads as
authoritative. Freezing v1 as a literal preserves backward verification. It does
not make the digest more immutable — digests are already immutable.

**Fact 5 decides the shape of the whole design.** "Versioned coexistence" is not
a preference here; without it, shipping v2 makes every v1 package permanently
unverifiable by the shipped verifier, including the evidence the merged
milestones cite.

## Decision Order

The five questions posed for this slice are not independent. Question 5 —
preventing synthetic evidence from being read as production evidence — decides
questions 1 through 4, so it is answered first and the rest follow from it.

## Q5. Preventing a synthetic-to-production upgrade

### Why the obvious mechanism does not work

The first revision of this candidate proposed a mandatory `evidence_class` field
with `SYNTHETIC` and `PRODUCTION` values and no transition edge between them.
That is insufficient, and the reason is worth stating precisely because it is the
same error this work stream has now made four times.

`RunnerIntegrationCoordinator.invoke` is an injected callable. Nothing in the
merged code distinguishes a real contained process from a synthetic
`InjectedContainedResult` handed back by a test. A caller can therefore construct
a fully valid package and simply **declare** `evidence_class = PRODUCTION` at the
start. No transition is needed, so removing the transition edge protects nothing.

`evidence_class` would be **authority intent, not execution provenance**. The
field records what the caller asserted, not what ran.

A second defect in the same proposal: "bound into the observation seal" does not
hold for all profiles. `RUNNER_CAPTURE_RESULT_UNKNOWN` and
`RUNNER_SEAL_UNAVAILABLE` packages have no seal at all — `verify_package`
validates them from the authority, contract and observation stage only. Any
mechanism that relies on seal binding is absent exactly where a crashed run
leaves evidence.

### What this slice actually does

**v2 admits `SYNTHETIC` only.**

- `evidence_class` is a mandatory closed field with no default, and in v2 the
  only accepted value is `SYNTHETIC`. `PRODUCTION` is a reserved token that the
  validator rejects.
- v1 packages have no such field; the verifier assigns `LEGACY_V1_SYNTHETIC`
  from the contract version alone.
- Nothing in this contract version can produce or accept a `PRODUCTION` package.
  The class is reserved so that a later version does not have to re-litigate the
  vocabulary, not because this slice can admit it.

Opening `PRODUCTION` requires all of the following, none of which is in scope
here and each of which needs its own design and authorization:

1. a durable **production-admission authority** — a create-once record proving
   admission, produced outside the caller's control;
2. a **real runner execution path**, so that the injected-callable seam is not
   the source of a production package; and
3. **machine-enforced path exclusivity** (group B), so that the existence of a
   real path does not also leave a synthetic path able to mint the same class.

Until those exist, a `PRODUCTION` package would assert provenance no artifact
could support. Reserving the token and refusing to issue it is the honest
position.

## Q1. Replace or version and coexist

**Version and coexist, with v1 frozen and read-only.**

- Introduce `gate3-route-v2.runner-integration-contract.v2`.
- Replace the computed constant with a frozen registry:
  `CONTRACT_BYTES_BY_VERSION = {"...v1": <literal bytes>, "...v2": <literal bytes>}`.
  The v1 entry is the exact bytes already pinned, written as a literal so that
  future edits to live constants cannot change which bytes the shipped verifier
  accepts as v1.
- v1 is verifiable but **not producible**: the coordinator emits v2 only. There
  is no flag, parameter or environment variable that makes it emit v1 again.

### Version dispatch happens first, not inside contract validation

The first revision proposed dispatching inside `_validate_contract_artifact`.
That is too late. `verify_package` calls `authority.validate()` **before** any
contract artifact is read, and `RuntimeAuthority.validate()` enforces the exact
`RUNTIME_SUBJECTS` key set. A v1 authority carrying seven runtime subjects
cannot pass a v2 `validate()` that requires eight, and a v1 authority artifact
retained on disk cannot equal a v2 `public_value()`. Dispatching later means
every v1 package fails before its version is ever consulted.

The order must therefore be:

1. **Total, fail-closed version identification** from the exact canonical bytes
   of the retained contract artifact, matched against the frozen registry. Any
   payload matching no registry entry is rejected; there is no fallback and no
   "assume latest".
2. Dispatch to the version's own authority schema, runtime-subject inventory and
   validator. v1 keeps its exact seven-subject inventory, its exact
   `public_value()` key set and its exact equality semantics, unchanged.
3. Only then validate artifacts under that version's rules.

This means `RuntimeAuthority` cannot remain a single class whose `validate()`
hard-codes one inventory. Separating the per-version authority schema is part of
the implementation tranche, not an incidental refactor.

Replacement was rejected because it would make the evidence cited by the merged
milestones unverifiable by the shipped verifier, which converts a documentation
problem into an evidence problem.

## Q2. What stays verifiable but cannot be upgraded

| Artifact class | Verifiable under v2 verifier | Class assigned | Upgradable |
| --- | --- | --- | --- |
| v1 runner-integration packages (all existing) | yes, via the frozen v1 registry entry | `LEGACY_V1_SYNTHETIC` | no |
| capture artifacts embedded in a runner-integration package | yes, unchanged — the capture adapter is not versioned by this slice | inherited from the enclosing package | no |
| standalone capture artifacts, with no enclosing runner package | yes, under the capture adapter's own verifier | none — they take no runner `evidence_class` | n/a |
| v2 packages, which can only be `evidence_class = SYNTHETIC` | yes | `SYNTHETIC` | no |
| `evidence_class = PRODUCTION` | not producible or acceptable in v2; the token is reserved and rejected | n/a | n/a |

A standalone capture artifact has no enclosing runner package, so there is
nothing to inherit from. It must not be classified as production or synthetic
*runner* evidence in either direction: the runner `evidence_class` vocabulary
does not apply to it, and treating its absence as a default would reintroduce
exactly the silent-classification problem this section exists to prevent.

Nothing is re-signed, rewritten or migrated in place. Old packages stay exactly
as they are on disk and in git; only the verifier learns to read their version.

## Q3. Bridge source — Git identity, runtime bytes, or both

**Both, in different roles.** Conflating them is the error the accepted bridge
design made in its first revision, and encoding both explicitly is what closes
it.

| Binding | Answers | Where it belongs | What it does not prove |
| --- | --- | --- | --- |
| `bridge_blob` — Git blob identity | which reviewed bytes were approved | `RuntimeAuthority`, beside `runner_blob` and `integration_blob` | nothing about runtime; it is a review identity |
| `bridge_source` — runtime byte digest | what was on disk at each checkpoint | a new member of `RUNTIME_SUBJECTS`, checked by `_check_runtime` | which instructions were already loaded or executed |

Adding `bridge_source` changes `runtime_subjects` inside the contract bytes,
which is one of the two reasons this slice needs v2 at all.

Note the asymmetry inherited from fact 6: like `runner_source` and
`integration_source`, `bridge_source` has no second source of truth in
`CaptureBindings`. It is authority-only. The design must not describe it as
cross-validated.

## Q4. Workspace baseline authority

Requirements: bind the exact baseline the run compares against, without naming
artifacts in public evidence.

| Layer | Content | Public |
| --- | --- | --- |
| private baseline map | `{artifact_id: sha256(content_bytes)}` | no |
| public binding | `workspace_baseline_sha256` = SHA-256 over the canonical bytes of that map | yes |

- Canonicalization reuses `capture.canonical_bytes` — sorted keys, ASCII, no
  trailing whitespace — so the digest is reproducible without a new serializer.
- The map itself, and therefore every artifact id and every content digest,
  stays private. This follows the existing precedent in
  `_runtime_binding_sha256`, which already summarizes the `public_schema_sha256`
  mapping into a single digest.
- Privacy boundary: a single digest over a mapping is not zero-knowledge. An
  adversary who already knows a candidate artifact set can confirm it by
  recomputation. This is acceptable because the artifact set is fixed by the
  action authority and is not itself secret, but the design claims
  confirmation-resistance nowhere.

### The binding gap, and the seam that closes it

A digest in the authority does not by itself bind anything. The current bridge
callback is `make_observe_workspace(read_workspace, baseline)`: it takes a
caller-supplied map, closes over it, and returns a zero-argument callable. It
never receives the authority or the digest, and the coordinator cannot inspect
what a closure captured. A caller could authorize one baseline and compare
against another, and every artifact would still verify.

The first revision asserted that "the observation callback recomputes the map
privately and compares against the authorized digest" while simultaneously
listing the bridge module as unchanged. Those two statements are incompatible;
the callback as merged cannot perform that comparison.

### An admission builder is not enough either

An earlier draft of this section proposed an admission function that refuses to
build a callback on digest mismatch, and then claimed the coordinator therefore
receives "the only callback that could have been constructed". That does not
follow. `RunnerIntegrationCoordinator.observe_workspace` accepts **any**
zero-argument callable. A caller can skip the admission function entirely and
pass its own closure. A builder existing is not a builder being the only
entrance.

This is the same defect as `evidence_class`, one layer down: a structural
guarantee asserted over a seam that still accepts arbitrary input.

### Closing it structurally — one design, not two

**The v2 coordinator receives the private baseline map, the authorized
`workspace_baseline_sha256` and a workspace reader, performs the digest
comparison itself, and derives the workspace observation internally. The
arbitrary observation-callback seam is removed.** There is no callable to
substitute because there is no callable.

This changes the v2 coordinator's public shape. v1 verification semantics are
unaffected: v1 packages are verified, never re-run.

Consequences that are part of this decision, not open options:

1. The artifact-id inventory has one authority source — the outer route/action
   authority — carried as part of the private baseline map, never as a public
   list.
2. A digest mismatch is a closed admission failure, not a `CAPTURE_FAILED`
   verdict. The two mean different things: one is "the caller supplied an
   unauthorized baseline", the other is "the workspace could not be read".
3. Baseline ownership moves from the bridge to the coordinator. The bridge keeps
   its mapping, disposition and privacy behaviour; it stops owning workspace
   observation construction.

### Rejected alternative: a token-guarded observer capability

An earlier revision offered, as an equal option, keeping the callback seam and
adding an `AdmittedWorkspaceObserver` capability constructible only through the
admission function. That is rejected, for two reasons.

**It is not one design.** Offering both would mean approving a candidate under
which the implementation could still choose between two different coordinator
shapes, bridge ownerships, failure models, test matrices and claim ceilings. A
design that admits either is not a specification.

**The guarantee was overstated.** That revision called the capability
"non-forgeable". A private module token plus a raising `__init_subclass__` is an
**API structural constraint**: it stops accidental and casual construction. It
is not a security boundary against a hostile in-process caller, who can reach
module privates directly. The existing `TrustedLiveRunner` precedent does not
change this — it inherits the same limit, and citing it as precedent does not
upgrade the property.

### What a verifier can and cannot reconstruct

The comparison is a property of the code path, not of any artifact. No amount of
retained evidence converts it into one. An earlier revision stated that
correctly and then, one paragraph later, claimed the private map "proves the run
compared against the authorized baseline". It does not.

The claim ladder is exactly three rungs, and each names what it adds:

| Inputs available to the verifier | Strongest admissible claim | What it does **not** establish |
| --- | --- | --- |
| public package only | `BASELINE_DIGEST_DECLARED` — a baseline digest was authorized and recorded | anything about a map, a comparison, or an execution |
| public package + private map, supplied out of band | `SUPPLIED_BASELINE_MAP_MATCHES_DECLARED_DIGEST` — the canonical digest over the supplied map equals the public field | that the coordinator ran; that this map was the one used at runtime; that the map described the real workspace |
| the above + reviewed runtime source | a **conditional code-contract statement**: *if that coordinator path executed, its structure forces the comparison* | that the path executed; this is not an execution-event proof |

The third rung is a statement about reviewed source, not about the run. It is
the same class of limit already recorded for the TOCTOU checkpoints in the
accepted bridge design: sampling bytes proves what was on disk at a checkpoint,
not what executed.

There is no arrangement of these inputs that yields "the run compared against
the authorized baseline". That sentence must not appear in any artifact, claim
token, PLAN entry or memory record derived from this design.

`gate3_final_message_runner_bridge.py` is therefore in the affected surfaces for
the later tranche. The first revision listed it as unchanged; that was wrong.

## Compatibility, Invalidation and Migration Boundaries

### Compatible

- All existing v1 packages remain verifiable, unmodified, under the frozen
  registry entry.
- The capture adapter, its schemas and `verify_public` are unchanged. This slice
  does not reopen the capture contract.
- `CodexExecRunner` and `TrustedLiveRunner` are unchanged.
- The bridge module is **not** in this list, but not because it gains any new
  responsibility. Its accepted mapping, disposition and privacy behaviour stay
  exactly as they are, and `make_observe_final` is unaffected. What changes is
  that `make_observe_workspace` is **retired**: workspace observation, including
  the digest comparison, belongs to the v2 coordinator, so the bridge stops
  owning that construction rather than acquiring a check inside it.

### Invalidated by the version bump

- `EXPECTED_INTEGRATION_CONTRACT_BYTES` and the whole
  `EXPECTED_PUBLIC_CHAIN_BYTES` map in the merged integration test, including
  every seal, authority, receipt and finalization digest.
- **These must be recomputed from the specification, not by running the
  production serializer and pasting its output.** Those literals exist precisely
  to be an independent oracle; regenerating them from the code under test
  destroys the property they were written to provide.

### Oracle provenance: what is achievable, and what is not

A hand-derived literal and one pasted out of the production serializer are
byte-identical. **Nothing in the retained evidence can distinguish them**, and no
mechanism proposed here changes that. An earlier draft of this section stated
that fact correctly and then, two paragraphs later, claimed the mechanisms below
make serializer reuse "detectable". That was a contradiction inside one
document, and the claim is withdrawn.

Specifically, and against the earlier draft:

- an import guard constrains what the oracle module imports **at test runtime**.
  It says nothing about what the author ran before pasting a value;
- mutation tests measure whether the *verifier* is sensitive to tampering. That
  is an orthogonal property to how a literal was historically produced. A
  serializer-derived literal survives mutation testing perfectly well.

The achievable claim is narrower:

1. **A retained derivation worksheet.** For each expected literal, the ordered
   canonicalization steps and intermediate digests that produce it, recorded as
   a reviewable artifact rather than a commit-message assertion.
2. **An oracle fixture that is runtime-independent of production code.** The
   expected bytes live in a module importing neither
   `gate3_final_message_runner_integration` nor
   `gate3_final_message_actual_capture`, asserted by an import-guard test. This
   prevents the test from *becoming* a round-trip of the code under test.
3. **Independent reviewer re-derivation.** A reviewer re-derives a sampled
   subset of the expected bytes from the specification, without the production
   modules.

Item 3 is **corroboration, not detection**: it raises confidence that the values
are correct, and it cannot establish how the author originally obtained them.
The honest summary is that the fixture is runtime-independent of production code
and its expected bytes have been independently re-derived — not that serializer
reuse would be caught.

### Not migrated

- No existing artifact is rewritten, re-signed, moved or re-classified on disk.
- No PLAN milestone digest is restated. The v1 pins stay exactly as recorded;
  they now name a frozen literal instead of a computed value, which makes them
  more durable, not different.

## Scope

### In scope

- Versioned contract registry and dispatch.
- `evidence_class`, restricted to `SYNTHETIC`, with `PRODUCTION` reserved and
  rejected, plus the named preconditions for opening it later.
- `bridge_blob` and `bridge_source` bindings.
- `workspace_baseline_sha256` binding and its privacy boundary.
- Compatibility, invalidation and migration boundaries.
- A later implementation tranche outline and its evidence plan.

### Explicit non-goals and prohibitions

- No implementation, staging, commit, push, MR or merge in this slice.
- No credentials, credential files, credential reads or credential-derived
  values.
- No preflight, zero-session probe or receipt generation.
- No Codex invocation, subprocess, model call or network call.
- No live, counted or non-counted execution.
- No reopening of the capture adapter contract or its public schemas.
- No reuse, retry, replacement or reinterpretation of the consumed pair.
- No group B or group C work, and no production wiring.
- No claim that any existing evidence becomes production evidence.

## DONE for a Later Offline Implementation Tranche

`DONE = The integration module identifies contract version from exact canonical
bytes before any authority validation and dispatches to per-version authority
schemas; the frozen v1 registry entry is a literal whose digest equals the value
already pinned by the runner/capture milestone; every existing v1 package still
verifies unmodified, proven by full retained-package fixture reconstruction; the
coordinator emits v2 only; v2 accepts evidence_class = SYNTHETIC and rejects
PRODUCTION; bridge_blob and bridge_source are bound in their distinct roles; the
v2 coordinator receives the private baseline map, the authorized digest and a
workspace reader, performs the comparison itself, and no longer exposes an
observation-callback seam; the verifier emits `BASELINE_DIGEST_DECLARED` from the
public package alone and `SUPPLIED_BASELINE_MAP_MATCHES_DECLARED_DIGEST` only
when the private map is supplied out of band, with no claim that any run
performed the comparison;
and the invalidated expected-byte literals ship with a retained derivation
worksheet, an oracle fixture proven runtime-independent of the production
modules, and independent reviewer re-derivation of a sampled subset, claimed as
corroboration rather than as detection of how the literals were produced.`

This is a proposed later tranche, not current implementation authority. It is
larger than the P3 tranche and should not be attempted as two files.

## Affected Surfaces if Later Implemented

- `gate3_final_message_runner_integration.py`
- `test_gate3_final_message_runner_integration.py`
- `gate3_final_message_runner_bridge.py` and its test — to **remove** the
  `make_observe_workspace` helper and adjust the tests that exercise it, now
  that workspace observation and its digest comparison belong to the v2
  coordinator. The bridge does not implement digest admission. Earlier revisions
  listed the bridge first as unchanged and then as the admission site; both were
  wrong.
- one new frozen-literals / oracle module and its test, which must not import
  the production modules

`gate3_final_message_actual_capture.py`, its schemas, `gate3_route_v2_codex.py`,
manifests, owner pins, promotion state, `PLAN.md`, memory and all evidence paths
remain unchanged unless a separate design and authorization expands that scope.

## Review Questions

1. Is coexistence correctly preferred over replacement, given that the only
   packages needing v1 verification are synthetic?
2. Is restricting v2 to `SYNTHETIC` the right call, or should `evidence_class`
   be omitted entirely until a production-admission authority exists, on the
   grounds that a reserved-but-rejected token invites future misreading?
3. Should `bridge_source` gain a second source of truth in `CaptureBindings`
   rather than inheriting the authority-only asymmetry of `runner_source`?
4. Is a single digest over a private artifact map an acceptable privacy
   boundary, given it is confirmable by recomputation?
5. Removing the observation-callback seam changes the v2 coordinator's public
   shape and moves baseline ownership out of the bridge. Is that shape change
   acceptable, given the alternative was rejected as an overstated guarantee
   rather than as a smaller change?
6. Is a baseline binding worth adding at all when the public verifier can only
   emit `BASELINE_DIGEST_DECLARED`, and the second rung depends on a private-map
   handover procedure that does not yet exist?
7. Is corroboration by independent re-derivation an acceptable ceiling for
   oracle provenance, given that detection of serializer reuse is not
   achievable?
8. Does per-version authority dispatch fit inside one class hierarchy, or does
   v1 need a frozen validator copy so that v2 refactoring cannot alter v1
   semantics?

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, old-pair reuse, retry, replacement, staging, commit, push, MR, merge,
manifest update, owner-pin update or promotion. Group B, group C, production
wiring, preflight and live each require their own separate authorization, and
none may be interleaved before this group is closed. Gate 3 remains
`NON_SUCCESS`.
