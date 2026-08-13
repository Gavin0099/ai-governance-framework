# Gate 3 Real-Runner Contained-Result Bridge Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-13

Revision: supersedes the pre-decision baseline at SHA-256
`ed7807d67dd4a106954b7c20e8f3cff172222327e25879a522330235bd82b577`, which was
never an approval target. That baseline received `CHANGES_REQUESTED` with five
blocking findings; the first revision applied all of them plus the eight
decisions recorded under "Decisions Applied", and was reviewed at SHA-256
`71a6943dc8e0d38d2dd1ef8653d0fd1afdc407acf9852401cdb9652f5802a2ab`. That review
returned `CHANGES_REQUESTED` with one blocking finding — the workspace baseline
was described as authority-bound although `RuntimeAuthority` has no field able to
express it — and one wording warning about live-path imports. This revision
applies both. The exact digest of this revision is the review target.

Design source baseline: `main@0e8f3b79d675e567a4daf2b6e210132f1614958c` (merge of
PR #61). Candidate commit base: `main@cc304a90f1ee269112aebc45c478a4fbe9451205`.
The source files named in "Current Repository Truth" are unchanged between them.

Scope: the single conversion seam by which one real `_ContainedResult` produced
inside `gate3_route_v2_codex.py` becomes the `InjectedContainedResult` that the
already-merged `RunnerIntegrationCoordinator` consumes

## Problem

PR #61 merged an offline runner/capture integration whose coordinator accepts an
**injected** contained-process callable. Every existing test supplies a fake. The
real contained runner still exists on the other side of an unbridged gap:

- `_run_contained` returns a private `_ContainedResult`;
- `CodexExecRunner.__call__` consumes that result and returns a
  `route.SyntheticResult` that carries raw stdout, decoded final-message bytes
  and observed workspace bytes;
- `RunnerIntegrationCoordinator.invoke` expects a zero-argument callable
  returning `InjectedContainedResult`.

Nothing converts one into the other. Writing that converter carelessly would
either leak private streams into public evidence, silently create a second
trusted execution path alongside `TrustedLiveRunner`, or claim a launch
disposition (notably `START_FAILED`) that the current runner boundary cannot
actually prove.

This candidate defines only that conversion seam and the ordering, privacy and
fail-closed rules around it. It grants no implementation, credential, preflight
or execution authority.

## Current Repository Truth

All digests below were computed offline from the working tree, which is
byte-identical to merged main for every file named here.

| Subject | Value |
| --- | --- |
| merged main | `0e8f3b79d675e567a4daf2b6e210132f1614958c` |
| `gate3_route_v2_codex.py` blob | `d5fa0c03c41ef3b5e374f170cbf6685cd86faa07` |
| `gate3_route_v2_codex.py` SHA-256 | `d308331cc59cfce50604488a2ab9121727338fd7886c61a7f2e6fa6b5b2af7e8` |
| `gate3_final_message_runner_integration.py` blob | `15e3c7d618ab17a50dd8fb0957cd1e19d9fa4a58` |
| `gate3_final_message_runner_integration.py` SHA-256 | `c2bc090b1a53dac44610dfa37a4eb3db9d62a6e52f27308be63eb6b585b9befa` |
| `gate3_final_message_actual_capture.py` SHA-256 | `67d098138d2442f1c68aae462d350a7a461e191d831b8bea8799d3498ee1d99d` |
| `test_gate3_final_message_runner_integration.py` SHA-256 | `71fe98ec433d33a53339c0ccedbd40d9287a0ec5f091911daeff0e6ff2f95bf6` |

Behavioural facts this design depends on:

1. `_ContainedResult` is a frozen dataclass with fields `returncode: int`,
   `stdout: bytes`, `stderr: bytes`, `timed_out: bool`, `tree_terminated: bool`.
2. `_run_contained` performs one `Popen`, one `communicate()` (a second
   `communicate()` after kill on timeout), terminates the process tree, and
   **raises** `route.RouteV2Error` when `tree_terminated` is false. A result with
   `tree_terminated = False` therefore never reaches a caller.
3. `InjectedContainedResult` fields are `returncode: int | None`, `stdout`,
   `stderr`, `process_disposition = "EXITED"`, `stdout_eof = True`,
   `stdout_reader_complete = True`, `stdout_read_failed = False`. The coordinator
   reads only `.stdout` and `.process_result()`; the `stderr` field is never
   read.
4. `capture.validate_process_result` enforces `exit_code` is an `int` **iff**
   disposition is `EXITED`, `None` otherwise, and rejects
   `stdout_read_failed = True` combined with either stdout flag being true.
   `PROCESS_DISPOSITIONS = {"EXITED", "TIMED_OUT", "TERMINATED", "START_FAILED"}`.
5. `RunnerIntegrationCoordinator.run()` orders side effects as: authority and
   bindings validation, `_validate_runtime_binding`, empty-store check,
   `_check_runtime("before_authorization")`, integration contract + authority
   publish, observation-stage publish, `publisher.authorize(bindings)`,
   `_check_runtime("before_invocation")`, one `invoke()`,
   `_check_runtime("before_private_parse")`, one `publisher.capture(...)`,
   `verify_public`, observations, `_check_runtime("before_seal")`, seal, then
   cleanup/receipt/finalization.
6. The coordinator already converts a raised `ContainedStartFailed` into a
   `START_FAILED` result itself, and converts every other non-crash exception
   from `invoke()` into `IntegrationError("INVOCATION_DISPOSITION_UNKNOWN")`
   without rendering the exception.
7. `RUNTIME_SUBJECTS` is the closed set `{runner_source, integration_source,
   adapter_source, adapter_contract, raw_contract, projector_contract,
   public_schemas}`, and `_check_runtime` requires exact set equality with
   `authority.runtime_sha256`.
8. `route._trusted_live_runner` accepts an `invoke` only when
   `invoke.__func__ is gate3_route_v2_codex._TRUSTED_CODEX_INVOKE` (which is
   `CodexExecRunner.__call__`), the owner type is exactly `CodexExecRunner`, and
   the module file digest equals `execution_identity["runner_sha256"]`.
9. `derive_profile` returns `RUNNER_CAPTURE_FINALIZED` only for
   `capture_status == "COMPLETE"` **and** `final_state == "CAPTURED"` **and**
   `workspace_state == "CHANGED"`; everything else is `RUNNER_CAPTURE_NEGATIVE`.
10. The consumed Gate 3 pair remains closed and `NON_SUCCESS`. Nothing here
    reopens, retries, replaces or reinterprets it.

## Target Outcome

Define one reviewable bridge that, for a later separately authorized execution:

1. maps exactly one `_ContainedResult` into exactly one
   `InjectedContainedResult` with a closed, schema-valid disposition;
2. hands the private stdout bytes to the capture publisher exactly once and
   never anywhere else;
3. keeps stderr entirely outside the adapter and outside public evidence;
4. leaves `CodexExecRunner.__call__` and `TrustedLiveRunner` provenance
   byte-identical and behaviourally unchanged, so no new trusted execution path
   appears by accident;
5. fixes the order of launch authorization, runtime TOCTOU checks and capture
   authorization;
6. derives final-message and workspace states from independent observations,
   never from stdout; and
7. fails closed, with no retry and no invented disposition, for every launch,
   timeout, termination, reader and unknown-exception boundary.

## Scope

### In scope

- The `_ContainedResult → InjectedContainedResult` field mapping.
- Ownership of the single stdout reference and exclusion of stderr.
- Non-interference with `CodexExecRunner.__call__` / `TrustedLiveRunner`.
- The exact ordering of launch authority, TOCTOU checkpoints and capture
  authorization, including where private workspace preparation belongs.
- Fail-closed mapping for `START_FAILED`, timeout, termination, reader failure
  and unknown exceptions.
- Independent final-message and workspace observation callbacks.
- Residual gaps this bridge cannot close on its own.

### Explicit non-goals and prohibitions

- No implementation, staging, commit, push, MR or merge in this slice.
- No modification of `gate3_route_v2_codex.py`, the merged runner integration,
  its tests, `PLAN.md`, memory, or any evidence path.
- No credentials, credential files, credential reads or credential-derived
  values.
- No preflight, zero-session probe or authorization receipt generation.
- No Codex invocation, subprocess, model call or network call.
- No live, counted or non-counted execution.
- No reuse, retry, replacement or reinterpretation of the consumed pair.
- No owner-pin, manifest, promotion, command, prompt, model or arm change.
- No reading or deriving facts from the untracked evidence paths currently in
  the working tree.
- No retention, logging, exception rendering, serialization, hashing, length or
  entropy summary of runtime stdout, stderr, prompts, final messages, reasoning,
  tool content, paths, identifiers, environment values, credentials, model IDs,
  usage or timestamps.
- No claim that an `agent_message` is a final answer or model completion.
- No model, adapter, CLI, task, treatment or framework effectiveness inference.

## Bridge Placement

The bridge is a **new callable in a new module**, not a change to the runner and
not a change to the merged coordinator.

| Option | Verdict |
| --- | --- |
| replace or wrap `CodexExecRunner.__call__` | rejected |
| add a method to `CodexExecRunner` | rejected in this slice |
| new module exposing a bridge factory | recommended |

Rationale for rejecting any change to `__call__`:

- `_TRUSTED_CODEX_INVOKE` is bound at import to `CodexExecRunner.__call__`. A
  wrapper passed to `route._trusted_live_runner` fails the `__func__` identity
  check, so the failure mode is at least loud rather than silent — but rebinding
  or redefining `__call__` would move the trusted identity itself.
- `route._trusted_live_runner` compares the on-disk module digest with
  `execution_identity["runner_sha256"]` from the measured preflight. Editing the
  module invalidates every already-measured preflight bound to that digest.
- `__call__` returns `SyntheticResult` carrying stdout, decoded final-message
  bytes and observed workspace bytes. Routing the bridge through it would create
  a second live reference to private stdout that the coordinator cannot see or
  constrain.

Consequence: the bridge calls `_run_contained` directly and never calls
`__call__`. `CodexExecRunner.__call__` and its `SyntheticResult` path stay
exactly as merged.

The two paths must be mutually exclusive per execution. In the offline tranche
this holds trivially: the tranche never constructs a `CodexExecRunner` and never
imports a live path. **Before any production wiring, exclusivity must be
enforced at the capability/authority layer** — a single path selection that a
caller cannot bypass — rather than by the rule "do not call both". Two callable
routes to one contained command, separated only by caller discipline, is not a
property a verifier can check, and a second undeclared execution is exactly what
the launch ordinal exists to prevent.

## The Mapping

### Fields

| `_ContainedResult` | `InjectedContainedResult` | Rule |
| --- | --- | --- |
| `stdout` | `stdout` | same object reference, passed through untouched |
| `stderr` | — | never mapped; the bridge sets `stderr = b""` |
| `returncode` | `returncode` | forwarded **only** when disposition is `EXITED`; `None` otherwise |
| `timed_out` | `process_disposition` | `True → "TIMED_OUT"`, `False → "EXITED"` |
| `tree_terminated` | — | always `True` on any returned result (see fact 2); a false value is an exception path, not a mapped field |
| — | `stdout_eof` / `stdout_reader_complete` | `True` on every returned-result path, because `communicate()` completed |
| — | `stdout_read_failed` | `False` on every returned-result path |

`InjectedContainedResult.stderr` exists but is never read by the coordinator.
Setting it to `b""` rather than forwarding `completed.stderr` means stderr has no
route into the adapter even if a future coordinator revision starts reading that
field, and means the object's auto-generated `repr` cannot render stderr.

### Disposition table

| Observed boundary | disposition | exit_code | eof / reader_complete / read_failed | capture ceiling |
| --- | --- | --- | --- | --- |
| normal return, `timed_out = False` | `EXITED` | `completed.returncode` | `True / True / False` | adapter-derived |
| normal return, `timed_out = True` | `TIMED_OUT` | `None` | `True / True / False` | adapter-derived, never upgraded |
| `_run_contained` raised, cause not provably pre-launch | *not mapped* — exception propagates | — | — | `RUNNER_CAPTURE_RESULT_UNKNOWN` |
| `_run_contained` raised from a future typed pre-launch boundary | `START_FAILED`, produced by the coordinator from `ContainedStartFailed` | `None` | `False / False / True` | `UNAVAILABLE` |

The timeout row is the one place where the mapping must actively **drop**
information: `_run_contained` still reports a `returncode` after killing the
tree, but `validate_process_result` requires `exit_code is None` for any
non-`EXITED` disposition. Forwarding it is a hard schema failure, so the bridge
must discard it rather than translate it.

### `START_FAILED` is currently not provable

`_run_contained` is a single opaque call. From outside it, a raised exception
could mean the `Popen` never created a process, or that the job-object
assignment, the gate write, `communicate()`, or the tree-termination check failed
**after** a process was already running. The bridge cannot distinguish these.

Therefore the bridge **must not** raise `ContainedStartFailed` on a generic
exception. Claiming `START_FAILED` would assert "no process ran" from evidence
that does not support it — precisely the kind of upgrade the capture contract
exists to prevent. Instead the exception propagates to the coordinator's existing
closed `IntegrationError("INVOCATION_DISPOSITION_UNKNOWN")`, the launch ordinal
stays consumed, no capture result is published, and `reconstruct_profile`
resolves to `RUNNER_CAPTURE_RESULT_UNKNOWN`. That is the honest state.

`START_FAILED` becomes reachable only if a later, separately authorized change
gives `_run_contained` a typed pre-launch failure boundary (for example, raising
a distinct exception before `Popen` returns and only there). That change is out
of scope here and is recorded as a residual gap below.

### Termination and reader failures

- Incomplete process-tree termination raises `RouteV2Error` inside
  `_run_contained`, so the `TERMINATED` disposition is unreachable through the
  returned-result path. The bridge must not synthesize `TERMINATED` from an
  exception it cannot attribute; that case takes the unknown path above.
- A `communicate()` failure likewise surfaces as an exception with no stdout
  object in hand. There is nothing to hand to the publisher, so no capture is
  published and the state is `RUNNER_CAPTURE_RESULT_UNKNOWN`.
- The bridge never catches an exception in order to convert it into a
  publishable result. Its only `except` clause, if any, exists to guarantee that
  no private object survives in the raised exception's state — the exception type
  and message are not modified beyond that.

## Ordering

### Full ordered sequence

| # | Step | Owner |
| --- | --- | --- |
| 1 | build `RuntimeAuthority` and `CaptureBindings` from separately authorized values (action, arm, executable, command contract, blobs, schemas) | outer route/action authority |
| 2 | `authority.validate()`, `bindings.validate()`, cross-binding equality, `_validate_runtime_binding`, empty-store check | merged coordinator |
| 3 | `_check_runtime("before_authorization")` — private re-read and digest comparison of all seven runtime subjects | merged coordinator |
| 4 | publish integration contract + integration authority, reopen both | merged coordinator |
| 5 | publish observation stage | merged coordinator |
| 6 | `publisher.authorize(bindings)` — **this fresh create consumes launch ordinal 1** | merged capture publisher |
| 7 | `_check_runtime("before_invocation")` | merged coordinator |
| 8 | `invoke()` → bridge: prepare private workspace, then one `_run_contained`, then map | **bridge (new)** |
| 9 | `_check_runtime("before_private_parse")` | merged coordinator |
| 10 | `publisher.capture(stdout, process_result, bindings)` — the single stdout handoff | merged capture publisher |
| 11 | `verify_public` | merged capture publisher |
| 12 | `observe_final()`, `observe_workspace()` | **bridge callbacks (new)** |
| 13 | `_check_runtime("before_seal")`, seal, cleanup, receipt, finalization | merged coordinator |

Steps 2–7 and 9–13 are already merged and unchanged. The bridge supplies only
steps 8 and 12 plus the readers used by steps 3, 7, 9 and 13.

Launch authorization therefore strictly precedes runtime TOCTOU re-verification
of the launch, which strictly precedes the launch, which strictly precedes
capture. There is no ordering in which stdout exists before the create-once
authorization that admits it.

### Where private preparation belongs

`CodexExecRunner.__call__` lazily calls `prepare_private`, which materializes the
workspace, the isolated Codex home and `auth.json`. Because the bridge does not
call `__call__`, this must be placed explicitly. Two options:

| Option | Effect |
| --- | --- |
| prepare **before** `run()` | credential material exists on disk before launch authority is consumed; a crash before step 6 leaves credentials with no launch claim |
| prepare **inside** `invoke()`, before `_run_contained` | decided: credential material exists only after launch authority is consumed and only inside the one-shot invocation window |

The decided production direction is to prepare inside `invoke()`. The accepted
cost is that a pure preparation failure still consumes the launch ordinal and
produces `RUNNER_CAPTURE_RESULT_UNKNOWN` with no retry. That is consistent with
the "cannot prove pre-launch" rule above and is strictly the conservative
direction. Either way, private-root cleanup remains the existing post-seal path
and remains forbidden before a durable seal reopen.

**This direction is not implementable in the first offline tranche.** Placing
real preparation inside `invoke()` means a real `auth.json` lands on disk under
a state machine that forbids ordinary cleanup until a durable seal exists. See
"Credential Residue and Pre-Seal Recovery" below. The first tranche must fake
preparation as well as the contained call, and must never write credential
bytes.

## Credential Residue and Pre-Seal Recovery

`prepare_private` writes `auth.json` into the isolated Codex home under the
private root. Once preparation moves inside `invoke()`, the following window
exists and is currently **undefined**:

> preparation has written credential bytes → the launch ordinal is consumed →
> a failure occurs before the seal → ordinary cleanup is forbidden → the
> credential bytes remain on disk with no defined owner.

`_continue_after_seal` is reachable only when `SEAL_PATH` exists, so no code
path in the merged coordinator can remove that residue. "External recovery only"
is not a sufficient answer, because this design does not specify:

1. a **residue locator** — how a recovery reader finds the private root of a
   crashed run without reading private contents or publishing a path;
2. a **durable recovery authorization** — a create-once record proving that
   residue removal was admitted exactly once, without becoming a second cleanup
   path or a retry channel;
3. the **link to existing recovery profiles** — how `RUNNER_CAPTURE_RESULT_UNKNOWN`
   and `RUNNER_SEAL_UNAVAILABLE` bind to that authorization; and
4. whether residue removal may proceed **before** the seal, which the current
   ordering forbids for evidence but which credential hygiene arguably requires.

Item 4 is a genuine tension between two safety properties, not an oversight to
be resolved by convention. It is out of scope here.

Consequences, both mandatory:

- The first offline tranche fakes preparation. No credential bytes are written,
  so no residue exists and none of the above is exercised.
- Real credential landing is deferred to a separate **production-wiring design**
  that must define items 1–4 before any execution is authorized. Approval of
  this candidate does not authorize that.

## Observation Callbacks

`observe_final` and `observe_workspace` are supplied by the bridge and read the
same private paths the runner would read. They return closed tokens only, and
never see stdout.

| Callback | Source | Returns |
| --- | --- | --- |
| `observe_final` | `private_root/final-message.json` | `CAPTURED` if the file exists and reads; `ABSENT` if not a file; `READ_FAILED` on `OSError` |
| `observe_workspace` | `observed_artifact_ids` under `private_root/workspace` | `CHANGED` / `UNCHANGED` by exact byte comparison against the supplied baseline (see the unresolved binding problem below); `CAPTURE_FAILED` on `OSError` |

The comparison logic lives in the callback. **Where the baseline comes from is an
unsolved problem in this slice, not a solved one.**

The risk is real: a callback that chooses its own baseline can turn a changed
workspace into `UNCHANGED` or the reverse, and `derive_profile` treats that axis
as a profile discriminator, so the choice moves an execution between
`RUNNER_CAPTURE_FINALIZED` and `RUNNER_CAPTURE_NEGATIVE`.

The obvious fix — have the outer authority bind the exact artifact-id set and a
digest over their canonical bytes — **cannot be expressed today**.
`RuntimeAuthority` has no baseline field, its `public_value()` emits a closed
key set, and this slice forbids modifying the merged integration. There is
therefore no linkage a verifier could reconstruct, and claiming the baseline is
"authority-bound" would assert a binding that does not exist.

Accordingly, for the first tranche:

- the baseline is an independently retained **synthetic fixture**, not an
  authority-bound input;
- the tranche claims mapping characterization only, and specifically **does not**
  claim a verifiable evidence-profile derivation for the workspace axis; and
- `CHANGED`/`UNCHANGED` produced under a fixture baseline is a test-local fact,
  not public evidence about a real workspace.

A real baseline authority — its schema, canonicalization, private/public linkage,
and how the binding digest is published without leaking artifact identities —
requires an independent design before production wiring. It is listed in the
preconditions below.

Two mapping notes:

- The runner's vocabulary is lowercase and lacks the changed/unchanged axis:
  `__call__` returns `captured|absent|read_failed` and `captured|capture_failed`,
  and hands back the observed bytes. The integration vocabulary is
  `CAPTURED|ABSENT|READ_FAILED` and `CHANGED|UNCHANGED|CAPTURE_FAILED`. The
  bridge must derive `CHANGED`/`UNCHANGED` itself by comparing observed artifact
  bytes with `baseline_workspace`, and must discard those bytes afterwards.
- `derive_profile` requires `CHANGED` for `RUNNER_CAPTURE_FINALIZED`. An
  execution that captured a complete lifecycle but left the workspace unchanged
  is `RUNNER_CAPTURE_NEGATIVE`. This is intended: an unchanged workspace is a
  negative discriminator, not a formatting detail.

Neither callback may read, parse, decode or infer from stdout, and neither may
place file contents in its return value. The coordinator already coerces an
out-of-vocabulary or raising callback to `READ_FAILED` / `CAPTURE_FAILED`, so the
bridge must not add its own fallback that could mask a failure as a success.

## Privacy Boundary

- The private stdout bytes object reaches exactly one destination:
  `publisher.capture` at step 10, through the `InjectedContainedResult.stdout`
  field. It is never returned by the bridge, stored on the bridge object, logged,
  hashed, measured, or attached to an exception.
- `stderr` is never mapped, never passed, never publicly recorded and never
  length-measured. The runner's own `stderr` bytes fall out of scope when
  `_ContainedResult` is released.
- Both `_ContainedResult` and `InjectedContainedResult` are dataclasses with
  auto-generated `repr`. A traceback, `print`, `%r`, assertion message or test
  diagnostic that renders either object leaks raw stdout. In the offline
  mapping-only tranche this is controlled by convention plus canary tests, which
  is proportionate because no real stdout exists. **Before any production
  wiring, it must be replaced by a structural non-`repr` boundary** — sensitive
  fields must be structurally unrenderable rather than merely un-rendered by
  discipline, because a single upstream traceback would otherwise publish raw
  stdout. Convention is not a control once real bytes are present.
- The bridge holds the mapped result only as a local value that it returns to the
  coordinator; it keeps no attribute referencing it after `invoke()` returns.
- Bridge errors are closed codes. No exception message, command, path,
  environment value or byte-derived property enters public evidence or logs.
- Managed-memory erasure is not claimed. This design controls publication,
  retention and normal diagnostics, not memory forensics.

## Runtime Subject Gap

`RUNTIME_SUBJECTS` is closed and exact, `_check_runtime` requires
`set(runtime_readers) == set(authority.runtime_sha256) == RUNTIME_SUBJECTS`, and
`RuntimeAuthority` has no `bridge_source` field. A new bridge module's own source
bytes therefore **cannot** be bound by the merged runtime authority at all, and
this candidate forbids modifying the merged integration.

An earlier revision suggested binding the bridge's Git blob in the outer action
authority and calling that the first-tranche default. That was wrong in kind, not
in degree: a Git blob pinned by outer authority is an immutable review identity,
not a runtime binding. It proves which bytes were reviewed. It does not cause any
checkpoint to re-read the bridge before authorization, launch, parsing or seal.
Presenting it as the runtime answer would describe the tranche as more bound than
it is.

The honest position:

| | |
| --- | --- |
| what the first tranche can prove | that the mapping, disposition table, privacy boundary and fail-closed transitions behave as specified under injected inputs |
| what it cannot prove | that the bridge source executing at runtime is the reviewed source |

Accordingly the first tranche is **mapping characterization only**. It must not
be described, in PLAN, memory, commit messages or evidence, as integrated runtime
authority, and it must not claim that the bridge participates in the TOCTOU
chain.

Closing the gap requires one of these, each needing its own design and
authorization:

1. Extend `RUNTIME_SUBJECTS` with a `bridge_source` entry, which changes
   `RuntimeAuthority`, `RUNNER_INTEGRATION_CONTRACT_BYTES` and therefore the
   integration contract digest already pinned by the merged milestone.
2. Place the bridge inside `gate3_route_v2_codex.py` so `runner_source` covers
   it, which changes the runner module digest and invalidates every measured
   preflight bound to it.

Option 1 is the structurally correct direction. Neither is in scope here, and
**production wiring is blocked until one of them lands.**

## Fail-Closed Summary

1. Authority or binding mismatch before step 6: no launch, no capture, no
   evidence beyond the failure.
2. Runtime digest mismatch at `before_authorization` or `before_invocation`: no
   launch.
3. Crash after step 6 and before the bridge is entered: ordinal consumed,
   `RUNNER_CAPTURE_RESULT_UNKNOWN`, no retry, no launch-disposition claim.
4. Any exception inside the bridge before a result is returned: same as 3. No
   `START_FAILED`, no `TERMINATED`, no synthesized empty-stdout capture.
5. Timeout with a returned result: `TIMED_OUT`, `exit_code = None`, capture
   proceeds once and is never upgraded.
6. Runtime digest mismatch at `before_private_parse`: capture is not published;
   ordinal remains consumed; no retry.
7. Non-complete capture status: retained closed result, negative profile only.
8. Observation failure: closed negative/indeterminate token; never inferred from
   stdout.
9. Crash before seal: ordinary cleanup remains forbidden; external recovery only.
10. Crash after seal: only the existing `resume_after_seal` continuation may run;
    it must never re-invoke the bridge or re-capture.

## Public Claim Ceiling

Unchanged. The strongest positive token remains
`PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`, meaning only that the retained
public artifacts are canonical and internally linked under the approved contract.

Adding a real runner behind the bridge does **not** establish:

- that private stdout corresponded to the reported projection;
- executable, credential, environment or transport provenance;
- that an `agent_message` was a final answer or a model completion;
- task, treatment, adapter, CLI or framework effectiveness;
- causality among capture, final-output and workspace observations; or
- any change to the consumed Gate 3 pair, which remains `NON_SUCCESS`.

## DONE Condition for a Later Mapping-Only Offline Tranche

`DONE = With both the contained call and the private preparation replaced by
fakes, with no credential bytes written and no credentials, preflight,
subprocess, network or live path executed, the bridge maps every returned-result
case to a schema-valid InjectedContainedResult, drops returncode on the timeout
path, sets stderr to empty, hands one stdout object to the coordinator exactly
once, derives final/workspace tokens from a retained synthetic baseline fixture
without reading stdout, never claims START_FAILED or TERMINATED from an
unattributable exception, and fails closed under the focused mapping, privacy and
crash tests — while claiming neither runtime authority over the bridge source nor
a verifiable evidence-profile derivation for the workspace axis.`

This is a proposed later tranche, not current implementation authority. It is
deliberately narrower than the earlier revision: runtime binding of the bridge,
credential residue recovery, structural non-`repr` and machine-enforced path
exclusivity are all excluded and are production-wiring preconditions.

## Focused Offline Evidence Plan

The tranche must inject a fake in place of `_run_contained` **and** a fake in
place of `prepare_private`. No test may write credential bytes, construct or
invoke a live path, or start a subprocess. An identity-only import of
`gate3_route_v2_codex` — reading module attributes with no execution side effect
— is permitted; constructing `CodexExecRunner` or entering its execution path is
not. Required tests:

1. `EXITED` mapping forwards `returncode` and passes `validate_process_result`.
2. `TIMED_OUT` mapping sets `exit_code = None` even when the fake reports a
   non-`None` returncode; forwarding it instead is shown to fail validation.
3. `stderr` canary bytes from the fake never appear in the mapped object, the
   adapter call, public artifacts or diagnostics.
4. The stdout object identity reaching `publisher.capture` is the same object the
   fake produced, and it appears nowhere else — not in the bridge's attributes,
   the coordinator return, logs or exception state.
5. `repr` of the mapped object is never produced on any code path under test;
   a canary in stdout is asserted absent from captured stdout/stderr of the test
   run itself.
6. A fake raising a generic exception yields `INVOCATION_DISPOSITION_UNKNOWN`,
   never `START_FAILED` or `TERMINATED`, publishes no capture result, and
   reconstructs as `RUNNER_CAPTURE_RESULT_UNKNOWN`.
7. Invocation count is exactly one for every completed path and at most one for
   every crash path.
8. `CodexExecRunner.__call__` and `_TRUSTED_CODEX_INVOKE` are unchanged, and a
   bridge callable passed to `route._trusted_live_runner` is rejected.
9. `observe_final` / `observe_workspace` return only closed tokens, produce
   `UNCHANGED` for an unmodified baseline workspace, and are proven not to touch
   stdout.
10. A complete capture with `UNCHANGED` workspace resolves to
    `RUNNER_CAPTURE_NEGATIVE`, not `RUNNER_CAPTURE_FINALIZED`.
11. Runtime digest mutation at each of the four checkpoints fails at the
    specified boundary.
12. The workspace baseline is a retained synthetic fixture, and no test or
    fixture asserts that it is authority-bound or that the resulting
    `CHANGED`/`UNCHANGED` token is verifiable public evidence.
13. The fake preparation is proven to be the only preparation reachable: no test
    path writes an `auth.json` or any credential byte.
14. The maximum verified claim remains exactly
    `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`, and no test or fixture
    asserts runtime authority over the bridge source.

Fixtures for expected public bytes are literal, independent of the production
serializer. Mutation tests recompute otherwise-valid digest links so they
exercise semantic verification rather than stale hashes.

## Affected Surfaces if Later Implemented

The smallest credible offline tranche may add only:

- one new bridge module in
  `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/`; and
- one focused test file beside it.

`gate3_route_v2_codex.py`, `gate3_final_message_runner_integration.py`,
`gate3_final_message_actual_capture.py`, their tests, schemas, manifests, owner
pins, promotion state, `PLAN.md`, memory and all evidence paths remain unchanged
unless a separate design and authorization expands that scope.

## Decisions Applied

The eight questions raised by the pre-decision baseline are closed. They are
recorded here as decisions, not as open items, so that a later reader does not
reopen them by accident.

| # | Question | Decision |
| --- | --- | --- |
| 1 | claim `START_FAILED` from an unattributable exception? | No. Conservative mapping stands; the consumed ordinal and the retry ban are the accepted cost. A typed pre-launch boundary is a separate design. |
| 2 | private preparation inside `invoke()` or before `run()`? | Inside `invoke()`, **as the production direction only**. The first tranche fakes preparation and writes no credential bytes. |
| 3 | timeout `returncode` — drop or extend the schema? | Drop it. No schema extension in the first tranche. |
| 4 | is the runtime-subject gap acceptable? | Acceptable **only** for a mapping-only tranche that claims no runtime authority over the bridge source. It is not acceptable for production wiring. |
| 5 | where does `CHANGED`/`UNCHANGED` derivation live? | Comparison logic in the observation callback. Authority binding of the baseline was the intended answer but is **not expressible** against the merged `RuntimeAuthority`; the first tranche uses a retained synthetic fixture and claims no evidence-profile derivation for that axis. |
| 6 | forward stderr into the unread field, or set it empty? | `stderr = b""`. Never forward an unused sensitive value. |
| 7 | is convention plus tests enough for the `repr` hazard? | Enough for the offline tranche; a structural non-`repr` boundary is required before production wiring. |
| 8 | are the two execution paths provably exclusive? | Not today. Machine-enforced exclusivity at the capability/authority layer is required before production wiring. |

## Residual Open Items for the Exact-Digest Reviewer

These are not owner decisions; they are the places where this design is most
likely to be wrong and should attract the most scrutiny:

1. Whether `INVOCATION_DISPOSITION_UNKNOWN` genuinely covers every post-launch
   exception shape `_run_contained` can produce, including the Windows job-object
   and gate-file paths.
2. Whether the mapping-only tranche can be reviewed at all without a stated
   runtime binding, or whether Finding 3's Option 1 must land first.
3. Whether the pre-seal credential-residue tension (evidence retention versus
   credential hygiene) has a resolution that does not require reordering the
   merged state machine.
4. Whether a workspace-baseline authority can be expressed without leaking
   artifact identities into public evidence, and whether it can be added without
   reopening the merged integration contract digest.

## Production-Wiring Preconditions

Production wiring is blocked until **all** of the following land, each with its
own design and authorization:

1. a runtime binding for the bridge source (`bridge_source` in
   `RUNTIME_SUBJECTS`, or relocation into a runner-covered module);
2. a pre-seal credential-residue recovery contract defining locator, durable
   recovery authorization, profile linkage and pre-seal removal policy;
3. a structural non-`repr` boundary for fields holding real stdout;
4. machine-enforced exclusivity between `CodexExecRunner.__call__` and the
   bridge; and
5. a workspace-baseline authority — schema, canonicalization, private/public
   linkage, and publication of the binding digest without leaking artifact
   identities — since the workspace axis is an evidence-profile discriminator.

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, old-pair reuse, retry, replacement, staging, commit, push, MR, merge,
manifest update, owner-pin update or promotion. **Design approval is not
credential, preflight or live authority.** Production wiring requires its own
separate authorization and the five preconditions above, and every later
transition requires explicit approval.
