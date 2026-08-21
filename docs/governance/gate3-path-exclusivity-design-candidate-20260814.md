# Gate 3 Machine-Enforced Path Exclusivity Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-14

Base: `main@d937d59e4573e365461e2736d10efa8942fdd5be` (merge of PR #68)

Scope: making the routes that reach the contained command structurally
exclusive — group B-2 of the five production-wiring preconditions

## Problem

The accepted bridge design records that the two execution routes are separated
only by caller discipline, and that this "is not a property a verifier can
check". Today the bridge does not call the runner at all — it takes an injected
callable — so exclusivity holds trivially in the offline tranche. Production
wiring is what breaks it: a wired bridge becomes a second route to the same
contained command, and a second undeclared execution is exactly what the launch
ordinal exists to prevent.

## Current Repository Truth

Verified against merged sources at the base commit; field and caller
inventories are quoted from the code.

1. `_run_contained` has **three** production callers, not two:
   - `_native_probe` (`gate3_route_v2_codex.py:589`), reached through the
     injectable `Probe` alias (`:450`), used by `_measure_preflight` (`:618`)
     and `main` (`:1060`);
   - `CodexExecRunner.__call__` (`:832`);
   - the bridge would become the third at production wiring; it is not one now.
2. `CodexExecRunner.trusted_capability()` (`:776`) builds the capability by
   calling `route._trusted_live_runner(execution_identity=…, preflight=…,
   invoke=self.__call__)`.
3. `route._trusted_live_runner` accepts an `invoke` only when
   `invoke.__func__ is gate3_route_v2_codex._TRUSTED_CODEX_INVOKE`, the owner
   type is exactly `CodexExecRunner`, the module file digest equals
   `execution_identity["runner_sha256"]`, and the owner's own identity and
   preflight match.
4. `TrustedLiveRunner` is token-guarded (`_LIVE_RUNNER_TOKEN`) and refuses
   subclassing via a raising `__init_subclass__`.
5. Live admission in `gate3_route_v2.py:1672` requires
   `type(runner) in {TrustedLiveRunner, TrustedLiveABArmRunner}` and revalidates
   the runner against the measured preflight.
6. **None of that touches `RuntimeAuthority`, the integration contract bytes or
   the public-chain oracle.** The admission gate is keyed on capability type and
   measured preflight; the integration coordinator has no knowledge of it.
7. Under contract v2 the launch ordinal is consumed by
   `CapturePublisher.authorize`, before `invoke()` is called.

## Decision: gate `_run_contained` itself, with two disjoint capability classes

The first revision said "the bridge receives a one-shot capability" and left the
other routes alone. That does not produce exclusivity, for three reasons found
in review and accepted here:

- `trusted_capability()` can be called repeatedly, so a new capability living
  **beside** a re-mintable `TrustedLiveRunner` leaves two action routes;
- provenance was bound to `_TRUSTED_CODEX_INVOKE = CodexExecRunner.__call__`,
  which returns `route.SyntheticResult` — the bridge needs `_ContainedResult`,
  so that identity is the wrong subject entirely;
- `Probe` is a bare `Callable` alias, so an action capability passed where a
  probe is expected fails, if at all, only by accident at call time.

**`_run_contained` is therefore made unreachable without presenting a
capability, and there are exactly two disjoint capability classes.** A route is
not excluded by asking callers not to take it; it is excluded by making the
primitive refuse it.

| Capability class | Admits | Minted by | Lifetime |
| --- | --- | --- | --- |
| action | the action command envelope | constructed inactive by the codex module; **armed** by the coordinator with the activation `authorize()` returned | one use, invalidated when the coordinator invocation ends |
| probe | a closed inventory of probe envelopes | the preflight path | its own lifetime; never an action route |

The two classes are structurally disjoint: an action capability presented where
a probe is expected is **rejected at admission**, and the reverse likewise. That
closes the `Probe` alias warning structurally instead of relying on a
coincidental `TypeError` at call time.

### Class alone is not enough: capabilities bind an execution envelope

A previous revision stopped at the class distinction. That is insufficient,
because both classes still reach a primitive accepting arbitrary `command`,
`cwd` and `env`:

> probe capability + action command → `_run_contained`

The class differs; the executed command does not. It also proposed binding the
action capability to `command_contract_sha256`, which is wrong: that digest
covers the command **template and Windows guard contract**, not the argv that
actually runs. The real argv carries a dynamic schema path, a dynamic final
path and an optional `--model`.

**A capability therefore binds an execution envelope, and the gated entry
verifies the whole envelope before running anything.**

| Envelope component | Action | Probe |
| --- | --- | --- |
| executable | exact executable digest from the measured preflight | same |
| argv form | the canonical argv with dynamic arguments replaced by their derived roles — `<schema_path>`, `<final_path>` — and `--model` present or absent as the bound arm requires; the presented argv must reproduce exactly from that form plus the run's fixed paths | one entry of a closed probe inventory |
| cwd | the derived private workspace role, not a free path | the derived preflight root role |
| environment | see below — the projection digest alone is insufficient | same |

**The environment projection cannot carry this binding.**
`_environment_projection_sha256` maps `CODEX_HOME` to the fixed string
`"isolated_private_home"`, so the correct private home and any other value
produce the same digest. Binding to that projection would prove nothing about
which home was used.

The envelope therefore binds the **derived role values themselves**, as private
runtime checks requiring no new public authority field:

- `CODEX_HOME` equals the exact private home derived for this run, compared by
  object identity rather than by string;
- `cwd` equals the derived workspace for the action envelope, or the derived
  preflight root for a probe envelope;
- the schema and final paths appearing in argv resolve to the same run's
  derivation, not merely to well-formed paths;
- the probe inventory is closed at exactly its canonical forms — version, root
  help and exec help — each bound individually.

**The projection digest does not prove key inventory either.**
`_environment_projection_sha256` builds its projection from a fixed set of known
keys and never enumerates the environment's own keys, so an added
`UNEXPECTED_PRIVATE_KEY` leaves the digest unchanged. An earlier revision
credited it with that property; that was wrong.

The static envelope therefore carries and checks the **exact environment key
inventory** itself. The projection digest is retained only for the value
normalization it already performs, and is evidence of neither the key set nor
which home was used.

Two consequences the previous revision got wrong:

- **the probe is not one command.** Version, root help and exec help all run
  through `_native_probe`, so "a different probe constant" cannot describe it. A
  probe capability binds a **closed inventory** of canonical argv forms, and any
  form outside the inventory fails closed.
- **canonicalization must be specified, not assumed.** Argv is compared as an
  exact sequence after role substitution; no reordering, no normalization of
  flag spelling, no partial match. A duplicate, unknown, reordered or
  non-canonical form is a closed failure with no execution.

The mutation tests must exercise this directly in both directions: an action
argv presented under a probe capability fails closed, and a probe argv under an
action capability fails closed.

## `_native_probe` is out of scope, and why

The accepted design says "two callable routes". There are three. The boundary
must be ruled rather than inherited:

| Caller | In scope for exclusivity | Reason |
| --- | --- | --- |
| `CodexExecRunner.__call__` | yes | executes the action command under live authorization |
| bridge (once wired) | yes | would execute the same action command |
| `_native_probe` | **no** | executes a preflight probe, not the action command; consumes no launch ordinal; produces no capture, seal or public chain |

The probe is nonetheless constrained, so that "out of scope" does not become a
hole:

- it may not be reachable through the action capability, and the action
  capability may not be reachable through the `Probe` seam;
- `Probe` is currently a bare `Callable` alias, so an action capability passed
  where a probe is expected would fail only by accident at call time, if at all.
  The probe seam must **reject a non-probe capability at admission**, before any
  call, and the action seam must reject a probe capability the same way. The two
  classes are disjoint types, not two spellings of `Callable`;
- a probe invocation must not be able to consume or observe a launch ordinal.

If a future change gives the probe any action-command capability, that change
reopens this group.

## Capability acquisition

The bridge must not import and call `_run_contained`, and must not be handed a
bare callable that happens to reach it.

| Element | Decision |
| --- | --- |
| what the bridge receives | a one-shot contained-execution capability object, not a callable and not the runner |
| construction | only through the codex module, guarded by the provenance predicate `_trusted_live_runner` already applies — exact owner type, exact `__func__` identity, module digest equal to the measured `runner_sha256` — but bound to the **new raw-contained canonical identity**, not to `_TRUSTED_CODEX_INVOKE`, which names a method returning `SyntheticResult` |
| token semantics | **extend the existing `_LIVE_RUNNER_TOKEN` mechanism rather than introducing a second token.** A parallel token would create two independent notions of "trusted", and a reader would have to know which one applied |
| subclassing | refused, as `TrustedLiveRunner` already refuses it |
| what the honest limit is | a private module token is an API structural constraint, not a boundary against a hostile in-process caller that reaches module privates directly. This is the same limit `TrustedLiveRunner` already carries; citing it as precedent does not upgrade the property |

The bridge's existing `make_invoke(prepare=…, run_contained=…)` shape does not
survive production wiring unchanged: `run_contained` becomes the action
capability, armed by the coordinator, and the bridge's job is to consume it
exactly once and map the resulting `_ContainedResult`. The mapping,
disposition and privacy behaviour accepted in the P3 tranche are unaffected.

## Launch-ordinal alignment, and why the coordinator is in scope

There must be exactly one notion of "once", not two.

The first revision put the capability outside the integration module and said
its single use was "subordinate to" the consumed launch ordinal. That is not
implementable from outside: **only the coordinator knows that
`CapturePublisher.authorize()` succeeded, and only the coordinator knows when
the invocation ended.** A capability armed elsewhere would have to guess both.

### Lifecycle: construct inactive → authorize → arm → use → invalidate

That is the only lifecycle this document describes. Earlier revisions also said
the coordinator "mints" the capability and that "no capability exists before
`authorize()`"; both are withdrawn. A capability exists before authorization —
it is simply **not armed**, and an unarmed capability cannot reach the contained
command.

### Activation is produced by the authorize transaction, not re-derived

The previous revision let anyone holding a capture store arm a capability by
reopening the published authorization. That does not work, and the reason
generalizes:

- `CreateOnceStore` is an in-memory object with a public `files` mapping. A
  caller can build a second store and publish identical authorization bytes, so
  reopening proves only that *some* caller-selected store holds those bytes —
  not that the official launch ordinal was consumed.
- Worse, provenance construction is not create-once. After capability A is used
  and dies, capability B can be constructed from the same valid runner and armed
  from the still-present authorization. The capture authorization's create-once
  property stops a second *authorization*; it never stopped a second
  *capability* adopting the first one. That is retry and replacement, reopened.

**`CapturePublisher.authorize()` therefore returns the activation.** It is not a
digest and not a store; it is a one-shot object that can exist only because that
create-once transaction succeeded, in that publisher instance, exactly once.

One-shot alone is not enough. An activation that only limits *count* still lets
authorization A arm a provenance-valid capability bound to action B. The
activation must therefore **bind what it authorizes**.

### Issuance dataflow

`publisher.authorize(self.bindings)` cannot compute an envelope digest:
`CaptureBindings` does not contain one, and the publisher has no runner, no
inactive capability and no run-derived paths. The issuance API is therefore
fixed rather than assumed:

```
result = publisher.authorize(bindings, activation_binding=<sealed binding | None>)
```

| Element | Rule |
| --- | --- |
| `activation_binding` | a sealed object derived from the **provenance-validated inactive capability**; the caller cannot construct one from a bare digest |
| instance identity | the activation **retains the exact capability object** and `arm()` requires `candidate is that object`. A nonce is not sufficient on its own: `copy.copy(capability_a)` need not copy the nonce, so a shallow clone can hold the same nonce reference and impersonate the original under any field- or nonce-equality check. Object identity cannot be forged that way |
| publisher check | the binding's `CaptureBindings` digest, action and arm must equal the `bindings` argument exactly; a mismatch is a closed failure and nothing is published |
| return, with a binding | a closed result `{authorization_digest, activation}`, only after successful publication |
| return, without a binding | a closed result `{authorization_digest, activation: None}` |

**Standalone capture keeps working.** The adapter's existing callers have no
runner capability; they pass no `activation_binding` and receive the
digest-only result. Those paths gain nothing and lose nothing, and the design
does not assume every `authorize()` has a runner envelope.

### Two layers: static envelope, runtime identity

An earlier revision required the envelope digest to include filesystem object
identity while also requiring the inactive capability to exist before
authorization. Those cannot both hold: private preparation happens **inside**
the bridge invocation, after `authorize()` and after arming, so at binding time
the workspace and `CODEX_HOME` may not exist yet.

| Layer | When | Contents | Bound by |
| --- | --- | --- | --- |
| static envelope | before authorization | run identity, trusted root anchor, relative role derivation, canonical argv form, environment-key policy | the activation binds this digest |
| runtime identity admission | after preparation, before `_run_contained` | the actual workspace, `CODEX_HOME`, schema and final paths resolve to the static derivation, with no disallowed replacement or reparse point | a use-time fail-closed check |

**Object identity is a use-time check and must not be described as bound at
authorization time.** The activation binds the static envelope; the runtime
admission is what makes the presented objects the derived ones.

**Residual TOCTOU, retained in the claim ceiling.** A window remains between the
runtime identity check and the actual process launch: the launch is not
handle-bound, so a substitution in that window is not excluded. The admissible
claim is therefore *"the presented objects matched the derived ones at the last
checkpoint"* — **not** that the process used the same filesystem objects.
Closing that window would require a handle-bound launch, which is not in this
group.

### Activation mechanics

| Property | Mechanism |
| --- | --- |
| obtainable only from a successful `authorize()` | the activation type has no public constructor. It is issued through a **publisher-owned private factory in the capture adapter** — deliberately *not* the route module's `_LIVE_RUNNER_TOKEN`, which lives in another module and answers a different question. This is an issuance guard, not a second "trusted runner" vocabulary, and the two must not be conflated |
| arms exactly one capability | a single lock covers bind-verify **and** the consumed-state transition, so the check and the transition cannot interleave |
| **when an attempt starts** | a candidate that is not the exact capability type is rejected at **admission**, and that is *not* an arm attempt — the activation stays usable. Once an exact-typed candidate passes admission, **entering the activation lock is the first attempt**. This matters: without it, a fake object that raises while its fields are extracted would leave the activation usable, contradicting the rule below |
| **a failed arm consumes it too** | from the moment the lock is entered, the first `arm()` attempt consumes the activation permanently, whether it succeeds or fails. Otherwise a mismatched attempt followed by a correct one would be a second arm attempt after the ordinal was already spent — a retry by another name. Concurrent attempts are decided by the same rule: the first to take the lock consumes it, and every other attempt fails closed |
| no caller code runs mid-comparison | all compared values are extracted to primitives before the lock is taken; no property, `__eq__` override or callback of a caller object is evaluated inside it |
| not copyable | `__copy__`, `__deepcopy__` and `__reduce__` refuse on the **activation, the capability and the sealed binding** alike; none of the three can be duplicated, pickled or reconstructed. Clone refusal is normative here, not only a test expectation |
| capability-owned state lock | the capability owns its **own** lock, and every `inactive → armed → used/invalidated` transition happens under it. Two activation locks are independent of each other, so activation locks alone cannot stop two valid activations arming the same capability |
| arming order | the activation consumes itself permanently under its own lock **first**, then calls the capability's locked `try_arm(exact_identity)`. A second activation, however valid, finds the capability non-inactive under the capability lock and fails closed |
| lock ordering | activation lock is always taken before capability lock, never the reverse, so no deadlock is reachable; **no caller code executes inside either lock** |
| a fresh capability cannot adopt an old authorization | arming needs an unconsumed activation, and a second `authorize()` on the same store is refused as already authorized |
| crash after publication, before the return reaches the caller | the authorization is durably retained and **no activation exists**; the state is permanently unknown, no retry, no re-issue. The ordinal is spent and the run cannot proceed |

The fail-closed matrix a later tranche must exercise: activation A arming a
capability bound to action B; a copy, deepcopy or pickle attempt; a second
consume; a substituted activation object; an activation whose static envelope
digest differs from the capability's; and two threads entering `arm()` together
through a barrier, where exactly one must succeed and at most one capability
may become armed.

### Privacy of the new private fields

The capability, the sealed binding and the activation hold private run
derivation, envelope data and any private diagnostic nonce. B-1's structural non-`repr`
boundary is not done, so this group must at minimum avoid **adding** a known
leak path:

- none of the three renders its private fields in `repr`;
- closed errors carry a fixed code and nothing else;
- exceptions, failed assertions and clone rejections emit no path, nonce or
  binding content.

This does not substitute for B-1. It only ensures B-2 does not open a new one.

### The residual limit, stated once and not restated as a guarantee

A caller with module access can construct its own publisher and its own store,
run `authorize()` there, and obtain an activation. Nothing in-process prevents
that, and this design does not claim otherwise.

What it does claim: within the coordinator's own lifecycle there is exactly one
armed capability and one launch, and no *structural* second route exists. What
it cannot claim: protection against a hostile in-process caller, nor that the
launched process used the same filesystem objects that passed the last identity
checkpoint. That is the
same limit `_LIVE_RUNNER_TOKEN` already carries. **Every mechanism in this
document is an API structural constraint, not a security boundary**, and no
later section upgrades that.

A parallel execution mounted that way also leaves no trace in the official
package — which is precisely why the attestation this group deliberately excludes
belongs to production admission.

**The coordinator arms and invalidates the action capability.**

### What this does and does not add to scope

The integration module and its tests **are** in scope: the coordinator gains the
arming and invalidation, and its shape changes accordingly.

What does not change, and what a reviewer should check byte-for-byte:
`RuntimeAuthority` fields, the v2 contract bytes, `VERIFIABLE_CONTRACT_VERSIONS`
and every oracle literal. Coordinator dataclass fields are not part of the
contract, so admitting the coordinator to scope does not reopen it. **A change
to any authority field, contract byte or oracle literal means this design chose
wrongly and must be re-reviewed, not patched.**

## Scope

### In scope

- one action capability type plus one disjoint probe capability type, their
  provenance-checked construction and their command-purpose binding;
- the bridge consuming a capability instead of a bare callable;
- the `_native_probe` boundary and its constraints;
- launch-ordinal subordination;
- affected surfaces and a focused offline evidence plan.

### Explicit non-goals and prohibitions

- No `RuntimeAuthority` field, contract bytes change, contract version or oracle
  recomputation. If the implementation finds one unavoidable, that is scope
  expansion and needs its own authorization.
- No claim that public evidence shows which path executed.
- No production wiring, credentials, preflight, subprocess, network or live
  execution.
- No change to the P3 mapping, disposition or privacy behaviour.
- No second token vocabulary alongside `_LIVE_RUNNER_TOKEN`.
- No reuse, retry, replacement or reinterpretation of the consumed pair.

## DONE for a Later Offline Implementation Tranche

`DONE = Using injected fakes and no subprocess, `_run_contained` is unreachable
without an armed capability whose execution envelope matches what is presented; the action and probe capability classes are disjoint and
each is rejected at the other's admission point before any call; provenance binds
to a raw-contained canonical identity returning _ContainedResult rather than to
`_TRUSTED_CODEX_INVOKE`; `CodexExecRunner.__call__` cannot arm a capability and
fails at `_run_contained` without one; the coordinator arms the action capability with the
activation returned by CapturePublisher.authorize() and invalidates it in a
finally around the invocation; neither a used capability nor a fresh replacement
capability can be armed again for the same run; the capability publishes nothing; the activation binds the static envelope and retains the exact
capability object, arming only a candidate that `is` it, while object identity
of the filesystem targets is admitted at use time; the first arm
attempt consumes the activation whether or not it succeeds; the static envelope
checks the exact environment key inventory itself; and every `RuntimeAuthority` field, contract byte and
oracle literal is byte-identical to the merged values.`

This is a proposed later tranche, not current implementation authority.

## Focused Offline Evidence Plan

1. `_run_contained` refuses every call that presents no capability, including a
   direct `CodexExecRunner.__call__`;
2. the bridge rejects a bare callable where an action capability is expected,
   and the rejection is a type boundary rather than a runtime convention;
3. an action capability is rejected at the probe seam's admission, and a probe
   capability at the action seam's admission — both before any call, neither by
   an incidental `TypeError`;
4. capability construction is refused for a wrong owner type, a `__func__` that
   is not the raw-contained canonical identity, a module digest that does not
   match the measured `runner_sha256`, and a subclass attempt; and the
   activation type has no publicly reachable constructor;
5. `CodexExecRunner.__call__` cannot arm a capability, and cannot obtain an
   activation;
6. no *armed* capability exists before `CapturePublisher.authorize()` succeeds,
   and an unarmed capability presented to the gated entry is refused;
7. the capability is invalidated on every exit path from the invocation —
   normal return, mapped failure, closed error and propagated crash — verified
   by asserting a second use fails after each;
8. neither a used capability nor a freshly constructed replacement can be
   armed for a run whose capture authorization already exists;
9. the capability produces no artifact, no claim and no public byte;
10. the retired direct route is provably retired: `TrustedLiveRunner` can no
    longer admit `CodexExecRunner.__call__` as a live action route, and no
    second token vocabulary is introduced;
10a. a capability presented with an execution envelope that does not match its
    bound envelope fails closed with no execution, in both directions —
    action command under a probe capability, and probe command under an action
    capability;
10b. arming requires the activation returned by `authorize()`; a store holding
    identical authorization bytes arms nothing, an activation arms exactly one
    capability, and a freshly constructed replacement capability cannot adopt an
    already-used authorization;
11. `RuntimeAuthority` fields, contract bytes, `VERIFIABLE_CONTRACT_VERSIONS`
    and every oracle literal are byte-identical to the merged values;
12. the P3 **mapping, disposition and privacy assertions** are unchanged; the
    `make_invoke` interface tests are updated for the capability shape, and the
    design does not claim the P3 test file is untouched;
13. two threads entering `arm()` simultaneously through a barrier: exactly one
    succeeds, the other fails closed, and at most one capability becomes armed;
14. a standalone `authorize()` with no `activation_binding` returns the
    digest-only closed result and yields no activation;
15. an `activation_binding` whose bindings, action or arm differ from the
    `authorize()` argument is refused **before** publication;
16. runtime identity admission rejects a workspace, `CODEX_HOME`, schema path or
    final path that does not resolve to the static derivation, and rejects a
    reparse-point substitution, in each case before `_run_contained` runs;
17. an environment carrying an unexpected key fails the static envelope's exact
    key-inventory check, and the test asserts the existing projection digest is
    unchanged by that key — so the check cannot be quietly delegated back to it;
18. a failed `arm()` consumes the activation: a mismatched attempt followed by a
    correct capability fails closed, and the barrier race resolves to exactly
    one consumer;
19. a freshly constructed capability with fields identical to the bound one
    fails to arm; a shallow copy and a deep copy of the bound capability each
    fail to arm; the capability refuses `copy`, `deepcopy` and `__reduce__`;
20. a copied sealed binding cannot produce an armable replacement, and a
    candidate sharing the nonce but not the object identity fails closed;
21. two activations naming the same capability arm it at most once, verified
    under a barrier;
22. a candidate of the wrong type is rejected at admission without consuming the
    activation, while an exact-typed candidate that fails binding comparison does
    consume it;
23. the capability, sealed binding and activation render no private field in
    `repr`, and no path, nonce or binding content appears in any closed error,
    failed assertion or clone rejection.

## Affected Surfaces if Later Implemented

- `gate3_route_v2_codex.py` and `test_gate3_route_v2_codex.py` — the capability
  gate on `_run_contained`, the raw-contained canonical identity, and the two
  disjoint capability classes
- `gate3_final_message_runner_integration.py` and
  `test_gate3_final_message_runner_integration.py` — **required**: the
  coordinator arms the action capability with the activation returned by
  `authorize()` and invalidates it in `finally`
- `gate3_final_message_runner_bridge.py` and its test — consuming a capability
  instead of a bare callable. The P3 mapping, disposition and privacy behaviour
  is unchanged, but the test file is not: its `make_invoke` interface tests move
  to the capability shape
- `gate3_route_v2.py`, `test_gate3_route_v2.py` and `CodexABArmRunner`'s tests —
  required by the retirement of the direct `SyntheticResult` live route, which
  is itself a scope expansion needing owner authorization

- `gate3_final_message_actual_capture.py` and
  `test_gate3_final_message_actual_capture.py` — **required**: `authorize()`
  currently returns the authorization digest and sets `_may_capture`; it must
  instead return a closed result carrying **both** that digest and the
  activation, and its crash matrix must cover publication-succeeded /
  return-not-delivered. Existing standalone callers pass no
  `activation_binding` and keep a digest-only closed result

The capture **schemas** stay unchanged, and the contract bytes and every oracle
literal stay byte-identical — but the capture adapter's source and tests cannot.
An earlier revision listed the adapter as unchanged; that was wrong.

The oracle module and worksheet, manifests,
owner pins, promotion state, `PLAN.md`, memory and all evidence paths remain
unchanged. **A change to any `RuntimeAuthority` field, contract byte or oracle
literal would mean this design chose wrongly and must be re-reviewed, not
patched.**

## Review Questions

1. Is `_native_probe` correctly out of scope as a *route*, now that it must
   still present a disjoint probe capability?
2. Retiring the direct `SyntheticResult` live route reaches
   `gate3_route_v2.py`, `CodexABArmRunner` and their tests. Is that expansion
   acceptable inside B-2, or should it be its own authorized slice ahead of the
   capability work?
3. Should the bridge receive a capability, or should the bridge be folded into
   the runner so that no cross-module handoff exists at all?
4. Is extending `_LIVE_RUNNER_TOKEN` right, or does a distinct capability
   deserve a distinct token despite the two-vocabularies cost?
5. Is a publisher-issued activation with bidirectional envelope binding the
   right unforgeable step, given it puts the capture adapter in scope?
6. Does changing `make_invoke`'s shape disturb any P3 property that was
   accepted on the basis of that shape?

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, old-pair reuse, retry, replacement, staging, commit, push, MR, merge,
manifest update, owner-pin update or promotion. Group C remains on hold; group
B-1, production-admission authority and production wiring each require their own
separate authorization. Gate 3 remains `NON_SUCCESS`.
