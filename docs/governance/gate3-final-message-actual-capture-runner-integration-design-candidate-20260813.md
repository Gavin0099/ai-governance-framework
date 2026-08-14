# Gate 3 Actual-Capture Runner Integration Design Candidate

Status: design-only candidate; not independently approved or implemented

Date: 2026-08-13

Base: `origin/main@e7410b3469d4e3112904b4f822180e51d5c1a3ea`

Scope: the minimum future seam between the contained Codex runner, the approved
offline actual-capture adapter, and the existing pre-cleanup evidence chain

## Problem

The repository now contains an independently approved offline actual-capture
adapter, but the live-capable `CodexExecRunner` does not call it. The runner
returns private stdout as part of `SyntheticResult`; it separately observes the
final-output path and calibrated workspace. Wiring these surfaces together
without a narrow contract could launch before durable capture authority, expose
private stdout through errors or retained objects, permit a second execution
after a crash, or clean the private evidence root before the public capture
artifacts are reopened and sealed.

This candidate defines only that missing integration boundary. It grants no
implementation or execution authority.

## Current Repository Truth

1. This candidate starts from merged main
   `e7410b3469d4e3112904b4f822180e51d5c1a3ea`.
2. `gate3_route_v2_codex.py` SHA-256 is
   `d308331cc59cfce50604488a2ab9121727338fd7886c61a7f2e6fa6b5b2af7e8`.
   `_run_contained` launches one process, reads stdout and stderr with
   `communicate()`, terminates the process tree, and only then returns a private
   `_ContainedResult`.
3. `CodexExecRunner.__call__` currently calls `_run_contained`, observes the
   final-message path and calibrated workspace, then returns a
   `SyntheticResult` containing private stdout. It does not publish an
   actual-capture authorization, process result, lifecycle projection or capture
   result.
4. `gate3_final_message_actual_capture.py` SHA-256 is
   `67d098138d2442f1c68aae462d350a7a461e191d831b8bea8799d3498ee1d99d`.
   Its independently approved offline API provides `CaptureBindings`,
   `CreateOnceStore`, `CapturePublisher.authorize`, `CapturePublisher.capture`,
   `build_process_result` and `verify_public`.
5. The accepted adapter design SHA-256 is
   `6d52ecda73c542e300c1612a712beb38c4ce7b44a66e5335965d254052905a34`.
   It requires capture authority before launch, create-once evidence, public
   reopen checks, exact seal links, no retry or replacement, and the claim
   ceiling `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`.
6. The existing diagnostic integration orders observation seal before cleanup,
   then cleanup result, receipt and finalization. It does not yet include the
   actual-capture artifact inventory in a real runner route profile.
7. The consumed Gate 3 pair remains closed and `NON_SUCCESS`. Nothing in this
   candidate reopens, repairs, retries, replaces or reinterprets it.

## Target Outcome

Define one reviewable integration seam that, for a later separately authorized
execution:

1. receives exact pre-existing action and capture bindings;
2. durably publishes and reopens create-once capture authorization before the
   contained command may launch;
3. invokes the contained command at most once;
4. after process-tree termination, hands the private stdout bytes exactly once
   to the approved capture publisher with a content-free process result;
5. observes the final-output and calibrated workspace axes without copying raw
   stdout into either axis;
6. reopens the required public capture artifacts and binds their exact bytes in
   the existing observation seal before private evidence-root cleanup becomes
   eligible; and
7. fails closed without retry, replacement or effect inference after any
   mismatch, publication failure or crash.

## DONE Condition for a Later Offline Implementation Tranche

`DONE = Using only injected synthetic contained-process results and retained
privacy canaries, the runner seam validates and reopens exact create-once capture
authority before one launch-equivalent call, hands private stdout once to the
approved adapter, reopens and seals the resulting public artifacts before
private evidence-root cleanup eligibility, and fails closed under focused
authority, privacy, TOCTOU, crash and mutation tests.`

This is a proposed later tranche, not current implementation authority.

## Scope

### In scope for this design

- One insertion point around the current `_run_contained` result.
- Authority ownership and exact digest bindings.
- Private-to-public data boundaries.
- Exact public evidence inventory and seal links.
- Ordering, crash, TOCTOU and fail-closed states.
- A smallest synthetic offline implementation tranche and focused test plan.

### Explicit non-goals and prohibitions

- No implementation, file staging, commit, push, MR or merge in this slice.
- No credentials, credential files, credential reads or credential-derived
  values.
- No preflight, zero-session probe or authorization receipt generation.
- No Codex executable invocation, subprocess invocation, model call or network
  call.
- No live, counted or non-counted execution.
- No reuse, retry, replacement, repair or reinterpretation of the consumed pair.
- No owner-pin, manifest, promotion, command, prompt, model or arm change.
- No reading or deriving facts from unrelated untracked evidence paths.
- No retention, logging, exception rendering, serialization or hashing of raw
  runtime stdout, stderr, prompt payloads, final messages, reasoning, tool
  content, paths, identifiers, environment values, credentials, model IDs,
  usage or timestamps. This does not prohibit a digest of an already reviewed
  Git blob that happens to contain static source constants; that digest is a
  code-identity binding and must not be presented as a prompt digest.
- No claim that an `agent_message` is a final answer or model completion.
- No model, adapter, CLI, task, treatment or framework effectiveness inference.
- No weakening or widening of the approved capture schemas or public verifier.

## Responsibility Boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| route/action authority | exact action, arm, executable, command, integration-contract and capture bindings | private stdout or dynamically learned live values |
| runner-integration coordinator | ordering, single invocation, sanitized process disposition, exact handoff and seal eligibility | credentials, NDJSON semantics, retries or cleanup implementation |
| `_run_contained` | command execution, stdout/stderr collection, timeout and process-tree termination | public diagnostic publication or receipt claims |
| approved capture publisher | private stdout parsing and create-once public capture artifacts | command launch, final-output/workspace observation or raw retention |
| observation collector | existing content-free final-output and workspace axes | parsing stdout or inferring cause |
| seal publisher | exact public artifact inventory and digest links | cleanup side effects or reconstruction of missing artifacts |
| cleanup/recovery implementation | existing post-seal cleanup or external recovery contract | recreating capture output, retrying the command or upgrading claims |
| public verifier | canonical bytes, closed schemas, inventory and cross-links | executable provenance, private-stream correspondence or effect truth |

The coordinator is an orchestration boundary, not a second parser or verifier.
It passes raw stdout directly from the private contained result to the approved
publisher and must not inspect, clone, transform or render those bytes.

## Exact Integration Seam

### Inputs

The future coordinator receives only:

- an already-constructed `CodexExecRunner` capability whose current preflight
  checks remain unchanged;
- `CaptureBindings` for the exact action and arm;
- an outer runner-integration contract whose digest is already pinned by the
  route/action authority;
- a fresh empty create-once capture store inside the private evidence root;
- callbacks for the existing final-output/workspace observations, observation
  seal publication and cleanup eligibility; and
- static approved adapter, raw-envelope, projector and public-schema bytes.

It does not receive credential bytes. Existing credential provisioning remains
inside the separately governed runner and is outside this design.

### Ordered state machine

| State | Required durable/public fact | Permitted next side effect |
| --- | --- | --- |
| `R0_UNAUTHORIZED` | empty capture store | validate static bindings and fresh-create authorization only |
| `R1_LAUNCH_ORDINAL_CONSUMED` | exact `capture-authorization.json` fresh-created and reopened; this is the sole durable launch-consumption claim | one contained-command invocation only in the same uninterrupted coordinator instance |
| `R2_CAPTURE_RETAINED` | exact process result and capture result; projection iff `COMPLETE`; all reopened | final-output/workspace observation |
| `R3_OBSERVATIONS_RETAINED` | content-free capture, final-output and workspace observations | publish one observation seal |
| `R4_SEALED` | exact seal durably published and reopened | existing private evidence-root cleanup/recovery path |
| `R5_CLEANUP_RECORDED` | existing cleanup result | existing receipt/finalization path |

Fresh creation and reopen of capture authorization consumes launch ordinal `1`;
there is no separate retained launch-disposition state. The only command
transition is an in-memory continuation from newly entered
`R1_LAUNCH_ORDINAL_CONSUMED`. A restarted coordinator sees pre-existing
authorization, cannot recreate it, and must report permanent unknown without
invocation. No state permits a second command launch. Public evidence therefore
does not claim whether a crash after authorization happened before, during or
after process launch.

### Concrete call ordering

1. Validate current runner-integration source/contract bytes and all
   `CaptureBindings` against authority supplied before this operation.
2. Call `CapturePublisher.authorize(bindings)` once and reopen the exact
   authorization bytes. Successful fresh creation is the durable consumption of
   launch ordinal `1`; only the same uninterrupted coordinator instance receives
   the one-shot in-memory capability to continue.
3. Run the approved pre-launch authorization check and invoke `_run_contained`
   once through that one-shot capability. A pre-existing authorization or any
   restart forbids invocation.
4. Convert only `_ContainedResult.returncode`, `timed_out` and the sanitized
   stdout-reader disposition into `build_process_result`; do not expose stderr.
5. Call `CapturePublisher.capture(completed.stdout, process_result, bindings)`
   once. The private stdout reference must not be placed in the coordinator's
   public return value or retained exception state.
6. Reopen and validate the exact capture authorization, process result, capture
   result and conditional lifecycle projection with `verify_public`.
7. Collect the existing content-free final-output and workspace observations.
8. Publish and reopen an observation seal that binds the exact inventory below.
9. Only after step 8 may the existing private evidence-root cleanup callback be
   made eligible.

`_run_contained` already terminates the child process tree before returning.
That containment cleanup is part of command completion and is not delayed by
this design. Every reference to “pre-cleanup seal” here means before cleanup or
removal of the private evidence root, workspace, locator or retained evidence;
it does not mean before child-process termination.

### Launch failure mapping

If `_run_contained` fails before returning a private result, the coordinator
must record only a sanitized content-free disposition:

| Observed runner boundary | Process disposition | Capture status ceiling |
| --- | --- | --- |
| process creation failed | `START_FAILED` | `UNAVAILABLE` |
| timeout returned with EOF/reader complete | `TIMED_OUT` | adapter-derived, never upgraded |
| process-tree termination incomplete or stdout unavailable | `TERMINATED` with read failure | `UNAVAILABLE` |
| normal return | `EXITED` | adapter-derived |

No exception text, command, path, stderr or raw-byte property enters public
evidence. A launch failure after durable authorization consumes the one launch
ordinal even when the public evidence cannot determine whether a process began.
For `START_FAILED` or an unavailable stdout reader, the coordinator calls the
capture publisher once with `stdout_read_failed = true`, both EOF/reader-complete
flags false, and a private empty placeholder that the approved publisher must
not parse in that row. This produces the closed non-complete capture result
without pretending that an empty stream was observed. If even that publication
does not complete, the state is `RUNNER_CAPTURE_RESULT_UNKNOWN`; it is never
recalled or retried.

## Authority Contract

### Authority supplied before the seam

The outer route/action authority must bind:

- exact action SHA-256 and arm token;
- exact executable and command-contract SHA-256 values from a separately
  authorized future receipt;
- exact `gate3_route_v2_codex.py` SHA-256;
- exact runner-integration Git blob/commit identity and contract SHA-256 values;
- all existing `CaptureBindings`, including adapter source, adapter contract,
  raw-envelope contract, lifecycle projector and public-schema SHA-256 values;
- `launch_ordinal = 1`, `capture_ordinal = 1`, `retry = false` and
  `replacement = false`; and
- the exact closed evidence inventory and maximum byte limits already enforced
  by the approved adapter.

This candidate supplies none of those future executable/receipt values and does
not promote any manifest. Static digests may be computed offline for review,
but authority cannot be manufactured from values observed after launch.

### Non-circular authority

The capture authorization remains the approved adapter-specific record. The
outer action authority independently pins the runner-integration Git blob,
commit and contract digest before the authorization or command side effect. The
observation seal then links those identities to that earlier authority; it
cannot authorize them. The reviewed Git object is the source-byte evidence and
is not copied into the public diagnostic package. No artifact may validate
itself by carrying only its own recomputed digest.

### TOCTOU checks

The reviewed Git commit/blob identities and their digests are immutable public
authority inputs. They are not the bytes re-read at runtime. At each checkpoint,
the coordinator must privately read the actual filesystem/module source and
contract/schema bytes that the runner or adapter is about to use, recompute
their digests, and compare them with the pre-authorized Git blob/contract/schema
digests. Those private runtime snapshots and their contents are not copied into
the public package.

This private comparison applies to the actual runner-integration source, runner
source, adapter source, adapter contract, raw-envelope contract, projector
contract and public schemas:

1. before capture authorization;
2. immediately before command invocation;
3. immediately before private stdout parsing; and
4. when reopening artifacts before seal publication.

Any mismatch is a closed contract failure. Before launch it forbids launch;
after launch it consumes the ordinal, forbids retry, prevents positive capture
classification and routes retained public state to the existing negative or
external-recovery profile.

A successful comparison proves only that the filesystem/module bytes sampled at
that checkpoint matched the pre-authorized identities. It does not prove which
instructions were already loaded or executed, executable provenance, memory
immutability, or absence of mutation between checkpoints. The public evidence
may attest to the closed checkpoint results and authority links, but it must not
contain the sampled source bytes or upgrade them into loaded-code provenance.

## Public Evidence Contract

### Required capture inventory

The observation seal must bind exact canonical bytes and SHA-256 values for:

- outer action/runner-integration authority;
- runner-integration contract bytes plus exact reviewed Git commit/blob identity
  and source SHA-256; the runner or integration source bytes themselves are not
  copied into the public package;
- `capture-authorization.json`;
- `process-result.json` when publication was reached;
- `capture-result.json` when publication was reached;
- `lifecycle-projection.json` if and only if capture status is `COMPLETE`;
- approved adapter source, adapter contract, raw-envelope contract, projector
  contract and public schemas;
- existing content-free final-output observation;
- existing content-free calibrated-workspace observation; and
- the exact closed inventory/profile identifier.

The seal must contain no raw private bytes or digest/length of those bytes.
Artifact names, schemas and digest links are closed; unknown or extra entries
fail verification.

### Evidence profiles

| Profile | Minimum retained state | Cleanup eligibility |
| --- | --- | --- |
| `RUNNER_CAPTURE_FINALIZED` | authority, `capture status = COMPLETE`, admitted non-negative final-output/workspace observations, seal, cleanup, receipt and finalization | only through existing sealed cleanup contract |
| `RUNNER_CAPTURE_NEGATIVE` | authority and a derived negative discriminator: closed non-complete capture status or negative/indeterminate final-output/workspace observation; retain the exact artifacts reached by the admitted negative seal/receipt path | only if the existing negative cleanup matrix admits the exact terminal state |
| `RUNNER_CAPTURE_RESULT_UNKNOWN` | authorization plus every artifact/transition durably present before crash; no synthesized result/projection | no ordinary cleanup; existing external recovery only |
| `RUNNER_SEAL_UNAVAILABLE` | all durably retained capture/observation artifacts and closed failure transition; no invented seal | no ordinary cleanup; existing external recovery only |

Profiles are exact and disjoint. Missing, extra, duplicated, renamed, mutated or
cross-profile artifacts fail closed. A recovery reader may report the durable
state but may not call `capture` again or recreate a missing artifact.
`RUNNER_CAPTURE_FINALIZED` is forbidden whenever any negative discriminator is
present. `RUNNER_CAPTURE_NEGATIVE` is selected from reconstructed capture and
observation facts, never from a caller-provided profile flag. A closed
non-complete capture can therefore never match the finalized profile, while a
complete capture with a negative/indeterminate observation matches only the
negative profile. Cross-profile mutation tests must change an otherwise-valid
tree, recompute its ordinary digest links, and still be rejected on the derived
discriminator/profile mismatch.

### Public claim ceiling

The capture verifier's strongest positive token remains
`PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`, meaning only that the retained
public capture artifacts are canonical and internally linked under the approved
contract.

The combined route verifier may additionally reconstruct existing public
final-output/workspace and cleanup/receipt facts. It cannot establish:

- that private stdout corresponded to the reported projection;
- executable, credential, environment or transport provenance;
- that an `agent_message` was a final answer;
- model completion, intent, correctness or effectiveness;
- task, treatment, adapter, CLI or framework effectiveness; or
- causality among capture, final-output and workspace observations.

## Failure, Crash and Recovery Rules

1. Authority missing or mismatched before launch: fail before invocation.
2. Crash after authorization and before invocation: the launch ordinal is
   already consumed; permanent `RUNNER_CAPTURE_RESULT_UNKNOWN`; no retry even if
   a process likely did not start. Public evidence does not claim a launch
   disposition.
3. Crash during invocation or before `_ContainedResult` return: launch ordinal
   consumed; sanitized unknown/unavailable state; no retry.
4. Crash after private stdout return and before process-result publication: raw
   bytes are not retained; result remains unknown; no retry.
5. Crash between process result, projection and capture result: retain exact
   create-once artifacts; do not adopt, overwrite or complete the chain.
6. Capture returns non-complete: retain the closed result, make lifecycle axes
   `INDETERMINATE`, and continue only to an admitted negative seal path.
7. Capture publication collision or reopen mismatch: no overwrite and no second
   capture call.
8. Final-output/workspace observation fails: retain the closed observation and
   use existing negative/indeterminate semantics; never infer it from stdout.
9. Crash before seal: ordinary cleanup remains forbidden.
10. Seal collision, mutation or reopen mismatch: ordinary cleanup remains
    forbidden; retain state for external recovery.
11. Crash after seal and before cleanup: restart may execute only the existing
    exact-once cleanup continuation after reopening the seal; it must not rerun
    the command or capture.
12. Mutation after seal: final verification rejects the digest/inventory link.

## Privacy Boundary

The coordinator and its tests must enforce deny-by-default public fields. In
particular:

- private stdout is passed by reference to one adapter call and never returned;
- stderr is never passed to the adapter and is never public;
- raw parser errors and runner exceptions are converted to closed codes without
  rendering their messages;
- ignored content positions include message/text, reasoning, command,
  arguments, result, diff, path, URL, model, MCP, environment, credential,
  identifiers, usage and timestamps;
- no raw stream digest, length, line count, prefix, suffix or entropy summary is
  retained; and
- logs and test diagnostics contain only closed state tokens and public artifact
  names.

Managed-memory secure erasure is not claimed. The design controls publication,
retention and normal diagnostics, not physical memory forensics.

## Focused Offline Evidence Plan

The later implementation tranche must use an injected fake contained-command
callable. It must not invoke `_run_contained`, a real CLI, credentials, preflight,
network or live code.

Required tests:

1. authorization is durably published/reopened before the fake invocation;
2. invocation count is exactly one for completed success/failure paths; it is
   zero for authority failure, every `R0` crash, and every crash after
   authorization but before fake-callable entry; it is exactly one once fake
   callable entry has occurred, including all later crash points; no path may
   exceed one;
3. private stdout object identity reaches the approved publisher once and never
   appears in the coordinator return, store, logs or sanitized exceptions;
4. stderr canaries never reach the adapter or public artifacts;
5. exact COMPLETE and non-complete capture inventories reopen and seal;
6. missing/extra/mutated/cross-linked artifacts fail public verification;
7. cleanup callback is impossible before durable seal reopen;
8. crash injection before and after every `R0`-`R5` transition reconstructs the
   required state and never enables retry/replacement;
9. source/contract/schema mutations at each TOCTOU checkpoint fail at the
   specified boundary;
10. launch failure mappings are closed and never expose exception text;
11. every ignored content family listed in the privacy boundary carries a
    distinct canary and no canary appears in public bytes or diagnostics;
12. unknown event/item/profile/schema fields fail closed;
13. expected public bytes are retained literal/spec fixtures independent of the
    production serializer/projector; and
14. the maximum verified claim remains exactly
    `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`.

Mutation tests must recompute otherwise-valid manifests and digest links so that
they exercise semantic verification rather than failing only on stale hashes.

## Affected Surfaces if Later Implemented

The smallest credible offline tranche may touch only:

- `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_route_v2_codex.py`;
- `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_final_message_diagnostic_integration.py`;
- `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/test_gate3_route_v2_codex.py`;
- `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/test_gate3_final_message_diagnostic_integration.py`;
- only if required, a new runner-integration helper and one focused test file in
  the same directory.

`gate3_final_message_actual_capture.py` and its schemas remain unchanged unless
a new independent design and authorization explicitly expands that scope.
Manifests, owner pins, promotion state, `PLAN.md`, memory and live evidence are
outside the tranche.

## Recommended Implementation Tranche

After independent exact-digest approval of this candidate and separate owner
authorization, implement only the dependency-injected coordinator, exact seal
inventory extension, public reconstruction checks and the focused synthetic
tests above. The production runner call must be replaced by a fake in every
test. No credential, preflight or live path may execute.

Stop after the focused offline DONE condition passes. Stage, commit, PLAN/memory
reconciliation, push, MR/merge, fresh preflight and any live operation each
require their own later authority.

## Review Questions

1. Does durable capture authorization precede the sole command invocation?
2. Is the integration authority independent and non-circular?
3. Can private stdout reach only the approved publisher, exactly once?
4. Is process-tree termination correctly distinguished from evidence cleanup?
5. Does the seal bind every required public capture and observation artifact?
6. Are crash states reconstructable without retry, replacement or adoption?
7. Do TOCTOU checks cover authority, launch, parsing and pre-seal reopen?
8. Are all evidence profiles exact, disjoint and fail closed?
9. Does the privacy boundary forbid both content and raw-byte metadata?
10. Is the public claim ceiling preserved without effect inference?
11. Is the later tranche synthetic/offline and narrow enough to review?

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, old-pair reuse, retry, replacement, staging, commit, push, MR, merge,
manifest update, owner-pin update or promotion. Acceptance of the design and
every later transition require separate explicit authorization.
