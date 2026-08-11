# Gate 3 Final-Message Diagnostic Design Candidate

Status: `CANDIDATE — REVISED; PENDING INDEPENDENT SEMANTIC REVIEW`

Date: 2026-08-11

## Problem

The one authorized Gate 3 non-counted live A/B pair terminated `NON_SUCCESS`.
Both arms exited zero, emitted structurally valid NDJSON and retained the
baseline workspace. At the runner's single post-process observation point,
neither arm had a regular file at the path supplied through
`--output-last-message`.

The committed evidence proves task-execution failure in both arms. It does not
prove that the final-output file was never created, because the runner checked
the path only after process return. It also does not preserve a versioned event
semantic contract or a content-free ordered event projection. The nearer cause
therefore remains unresolved among process execution, turn/completion,
final-output materialization, adapter capture and task execution.

The consumed pair cannot be retried, replaced or retrospectively enriched. The
next problem is narrower:

> Define a reviewable, privacy-safe diagnostic evidence design that separates
> those observation axes, fails closed when semantic authority or lifecycle
> evidence is missing, and can first be exercised entirely with synthetic
> in-memory fixtures.

This document is a design only. It does not implement the diagnostic, authorize
credentials, preflight or live execution, or change the consumed pair result.

## Current Repository Truth

1. `PLAN.md:1577-1607` records the promoted Gate 3 contract, one consumed live
   pair and its `NON_SUCCESS` result. Retry, replacement, counted execution and
   treatment-effect conclusions remain unauthorized.
2. In each committed arm, `attestation.json:2-17` records exit class `zero`,
   five valid NDJSON values, 725 stdout bytes, final-message status `absent`,
   final-schema validation `not_attempted` and successful workspace capture.
   Event types and payloads were not published.
3. In each committed arm, `packet.json:4-22` records `exit_zero=true`,
   `stdout_ndjson=true`, `final_schema=false`,
   `workspace_matches_expected=false` and `eligible_success=false`.
4. `gate3_route_v2_codex.py:783-792` supplies a private path through
   `--output-last-message`. Only after the process returns,
   `gate3_route_v2_codex.py:843-847` calls `is_file()` and conditionally reads
   the path. This establishes `absent at post-termination observation`; it does
   not establish `never produced` or exclude create-then-delete behavior.
5. `gate3_route_v2.py:1255-1335` validates NDJSON transport structure and final
   schema conformance without publishing raw content.
   `gate3_route_v2.py:406-433` rejects non-canonical public JSON and obvious
   private paths or bearer-token surfaces.
6. `docs/governance/gate3-route-v2-charter-20260805.md:318-324` states that
   NDJSON is transport, not a stable semantic schema, and forbids task-semantic
   inference from undocumented event fields.
7. `docs/governance/gate3-route-v2-charter-20260805.md:115-139` requires an
   ordered chain of pre-cleanup observation seal, cleanup and separate final
   receipt. `memory/03_knowledge_base.md:151-164` rejects summary-only
   cross-boundary evidence that does not bind each hop.
8. Both arms retained the eight-byte `PENDING\n` baseline rather than the
   fifteen-byte `CALIBRATION_OK\n` expected result. Repair commit `230679cf`
   makes the exact Git evidence tree independently reconstructable; it does not
   add event semantics or final-path lifecycle evidence.

The current truth supports `task execution failed`, `final output was absent at
the post-termination observation` and `near cause unresolved`. It does not
support `NOT_PRODUCED`, CLI fault, model fault or turn-completion fault.

## Target Outcome

Produce a reviewable candidate contract for a future, distinct, non-counted
diagnostic session that would:

- preserve process, turn/event, final-output and task-execution observations as
  independent axes;
- bind any event-derived semantics to a versioned, preserved and reconstructable
  event contract;
- publish only an ordered, closed, content-free event-marker projection;
- distinguish observation classes only when the necessary semantic and
  lifecycle evidence exists;
- apply explicit contradiction and fail-closed precedence rules;
- preserve the action -> pre-cleanup observation seal -> cleanup -> final
  receipt chain; and
- permit offline reconstruction of the classification from public closed
  observations without claiming that deleted private bytes can be recovered.

The first recommended implementation tranche remains smaller: an offline
in-memory classifier and synthetic fixtures only.

## Scope

This candidate covers only:

- a proposed new diagnostic identity, action identity and run identity;
- four separate observation axes;
- a proposed versioned event semantic contract and closed ordered projection;
- final-output lifecycle and path-identity observations;
- deterministic precedence and classification rules;
- the eventual two-stage public evidence chain; and
- an offline synthetic evidence plan, including TOCTOU mutations.

The diagnostic is single-session and common-harness. It has no treatment arm,
comparison arm or effect estimator.

## Non-Goals

- No credentials, login, auth-file read, model call or live CLI invocation.
- No preflight, owner signature, promotion or live authorization in this slice.
- No reuse of either consumed run ID or the consumed pair ID.
- No retry, replacement, counted Gate 3 execution or additional A/B sample.
- No raw prompt, final message, task text, Skill text, credential value, model
  output, filesystem path or arbitrary event value in public evidence.
- No retrospective causal reclassification of the consumed pair.
- No treatment, Skill, quality, productivity or framework-effect conclusion.
- No runtime, verifier, schema, owner-pin, contract, receipt or evidence-file
  implementation in this design slice.

## Proposed Diagnostic Contract

Exact field names remain candidate API until a later implementation review.
The eventual public evidence would use canonical JSON and a new schema identity,
for example `gate3-route-v2.final-message-diagnostic.v1`.

### Identity and authority

The evidence chain must bind:

- `diagnostic_id`: new create-once identifier;
- `run_id`: new single-session identifier;
- `authorization`: fixed synthetic, diagnostic-only and non-counted token;
- `action_sha256`: digest of a durable public, privacy-safe action descriptor;
- `execution_identity_sha256`: executable, runner and command-contract identity;
- `event_contract_sha256`: exact versioned event semantic contract bytes;
- `event_schema_sha256`: exact closed event-schema bytes;
- `event_parser_validator_sha256`: exact pre-cleanup raw parser and semantic
  validator implementation identity;
- `event_projector_sha256`: validated-event-to-projection implementation
  identity;
- `diagnostic_classifier_sha256` and `diagnostic_verifier_sha256`; and
- `claim_ceiling`:
  `synthetic_non_counted_final_message_diagnostic_only`.

The public action descriptor must contain all closed inputs needed to identify
the diagnostic shape, including the schema and implementation digests. A digest
without retained descriptor bytes is not an independently reviewable action.
No identity may derive from or describe the consumed pair as a parent, retry or
replacement.

### Event semantic authority and projection

Event-derived causal classification is admissible only if official
documentation or pinned source establishes the exact event contract. That
contract and its closed schema must be preserved as public bytes and bound by
`event_contract_sha256` and `event_schema_sha256`.

For a synthetic fixture, the fixture's versioned event contract is authoritative
only for that synthetic fixture. Passing synthetic rules does not establish the
semantics of a real CLI version. If no authoritative contract exists for a
future real executable, the turn/event axis is `INDETERMINATE` and no event-
derived near-cause class is allowed.

The public projection is an ordered array. Each entry contains only:

- zero-based `ordinal`;
- one closed top-level marker such as `turn_started`, `turn_completed`,
  `turn_failed`, `item_started` or `item_completed`; and
- for an item entry, an optional closed item marker such as `agent_message`.

No IDs, text, content, arguments, usage values, timestamps, unknown names or
arbitrary nested values are allowed. Unknown markers, malformed input,
duplicate terminal markers, non-contiguous ordinals or invalid ordering make
the event axis `INDETERMINATE`; an unknown string is never copied into public
evidence.

The pre-cleanup observation seal binds the exact private raw-stream digest, the
canonical projection digest, the event contract, schema, parser/validator and
projector identities, and the documented raw-to-validated-event-to-projection
transformation. `event_parser_validator_sha256` must identify the exact bytes
that parse the private raw stream and validate it against the bound event
contract before projection; no additional unbound parser or validator may
supply the attestation. The offline verifier can reconstruct classification
from the retained projection and verify this digest chain. It cannot
independently recover deleted raw content or prove semantic correspondence
beyond that bound pre-cleanup parser/validator's attestation. The safe claim is
therefore `closed projection and attestation chain reconstructed`, not `private
raw stream independently replayed`.

### Process axis

Publish only closed observations:

- `launch_status`: `not_attempted`, `started` or `failed`;
- `exit_classification`: `zero`, `nonzero`, `signal_or_termination` or
  `unavailable`;
- `timed_out`: boolean;
- `stdout_capture`: `absent`, `empty`, `nonempty` or `capture_failed`;
- `stderr_capture`: `absent`, `empty`, `nonempty` or `capture_failed`; and
- `tree_cleanup`: `PASS`, `FAIL` or `NOT_ATTEMPTED`.

Process termination is not a turn or model conclusion. Nonzero, timeout or
signal evidence may establish a process-axis failure, but cannot alone establish
that a turn failed or that a model did not complete.

### Turn/event axis

After event-contract, projection and ordering validation, publish one of:

- `TURN_COMPLETED_WITH_AGENT_MESSAGE`;
- `TURN_COMPLETED_WITHOUT_AGENT_MESSAGE`;
- `TURN_FAILED`;
- `NO_ADMISSIBLE_TERMINAL`; or
- `INDETERMINATE`.

These names describe observations under the bound event contract. They do not
assign fault to model internals. Without authoritative event semantics, the only
allowed value is `INDETERMINATE`.

### Final-output axis

The path is represented publicly only by logical identifier `final_message`.
An eventual integration must observe the parent and target boundary from before
launch through process-tree termination and capture:

1. pre-launch parent identity and target state;
2. content-free lifecycle markers for target create, replace, remove and
   reparse/identity change;
3. post-termination parent and target identity; and
4. when a stable regular file can be opened without link traversal, handle-
   bound read and schema-validation status.

The closed final-output classes are:

- `ABSENT_AT_POST_TERMINATION_OBSERVATION`;
- `NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE`;
- `CREATED_THEN_REMOVED`;
- `CAPTURED_VALID`;
- `CAPTURED_INVALID`;
- `READ_FAILED`;
- `PATH_INVALID`; and
- `INDETERMINATE`.

`NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE` is permitted only when the
bound lifecycle observer proves uninterrupted coverage. A single post-process
`is_file()` check maps only to
`ABSENT_AT_POST_TERMINATION_OBSERVATION`. Parent switch, target replacement,
symlink, junction, reparse point, directory, pre-existing target or an
unresolved stat/read race maps to `PATH_INVALID` or `INDETERMINATE`, never to
adapter failure or non-production.

### Task-execution axis

Publish only closed artifact identifiers plus manifest-relative byte counts and
digests already permitted by the diagnostic's synthetic privacy contract.
Compare observed artifacts against baseline and expected manifests. Classes:

- `MATCHED_EXPECTED`;
- `UNCHANGED_BASELINE`;
- `OTHER_MISMATCH`;
- `CAPTURE_FAILED`; and
- `INDETERMINATE`.

This axis is independent. A final message does not repair a workspace mismatch,
and a correct workspace does not prove a final-message route.

### Synthetic digest boundary

In the first implementation tranche, stdout, stderr and final-message byte
counts or SHA-256 values are permitted only for fixed synthetic fixture bytes.
They do not authorize publication of live model-content digests. Content hashes
can disclose low-entropy or guessable content and are not automatically privacy
safe. Any future live integration must obtain a new privacy decision defining
whether such fields are omitted, transformed or retained privately; this design
carries no live-content digest authority forward.

## Classification and Precedence

The classifier preserves all four axes. It does not collapse them into a causal
label unless every prerequisite is independently admissible.

Precedence is:

1. identity, privacy, integrity, event-contract or terminal contradiction
   failure => overall `INDETERMINATE`;
2. incomplete process-tree termination, incomplete lifecycle coverage, path
   identity contradiction, task `CAPTURE_FAILED` or task `INDETERMINATE` =>
   affected axes and overall result `INDETERMINATE`;
3. otherwise record each evidenced axis class independently;
4. `MULTIPLE_FAILURES` may combine only individually evidenced,
   non-contradictory failures on orthogonal axes; and
5. success-like route language is allowed only when every required axis is
   complete and non-failing.

| Required admissible observations | Diagnostic class | Claim boundary |
|---|---|---|
| nonzero, timeout or signal, with no contradictory terminal evidence | `PROCESS_EXECUTION_FAILURE` | Process axis only; no model/turn inference. |
| bound event contract + completed turn + completed agent-message marker + complete lifecycle with no creation | `CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED` | The command-bound output was not observed to materialize; no internal CLI fault assignment. |
| bound event contract + completed turn without agent-message marker + complete final lifecycle | `TURN_COMPLETED_WITHOUT_AGENT_MESSAGE` | Turn/event observation only; no model fault assignment. |
| stable regular file + handle-bound read failure | `ADAPTER_CAPTURE_FAILURE` | File existence/identity is established; content is not. |
| stable captured final + bound schema failure | `FINAL_SCHEMA_FAILURE` | Production and capture occurred; schema failed. |
| task class `UNCHANGED_BASELINE` or `OTHER_MISMATCH` | `TASK_EXECUTION_FAILURE` | An admissibly captured workspace result failed independently of final-output state. |
| task class `CAPTURE_FAILED` or `INDETERMINATE` | `INDETERMINATE` | Observation failure does not prove task execution failure. |
| two or more compatible orthogonal failures | `MULTIPLE_FAILURES` | Preserve every axis; do not claim one root cause. |
| missing authority, incomplete observation or contradiction | `INDETERMINATE` | Fail closed; no near-cause inference. |
| all required axes complete; final valid; task matched expected | `DIAGNOSTIC_PATH_COMPLETE` | Diagnostic path only; not Gate 3 success or effect evidence. |

A nonzero process plus a valid `turn_completed` marker is not normalized into a
turn failure. It is either an evidenced process failure alongside an
independently evidenced turn observation, or `INDETERMINATE` if the contract
defines the combination as contradictory.

## Retrospective Boundary for the Consumed Pair

The old pair maps only to:

- process: exit zero in both arms;
- event stream: valid NDJSON transport, five values and 725 bytes per arm, with
  no public ordered semantic projection or event contract;
- final output: `ABSENT_AT_POST_TERMINATION_OBSERVATION`;
- task execution: `UNCHANGED_BASELINE`; and
- pair decision: `NON_SUCCESS`.

The old pair cannot be assigned `NOT_PRODUCED`,
`CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED`, turn-completion failure,
adapter failure or model fault. Its nearer final-message cause remains
unresolved.

## Eventual Public Evidence Chain

A future integration, if separately designed and authorized, must preserve the
existing three ordered phases:

1. **Pre-cleanup observation seal.** Atomically publish a create-once,
   privacy-validated seal outside the cleanup target. It pins the durable action
   descriptor, closed ordered event projection, exact private-artifact digests,
   all schema/contract/projector/classifier identities and closed axis
   observations. It records `cleanup=PENDING` and `decision=PENDING`.
2. **Cleanup attempt.** Attempt private cleanup and record the actual result
   without rewriting the seal.
3. **Final receipt.** Atomically publish a separate create-once receipt that
   pins the seal digest and cleanup result. The recovery locator remains until
   final publication and zero-residue checks succeed.

If seal creation fails, no route receipt is fabricated. If cleanup, final
publication or locator removal fails, an external terminal and recovery path
must preserve that failure. Offline reconstruction proves the public action,
seal, cleanup and receipt chain; it does not replay deleted private content.

## Affected Surfaces

This design slice changes only this document. A later, separately authorized
implementation might require:

- an isolated in-memory classifier library;
- a versioned synthetic event contract and closed fixtures;
- later, separately reviewed lifecycle observer and evidence-chain integration;
- a new public diagnostic schema and verifier; and
- an independently reviewed candidate manifest before any integration proposal.

These are expected surfaces, not authorized changes.

## Boundary and API Considerations

- The promoted Gate 3 contract, evidence, owner pin and consumed pair remain
  immutable.
- Producer, projector, classifier and offline verifier identities are separate
  and bound.
- The event contract is public and byte-preserved; undocumented CLI event names
  cannot supply semantic authority.
- Public projection fields use only fixed enums, ordinals, integers, booleans
  and explicitly approved digests.
- Raw streams and final content remain private; deletion occurs only after a
  durable admissible observation seal exists.
- A receipt is route/capture evidence, not treatment, model-quality or framework-
  effectiveness evidence.

## Failure Paths and Risk Points

- Missing or drifting event contract: event-derived class is `INDETERMINATE`.
- Projection order gap, unknown marker or terminal contradiction:
  `INDETERMINATE`.
- Nonzero/timeout/signal without event evidence: process failure only.
- Exit zero without an admissible terminal: `INDETERMINATE`, not completion.
- Single post-termination path absence: preserve
  `ABSENT_AT_POST_TERMINATION_OBSERVATION`.
- Create then delete: preserve `CREATED_THEN_REMOVED`; do not relabel as never
  produced.
- Parent/target identity switch or stat/read replacement: `PATH_INVALID` or
  `INDETERMINATE`.
- Stable regular file with handle-bound read failure: `READ_FAILED` and, when
  all prerequisites hold, `ADAPTER_CAPTURE_FAILURE`.
- Valid final with baseline workspace: preserve final success and
  `TASK_EXECUTION_FAILURE` together.
- Seal/publication/cleanup crash: retain the last durable stage and fail closed.
- Synthetic digest publication: limited to fixed fixtures; no live authority.
- Digest chain: establishes byte identities and transformations, not the
  semantic truth of deleted private content.

## Evidence Plan

### First implementation tranche: offline in-memory only

If separately authorized, test a pure classifier with no filesystem watcher,
public publication, real CLI or cleanup integration:

1. each process class independent of each turn class;
2. completed synthetic turn with and without synthetic agent-message marker;
3. authoritative synthetic event contract present, missing, mutated and
   digest-mismatched;
4. ordered projection with malformed value, unknown marker, ordinal gap,
   duplicate terminal, terminal-before-start and contradictory terminals;
5. every final-output and task-execution class as supplied closed inputs;
6. nonzero plus completed turn, timeout plus terminal, and other precedence
   combinations;
7. compatible orthogonal failures versus contradictory evidence;
8. fixed synthetic stdout/stderr/final digests accepted, while live-like or
   unapproved content-digest fields are rejected; and
9. deterministic classification reconstruction from canonical synthetic public
   inputs.

This tranche does not claim an observation seal, path lifecycle observer,
cleanup workflow or public receipt exists.

### Deferred integration evidence requirements

Before any later integration candidate could be reviewable, synthetic
filesystem and publication fixtures must cover:

1. pre-existing target, symlink, junction/reparse point and directory;
2. stat/read target replacement;
3. create then delete;
4. parent directory identity switch;
5. target replacement after observation but before read;
6. lifecycle observer gap or overflow;
7. stable file with simulated handle-bound read failure;
8. observation-seal write collision and crash before durable seal;
9. crash after seal but before cleanup;
10. cleanup failure and partial residue;
11. final-receipt publication failure or collision;
12. external terminal and recovery-locator retention/removal;
13. privacy mutations containing paths, prompt/model/Skill text, credentials,
    arbitrary event values and raw stderr; and
14. fresh-root reconstruction of action -> seal -> cleanup -> receipt with
    byte-exact canonical comparison.

All fixtures remain synthetic. No real CLI, credential, session, preflight,
network call or live model content is used.

## Claim Ceiling

This design may claim only:

- a revised proposed diagnostic contract;
- current evidence gaps and retrospective boundaries;
- proposed closed axes, semantic-authority rules and precedence;
- an intended two-stage public evidence chain; and
- one recommended offline synthetic implementation tranche.

It may not claim that:

- any diagnostic, schema, parser, projector, watcher, classifier, seal or
  verifier exists or is enforced;
- private raw content is independently reconstructable after deletion;
- the old pair has been causally reclassified;
- credentials, preflight or a new live session are authorized;
- Gate 3 passed or produced a counted sample; or
- treatment, Skill, model, route or framework effectiveness is established.

## Implementation Tranche Recommendation

The smallest meaningful next tranche, only if separately authorized, is a pure
offline library:

1. define closed in-memory data types for the four axes and the synthetic event
   contract;
2. implement precedence and deterministic classification without filesystem,
   process, cleanup or publication I/O;
3. add the first-tranche synthetic fixture groups above; and
4. stop for independent semantic review.

Do not implement the lifecycle observer or evidence-chain integration, alter
the promoted contract, prepare credentials, run preflight or request live
authorization in that tranche. Every later tranche requires a new explicit
scope and independent review.
