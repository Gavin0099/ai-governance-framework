# Gate 3 Route v2 Non-Counted A/B Design Candidate

Status: `CANDIDATE — PENDING INDEPENDENT SEMANTIC REVIEW`

Date: 2026-08-08

## Problem

Gate 3 route v2 has one independently approved, real, single-session,
synthetic, non-scoring vertical slice. That result establishes one complete
action -> observation -> verification -> claim chain, but it does not establish
that the route can preserve an A/B comparison across two fresh contexts.

The next problem is therefore narrower than Gate 3 execution:

> Define a synthetic, non-counted A/B contract that reuses the proven
> single-session route twice, proves the two contexts are fresh and isolated,
> permits only the candidate treatment difference promoted before execution,
> and fails closed on any
> model, executable, harness, input or evidence mismatch.

This document is a design only. It does not implement an A/B orchestrator,
authorize a session, or reopen counted Gate 3.

## Current Repository Truth

1. `docs/governance/gate3-route-v2-charter-20260805.md` defines Layer 0
   evidence acquisition and explicitly excludes A/B work from its first
   tranche.
2. `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_route_v2.py`
   implements one route invocation, create-once public artifacts, cleanup,
   recovery and offline verification. Its live authorization is
   `gate3_route_v2_single_session_non_scoring_only`.
3. The single-arm public set is exactly `preflight.json`, `action.json`,
   `attestation.json`, `packet.json`, `seal.json` and `final.json`. The offline
   verifier independently loads those files and rejects a remaining locator,
   same-run external terminal, private cleanup target, missing artifact,
   action mismatch or final-receipt mismatch.
4. `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_route_v2_codex.py`
   pins CLI version `codex-cli 0.146.0`, executable SHA-256, runner SHA-256,
   command-contract SHA-256, environment-policy SHA-256 and a measured
   zero-session preflight. Its current command contract does not include an
   explicit model selector.
5. The execution identity currently names the CLI/executable build. It does
   not expose or verify an independently named backend model build. This
   design must not relabel the executable digest as a backend model-build
   identity.
6. The independently reviewed live result
   `gate3-route-v2-live-v2-20260808` returned `SUCCESS`, passed byte-level
   public privacy validation and reconstructed its complete digest chain from
   source commit `c37721e55760f9febdd7f3c825fc6cb3589b5a41`. Its final receipt
   SHA-256 is
   `fb88b586034d0133fe21a298036afc27fbdf2a0a23dee49d12ea26a29bab1857`.
   This local public evidence is not yet a repository-bound experiment
   artifact and proves only one non-scoring synthetic invocation.
7. The existing Gate 3 preregistration candidate defines the proposed primary
   treatment contrast:
   arm A is the common harness without the Bug Fix Skill; arm B is the same
   harness with the Bug Fix Skill. Within a pair, only Skill presence may
   differ. This design reuses that treatment meaning but does not reuse any
  prior execution authorization or counted-sample status. Those candidate
  treatment bytes are not an authority until independent review, owner
  signature and canonical promotion are complete.

## Target Outcome

Produce a reviewable contract for one non-counted synthetic A/B pair in which:

- arm A and arm B each use one fresh isolated context;
- both arms use one exact owner-selected model identifier promoted before
  execution and one exact CLI/executable build;
- all non-treatment inputs and implementation identities are equal after
  approved path-token normalization;
- only the treatment packet differs: absent for A and the exact approved Bug
  Fix Skill packet for B;
- each arm independently produces and verifies the complete route v2 evidence
  chain; and
- one pair verifier reconstructs both arms, checks freshness and equality, and
  atomically publishes a privacy-safe non-counted pair receipt.

The target is a design that can later be implemented with synthetic fixtures.
It is not a claim that the pair route exists.

## Scope

This candidate covers only:

- one synthetic non-counted pair containing exactly arm A and arm B;
- two fresh isolated execution contexts;
- pair-level identity and mismatch-fail rules;
- per-arm reuse of the existing route v2 evidence chain;
- one pair-level public receipt and offline verifier contract; and
- synthetic positive and mutation fixtures for a future implementation slice.

## Non-Goals

- No real Codex invocation, credential read, login or model call.
- No implementation or schema change in this slice.
- No counted Gate 3 execution, natural-bug task or scorer packet.
- No treatment-effect, quality, cost or Skill-effect conclusion.
- No replacement session, retry policy or third arm.
- No change to Gate 3 v1, its evidence or `_single_rollout()`.
- No weakening of single-arm route v2 privacy, cleanup or verification.
- No claim that a backend model-build identifier is available from the current
  supported process boundary.
- No selection of a final model literal in this candidate. The promoted A/B
  contract must contain one exact owner-approved model identifier before any
  session authorization; `default` or an omitted selector is forbidden.

## Affected Surfaces

Current design slice:

- this document only.

Potential future synthetic implementation, subject to separate approval:

- one isolated pair module under
  `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/`;
- one focused synthetic test module in the same namespace; and
- reviewed, minimal changes to `gate3_route_v2.py` and
  `gate3_route_v2_codex.py` that add per-arm model/treatment admission and
  prelaunch staged-input attestation;
- focused regression tests for those single-arm changes; and
- pair action, attempt-ledger and receipt schemas implemented as closed
  validation in the experiment namespace, not repository-wide schema changes.

The current single-session modules remain the starting authority for each arm.
The treatment and model-selection bindings below require reviewed schema bumps
to the single-arm action, runner and verifier; a pair module alone is
insufficient.

## Boundary and API Considerations

### Model and build identity

The promoted pair contract must define the shared identity tuple as:

```text
model_id
cli_version
executable_sha256
runner_sha256
command_contract_sha256
environment_policy_sha256
single_arm_verifier_sha256
pair_verifier_sha256
```

`model_id` must be an exact non-empty owner-approved literal passed explicitly
to both invocations through a pinned command argument. The command template,
required-flag preflight and command-contract digest must all include that
selector. An omitted selector, alias such as `default`, or arm-specific model
value is invalid.

In this design, “build equality” means exact equality of the pinned CLI
executable and route implementation identities above. It does not mean an
unobserved backend model deployment build. If a supported backend build
identity later becomes available, adopting it requires a new reviewed design;
it must not be inferred from private or undocumented rollout state.

### Fresh isolated contexts

Each arm must have independently created, current-user-only:

- `CODEX_HOME` containing only its own seeded `auth.json` before launch;
- synthetic workspace created from the same baseline bytes;
- output-schema and final-message paths;
- private raw-output root;
- public single-arm output root; and
- recovery locator namespace.

The two arms must have different run IDs and different resolved private roots.
No file, process, session/thread identifier, workspace mutation or public
single-arm output may be reused across arms. Freshness is established before
either arm runs by an immutable pair action, then verified after both arms by
distinct normalized context tokens and the absence of cross-root artifacts.

Absolute paths are private. Public evidence contains only `ARM_A_CONTEXT` and
`ARM_B_CONTEXT` tokens plus closed equality/distinctness results. A path token
proves only the pair validator's normalization result; it does not reveal a
path.

### Treatment boundary

The treatment definitions are:

| Arm | Common harness | Bug Fix Skill treatment |
| --- | --- | --- |
| A | exact shared bytes | absent |
| B | exact shared bytes | exact approved Skill packet bytes |

The future A/B single-arm action schema must add `pair_id`, `arm_id`,
`pair_action_sha256`, `model_id`, `treatment_projection` and
`staged_input_manifest_sha256`. The future runner must build its actual
invocation workspace only from that action-bound staged-input manifest. Before
launch, a pinned capability-bound validator reads the staged workspace and
produces the retained public `input-attestation.json` defined below. The public
action and attestation retain only artifact IDs, byte counts, approved content
SHA-256 values, closed validation results and implementation identities; they
contain no Skill text or private path.

Treatment is delivered through a caller-controlled, action-bound workspace
envelope rather than undocumented Skill discovery:

- both arms receive the same prompt and an exact canonical
  `treatment-manifest.json` artifact;
- A's manifest contains `state=absent`, and no Skill packet artifact may exist;
- B's manifest contains `state=present` plus the approved Skill packet artifact
  ID and SHA-256, and the exact Skill packet must exist in the staged workspace;
  and
- the common prompt instructs the producer to apply the treatment manifest,
  leaving the task prompt itself byte-identical across arms.

The pair action pins both treatment projections and staged-input manifest
identities before either arm runs. The B Skill packet digest must be exact and
non-empty. The A projection must use the closed value `absent`; an empty file is
not equivalent to absence. The baseline task workspace, expected workspace,
output schema, permission profile, timeout, environment policy and all
non-treatment instructions must be byte-identical after approved context-token
substitution.

The single-arm packet must pin the exact raw SHA-256 of the prelaunch input
attestation; the seal pins the packet and the final receipt pins the seal. The
final single-arm verifier must reject a missing/non-canonical attestation, a
digest mismatch, a staged-input mismatch, a treatment-state mismatch or a
model selector that differs from the action. This binds what the runner
actually staged and invoked, rather than letting the pair action attest to its
own treatment declaration. The action does not pin a future observation and
therefore avoids a circular digest dependency; the observation pins the prior
action, then packet -> seal -> final carries it forward.

This synthetic pair tests whether route v2 preserves the planned difference.
It does not test whether the Skill improves software engineering.

### Execution order and invocation budget

The pair action fixes arm order before launch. A future live canary requires a
separate exact-two/no-replacement authorization. The orchestrator may invoke
each arm at most once, for exactly two total invocations. It must not replace a
failed arm, reverse order after seeing an outcome or publish a pair success
from one completed arm.

Before any runner capability is made callable, the pair orchestrator must
create a protected, create-once attempt-ledger namespace outside both arm
cleanup roots. The ledger is an append-only digest chain with exactly these
events:

```text
0000 pair_action_pinned
0001 first_arm_started
0002 first_arm_terminal
0003 second_arm_started
0004 second_arm_terminal
0005 pair_closed
```

Every event pins the exact previous event bytes, pair ID, ordinal, arm ID,
run ID and closed terminal class where applicable. The trusted pair runner must
publish the corresponding `*_started` event before it can call an arm runner
and the terminal event immediately after the call returns or raises. It accepts
only ordinals 1 and 2 and cannot manufacture a third arm capability. The pair
verifier enumerates the fixed ledger namespace and rejects missing, extra,
duplicated, reordered or coherently relabelled events.

This ledger proves the invocation count of the reviewed pair orchestrator; it
does not claim to enumerate unrelated processes launched outside that
authority. The execution authorization is therefore bounded to that exact
orchestrator identity and fixed pair namespace.

The synthetic implementation must exercise both orders. Order is recorded but
is not a treatment and cannot alter the equality contract.

### Retained closed runtime attestations

Two privacy-safe runtime observations are retained as canonical create-once
public JSON. They are observations produced by manifest-pinned,
capability-bound validator implementations; they are not caller-supplied
booleans.

`pair-preflight-attestation.json` is published and externally pinned before
the pair action. Its exact closed schema is:

```text
schema
pair_id
contract_manifest_sha256
validator_sha256
credential_policy_sha256
credential_seed_equal
arm_a_only_auth_inventory
arm_b_only_auth_inventory
arm_a_acl
arm_b_acl
private_roots_distinct
normalization_policy_sha256
```

Every result field is the literal `PASS`; any failure prevents pair-action
publication. The trusted validator receives two private credential/root
capabilities from the canonical pair builder, reads both private trees, and has
no API for a caller to inject result values. The artifact contains no secret,
secret digest, account value or path. Its external pin is canonical
`sha256 + LF`; the pair action pins the attestation's raw-byte SHA-256 and the
first ledger event pins the pair action.

Each arm publishes `input-attestation.json` after staging and before calling
the runner. Its exact closed schema is:

```text
schema
pair_id
arm_id
run_id
pair_action_sha256
action_sha256
contract_manifest_sha256
validator_sha256
model_id
treatment_state
treatment_packet_sha256
staged_input_manifest_sha256
staged_inventory_match
staged_content_match
staged_acl
only_auth_inventory
credential_acl
model_selector_match
```

For A, `treatment_packet_sha256` is the literal `absent`; for B it is the
approved 64-character digest. All six closed result fields are literal `PASS`.
The trusted validator receives the private staged-root capability directly
from the canonical arm runner and has no API for injected booleans or an
alternate path. The artifact is canonical, privacy-validated and create-once.
The arm packet pins its exact raw-byte SHA-256, so packet -> seal -> final binds
the observation. Offline verification revalidates schema, canonical bytes,
identity linkage and the complete digest chain. It does not claim to re-read
deleted staged bytes or credentials.

These artifacts extend the future A/B arm public set from six to seven files
per arm and add one pair-level preflight artifact. Existing single-session
evidence remains governed by its original six-file schema and is not silently
reinterpreted.

## Pair Action Contract

Before either synthetic runner is called, the future pair builder must load an
owner-signed, canonical `gate3-route-v2-ab-contract-manifest.v1`. That manifest
pins the exact bytes of:

- the promoted treatment definition and exact A/B treatment packets;
- the selected model ID;
- the pair contract and path-normalization policy;
- the single-arm route, Codex runner and single-arm verifier;
- the pair builder, trusted orchestrator and pair verifier;
- the pair-action, attempt-ledger and pair-receipt schemas; and
- permissions, timeout, environment and credential-equality policies.

The builder must deterministically rebuild the pair action from that manifest,
the pair ID, two preallocated run IDs, frozen execution order, baseline/task
artifacts and two private context-root tokens. It then create-once publishes the
immutable pair action and a separate external `pair-action.sha256` pin before
creating either `*_started` ledger event or exposing either arm capability.
The first ledger event pins both the manifest and pair-action digests. A
monotonic create-once ledger order, not a mutable timestamp, proves that the
pair action preceded both starts.

The immutable pair action pins:

- pair ID and ordered arm IDs;
- non-counted synthetic authorization;
- exact single-arm authorization expected for each arm;
- pair-preflight attestation and external-pin identities;
- exact model/build identity tuple;
- prompt, output-schema, baseline-workspace and expected-workspace digests;
- common-harness and treatment projections for both arms;
- permission, timeout and environment-policy identities;
- single-arm route/verifier and pair-verifier identities;
- each arm's complete action-input projection; and
- the approved path-token normalization policy digest.

The pair action is invalid if it is written after an arm action, if either arm
action cannot be deterministically rebuilt from it, or if its two arm entries
do not contain exactly A and B. Passing only a pair-action file path is never
an external identity: verification requires the signed contract manifest, the
external action pin and the initial ledger event.

## Per-Arm Action -> Observation -> Verification -> Claim

Each arm must independently use the existing route v2 chain:

| Stage | Required arm artifact | Pair-level use |
| --- | --- | --- |
| Action | `preflight.json` + extended `action.json` + action-bound staged-input manifest | Rebuild exact requested model/build, frozen inputs and arm treatment |
| Observation | prelaunch staged-input attestation + `attestation.json` + `packet.json` + `seal.json` | Establish what was actually staged/invoked plus closed process, structured-output and workspace observations before cleanup |
| Verification | Existing offline `verify()` from the pinned implementation | Reject missing, altered, mismatched or residue-bearing arm evidence |
| Claim | `final.json` + external final pin | Admit only that arm's non-scoring Layer 0 result |

“Existing offline `verify()`” means its Layer 0 logic is reused after a reviewed
schema bump; the current unmodified function cannot verify model/treatment
admission and is not sufficient for the pair.

An arm with a negative final receipt, external no-admissible terminal, missing
final pin or failed offline verification remains part of the attempted pair but
makes the pair non-success. Its failure must not suppress verification of the
other arm's already published evidence.

## Cross-Arm Identity and Mismatch-Fail Rules

After independently verifying both arm chains, the pair verifier must apply the
following schema-driven classifications. For every schema below, the
implementation defines a frozen `CLASSIFIED_KEYS` set and requires
`schema.keys == CLASSIFIED_KEYS`. Nested objects have their own exact key sets.
Adding an unclassified field is a contract error and fails review and runtime
admission.

### Current preflight schema — complete key set

| Field | Classification | Required comparison |
| --- | --- | --- |
| `schema` | equal | exact value |
| `authorization` | equal | exact value |
| `run_id` | distinct | A and B preallocated IDs |
| `checks` | equal | exact closed object |
| `compatibility` | equal | exact closed object |
| `required_flags` | equal | exact ordered values |
| `probe_outputs` | equal | exact closed lengths/digests/results |
| `environment_policy_sha256` | equal | exact digest |
| `environment_projection_sha256` | equal | exact normalized digest |
| `execution_identity` | equal | exact nested object |

The exact nested `execution_identity` key set is `cli_version`,
`command_contract_sha256`, `executable_sha256`, `kind` and `runner_sha256`;
every value must be equal.

### Proposed A/B arm action schema — complete key set

The current action keys remain and the proposed A/B keys are added in one
reviewed schema version.

| Field | Classification | Required comparison |
| --- | --- | --- |
| `schema` | equal | exact A/B action schema |
| `authorization` | equal | exact single-arm class |
| `execution_identity` | equal | exact nested object/key set above |
| `expected_workspace` common entries | equal | artifact IDs/bytes/digests |
| `expected_workspace` treatment entries | treatment | A absent; B exact approved entries |
| `output_schema` | equal | canonical object bytes |
| `preflight_sha256` | derived outcome | pins that arm's validated preflight |
| `prompt_sha256` | equal | common prompt digest |
| `run_id` | distinct | matches allocated arm entry |
| `pair_id` | equal | exact pair identity |
| `arm_id` | distinct | exactly A and B |
| `pair_action_sha256` | equal | exact externally pinned pair action |
| `model_id` | equal | exact owner-selected literal |
| `treatment_projection` | treatment | closed A/B projection |
| `staged_input_manifest_sha256` | treatment-derived | common bytes plus exact arm treatment |

The exact nested `treatment_projection` key set is `state`,
`treatment_manifest_sha256` and `treatment_packet_sha256`. A uses
`state=absent` and literal `absent` for the packet; B uses `state=present` and
the promoted packet digest. No prelaunch-attestation digest is placed in the
action; `input-attestation.json` pins the already-published action, and the arm
packet later pins the attestation.

### Pair-preflight attestation schema — complete key set

| Field | Classification | Required comparison |
| --- | --- | --- |
| `schema` | equal control | exact value |
| `pair_id` | equal control | exact pair identity |
| `contract_manifest_sha256` | equal control | signed manifest identity |
| `validator_sha256` | equal control | manifest-pinned validator |
| `credential_policy_sha256` | equal control | manifest-pinned policy |
| `normalization_policy_sha256` | equal control | manifest-pinned policy |
| `credential_seed_equal` | private-attested | `PASS` |
| `arm_a_only_auth_inventory` | private-attested | `PASS` |
| `arm_b_only_auth_inventory` | private-attested | `PASS` |
| `arm_a_acl` | private-attested | `PASS` |
| `arm_b_acl` | private-attested | `PASS` |
| `private_roots_distinct` | private-attested | `PASS` |

Identity/policy fields must match the signed manifest; closed results must be
`PASS`. The raw artifact is independently pinned and then pinned by the pair
action.

### Per-arm input-attestation schema — complete key set

| Field | Classification | Required comparison |
| --- | --- | --- |
| `schema` | equal | exact value |
| `pair_id` | equal | exact pair identity |
| `arm_id` | distinct | exactly A and B |
| `run_id` | distinct | allocated run ID |
| `pair_action_sha256` | equal | external pair-action identity |
| `action_sha256` | derived control | exact prior arm action bytes |
| `contract_manifest_sha256` | equal | signed manifest identity |
| `validator_sha256` | equal | manifest-pinned validator |
| `model_id` | equal | exact selected model |
| `treatment_state` | treatment | A absent; B present |
| `treatment_packet_sha256` | treatment | A literal absent; B promoted digest |
| `staged_input_manifest_sha256` | treatment-derived | equals arm action value |
| `staged_inventory_match` | private-attested | `PASS` |
| `staged_content_match` | private-attested | `PASS` |
| `staged_acl` | private-attested | `PASS` |
| `only_auth_inventory` | private-attested | `PASS` |
| `credential_acl` | private-attested | `PASS` |
| `model_selector_match` | private-attested | `PASS` |

### Pair action schema — complete key set

| Field | Classification | Required comparison |
| --- | --- | --- |
| `schema` | equal control | manifest-pinned value |
| `pair_id` | equal control | exact pair identity |
| `authorization` | equal control | synthetic non-counted pair class |
| `contract_manifest_sha256` | equal control | owner-signed canonical manifest |
| `pair_preflight_attestation_sha256` | private-attested | exact retained artifact digest |
| `pair_preflight_pin_sha256` | derived control | exact external pin bytes digest |
| `model_build_identity` | equal | exact closed model/CLI tuple |
| `ordered_arms` | derived control | exactly two frozen arm entries |
| `prompt_sha256` | equal | common prompt digest |
| `output_schema_sha256` | equal | common schema digest |
| `baseline_workspace_sha256` | equal | common baseline manifest digest |
| `expected_workspace_sha256` | equal | common expected-outcome manifest digest |
| `permissions_sha256` | equal | exact policy digest |
| `timeout_policy_sha256` | equal | exact policy digest |
| `environment_policy_sha256` | equal | exact policy digest |
| `common_harness_sha256` | equal | exact harness digest |
| `single_arm_route_sha256` | equal control | exact implementation digest |
| `single_arm_runner_sha256` | equal control | exact implementation digest |
| `single_arm_verifier_sha256` | equal control | exact implementation digest |
| `pair_builder_sha256` | equal control | exact implementation digest |
| `pair_orchestrator_sha256` | equal control | exact implementation digest |
| `pair_verifier_sha256` | equal control | exact implementation digest |
| `schema_set_sha256` | equal control | all exact schema bytes |
| `path_normalization_policy_sha256` | equal control | exact policy digest |
| `credential_policy_sha256` | equal control | exact policy digest |

Each item of `ordered_arms` has the exact key set `arm_id`, `run_id`,
`single_arm_authorization`, `context_token`, `treatment_projection` and
`staged_input_manifest_sha256`. `arm_id`, `run_id` and `context_token` are
distinct; authorization is equal; treatment fields are the only planned
difference. The pair action contains complete arm-action inputs, not expected
arm-action digests, avoiding a circular dependency with
`arm_action.pair_action_sha256`.

### Attempt-ledger schema — complete key set

Each event has exactly `schema`, `pair_id`, `pair_action_sha256`, `ordinal`,
`event_type`, `arm_id`, `run_id`, `terminal_class` and
`previous_event_sha256`. `schema`, `pair_id` and `pair_action_sha256` are equal
controls; `ordinal`, `event_type`, `arm_id`, `run_id` and the previous digest
are derived controls fixed by the six-event state machine; `terminal_class` is
a derived outcome and is literal `not_applicable` for non-terminal events.
`arm_id` and `run_id` are also literal `not_applicable` for the pair-level
`pair_action_pinned` and `pair_closed` events.

The credential-equality validator runs before pair-action publication inside a
current-user-only private root. It compares the two seeded auth payloads byte
for byte and verifies each arm's only-auth inventory and ACL. The retained
pair-preflight attestation records only closed PASS values and validator/policy
identities; it never publishes credential bytes, paths or a credential digest.
After cleanup, the offline verifier proves the exact retained attestation and
digest chain. It does not claim to re-read deleted secrets.

### Must be equal

- exact `model_id`;
- CLI version and executable SHA-256;
- runner, command-contract, environment-policy and verifier identities;
- prompt and output-schema digests;
- baseline and expected workspace projections;
- permission and timeout identities;
- common-harness identity;
- authorization class;
- preflight required-flag set, compatibility results,
  `environment_projection_sha256` and closed probe outputs;
- the closed credential-equality attestation identity and `PASS` result; and
- path-token normalization policy identity.

### Must be distinct

- run IDs;
- arm IDs;
- normalized context tokens;
- private context roots, checked privately before deletion;
- public single-arm output roots;
- recovery locator identities; and
- any supported session/thread identifier if one is observed. Absence of a
  supported identifier is allowed and must not be replaced with undocumented
  session-store discovery.

### Only approved difference

- treatment projection: A=`absent`; B=`present` with the exact approved Bug Fix
  Skill packet SHA-256.

Any additional difference is `cross_arm_identity_mismatch`. The verifier must
not classify a pair as success, select the better-looking arm, normalize an
unknown field away or infer that a mismatch is harmless. Unknown comparison
fields are `unattributable` and fail the candidate pair.

## Pair Verification and Public Receipt

The future offline pair verifier must accept only pinned paths to:

- the owner-signed canonical pair contract manifest;
- the pair-preflight attestation and its external pin;
- the pair action;
- the external pair-action pin;
- the complete fixed-namespace attempt ledger and its external final pin;
- both complete public single-arm evidence directories;
- both external final pins; and
- the proposed pair final receipt.

It must independently:

1. verify the manifest signature/identity and rebuild the pair action from the
   complete manifest-pinned contract inputs;
2. verify the external pair-action pin and prove through ledger ordering that
   it predates both starts;
3. validate the canonical pair-preflight attestation, its external pin and its
   identity linkage into the pair action;
4. invoke the manifest-pinned single-arm verifier separately for A and B,
   including each retained `input-attestation.json`;
5. reconstruct each arm action, staged-input attestation and treatment
   projection;
6. enforce the closed field-classification table, equal, distinct and
   only-approved-difference rules;
7. enumerate and verify the complete six-event ledger, proving exactly two
   orchestrator invocations and no replacement;
8. compute a pair decision without trusting caller-supplied arm summaries;
9. verify zero private and locator residue for both arms; and
10. compare the proposed pair receipt byte-for-byte with its deterministic
   reconstruction.

The pair final receipt is create-once, privacy-safe and closed. It may contain
only:

- schema and pair ID;
- contract-manifest, pair-preflight-attestation/pin, pair-action,
  pair-action-pin and attempt-ledger digests;
- ordered arm IDs and run IDs;
- each arm final-receipt and final-pin SHA-256;
- shared model/build identity tuple;
- A/B treatment projection identities;
- closed checks for arm verification, equality, distinctness, treatment-only
  difference, private credential equality attestation, invocation count and
  cleanup;
- pair decision: `SUCCESS` or `NON_SUCCESS`; and
- claim ceiling: `synthetic_non_counted_route_qualification_only`.

It must not contain raw prompts, model output, stdout/stderr, credentials,
paths, Skill text, workspace bytes or unsupported backend/session metadata.

## Decision Rule

Pair `SUCCESS` requires all of the following:

1. the owner-signed contract manifest is canonical and every implementation,
   policy, schema, model and treatment identity matches it;
2. the retained pair-preflight attestation matches its external pin, all
   closed private results are `PASS`, and the pair action pins it;
3. the pair action matches its external pin and the first ledger event proves
   it predates both arm starts;
4. the complete ledger contains exactly the six expected events and therefore
   exactly two reviewed-orchestrator invocations, one A and one B, with no
   replacement;
5. both single-arm offline verifications return `SUCCESS`, including the new
   model/treatment staged-input binding;
6. every field in the closed classification table validates, including the
   private credential equality attestation;
7. all must-equal fields are equal;
8. all must-be-distinct fields are distinct;
9. the only remaining planned input difference is the candidate treatment
   projection promoted before execution;
10. both cleanup results pass and both locator/private roots are absent;
11. the deterministic pair receipt is published create-once; and
12. a fresh offline verification reproduces the pair decision and exact bytes.

Otherwise the pair decision is `NON_SUCCESS`. A `NON_SUCCESS` pair is retained
as diagnostic evidence but cannot authorize replacement, count toward Gate 3
or be selectively excluded from a later claim.

## Failure Paths and Risk Points

- Pair action missing or published after an arm starts: do not invoke the
  remaining arm; pair is non-admissible.
- Contract manifest missing, unsigned, non-canonical or inconsistent with the
  pair builder/verifier: do not expose either arm capability.
- Pair-action external pin missing or different: do not expose either arm
  capability.
- Attempt ledger missing, extra, reordered, duplicated, relabelled or not
  externally pinned: pair non-success; never infer exactly-two from two chosen
  arm directories.
- Model selector omitted, aliased or different: fail before invocation when
  detectable, otherwise `cross_arm_identity_mismatch`.
- Executable, CLI, runner, verifier or command-contract mismatch: fail closed.
- Shared input or harness mismatch: fail closed; do not call it treatment.
- Treatment absent from B, present in A or wrong digest: fail closed.
- Staged workspace differs from the action-bound input manifest, or the
  prelaunch validator attestation is missing: fail before that arm invocation.
- Credential seeds differ, only-auth inventory/ACL fails or the closed private
  equality attestation is missing: fail before pair-action publication.
- Context root reused or context token duplicated: fail before the second
  invocation when detectable; otherwise pair non-success.
- One arm fails: verify and retain both available evidence sets, but pair
  remains non-success and no replacement is allowed.
- One arm produces no admissible final receipt: retain its external terminal
  if available; never fabricate an arm or pair success receipt.
- Pair receipt publication fails: no admissible pair result exists; single-arm
  evidence remains bounded to single-arm claims.
- Unknown comparison field: `unattributable`, not silently ignored.
- Public projection exposes a path, prompt, Skill content or model output:
  privacy failure; do not publish the pair receipt.

## Evidence Plan

The future synthetic implementation must provide:

1. a positive fixture for A-then-B and B-then-A;
2. deterministic contract-manifest and pair-action reconstruction plus external
   pin verification;
3. proof that the six-event attempt ledger records exactly two runner calls,
   one per arm, with distinct roots;
4. ledger mutations for missing/extra/reordered events, a third call,
   replacement, duplicate arm and coherent run-ID relabelling;
5. independent single-arm verification for both complete chains, including
   actual staged model/treatment admission;
6. deterministic pair receipt reconstruction from pinned artifacts;
7. mutations for every must-equal identity and every current
   preflight/action field classification;
8. mutations for reused run ID, arm ID, context root, output root and locator;
9. treatment mutations: A present, B absent, wrong B digest, empty-file-as-
   absent and an extra non-treatment difference;
10. staged-input mutations before invocation and attestation substitution;
11. credential mutations proving private byte mismatch, inventory/ACL failure
    and digest/value publication all fail;
12. one-arm failure, missing final receipt, failed final pin and failed cleanup;
13. reordered, omitted, duplicated and coherently rewritten pair evidence;
14. unknown comparison-field rejection;
15. public privacy mutations containing path, credential, prompt, Skill or raw
    model content; and
16. fresh-root offline verification plus byte-for-byte pair receipt comparison.

No real CLI, credential or session is used by these fixtures.

## Claim Ceiling

This design may claim only:

- the proposed non-counted A/B boundary;
- fields intended to be equal, distinct or treatment-specific;
- the proposed pair evidence and decision chain;
- synthetic evidence required before any live pair request; and
- the smallest recommended implementation tranche.

It does not claim:

- the pair orchestrator or verifier exists;
- an exact model literal has been owner-selected;
- backend model-build identity is observable;
- two live contexts have been compared;
- the Skill changes behavior or quality;
- a scorer packet exists;
- Gate 3 counted execution has started; or
- any session authority exists.

The proposed A/B treatment remains a candidate definition. No live pair may be
requested until the treatment contract, exact pair manifest and exact model ID
receive independent review, owner signature and canonical promotion.

## Implementation Tranche Recommendation

Recommend one future tranche only:

> Implement a synthetic pair orchestrator and offline verifier that compose
> two injected single-arm route runners; extend the arm action/runner/verifier
> with manifest-bound model and staged treatment admission; publish a
> manifest-pinned pair action and external pin before either call; record every
> start/terminal transition in a fixed create-once six-event ledger; enforce
> exactly two calls/no replacement; independently verify both complete arm
> chains; fail on every non-treatment mismatch; and deterministically publish
> one privacy-safe non-counted pair receipt.

That tranche should touch one new pair module, its focused test module, and the
smallest reviewed model/treatment-binding changes to the existing single-arm
route, Codex runner and their tests. It must not add live credential handling
or invoke Codex.

Passing that tranche authorizes nothing further. A later live non-counted pair
would require an owner-selected exact model ID, reviewed bytes, clean detached
execution boundary and a separate exact-two/no-replacement authorization.
