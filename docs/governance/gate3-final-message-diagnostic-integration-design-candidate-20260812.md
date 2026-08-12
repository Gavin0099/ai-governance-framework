# Gate 3 Final-Message Diagnostic Integration Design Candidate

Status: `CANDIDATE — REVISED DESIGN ONLY; PENDING INDEPENDENT REVIEW`

Date: 2026-08-12

## Problem

The consumed Gate 3 non-counted pair remains `NON_SUCCESS`. Both arms exited
zero, but the committed public evidence contains neither a final message nor a
versioned raw-event projection that can distinguish final-output production,
adapter capture, model completion and task execution. The pair is consumed and
cannot be retried, replaced or retrospectively instrumented.

Commit `7c1c42e02a78385c3f855f62c9c34abf04e83b55` now provides a pure,
in-memory classifier for closed synthetic observations. It does not observe a
filesystem lifecycle, publish a pre-cleanup seal, perform cleanup, issue a
final receipt or verify a public artifact tree. Therefore it closes the
classification-logic tranche only; it does not close the diagnostic evidence
chain.

The next design problem is narrower than a new execution:

> Define a synthetic-only integration contract that can exercise lifecycle
> observation, durable-stage ordering, cleanup and offline reconstruction
> without credentials, a real CLI, preflight, live content or any relationship
> to the consumed pair.

This candidate specifies that contract. It does not implement or authorize it.

## Current Repository Truth

1. `PLAN.md` records one consumed live pair with result `NON_SUCCESS`. Retry,
   replacement, counted execution and effect conclusions remain unauthorized.
2. `docs/governance/gate3-final-message-diagnostic-design-candidate-20260811.md`
   defines four independent observation axes, a fail-closed classifier, a
   content-free event projection and a required action -> pre-cleanup seal ->
   cleanup -> final receipt sequence.
3. `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/
   gate3_final_message_diagnostic.py` implements only pure classification of
   fixed synthetic observations. Its public-input and implementation digests
   are not an observer, publisher or artifact-tree verifier.
4. `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/
   test_gate3_final_message_diagnostic.py` provides focused offline regression
   coverage for classification, event derivation, contradiction handling and
   fixed-synthetic privacy boundaries.
5. `docs/governance/gate3-route-v2-charter-20260805.md` requires the
   pre-cleanup seal to be immutable, cleanup to occur after that seal and the
   final receipt to pin both the seal and actual cleanup result.
6. No lifecycle observer, diagnostic public schema, diagnostic tree verifier,
   cleanup adapter, durable publisher or recovery-state implementation is
   claimed by this candidate.

The current evidence supports only `offline synthetic classifier reviewed`.
It does not support `integration exists`, `observer coverage is complete`,
`private cleanup is safe`, `live privacy is approved` or `Gate 3 passed`.

## Target Outcome

Produce one reviewable design candidate that:

- defines a deterministic synthetic lifecycle-observer fixture contract;
- separates observation, classification, publication, cleanup and verification
  responsibilities;
- preserves an immutable pre-cleanup seal, an independently recorded cleanup
  outcome and a create-once final receipt;
- specifies TOCTOU, crash and recovery fixtures whose expected results are
  independent of a future implementation;
- defines closed public schemas and an offline verifier contract;
- excludes private or live content, including content digests that could be
  guessed; and
- makes every missing hop, mutation, ambiguity or unsupported platform
  capability fail closed.

## Scope

This candidate covers proposed contracts only for:

- a new synthetic diagnostic action and run identity;
- an observer-neutral lifecycle event vocabulary;
- a synthetic filesystem/process-tree fixture model;
- pre-cleanup seal, cleanup-result and final-receipt artifacts;
- recovery locator and external terminal states;
- closed canonical public JSON schemas;
- a fresh-root offline tree verifier;
- privacy validation; and
- focused synthetic TOCTOU, crash and fail-closed tests.

The candidate is single-run and diagnostic-only. It has no A/B arms, treatment,
comparison, sample counter or effect estimator.

## Explicit Non-Goals and Prohibitions

- No credentials, login, token, auth-file read, secret lookup or inherited
  credential-bearing environment.
- No preflight, zero-session probe, real CLI invocation, model call, network
  access or live session.
- No reuse of the consumed pair ID, either consumed run ID, their task IDs,
  their authorization, their private paths or their artifacts.
- No `parent_pair_id`, `replay_of`, `retry_of`, `replacement_for` or equivalent
  lineage field.
- No retry, replacement, replay, counted Gate 3 execution or new sample.
- No owner signature, manifest promotion, owner-pin update or live authority.
- No raw prompt, task text, Skill text, event payload, final message, stdout,
  stderr, filesystem path, username, hostname, environment value or credential
  in public evidence.
- No digest or byte count of live or user-controlled content. Hashing private
  live content does not make it public-safe.
- No retrospective reclassification or enrichment of the consumed pair.
- No claim about model, adapter, CLI, Skill, route, task or framework effects.
- No runtime, schema, verifier, observer, cleanup or publication implementation
  in this design slice.

## Architecture and Responsibility Boundaries

The proposed integration has five components. Each component has one owner and
must not silently absorb another component's authority.

| Component | Layer | Responsible for | Must not claim or perform |
| --- | --- | --- | --- |
| synthetic fixture driver | Application test harness | deterministic scripted actions and expected state transitions | credentials, real process launch, model/CLI semantics |
| lifecycle observer adapter | Infrastructure | content-free target/parent/process-tree observations and coverage health | causal classification, cleanup, publication |
| classifier | Domain/pure transformation | four-axis classification from closed admitted observations | filesystem, time, process or publication I/O |
| publisher/cleanup adapters | Infrastructure | create-once stage publication and bounded synthetic cleanup | rewriting a prior stage or upgrading classification |
| offline verifier | Application/pure plus read-only tree adapter | canonical/schema/link/tree reconstruction and fail-closed verdict | reading private content or asserting semantic truth of deleted bytes |

The observer and durable publisher are external-state boundaries and require
explicit interfaces. A future platform adapter may translate native identity,
reparse and durability behavior into this closed contract, but platform-native
details cannot enter the classifier or public evidence. If an adapter cannot
prove a required capability, it reports `UNAVAILABLE`; it must not emulate a
stronger observation.

## Synthetic Lifecycle Observer Contract

### Fixture world

The first integration tranche uses a deterministic synthetic world, not the
host filesystem or a real process. The world contains:

- one synthetic private root;
- one parent object with opaque fixture identity `parent_0`;
- one logical target named `final_message`;
- one retained closed process-tree topology;
- one retained raw synthetic action script and one independent expected
  lifecycle projection;
- one monotonic fixture sequence supplied by the fixture, not wall-clock time;
- one observer cursor and explicit start/stop barriers; and
- an append-only private event buffer visible only to the synthetic observer.

Fixture identities are closed labels from a retained fixture manifest. They
are not filesystem paths, host object identifiers or digests of private data.
Unexpected labels are rejected rather than copied to public output.

The fixture manifest retains, for each scenario:

- a closed `fixture_id`;
- the exact raw script path and SHA-256;
- the exact expected projection path and SHA-256;
- a topology containing every closed node ID and its optional parent node ID;
- the expected set of started and terminated nodes;
- the expected initial parent/target identities and target type;
- the maximum cleanup attempts; and
- the independently authored expected final-axis, cleanup and terminal
  dispositions.

Expected projections are specification fixtures. Tests must not generate them
by calling the observer under test. The raw script, topology and expected
projection bytes are retained in the public tree so a reviewer can reconstruct
each assertion without trusting summary booleans.

### Observer start and stop barriers

The observer lifecycle is:

1. bind the expected synthetic root, parent and logical target;
2. capture the pre-launch parent identity and target state;
3. establish `coverage_started` before the fixture may emit `launch_started`;
4. consume every scripted event in contiguous sequence order and project each
   admitted event with its ordinal and closed fixture identity;
5. prove that every topology node started once, every started node terminated
   once, no child started before its parent and all nodes terminated before
   `process_tree_terminated`;
6. establish `coverage_stopped` only after a final parent/target snapshot; and
7. emit the closed projection and observation record with no causal class.

`coverage_started` after launch, a missing sequence, duplicated sequence,
buffer overflow, event after `coverage_stopped`, missing tree termination or a
failed final snapshot makes coverage incomplete. Incomplete coverage forbids
`NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE` and makes the affected final
axis `INDETERMINATE`.

### Closed lifecycle markers

The retained raw synthetic script and closed public projection use only these
markers:

- `coverage_started`;
- `launch_started`;
- `process_node_started`;
- `process_node_terminated`;
- `target_created`;
- `target_replaced`;
- `target_removed`;
- `target_type_changed`;
- `parent_identity_changed`;
- `observer_gap`;
- `observer_overflow`;
- `process_tree_terminated`;
- `final_snapshot_acquired`; and
- `coverage_stopped`.

Each projection entry contains exactly `ordinal`, `marker`, and only the
marker-specific closed identity fields permitted by the lifecycle contract.
Process markers contain a node ID from the retained topology. Target and parent
markers contain only closed fixture identities from the manifest. Gap/overflow
markers contain no arbitrary payload. Ordinals are contiguous from zero.

The observation seal pins the exact raw script digest, lifecycle projection
digest, fixture topology digest, observer implementation digest and
raw-script-to-projection contract. The verifier runs the retained raw script
through the exact bound observer and requires byte equality with both the
retained expected projection and sealed projection. It then independently
checks topology and ordering invariants. Summary classes are derived from that
projection; they cannot serve as their own evidence.

Unknown identities, unknown markers, non-contiguous ordinals, topology
mismatch, contradictory markers or any projection not derived from the retained
raw fixture make the seal inadmissible. This proves only synthetic observer
behavior under fixed fixtures; it does not establish host/native watcher or
real process-tree coverage.

### Identity and handle-bound read

The synthetic world models parent and target identity separately. A stable
read requires all of the following:

- unchanged parent identity from pre-launch through final snapshot;
- target type `regular_file` with no link/reparse marker;
- a no-follow open bound to one target fixture identity;
- the same identity before open, on the opened handle and after read;
- bytes obtained from that handle rather than by reopening the logical name;
  and
- schema validation over exactly those handle-bound bytes.

Replacement before open, during read or between post-read identity checks is a
TOCTOU contradiction. It maps to `PATH_INVALID` or `INDETERMINATE`, never to a
valid capture or a claim that output was not produced.

## Proposed Public Artifact Set

One route evidence package contains exactly the files enumerated by the reviewed
`tree-manifest.json`. The proposed minimum inventory is:

```text
diagnostic-public/
  tree-manifest.json
  action.json
  locator-snapshot.json
  lifecycle-projection.json
  observation-seal.json
  cleanup-result.json
  final-receipt.json
  finalization.json
  recovery-transition-projection.json
  recovery-transitions/
    <zero-padded-ordinal>.json
  schemas/
    tree-manifest.schema.json
    action.schema.json
    observation-seal.schema.json
    cleanup-result.schema.json
    final-receipt.schema.json
    finalization.schema.json
    recovery-locator.schema.json
    recovery-transition.schema.json
    external-terminal.schema.json
    external-recovery-finalization.schema.json
    setup-temp-snapshot.schema.json
    setup-temp-removal-authorization.schema.json
    setup-temp-removal-result.schema.json
    fixture-manifest.schema.json
    lifecycle-projection.schema.json
    recovery-transition-projection.schema.json
  contracts/
    lifecycle-observer-contract.json
    privacy-contract.json
    recovery-state-contract.json
    execution-command-contract.json
  fixtures/
    fixture-manifest.json
    raw/<closed-fixture-id>.json
    expected-lifecycle/<closed-fixture-id>.json
    expected-recovery/<closed-fixture-id>.json
  implementations/
    lifecycle_observer.py
    diagnostic_classifier.py
    canonical_publisher.py
    cleanup_adapter.py
    recovery_finalizer.py
    offline_verifier.py
  implementation-identities/
    lifecycle-observer.identity.json
    diagnostic-classifier.identity.json
    canonical-publisher.identity.json
    cleanup-adapter.identity.json
    recovery-finalizer.identity.json
    offline-verifier.identity.json
```

This is the **route evidence package**. External recovery uses a separate
privacy-safe package and never impersonates a route receipt:

```text
diagnostic-external-recovery-public/
  tree-manifest.json
  action.json
  external-terminal.json
  locator-snapshot.json                    # absent in pre-locator profiles
  setup-temp-snapshot.json                 # every profile in which a temp existed
  setup-temp-removal-authorization.json    # every profile that attempted temp removal
  setup-temp-removal-result.json           # absent only when crash left result unknowable
  recovery-transition-projection.json      # absent when no locator existed
  recovery-transitions/                    # absent when no transition existed
    <zero-padded-ordinal>.json
  external-recovery-finalization.json      # closed profile only
  schemas/                                  # exact same retained schema bytes
  contracts/                                # exact same retained contract bytes
  fixtures/                                 # exact fixed synthetic fixtures
  implementations/                          # exact retained implementation bytes
  implementation-identities/                # exact retained identity descriptors
```

The external package has five closed manifest profiles:

- `SETUP_TERMINAL_BEFORE_LOCATOR`: action, external terminal and, when a temp
  existed, its exact snapshot plus removal authorization/result records;
  locator, recovery transition projection and finalization are structurally
  absent because no durable locator or private root ever existed;
- `SETUP_TEMP_RESIDUE_OPEN`: action, external terminal and a privacy-safe
  setup-temp snapshot, removal authorization and result; no valid locator,
  private root, recovery-transition projection, route artifact or finalization
  exists, and setup residue remains unresolved;
- `SETUP_TEMP_ATTEMPT_UNKNOWN`: action, setup-temp snapshot, durable removal
  authorization and external terminal; the removal result is structurally
  absent because a crash occurred after authorization and before a durable
  result, so residue is permanently `UNKNOWN` and removal cannot be retried;
- `EXTERNAL_RECOVERY_CLOSED`: action, privacy-safe locator snapshot, external
  terminal, complete transition projection and linked external finalization;
  and
- `EXTERNAL_RECOVERY_OPEN`: action, locator snapshot, external terminal and the
  transition prefix; finalization is structurally absent and the terminal says
  recovery remains required.

Each external package has its own non-self-hashing `tree-manifest.json`, exact
file inventory and independently reviewed out-of-band manifest digest. The
same pure verifier reconstructs route and external captured-byte profiles. A
reconstructed external profile means only that the supplied synthetic recovery
bytes are internally linked; it is never a route receipt or Gate 3 result.

The actual synthetic private directory and active recovery locator do not
belong in either public package. A privacy-validated immutable evidence copy,
`locator-snapshot.json`, belongs in both locator-bound route profiles and in
locator-bound external profiles; the exact external-terminal bytes belong only
in the external package. The locator snapshot is never an active cleanup
capability. Only fixed synthetic fixture scripts and projections are public;
no live or user-controlled raw bytes are permitted.

`tree-manifest.json` is deliberately non-self-hashing. For one fixed fixture it
declares one closed profile and enumerates every other file by exact relative
path, byte count and SHA-256, with no directory entries. `FINALIZED_CHAIN`
requires `locator-snapshot.json`, `finalization.json` and
`recovery-transition-projection.json`; `RECOVERY_REQUIRED_NEGATIVE` requires a
negative receipt plus `locator-snapshot.json` and structurally omits only
`finalization.json`. Because every route profile reaches observation only after
private-root creation authorization and a linked success result, both route
profiles require the exact privacy-safe locator snapshot whose digest is pinned
by that authorization. `RECOVERY_REQUIRED_NEGATIVE` also requires
`recovery-transition-projection.json` and every exact creation/recovery record
under `recovery-transitions/`. Every profile with recovery transitions requires
each canonical record plus the projection; record count, zero-padded filename
ordinal, content ordinal and projection length must match exactly. External
package profiles enforce the distinct inventories above
and reject every route seal/cleanup/receipt field. A no-seal
external terminal does not form a public route tree, but its external package
is independently reconstructable. The independent candidate review supplies
the expected SHA-256 of each fixture's `tree-manifest.json` out of band. The
reviewer invocation must supply both that reviewed manifest digest and the
reviewed SHA-256 of `implementations/offline_verifier.py`. These values let a
reviewer compare captured bytes; they do not prove which program or interpreter
performed capture or verification. The running verifier checks the supplied
captured entries and rejects every extra or missing entry. An in-tree identity
assertion is never its own authority.

Every implementation digest pinned by the action is recomputable from the
retained exact implementation bytes and identity descriptor. Each identity
descriptor pins source SHA-256, the exact execution-command-contract digest,
the canonical executable code-object descriptor (including nested code,
constants, bound data and exception-dispatch bytes) and its resulting
implementation identity. A separately trusted reviewer mechanism may compare
the running environment with the retained command contract and recompute each
descriptor, but this candidate does not make that mechanism self-proving. A
source digest alone and an identity-shaped JSON assertion are both insufficient
for an execution-authenticity claim. Every fixture digest is recomputable from the retained
manifest, raw script and expected projection bytes. Empty directories are not
semantic artifacts, so fresh-checkout reconstruction does not depend on
untracked directory existence.

## Identity and Action Descriptor

`action.json` is published before the synthetic action begins and is immutable.
It contains only:

- `schema`: `gate3.final-message-diagnostic.action.v1`;
- new `diagnostic_id` and `run_id` using the candidate's closed synthetic ID
  format;
- `authorization`: `synthetic_offline_diagnostic_only`;
- `counted`: `false`;
- `origin`: `new_independent_diagnostic`;
- `max_cleanup_attempts`, fixed to a positive bounded integer no greater than
  the schema maximum;
- exact digests for every schema, contract and implementation-identity
  descriptor in the public tree;
- exact identities for observer, classifier, publisher, cleanup adapter and
  recovery finalizer and verifier implementations;
- the retained closed fixture-manifest digest;
- `claim_ceiling`:
  `synthetic_lifecycle_and_publication_reconstruction_only`; and
- a forbidden-lineage assertion whose only valid value is
  `no_parent_no_retry_no_replacement`.

The descriptor schema forbids unknown fields. A new identifier must be created
without reading the consumed pair. A verifier rejects any lineage-like field
even if its value is empty or null.

## Ordered Evidence Chain

The normal evidence path has four immutable public stages:

`action -> observation seal -> cleanup result -> final receipt -> finalization`

The finalization stage exists to avoid asking an immutable receipt to attest to
locator removal that can occur only after that receipt has been published and
verified. No stage may be rewritten. A no-seal recovery path uses the external
recovery artifacts described below and never fabricates a public route receipt.

### Phase 1: pre-cleanup observation seal

After synthetic process-tree termination and before cleanup, the publisher
validates privacy and atomically creates `observation-seal.json` outside the
synthetic private root. The seal is create-once and contains:

- `schema`: `gate3.final-message-diagnostic.observation-seal.v1`;
- `action_sha256` and every identity pinned by the action;
- closed process, turn/event, final-output and task-execution observations;
- the canonical classifier input and its deterministic classification digest;
- the retained fixture/topology/raw-script/projection digests and their exact
  observer derivation identity;
- lifecycle coverage health and closed identity/read dispositions derived from
  that projection;
- only approved fixed-synthetic fixture identities and digests;
- `cleanup_status`: `PENDING`;
- `receipt_status`: `PENDING`; and
- `seal_state`: `PRE_CLEANUP_IMMUTABLE`.

The seal must be canonical JSON and byte-identical to the bytes hashed by later
artifacts. Publication requires create-exclusive temporary creation, complete
write, file durability, atomic no-replace publication and directory durability
where the platform contract supports it. A future adapter that cannot establish
the required durability must return `DURABILITY_UNAVAILABLE`; no admissible
seal is claimed. The synthetic tranche models each durability acknowledgement
as an explicit state transition and does not claim host-OS durability.

Seal collision, privacy rejection, partial write, durability failure, rename
failure or crash before completed publication forbids the normal route-receipt
path. It does **not** forbid recovery cleanup. The launcher must enter the
external bounded recovery path, retain the recovery locator, attempt cleanup of
only the exact identity-bound synthetic private root up to
`max_cleanup_attempts`, record an external terminal and confirm residue and
locator disposition. No public observation seal or route receipt is fabricated.

### Phase 2: cleanup and cleanup result

Normal-path cleanup starts only after the exact seal bytes have been reopened
read-only and their digest confirmed. The immutable seal is never rewritten.
Pre-seal recovery cleanup is a separate external path and cannot produce
`cleanup-result.json` because no admissible seal exists.

`cleanup-result.json` is a separate create-once artifact containing:

- `schema`: `gate3.final-message-diagnostic.cleanup-result.v1`;
- `action_sha256` and `observation_seal_sha256`;
- `attempted`: boolean;
- `result`: `PASS`, `FAIL`, `PARTIAL` or `NOT_ATTEMPTED`;
- closed residue class: `ZERO_RESIDUE`, `RESIDUE_PRESENT` or `UNKNOWN`;
- `attempt_count`, bounded by `action.max_cleanup_attempts`;
- closed failure code, never a path or exception message; and
- recovery-locator disposition.

Cleanup must operate only on the exact synthetic private-root identity bound in
private state. Root mismatch, parent switch or unresolved identity causes
`NOT_ATTEMPTED` or `FAIL`; it must never broaden the target. The public cleanup
result records disposition only, not deleted names or bytes.

The schema plus verifier enforce this complete normal-path matrix:

| `attempted` | `result` | `attempt_count` | residue | failure code | locator disposition |
| --- | --- | --- | --- | --- | --- |
| `false` | `NOT_ATTEMPTED` | `0` | `UNKNOWN` | one closed not-attempted code | `RETAINED` |
| `true` | `PASS` | `1..max` | `ZERO_RESIDUE` | `NONE` | `RETAINED_PENDING_FINALIZATION` |
| `true` | `FAIL` | `1..max` | `RESIDUE_PRESENT` or `UNKNOWN` | one closed failure code | `RETAINED` |
| `true` | `PARTIAL` | `1..max` | `RESIDUE_PRESENT` or `UNKNOWN` | one closed partial code | `RETAINED` |

Every other combination, including `attempted=false + PASS`, `PASS + residue`,
zero attempts with `attempted=true`, attempts above the action bound or a
non-`NONE` failure code on `PASS`, is a fail-closed contradiction.

### Phase 3: final receipt

`final-receipt.json` is a separate create-once canonical artifact containing:

- `schema`: `gate3.final-message-diagnostic.final-receipt.v1`;
- `action_sha256`, `observation_seal_sha256` and `cleanup_result_sha256`;
- exact schema, contract, classifier and verifier identities;
- reconstructed four-axis classification and overall result;
- cleanup and residue dispositions;
- recovery-locator state, which must still be
  `RETAINED_PENDING_FINALIZATION` for an admissible diagnostic receipt;
- `counted`: `false`;
- the same synthetic-only claim ceiling; and
- terminal disposition:
`DIAGNOSTIC_RECEIPT` or `NEGATIVE_RECEIPT`.

`DIAGNOSTIC_RECEIPT` requires an admissible seal, cleanup `PASS`,
`ZERO_RESIDUE`, deterministic classification reconstruction and locator state
`RETAINED_PENDING_FINALIZATION`. It is a route-result receipt, not the final
locator-absence attestation and not yet a fully finalized chain.

`NEGATIVE_RECEIPT` is permitted only when an admissible seal exists and one of
the following closed rows applies:

| Observation seal | cleanup result | residue | locator | receipt |
| --- | --- | --- | --- | --- |
| admissible diagnostic-negative observation | `PASS` | `ZERO_RESIDUE` | `RETAINED_PENDING_FINALIZATION` | `NEGATIVE_RECEIPT`, eligible for finalization |
| admissible observation | `FAIL` or `PARTIAL` | `RESIDUE_PRESENT` or `UNKNOWN` | `RETAINED` | `NEGATIVE_RECEIPT`, not eligible for finalization |
| admissible observation | `NOT_ATTEMPTED` | `UNKNOWN` | `RETAINED` | `NEGATIVE_RECEIPT`, not eligible for finalization |

An incomplete observer projection, privacy failure, broken digest link,
inadmissible seal or missing cleanup result cannot produce either receipt.

### Phase 4: locator removal and finalization

After the final receipt is durably published, the launcher reopens and verifies
the exact receipt and independently rechecks `ZERO_RESIDUE`. It appends a
create-once `LOCATOR_REMOVAL_AUTHORIZED` recovery transition that pins the
receipt, then removes only the exact identity-bound recovery locator, confirms
its absence and appends `LOCATOR_ABSENT_CONFIRMED`. It then atomically publishes
create-once `finalization.json`, containing:

- `schema`: `gate3.final-message-diagnostic.finalization.v1`;
- `action_sha256`, `observation_seal_sha256`, `cleanup_result_sha256` and
  `final_receipt_sha256`;
- exact recovery-finalizer and verifier implementation digests;
- `residue`: `ZERO_RESIDUE`;
- `locator_before`: `RETAINED_PENDING_FINALIZATION`;
- `locator_after`: `ABSENT_CONFIRMED`;
- the retained recovery-transition projection digest, whose canonical entries
  enumerate every transition-record path, byte count, digest, ordinal and
  previous-record link; and
- terminal class `FINALIZED_DIAGNOSTIC` or `FINALIZED_NEGATIVE`.

The expected recovery-transition projection is produced from the retained
synthetic recovery fixture by the exact bound recovery finalizer. The evidence
package separately retains every actual emitted transition record. The offline
verifier checks actual-record bytes/links against the projection, then compares
the result with the independent expected fixture. It does not inspect an active
locator and does not claim host-state truth.

Failure after receipt publication but before locator absence or finalization
retains the locator when it has not been removed. If removal already occurred,
recovery uses the durable `LOCATOR_REMOVAL_AUTHORIZED` transition and observed
absence to append `LOCATOR_ABSENT_CONFIRMED`; it never recreates the locator.
Any ambiguity records an external terminal. Recovery cannot rewrite the receipt
or claim a finalized chain.

### External recovery locator and terminal

The recovery locator, append-only recovery transitions and external terminal
are create-once canonical artifacts under a synthetic recovery root outside
both private cleanup and route-tree roots. Their exact schemas, recovery-state
contract and fixed synthetic instances are retained in the independently
verifiable external-recovery package. The package contains privacy-validated
evidence copies; it never exposes an active locator capability.

The immutable locator descriptor pins `action_sha256`, the exact synthetic
private-root fixture identity, recovery contract and recovery-finalizer
identity. It contains no path and no mutable current-state claim. Each recovery
transition is a separate create-once artifact whose filename is derived from a
bounded ordinal and whose content pins the locator digest, previous-transition
digest (structurally absent for ordinal zero), ordinal and one closed transition
class. The retained transition projection is the ordered digest chain of these
records. Every actual canonical transition record byte sequence is copied
without transformation into the evidence package under
`recovery-transitions/<ordinal>.json` and enumerated by its manifest. The
projection entry pins that retained record's path, byte count, SHA-256, ordinal
and previous-record SHA-256. The verifier recomputes every record digest and
previous link from these emitted durable bytes; replayed expected fixtures are
an independent comparison, not a substitute for actual record bytes.
Private-root creation uses the same transition chain rather than a parallel
evidence authority. `PRIVATE_ROOT_CREATION_AUTHORIZED` is a closed create-once
transition class that pins the locator snapshot, exact intended private-root
fixture identity, creation-operation identity, `attempt_ordinal=1` and
`retry_permitted=false`. It must be durable and reopened before the call.
`PRIVATE_ROOT_CREATION_SUCCEEDED` and `PRIVATE_ROOT_CREATION_FAILED` are the
only result transition classes; each pins the authorization transition digest,
attempt ordinal, operation identity and exact returned result. The success
record also pins the created root fixture identity. The failure record contains
no root-presence claim and requires a later independent absence observation
before zero residue may be asserted. Neither result is valid if the operation
did not return or its outcome is unknown. All authorization and result record
bytes are retained through the existing `recovery-transitions/<ordinal>.json`
inventory and projection.
`recovery-transition-projection.json` is the sole non-circular canonical
transition-record aggregate. There is no separate transition-record manifest
and no finalization-to-tree-manifest reference; the outer tree manifest hashes
the projection and record files after the profile's terminal route/external
bytes exist. Finalization is required only by closed profiles and is not a
prerequisite for retaining or manifesting transition evidence.
A non-identical collision, identity mismatch, missing/duplicate
ordinal, broken previous link or ordinal regression fails closed and cannot
broaden cleanup scope.

The external-terminal schema has four mutually exclusive closed shapes:

| `origin_stage` | Locator fields | Cleanup fields | Permitted terminal codes |
| --- | --- | --- | --- |
| `SETUP_BEFORE_LOCATOR` | valid-locator fields are absent; temp fields are absent only when no temp ever existed, otherwise removal authorization/result digests are required | no temp after an observed locator-publication failure: `attempted=false`, `attempt_count=0`, `NOT_ATTEMPTED`; temp created by that failed publication and then successfully removed: `attempted=true`, `attempt_count=1`, `PASS`, `ZERO_RESIDUE` | no-temp subcase only: `ACTION_PUBLISHED_LOCATOR_NOT_CREATED`; successfully-removed-temp subcase only: `LOCATOR_PUBLICATION_FAILED` |
| `SETUP_TEMP_RESIDUE` | valid-locator fields are absent; `setup_temp_snapshot_sha256`, removal authorization digest and removal result digest are required | `attempted=true`, `attempt_count=1`, `result=FAIL`, `residue=SETUP_TEMP_PRESENT` or `UNKNOWN` | `LOCATOR_TEMP_REMOVAL_FAILED`, `LOCATOR_TEMP_ABSENCE_UNCONFIRMED` |
| `SETUP_TEMP_ATTEMPT_UNKNOWN` | valid-locator fields and removal-result digest are absent; temp snapshot and removal authorization digests are required | `attempted=true`, `attempt_count=1`, `result=UNKNOWN`, `residue=UNKNOWN` | `LOCATOR_TEMP_REMOVAL_RESULT_UNAVAILABLE` |
| `LOCATOR_BOUND_RECOVERY` | locator snapshot digest, locator disposition and transition-projection digest are required | `attempted`, `attempt_count`, result and residue must match the external cleanup matrix | cleanup/recovery codes listed below |

All four shapes pin `action_sha256`, the external-terminal schema, recovery
contract and recovery-finalizer identity. Seal, cleanup-result and receipt
digests are required only when those artifacts durably exist and are otherwise
structurally absent, never null. The setup shape is valid only because the
ordering contract forbids private-root creation until after durable locator
publication. A partial locator temporary file is not a locator. Before any
removal side effect, the launcher durably publishes and reopens
`setup-temp-removal-authorization.json`, pinning the action, exact temp snapshot
digest, publisher/cleanup identities, `attempt_ordinal=1`, operation
`REMOVE_EXACT_SETUP_TEMP`, and `retry_permitted=false`. Only then may it attempt
removal of that exact temporary identity; it never creates a private root.

After the attempt, the launcher durably publishes
`setup-temp-removal-result.json`, pinning the authorization digest,
`attempt_ordinal=1`, closed operation result, and an indivisible canonical
`absence_observation` subrecord. That required subrecord contains only
`observation=ABSENT_CONFIRMED|PRESENT_CONFIRMED|UNKNOWN` and
`observed_temp_fixture_id`, which must equal the authorization-bound fixture
identity and is structurally absent only when observation is `UNKNOWN`.
Operation result and absence observation are written, made durable and
create-once published as the same result artifact; neither can exist or be
hashed independently. A crash before that artifact is durable is exactly the
authorization-without-result state and permanently maps to
`SETUP_TEMP_ATTEMPT_UNKNOWN`. Successful removal plus confirmed absence is `PASS/ZERO_RESIDUE`;
failed removal is `FAIL/SETUP_TEMP_PRESENT`; inability to confirm absence is
`FAIL/UNKNOWN`. All successful and failed profiles retain both canonical
authorization and result bytes, so an actual attempt is never represented as
`NOT_ATTEMPTED`.

If restart observes a durable authorization but no durable result, it must not
repeat removal. It publishes terminal shape `SETUP_TEMP_ATTEMPT_UNKNOWN` with
`attempted=true`, `attempt_count=1`, `result=UNKNOWN`, `residue=UNKNOWN`, and
profile `SETUP_TEMP_ATTEMPT_UNKNOWN`. This is permanent for the authorized
workflow even if the temp is later observed absent; no post-crash observation
may invent the missing side-effect result.

`setup-temp-snapshot.json` pins `action_sha256`, the closed temporary-purpose
label, exact pre-attempt temp fixture identity and publisher identity. It
contains no result or mutable state, no path and grants no cleanup authority
over any other object. Authorization pins its digest; the result and terminal
pin the authorization.
Every setup-temp profile is terminal for the authorized workflow and authorizes
neither private-root creation nor another removal attempt. A present temp is
retained; unknown residue stays unknown.

For locator-bound recovery, every cleanup-attempt transition contains
`attempt_ordinal` in `1..action.max_cleanup_attempts`. Ordinals are contiguous,
each attempt is represented once, and `external-terminal.attempt_count` must
equal both the number and greatest ordinal of retained attempt transitions.
`attempted=false` requires zero attempt transitions; `attempted=true` requires
at least one. Exceeding the action bound or disagreeing with the transition
chain fails closed. These cleanup counters exclude private-root creation
authorization/result transitions; creation has its own fixed ordinal one and
may never be retried.

The external terminal is create-once and durable. The external verifier never
treats it as a route receipt and the route verifier never imports it to upgrade
a route result.

An external terminal that authorizes locator removal is durably published and
reopened while the locator still exists. It records
`RETAINED_PENDING_REMOVAL`, not a future absence. Only after terminal
verification and an independent `ZERO_RESIDUE` recheck may a create-once
`LOCATOR_REMOVAL_AUTHORIZED` transition be appended. That transition pins the
terminal digest. The exact locator descriptor is then removed; a subsequent
create-once transition records `LOCATOR_ABSENT_CONFIRMED`. The transition chain
and terminal remain durable outside the public route tree; the locator
descriptor alone is removed and is never recreated.

After `LOCATOR_ABSENT_CONFIRMED`, the external publisher creates
`external-recovery-finalization.json`. It pins the action, privacy-safe locator
snapshot, external terminal, complete transition projection, recovery
finalizer/verifier identities and `locator_after=ABSENT_CONFIRMED`. It has
terminal class `EXTERNAL_RECOVERY_CLOSED` and cannot contain route
classification fields. An open recovery profile has no finalization and must
retain locator disposition `RETAINED`.

For a pre-seal failure the required external matrix is:

| bounded recovery cleanup | residue | terminal-time locator | external terminal and closeout |
| --- | --- | --- | --- |
| `PASS` | `ZERO_RESIDUE` | `RETAINED_PENDING_REMOVAL` | publish/verify `NO_ADMISSIBLE_SEAL_CLEANED`, then remove exact locator and append `LOCATOR_ABSENT_CONFIRMED` transition |
| `FAIL` or `PARTIAL` | `RESIDUE_PRESENT` or `UNKNOWN` | `RETAINED` | `NO_ADMISSIBLE_SEAL_RECOVERY_REQUIRED` |
| identity cannot be established | `UNKNOWN` | `RETAINED` | `RECOVERY_IDENTITY_UNAVAILABLE` |

No row creates `observation-seal.json`, `cleanup-result.json`,
`final-receipt.json` or `finalization.json`.

For an admissible seal followed by a non-finalizable negative receipt, bounded
recovery does not rewrite any public stage:

| recovery after negative receipt | residue | terminal-time locator | external terminal and closeout | public-tree profile |
| --- | --- | --- | --- | --- |
| cleanup reaches `PASS` | `ZERO_RESIDUE` | `RETAINED_PENDING_REMOVAL` | publish/verify `NEGATIVE_RECEIPT_RECOVERY_CLEANED`, then remove exact locator and append `LOCATOR_ABSENT_CONFIRMED` transition | remains `RECOVERY_REQUIRED_NEGATIVE`; no finalization |
| cleanup remains `FAIL` or `PARTIAL` | `RESIDUE_PRESENT` or `UNKNOWN` | `RETAINED` | `NEGATIVE_RECEIPT_RECOVERY_REQUIRED` | `RECOVERY_REQUIRED_NEGATIVE` |
| identity becomes unavailable | `UNKNOWN` | `RETAINED` | `RECOVERY_IDENTITY_UNAVAILABLE` | `RECOVERY_REQUIRED_NEGATIVE` |

The external cleanup cross-field matrix is:

A durable `PRIVATE_ROOT_CREATION_AUTHORIZED` transition without either result
transition is a permanent unknown creation outcome. Restart must not call
creation again or infer its result from later root presence/absence. It
publishes an `EXTERNAL_RECOVERY_OPEN` locator-bound terminal with code
`PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE`, cleanup `attempted=false`,
`attempt_count=0`, `result=NOT_ATTEMPTED`, `residue=UNKNOWN` and locator
`RETAINED`. If a durable failure result exists but independent root absence
cannot be confirmed, the same open matrix row uses terminal code
`PRIVATE_ROOT_ABSENCE_UNCONFIRMED`. Neither code authorizes automated cleanup,
locator removal or another creation call.

The zero-attempt/zero-residue row uses closed terminal code
`LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED`; it requires a retained
`PRIVATE_ROOT_CREATION_AUTHORIZED` transition, its linked
`PRIVATE_ROOT_CREATION_FAILED` result proving that the single creation call
returned failure, and a subsequent independent private-root absence observation.
Locator durability plus absence is insufficient. In particular, the row is not
inferred from a missing path after a crash. A plain retained `E2` state with no
authorization may publish/reopen authorization but cannot invoke creation
before it; authorization without result is permanently unknown and cannot
resume or repeat the call.

| `attempted` | `attempt_count` | result | residue | locator at terminal | external profile |
| --- | --- | --- | --- | --- | --- |
| `false` | `0` | `NOT_ATTEMPTED` | `UNKNOWN` | `RETAINED` | `EXTERNAL_RECOVERY_OPEN` |
| `false` | `0` | `NOT_ATTEMPTED` | `ZERO_RESIDUE` | `RETAINED_PENDING_REMOVAL` | locator exists but private root was independently observed never created; may advance to `EXTERNAL_RECOVERY_CLOSED` after terminal verification |
| `true` | `1..max` | `PASS` | `ZERO_RESIDUE` | `RETAINED_PENDING_REMOVAL` | may advance to `EXTERNAL_RECOVERY_CLOSED` only after terminal verification and absence transition |
| `true` | `1..max` | `FAIL` | `RESIDUE_PRESENT` or `UNKNOWN` | `RETAINED` | `EXTERNAL_RECOVERY_OPEN` |
| `true` | `1..max` | `PARTIAL` | `RESIDUE_PRESENT` or `UNKNOWN` | `RETAINED` | `EXTERNAL_RECOVERY_OPEN` |

`NOT_APPLICABLE` residue exists only in the pre-locator setup shape. `PASS`
with nonzero residue, an absent locator in locator-bound recovery, an attempt
count outside the action bound, or any result/transition disagreement is
invalid.

The complete durable transition graph is linear on the normal path and branches
only to external recovery. Its setup prefix delegates to the external durable
graph below as the sole authority for locator publication and private-root
creation; the `S` graph has no direct locator-to-root side-effect edge:

| State | Required durable artifacts | Only permitted next transition |
| --- | --- | --- |
| `S0` | none | publish action |
| `S1_ACTION` | action | execute only the `E0_ACTION` through `E2_CREATION_RESULT_RECORDED` setup prefix; any setup failure follows its matrix-defined external terminal path |
| `S2_RECOVERY_READY` | action + locator snapshot/active locator + linked `PRIVATE_ROOT_CREATION_AUTHORIZED`/`PRIVATE_ROOT_CREATION_SUCCEEDED` transitions + exact authorized private-root identity | start observer without recreating the root, or external recovery if observer setup fails |
| `S3_OBSERVING` | prior setup evidence + private state + active observer | publish seal, or external recovery if seal is inadmissible/unavailable |
| `S4_SEALED` | action + immutable seal + locator | bounded cleanup and cleanup-result publication |
| `S5_CLEANUP_RECORDED` | prior stages + cleanup result | matrix-permitted receipt, or external recovery if receipt publication fails |
| `S6_RECEIPT` | prior stages + receipt + locator | verify receipt; if cleanup is not `PASS/ZERO_RESIDUE`, external recovery only |
| `S7_RECEIPT_VERIFIED` | verified receipt + independently confirmed zero residue + locator | append removal authorization, remove exact locator, confirm absence and append absence transition |
| `S8_LOCATOR_ABSENT` | retained public stages + linked authorization/absence transitions | publish exact linked finalization |
| `S9_FINALIZED` | complete finalized public profile | terminal; no further mutation |

Every transition is create-once or removal of the exact locator. No transition
rewrites an earlier artifact. Skipping a state, moving backward, creating a
second action, rerunning the synthetic action, or publishing a finalization
from any state other than `S8_LOCATOR_ABSENT` fails closed.

The external durable graph is separate and complete:

An action-only restart remains in `E0_ACTION` and resumes the one
locator-publication step; action durability alone is not evidence that
publication was attempted or failed. The no-temp edge is explicit only after
that locator publication is observed to fail and retained capture proves that
neither a locator temp nor private root was created:
`E0_ACTION -> E1_SETUP_TERMINAL` publishes terminal code
`ACTION_PUBLISHED_LOCATOR_NOT_CREATED` with no temp/locator fields. If temp
existence is `UNKNOWN`, this edge is forbidden and the workflow fails closed
without claiming a verified external package. If the failed publication created
an exact temp that is subsequently removed with a durable `PASS` result and
confirmed absence, the distinct successfully-removed-temp subcase publishes
`LOCATOR_PUBLICATION_FAILED`; neither terminal code is valid for the other
subcase.

The successful edge is equally explicit: only after the locator bytes are
durably create-once published, reopened byte-identically and captured as an
active locator snapshot may the workflow take
`E0_ACTION -> E2_LOCATOR_READY`. The `E2` retained state binds the action,
locator snapshot and active locator; it does not yet contain or imply a private
root. A crash after this successful edge resumes from `E2_LOCATOR_READY`, never
republishes the locator and may perform only the graph's next create-once
creation-authorization publication; it cannot call creation directly.

| State | Required durable artifacts | Only permitted next transition |
| --- | --- | --- |
| `E0_ACTION` | action | if no locator-publication outcome is retained, resume the single locator-publication step and remain in `E0_ACTION` until its outcome is observed; durable byte-identical publication plus reopen/capture of the active locator takes `E0_ACTION -> E2_LOCATOR_READY`; only an observed failure may publish the no-temp setup terminal when no temp/private root is confirmed, or publish a temp snapshot when the exact failed-publication temp is confirmed |
| `E0_TEMP_SNAPSHOTTED` | action + temp snapshot; no valid locator/private root | publish/reopen create-once removal authorization; no side effect before durability |
| `E0_TEMP_REMOVAL_AUTHORIZED` | action + temp snapshot + removal authorization | attempt exact temp removal once; on restart with no result, removal is forbidden and unknown terminal is required |
| `E0_TEMP_RESULT_RECORDED` | action + snapshot + authorization + result | publish matrix-valid setup terminal; never remove again |
| `E1_SETUP_TERMINAL` | action + setup terminal; no locator/private root | build and verify `SETUP_TERMINAL_BEFORE_LOCATOR` external package; terminal |
| `E1_TEMP_RESIDUE` | action + temp snapshot + setup-residue terminal; no valid locator/private root | build and verify `SETUP_TEMP_RESIDUE_OPEN`; retain exact temp only when observed present, otherwise preserve `UNKNOWN`; terminal |
| `E1_TEMP_ATTEMPT_UNKNOWN` | action + temp snapshot + authorization + unknown terminal; result absent | build and verify `SETUP_TEMP_ATTEMPT_UNKNOWN`; never retry or infer result; terminal |
| `E2_LOCATOR_READY` | action + locator snapshot + active locator; no creation authorization | publish/reopen create-once `PRIVATE_ROOT_CREATION_AUTHORIZED`; no creation side effect is permitted in `E2` |
| `E2_CREATION_AUTHORIZED` | action + locator + creation authorization; no creation result | only the uninterrupted authorizing process may invoke creation once and publish the exact returned result; any restart with no result publishes `PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE`, never invokes creation and enters the open terminal path |
| `E2_CREATION_RESULT_RECORDED` | action + locator + linked authorization/result | success with the exact root identity enters observation without recreating it; failure requires an independent absence observation, then enters zero-attempt `E4_RECOVERY_OUTCOME`; unconfirmed absence enters the open terminal path |
| `E3_RECOVERY_ENTERED` | locator-bound failure transition | append zero or more bounded cleanup-attempt transitions |
| `E4_RECOVERY_OUTCOME` | zero-or-more contiguous cleanup-attempt transitions + residue observation; zero attempts with zero residue additionally require linked creation authorization/failure-result transitions | publish matrix-valid external terminal |
| `E5_TERMINAL_DURABLE` | external terminal + locator | reopen and verify terminal; on fail/partial publish open package and retain locator; on pass continue |
| `E6_TERMINAL_VERIFIED` | verified terminal + independent zero-residue recheck | append `LOCATOR_REMOVAL_AUTHORIZED` |
| `E7_REMOVAL_AUTHORIZED` | linked authorization transition + locator | remove exact locator descriptor; never recreate it |
| `E8_LOCATOR_ABSENT` | observed absence + `LOCATOR_ABSENT_CONFIRMED` transition | publish external recovery finalization |
| `E9_EXTERNAL_FINALIZED` | complete `EXTERNAL_RECOVERY_CLOSED` package | terminal; no mutation |

Neither setup branch can enter `E2` after its terminal. The open branch ends at
`E5`; it retains the locator and reports recovery required. No automated
transition may follow a create-once open terminal. Any future manual recovery
design would require separate authority and a new evidence contract; this
candidate does not authorize one.

## Public Schema Contract

Each proposed schema is retained as canonical JSON and uses:

- a fixed `schema` discriminator;
- `type: object`;
- explicit `required` lists;
- `additionalProperties: false` recursively;
- closed enums for every disposition;
- lowercase 64-character SHA-256 syntax for public artifact and implementation
  identities;
- non-negative integers with explicit maxima for counts;
- no free-form maps; and
- no nullable escape hatch for required evidence.

Strings are permitted only for schema IDs, closed enum values, fixed synthetic
IDs and lowercase SHA-256 values. Arbitrary strings, exception messages and
implementation-provided reason text are prohibited. Public failure reasons are
closed codes from the schema.

The public-stage, fixture, locator and terminal schemas are separate to prevent
a later-stage field from being backfilled into an earlier immutable artifact.
Cross-field matrices above are semantic verifier rules in addition to JSON
shape validation. A schema digest is valid only when its exact schema bytes are
retained in the public tree and pinned by `action.json`.

## Privacy Contract

The public privacy contract is deny-by-default and validates keys, value types,
closed string domains and cross-field provenance before publication.

### Permitted public data

- closed schema/contract identifiers;
- new synthetic diagnostic/run IDs;
- fixed enums, booleans and bounded integers;
- ordinals and counts that describe fixed synthetic fixtures only;
- retained fixed synthetic lifecycle/recovery scripts and expected projections
  containing only closed markers and fixture IDs;
- fixed synthetic locator snapshots, external terminals and recovery
  transitions whose complete bytes are enumerated by an approved fixture
  manifest;
- fixed synthetic setup-temp snapshots, removal authorizations and removal
  results containing only closed fixture identities, enums and ordinals;
- actual emitted canonical synthetic transition-record bytes after the privacy
  validator confirms they contain only closed fixture identities and enums;
- digests of retained public contract, schema, implementation and artifact
  bytes; and
- digests of explicitly enumerated fixed synthetic fixture bytes whose bytes
  are retained for reviewer reconstruction.

### Forbidden public data

- credentials or authentication state, including booleans that reveal whether
  two secret seeds match;
- prompts, task text, Skill text, final responses, event payloads, stdout or
  stderr;
- host paths, path fragments, usernames, home/profile names, hostnames, process
  arguments or environment data;
- IDs or digests copied from the consumed pair;
- arbitrary event names, arbitrary failure messages or stack traces;
- hashes, byte counts or equality signals derived from live, user-controlled or
  low-entropy private content; and
- any live locator, recovery path, cleanup target identity or external terminal
  instance; and
- fields whose safety depends only on redaction or substring scanning.

The privacy validator must reject unknown fields before inspecting values. It
then enforces field-specific closed domains and provenance. A generic
"sensitive-looking substring" scan may be defense in depth but cannot establish
admissibility. The observer, classifier and verifier never receive credentials.
Synthetic tests pass an explicitly empty capability object; they do not inspect
or copy the host environment.

Any future live design requires a new privacy authority decision. This
candidate grants no live-content digest, path, event or credential authority.

## Offline Verifier Contract

The verifier consumes one caller-selected route or external-recovery package
through a read-only tree adapter. It never discovers a default live evidence
location. Its pure input requires three out-of-band values from the independent
candidate approval: `expected_tree_manifest_sha256`,
`expected_verifier_sha256` and the reviewed execution-command-contract digest.
Absence or mismatch of any value is `VERIFICATION_UNAVAILABLE`, not a
self-authorized fallback.

### Honest bootstrap and byte-capture boundary

This candidate defines no self-verifying bootstrap. `offline_verifier.py`
cannot prove which interpreter loaded it, which launcher opened it or whether
that launcher was itself the reviewed program. The execution command contract
and retained implementation identities are comparison inputs only.

The verifier core is therefore a pure in-memory function over a captured
package byte set plus the three reviewed expected digests. It performs no
imports, path discovery or file opens. A caller-selected capture adapter may
supply bytes and private capture metadata, but that adapter's execution
authenticity is outside this candidate unless a reviewer independently trusts
and identifies it.

The only positive verifier claim is `CAPTURED_BYTE_SET_RECONSTRUCTED`: the pure
verifier recomputed canonical schemas, links, fixtures and classifications from
the supplied captured bytes. It makes no claim that the bytes were captured by
a reviewed executable, that they represent one simultaneous filesystem state,
or that the package stayed immutable during capture. If a caller requests
execution authenticity or a closed-snapshot claim, the candidate returns
`VERIFICATION_UNAVAILABLE` for that stronger claim.

No route/external semantic result may cite `CAPTURED_BYTE_SET_RECONSTRUCTED` as
proof of trusted execution. An independent review may elevate confidence only
by naming its own prior trusted mechanism and exact command outside this
candidate. The candidate never hashes or validates that mechanism from inside
the environment it is meant to authenticate. The capture adapter receives an
explicitly empty capability input and must not inspect or copy credentials.

### Defensive filesystem byte capture

An optional filesystem capture adapter may defensively reduce races. Before
reading the manifest it should:

1. opens the selected package's parent and root directories with no-follow
   semantics and retains both handles through verdict construction;
2. rejects root/parent symlink, junction or reparse state;
3. records private parent/root identities and the parent-name-to-root mapping;
4. enumerates names and entry identities through the retained root handle;
5. opens every expected entry relative to that root handle, with no-follow
   semantics, and retains all entry handles;
6. read each entry once and record identity, bytes, count and digest;
7. re-enumerate through the same root handle after every artifact and semantic
   check;
8. compare the final names and identities with the initial inventory and exact
   manifest; and
9. recheck parent/root identities and the parent-name-to-root mapping
   immediately before constructing the verdict.

Insertion, removal, replacement, case-collision, parent switch or root-name
replacement at any point makes the verification fail closed. All directory and
entry handles remain open until the captured byte-set descriptor is durably
built. The descriptor records exactly the bytes actually read. Initial/final
inventory and identity checks may detect replacements, but same-identity
in-place mutation after an entry's read may remain undetected. Therefore the
evidence level is always `CAPTURED_BYTE_SET_RECONSTRUCTED`; the report must not
use `closed tree`, `immutable snapshot` or equivalent language.

If the platform cannot provide root-relative no-follow opens or a stable
one-time read, byte capture is `VERIFICATION_UNAVAILABLE`. This design does not
specify, consume or validate a write-denial capability. A future immutable-
snapshot claim requires a separate design and authority.

Verification is deterministic and performs these ordered checks:

1. receive an immutable captured-byte-set descriptor and the three reviewed
   expected digests; reject every request for a stronger execution or snapshot
   claim;
2. read the captured `tree-manifest.json` bytes, require
   canonical bytes and compare its digest with the reviewed
   `expected_tree_manifest_sha256`;
3. validate the manifest schema and its closed artifact profile;
4. reject symlinks, junctions/reparse points, non-regular files, duplicate
   logical names, case-colliding names and files outside the exact manifest;
5. require the exact file inventory for the declared profile; reject every
   missing or extra file;
6. bind every captured entry's bytes, digest, count and private capture identity
   to the captured-byte-set descriptor;
7. require canonical JSON byte equality for every JSON artifact;
8. validate each artifact against its pinned exact schema with no unknown
   fields;
9. run the privacy contract over every public artifact;
10. recompute all schema, contract, retained implementation, fixture and
    artifact digests from exact retained bytes;
11. for a route profile, validate fixture topology and replay the retained raw
    script through the exact bound observer, requiring byte equality with both
    the independent expected projection and sealed projection;
12. for a route profile, independently enforce per-node start/termination,
    parent-before-child, barrier, contiguous-ordinal, gap/overflow and
    final-snapshot invariants;
13. for a route profile, require exact `locator-snapshot.json`, validate its
    canonical bytes, recovery-locator schema and privacy contract, recompute its
    digest, then require the creation authorization to pin that digest; verify
    action -> seal -> cleanup result -> final receipt links and the retained
    transition projection/records including linked creation authorization/
    success result; only `FINALIZED_CHAIN` additionally verifies receipt ->
    finalization, while `RECOVERY_REQUIRED_NEGATIVE` must reject any
    `finalization.json`;
14. for an external profile, reject every route-only artifact/field, verify the
    setup or locator-bound terminal shape, replay the retained raw external
    fixture through the exact bound recovery state machine, compare it with the
    independently authored expected recovery projection and retained terminal,
    reconstruct the attempt-count-bound transition chain and require exact
    external-finalization links only for `EXTERNAL_RECOVERY_CLOSED`;
15. require every route seal to retain `PENDING` cleanup/receipt fields and reject any
   evidence that it was rewritten after cleanup;
16. reconstruct route classification from the canonical seal input using the exact
   retained bound classifier and compare byte-for-byte with seal and receipt;
17. enforce every applicable route or external cleanup, residue, receipt,
    locator and finalization state matrix;
18. preserve the explicit captured-byte-only evidence level regardless of
    defensive capture metadata; and
19. emit a profile-specific evidence-level verdict without echoing rejected
    values.

Any failed check yields `FAIL_CLOSED`. The verifier must never downgrade a
schema, privacy, identity, tree-closure or cross-link failure to a warning.
Ordinary invalid input returns a well-formed failure result and does not throw;
environmental inability to establish safe byte capture returns
`VERIFICATION_UNAVAILABLE`, never a reconstruction verdict.

`CAPTURED_BYTE_SET_RECONSTRUCTED` proves only that supplied synthetic public
bytes are canonical, privacy-admissible and internally linked under the pinned
transformation identities; it does not prove a simultaneous closed tree or
trusted verifier execution.
`FINALIZED_CHAIN` proves reconstruction of the
retained synthetic locator transition; it does not independently inspect a
runtime locator. `EXTERNAL_RECOVERY_CLOSED` proves reconstruction of the
retained synthetic external terminal and closeout transitions;
`EXTERNAL_RECOVERY_OPEN` proves that recovery remains open, not that cleanup
succeeded. No verdict proves the truth of deleted private bytes, host-OS
durability, real CLI semantics or any live effect.

## TOCTOU and Observer-Failure Test Plan

Expected values come from this candidate's state machine and closed invariants,
not from duplicating future production logic inside tests.

| Synthetic mutation | Required result |
| --- | --- |
| pre-existing target | `PATH_INVALID` or fixture-declared baseline state; never silently overwritten |
| target is directory | `PATH_INVALID` |
| target is symlink/junction/reparse point | `PATH_INVALID` |
| parent identity changes before launch | no launch; `INDETERMINATE` |
| parent identity changes during observation | final axis `INDETERMINATE` |
| target created then removed | `CREATED_THEN_REMOVED` |
| target replaced before handle open | `PATH_INVALID` |
| target replaced after open before read | stable-handle bytes may be read, but identity contradiction makes overall result `INDETERMINATE` |
| target replaced during/after read | `INDETERMINATE`; captured-valid forbidden |
| handle-bound read fails | `READ_FAILED`; adapter-capture class only when all other prerequisites are admissible |
| observer starts after launch | incomplete coverage; no no-creation claim |
| sequence gap, duplicate or reorder | `INDETERMINATE` |
| observer overflow | `INDETERMINATE` |
| event after coverage stop | `INDETERMINATE` |
| missing process-tree termination | `INDETERMINATE` |
| child outlives synthetic root process | incomplete tree termination; `INDETERMINATE` |
| final snapshot fails | `INDETERMINATE` |
| unknown lifecycle marker | reject without echoing marker |
| package root replaced after initial enumeration | verifier `FAIL_CLOSED`; retained root handle and parent mapping disagree |
| extra file inserted after initial inventory | final root-handle enumeration differs; `FAIL_CLOSED` |
| entry deleted/recreated with same bytes | entry identity differs; `FAIL_CLOSED` |
| entry mutates in place during read and adapter detects unstable read | `VERIFICATION_UNAVAILABLE` for capture; no partial reconstruction claim |
| entry mutates in place during or after read without a detected read failure | exactly captured bytes may be reconstructed, but only `CAPTURED_BYTE_SET_RECONSTRUCTED` is allowed |
| caller labels capture as immutable or write-denied | label is ignored/rejected; verifier cannot upgrade beyond captured-byte evidence |
| package parent or root-name mapping switches before verdict | `FAIL_CLOSED` |
| platform lacks root-relative no-follow enumeration | `VERIFICATION_UNAVAILABLE` |
| caller asks candidate to prove its own interpreter/import authenticity | `VERIFICATION_UNAVAILABLE`; no self-bootstrap claim |
| captured verifier bytes mismatch reviewed verifier digest | captured-byte reconstruction fails closed; no execution-authenticity inference |

Tests must also mutate each identity, schema digest and stage link independently
to prove that no summary-only cross-boundary evidence is accepted.

## Crash, Publication and Recovery Test Plan

The synthetic durable-store fixture exposes a crash point before and after
every state transition. Recovery begins from retained bytes only; it cannot use
in-memory state from the interrupted process.

| Crash or failure point | Required durable state and recovery disposition |
| --- | --- |
| before action publication | no action, locator or private root; no execution or cleanup |
| partial action write | no published action; no locator, launch or cleanup |
| after action, before any locator-publication attempt or retained publication outcome | action retained; no launch, cleanup or setup terminal; remain in `E0_ACTION` and resume the single locator-publication step |
| after durable byte-identical locator publication/reopen, before creation authorization | action, locator snapshot and active locator retained; resume from `E2_LOCATOR_READY`, do not republish locator, and publish/reopen authorization before any creation call |
| after durable creation success result, before observer start | action, locator, linked authorization/success result and identity-bound private root retained; do not recreate the root; resume observation setup, or bounded external recovery if setup fails |
| during observation before seal | no admissible seal; bounded external recovery cleanup; terminal records residue and locator outcome |
| seal temp write/durability failure | no admissible seal; bounded external recovery cleanup; no route receipt |
| seal publication collision | compare exact bytes; any non-identical collision fails closed; no overwrite |
| after durable seal, before cleanup | immutable seal retained; recovery may attempt bounded cleanup |
| during cleanup | seal retained; cleanup result `PARTIAL` or `UNKNOWN`; locator retained |
| cleanup reports success but residue exists | contradiction; no diagnostic receipt |
| cleanup-result publication failure | locator retained; external terminal records failure |
| after durable cleanup result, before final receipt | seal and cleanup result retained; recovery may publish only the matrix-permitted receipt without rerunning the action or cleanup |
| final-receipt partial write or collision | no overwrite; locator retained |
| after receipt publication, before reopen verification | receipt retained; locator retained until verification completes |
| after receipt verification, before locator removal | chain retained; bounded recovery may remove only the exact locator after rechecking zero residue |
| after `LOCATOR_REMOVAL_AUTHORIZED`, before removal | locator retained; recovery may remove only the exact descriptor pinned by the transition |
| after locator removal, before absence confirmation | no finalization; recovery requires the authorization transition plus observed absence, appends `LOCATOR_ABSENT_CONFIRMED`, and never recreates the locator |
| after absence confirmation, before finalization publication | receipt retained; recovery may publish only the exact linked finalization from retained transition records |
| finalization partial write or collision | no overwrite; external terminal records unfinalized chain |
| locator removal fails or locator reappears | no finalization; receipt remains unfinalized and recovery-required |

Every external durable transition has its own before/after crash fixture:

| External crash/collision point | Required restart behavior from retained bytes |
| --- | --- |
| locator publication fails with confirmed no temp/private root | take explicit `E0_ACTION -> E1_SETUP_TERMINAL` edge; publish no-temp profile with no removal records |
| locator publication fails but temp existence is unknown | no setup-terminal package is verified; fail closed without cleanup or private-root creation |
| locator temp exists after failed durable locator publication | publish exact temp snapshot, then durable removal authorization; private root must be absent |
| after temp snapshot, before removal authorization | publish/reopen authorization; no removal has occurred and restart follows the same step |
| removal-authorization partial write/collision | no removal until exact canonical authorization is durable and reopened; identical bytes resume, non-identical bytes fail closed |
| after durable authorization, before removal call | restart must not call removal because it cannot distinguish this state from a crash during/after the side effect; publish `SETUP_TEMP_ATTEMPT_UNKNOWN` |
| during removal or after return, before durable result | publish `SETUP_TEMP_ATTEMPT_UNKNOWN`; retain actual temp when present; never call removal again or infer success from later absence |
| removal-result partial write/collision | result is not admissible unless exact canonical bytes are durable; restart treats missing/non-identical result as permanent unknown and never removes again |
| operation result and absence fields disagree or one is missing | entire indivisible result artifact is invalid; permanent unknown terminal; no retry |
| after durable removal result, before terminal | publish only the terminal row exactly linked to the result; no side effect repeats |
| locator-temp removal fails | publish/verify `SETUP_TEMP_RESIDUE_OPEN` with `LOCATOR_TEMP_REMOVAL_FAILED`; retain exact temp; no retry or private root |
| locator-temp removal reports success but absence cannot be confirmed | publish/verify `SETUP_TEMP_RESIDUE_OPEN` with `LOCATOR_TEMP_ABSENCE_UNCONFIRMED`; residue is `UNKNOWN` and this candidate performs no further action |
| setup-temp snapshot partial write/collision | no terminal/package claim; identical bytes may resume, non-identical bytes fail closed; no private root |
| setup-residue terminal partial write/collision | no verified package until identical create-once terminal is reopened; non-identical collision fails closed |
| after setup-residue terminal, before package manifest | retain temp and terminal; package exact `SETUP_TEMP_RESIDUE_OPEN` inventory only |
| locator publication collision | identical canonical bytes may resume; non-identical bytes fail closed; private root remains uncreated |
| plain crash after durable locator, before creation authorization | retain locator snapshot and resume from `E2_LOCATOR_READY`; publish/reopen authorization before any call |
| creation-authorization partial write/collision | creation is forbidden until exact canonical authorization is durable and reopened; identical bytes resume publication, non-identical bytes fail closed |
| after durable creation authorization, before the call | restart treats authorization-without-result as permanently unknown, publishes `PRIVATE_ROOT_CREATION_RESULT_UNAVAILABLE` and never calls creation |
| during creation or after return, before durable result | authorization-without-result remains permanently unknown; publish the same open terminal, do not call creation again and do not infer outcome from later presence/absence |
| creation-result partial write/collision | result is inadmissible unless exact canonical bytes are durable; missing/non-identical result maps to permanent unknown and never permits another call |
| after durable `PRIVATE_ROOT_CREATION_SUCCEEDED`, before observer start | retain the exact authorized root identity and enter observation without recreating the root |
| after durable `PRIVATE_ROOT_CREATION_FAILED`, before absence observation | perform only the independent absence observation; confirmed absence enters zero-attempt `E4_RECOVERY_OUTCOME`, while unknown/present observation publishes `PRIVATE_ROOT_ABSENCE_UNCONFIRMED` and remains open |
| after linked failure result and confirmed absence, before terminal | enter `E4_RECOVERY_OUTCOME` with zero attempts and publish only `LOCATOR_CREATED_PRIVATE_ROOT_NOT_CREATED` |
| after private-root creation success, before recovery-entry transition | append exact `RECOVERY_ENTERED` only when observation/setup subsequently fails; never recreate the root or relaunch action |
| before/after each cleanup-attempt transition | resume from greatest contiguous durable ordinal; never repeat or exceed `action.max_cleanup_attempts` |
| cleanup-attempt transition collision | identical bytes resume; non-identical bytes make external recovery open and fail closed |
| transition record copied to package but projection/manifest missing | no verified package; rebuild projection and manifest only from retained canonical record bytes |
| transition projection exists but one record is missing/mutated | package verification fails closed; fixture replay cannot substitute for the missing emitted record |
| after last attempt, before residue observation | locator retained; residue `UNKNOWN`; no terminal may claim `PASS` |
| after residue observation, before external-terminal publication | reconstruct exact matrix row from transitions and observation; publish once |
| external-terminal partial write/durability failure | no terminal claim; locator retained; retry publication of identical bytes only |
| external-terminal collision | identical bytes reopen/verify; non-identical bytes fail closed and retain locator |
| after terminal publication, before reopen verification | terminal retained; locator retained; verification precedes any removal authorization |
| removal-authorization partial write/collision | no locator removal unless exact linked authorization is durable; non-identical collision fails closed |
| after authorization, before locator removal | remove only descriptor whose digest is pinned by authorization |
| after locator removal, before absence transition | require durable authorization plus observed absence; append absence transition; never recreate locator |
| absence-transition partial write/collision | no external finalization; identical bytes resume, non-identical bytes fail closed |
| external-finalization partial write/collision | no closed-profile claim; identical bytes reopen/verify, non-identical bytes fail closed |
| after external finalization, before package manifest | rebuild exact profile inventory from retained handles; no state transition is rerun |
| external-package manifest partial write/collision | no verified package until exact out-of-band manifest digest matches; non-identical collision fails closed |

The `SETUP_TERMINAL_BEFORE_LOCATOR` and `SETUP_TEMP_RESIDUE_OPEN` branches have
the same terminal publication/reopen and package-manifest crash fixtures. The
residue profile additionally has temp-snapshot publication/removal-failure
fixtures, but neither branch has valid-locator cleanup transitions or locator
removal authorization. Every expected restart disposition is authored in the
retained fixture manifest rather than calculated by the publisher under test.

Create-delete-create attacks against temporary and final publication names,
case collisions, parent-directory switches and file replacement during verifier
reads are mandatory fixtures. No retry may create a second diagnostic action;
bounded recovery continues only the same synthetic state machine and can never
rerun the synthetic action.

## Focused Evidence Plan

A later implementation, if separately authorized, must remain offline and use
only stdlib plus the repository test runner. Focused evidence must include:

1. contract tests for every required/forbidden schema field and every closed
   enum;
2. independent expected-value sequence tests for all observer and per-node
   topology transitions, including a retained child-outlives-parent fixture;
3. mutation-sensitive TOCTOU tests listed above;
4. crash-point tests immediately before and after every transition from `S0`
   through `S9`, plus every external-recovery branch;
5. privacy mutation tests for paths, prompts, model/Skill text, credential-like
   values, arbitrary events, raw stderr and live-like content digests;
6. same-shaped but unapproved fixture IDs and content identities;
7. byte mutation of every action/seal/cleanup/receipt/finalization, locator and
   recovery-transition digest link;
8. immutable-seal tests proving cleanup cannot rewrite the seal;
9. fresh-root reconstruction from an exact committed file inventory, including
   expected out-of-band manifest/verifier/command-contract digests and an
   archive/export simulation that does not depend on empty directories;
10. verifier tree attacks: root/parent switch, insertion after first inventory,
    deletion/recreation, extra/missing file, symlink/reparse, case collision,
    replacement during read and non-canonical JSON;
11. bootstrap-boundary tests proving the candidate never upgrades captured
    bytes into trusted-execution evidence, and returns
    `VERIFICATION_UNAVAILABLE` when execution authenticity or a closed snapshot
    is requested;
12. implementation-identity collision tests for source bytes, command contract,
    nested code, bound data and exception-dispatch bytes;
13. every allowed and forbidden row in the cleanup, receipt, external recovery
    and durable-transition matrices, including authorization-without-result
    restart behavior, action-only restart remaining in `E0_ACTION`, the
    explicit observed-failure no-temp E-graph edge, the disjoint mapping of
    no-temp and successfully-removed-temp terminal codes, successful durable
    locator publication taking `E0_ACTION -> E2_LOCATOR_READY`, restart from
    that retained `E2` state without locator republication, create-once
    `PRIVATE_ROOT_CREATION_AUTHORIZED` before the call, permanent unknown/no
    retry for authorization without result, linked success/failure result
    transitions, failure plus independent absence to the zero-attempt terminal,
    normal-route admission only after linked creation authorization/success
    evidence, both route profiles retaining the exact privacy-safe locator
    snapshot pinned by authorization, negative-route retention of the complete
    transition projection, and every operation-result/absence-subrecord
    combination;
14. all route and external package profiles: `FINALIZED_CHAIN`,
    `RECOVERY_REQUIRED_NEGATIVE`, `SETUP_TERMINAL_BEFORE_LOCATOR`,
    `SETUP_TEMP_RESIDUE_OPEN`, `SETUP_TEMP_ATTEMPT_UNKNOWN`,
    `EXTERNAL_RECOVERY_CLOSED` and `EXTERNAL_RECOVERY_OPEN`;
15. deterministic repeated reconstruction with no wall clock, random or test
    order dependency; and
16. a never-raises invalid-input corpus for the verifier's public result API.

The focused suite must prove sensitivity by reintroducing at least these
mutations: permit a normal cleanup result/receipt before a seal; suppress the
required pre-seal external recovery cleanup; allow seal rewrite; accept one
broken digest or recovery-transition link; trust process-tree completion
without per-node termination; accept observer overflow; accept a live-like
content digest; treat an unfinalized receipt as locator-absent; and accept a
replacement during verifier read; omit a locator digest from locator-bound
terminal; accept an attempt count above the action bound; trust a setup terminal
as a route receipt; omit one canonical transition record while retaining its
projection; accept a failed temp-removal as residue-free; upgrade byte-capture
only to immutable snapshot; or describe same-identity post-read mutation as a
closed-tree capture; retry removal after durable authorization without result;
represent an actual setup-temp removal as `NOT_ATTEMPTED`; or omit the canonical
snapshot/authorization/result bytes from a setup profile; split operation
result and absence observation across publications; or accept a no-temp setup
terminal when temp existence is `UNKNOWN`; manufacture a setup terminal from
an action-only crash without an observed locator-publication failure; or swap
the no-temp and successfully-removed-temp terminal codes; remove the successful
`E0_ACTION -> E2_LOCATOR_READY` edge; enter `E2` without byte-identical durable
publication/reopen and an active locator snapshot; or republish the locator
when restarting from retained `E2` state; call private-root creation before
durable authorization; call it again after authorization without result; infer
creation success or failure from later presence/absence; omit, unlink or forge
the authorization or result transition; accept success without the exact
authorized root identity; enter observation without a durable success result;
or accept the zero-attempt terminal without linked authorization/failure result
followed by an independent confirmed-absence observation; let the normal `S`
graph bypass any `E2` creation substate; omit the projection or one creation
record from `RECOVERY_REQUIRED_NEGATIVE`; or require finalization merely to
manifest otherwise durable transition evidence; omit `locator-snapshot.json`
from either route profile; mutate its canonical bytes/schema/privacy fields;
substitute its digest while leaving authorization unchanged; or accept an
authorization whose locator-snapshot digest does not match the retained exact
snapshot bytes.
Each mutation must make at least one specific test fail.

No test may read host credentials, invoke preflight/live, access the network or
copy the consumed pair. Synthetic IDs and bytes are generated from retained
fixtures only.

## Failure Precedence and Closed Outcomes

Precedence is fixed:

1. privacy, schema, identity, canonical-byte, tree-closure or stage-link failure
   invalidates the public chain;
2. incomplete observer coverage, process-tree termination or identity stability
   makes affected observations `INDETERMINATE`;
3. seal absence forbids normal `cleanup-result.json` and any route receipt, but
   requires bounded external recovery cleanup when an identity-bound private
   root exists;
4. cleanup ambiguity or residue contradiction forbids a diagnostic receipt and
   permits only the matrix-defined negative/external recovery path;
5. a receipt without the linked finalization remains unfinalized and cannot
   attest locator absence;
6. final publication or locator-finalization failure retains recovery state and
   yields an external terminal; and
7. only after all preceding checks pass may the existing classifier's closed
   diagnostic result be reported at the evidence maturity established by the
   tree profile.

No cleanup or publication outcome can upgrade a weak observation. No classifier
output can repair a broken evidence chain.

## Affected Surfaces if Later Implemented

This design slice changes only this candidate document. A later implementation
would likely require, subject to a new exact allowlist:

- an isolated synthetic lifecycle fixture/observer module;
- canonical schema and contract files under a diagnostic-specific artifact
  namespace, not the repository-wide `schemas/` authority by default;
- a create-once synthetic publisher/cleanup state machine;
- route and external-recovery evidence package builders;
- a read-only offline verifier with a synthetic root-handle snapshot adapter
  and explicit captured-byte-set descriptor;
- focused synthetic tests; and
- an independently reviewed candidate manifest that pins every exact byte.

The promoted Gate 3 contract, owner pin, old evidence, old pair verifier and
existing classifier remain unchanged unless separately authorized. Repository-
wide schemas, runtime hooks, gate policy, CI and enforcement are not implied by
this candidate.

## Claim Ceiling

This candidate may claim only:

- a proposed synthetic integration architecture;
- proposed closed public schemas and verifier behavior;
- proposed lifecycle, TOCTOU, crash, recovery and privacy fixtures;
- current repository gaps observed from committed files; and
- one recommended next offline implementation tranche.

It may not claim that:

- an observer, publisher, cleanup adapter, schema, verifier, seal or receipt has
  been implemented or enforced;
- any host filesystem durability or native watcher guarantee is proven;
- private raw content can be reconstructed after deletion;
- live content digests or event semantics are privacy-approved;
- the consumed pair has been reclassified, retried, replaced or enriched;
- credentials, preflight, live execution, a new sample or Gate 3 success are
  authorized; or
- model, adapter, CLI, Skill, route, task or framework effectiveness is known.

## Recommended Next Implementation Tranche

Only after this exact candidate receives an independent read-only approval, the
smallest meaningful implementation tranche would be:

1. implement the deterministic in-memory synthetic world and lifecycle observer
   state machine;
2. implement canonical value builders and pure validators for the proposed
   public-stage, manifest, fixture and recovery schemas;
3. implement an in-memory create-once durable-store simulator, normal and
   external recovery state machines, both evidence-package profiles and the
   read-only root-snapshot verifier;
4. reuse the existing pure classifier only through its public closed-input API;
5. add the focused synthetic observer, TOCTOU, crash, privacy and reconstruction
   tests in this candidate; and
6. stop for a new independent byte-exact review.

That tranche must not use the host filesystem as evidence, implement a native
watcher, invoke a process, read credentials, execute preflight/live, create or
reuse a Gate 3 pair, update an owner pin, promote a manifest or request live
authorization. Native filesystem observation and any future live privacy
decision remain separate design problems requiring separate owner authority.
