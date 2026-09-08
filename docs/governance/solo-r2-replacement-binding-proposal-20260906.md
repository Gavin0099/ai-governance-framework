# Solo R2 replacement disposable binding proposal

Status: CANDIDATE / NOT REVIEWED / NOT ADOPTED / NOT IMPLEMENTED
Baseline: f75a78eeb32bf79e58a91898d0775fd3f58854b8
Task: REPLACEMENT_BINDING_DESIGN

## Problem and DONE

The adopted replacement allocation is not consumable through production's old disposable placement constants. Reusing the old Phase A state would also reuse instance-bound authority. This proposal describes the smallest explicit replacement binding; it does not establish production compatibility.

DONE = a reviewable proposal specifying fixed placement, authority dependencies, creation ordering, old/new isolation, affected consumers, negative tests and unresolved prerequisites. Stop after drafting and identity recording. No production edits or creation operations are authorized by this document.

## Current repository truth

- `docs/governance/solo-r2-replacement-disposable-owner-adoption-20260906.json`, committed at the baseline, adopts exactly one replacement allocation and two fixed repository paths. Its decision bytes have SHA-256 `bbc12627300df01f0145ba0b76aa75191291b3974ccf95dd1255fb4f031bafd3`.
- Old evaluation `1ebfbc48-d2fe-459d-bab7-b9fd75a5810b` and Pair `747c09b2-56d0-42d0-bc34-d505e23e311e` remain FAILED_MECHANISM_SHAKEDOWN / PRESERVED / NO_FURTHER_ARM. Its five-event ledger SHA-256 is `649b2d40c25460647247601ea18e7f2465a07280d58fad8ff7e96c003e0a0836`. These are historical identities, never replacement defaults.
- `solo_r2_disposable_profile.py` fixes the old ledger/binding/controller paths; `solo_r2_disposable_binding.py` uses them for creation, genesis verification and historical cost evidence. `_existing_evaluations` currently checks the original and first replacement v2 evaluations, not the failed disposable evaluation.
- `solo_attempt_ledger_v2.py::append_event` permits the old disposable path only. `solo_r2_pair_creation.py` routes disposable creation through that writer. `solo_r2_disposable_execution.py::DisposableLifecycle.attach` independently uses old ledger/binding paths and requires exactly GENESIS + PAIR_CREATED.
- `solo_r2_disposable_materialization.py` consumes frozen input authority, not a disposable ledger path. Keep its subtree verification and CONTROL/TREATMENT packet distinction unchanged.
- The old external `controller.py::phase_a` creates a custody key before evaluation creation, then creates genesis, Pair/order seal and Pair-specific payload-pin candidate. Its Phase A state binds the old manifest and instance. Execution consumes a live readiness result; saved JSON is not a resume token.
- Harness repair baseline is `0402b7937cfcfce8af55d50cb56744d8e1a8adfd`. This proposal does not reopen the file_change or exception-handler repair.

## Fixed placement

Repository root is exactly `D:/ai-governance-framework`. The first two paths below are already adopted; remaining paths are proposed here and require exact-byte adoption before use.

| Purpose | Exact path |
| --- | --- |
| Public ledger | `D:/ai-governance-framework/artifacts/evidence/solo-r2-replacement-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson` |
| Genesis binding | `D:/ai-governance-framework/memory/evidence/solo-r2-replacement-disposable-mechanism-shakedown-20260906/genesis-binding.json` |
| Launcher directory | `D:/ai-governance-framework/artifacts/experiments/solo-r2-replacement-disposable-launcher-20260906` |
| Runtime root | `D:/r2-replacement-disposable-shakedown-20260906` |
| Isolated Codex home | `C:/Users/daish/.codex-r2-replacement-canary` |

Under that runtime root, use only `consumer/`, `materialization/`, `execution/`, `scoring/`, `controller/`, `keys/`, `commitments/`, and `temp/`; Phase A state is `phase-a.json`. The new key is `keys/controller-key.json`; its order-seal commitment is `commitments/sealed-package-digest.commitment`. Keep existing Pair-derived checkpoint filenames under the new controller root; never invent a Pair ID in the spec.

Reject arbitrary paths, aliases/reparse points, hardlinks, overlaps with protected roots, and occupied create-once targets. Canonical containment checks apply before writes. No fallback to the old runtime root, ledger, keys, Codex home, state or checkpoint. This document creates none of these directories. Private runtime evidence remains in the contract-governed runtime custody; session/review records remain under repository `memory/`.

## Authority dependency graph

```text
committed replacement decision + its owner-adoption record
  -> exactly one allocation + adopted ledger/binding paths
  -> adopted binding proposal (additional custody/launcher paths)
  -> committed replacement consumers + exact outer manifest
  -> separately authorized creation
  -> new evaluation ID + exact genesis/binding
  -> new Pair ID + new key-bound order seal/commitment
  -> new Pair-specific OwnerPayloadPin candidate
  -> separate owner adoption of canonical pin bytes
  -> current identity checks + quiescence + live readiness
  -> separate execution authorization (outside this proposal)
```

Shared *material* authority remains the exact committed input record at `d4d8e0f6b41d7c1837edd70f77214212d99ae372:artifacts/experiments/solo-r2-disposable-input-definition-20260906/input-authority.owner-adopted.json`, SHA-256 `5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb`. Resolve its exact task/rubric/subtree/oracle/reference-repair identities again. Derive repository only from `base_snapshot.source_repository`; equal caller labels are insufficient provenance.

Reuse the adopted input schema identity `solo_attempt_ledger.v2.1@sha256:ced964f9166aa59a878faa3afdd96c19fe8accaf60a2788c4aaf5a8dbb4680ab`, protocol SHA-256 `1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff` and execution-contract SHA-256 `3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea`. Reuse does not inherit a prior evaluation's readiness, execution or cost-extension authorization.

Keep the existing public genesis schema. In the independent genesis-binding record, `allocation_sha256` and `placement_sha256` both identify the exact adopted replacement decision bytes: that decision carries both authorities. The associated adopted proposal fixes additional custody paths, not a replacement public schema. The consumer must verify the committed owner-adoption record as well as the decision; candidate bytes alone confer no authority. Pin their enclosing baseline commit and exact bytes; do not resolve mutable HEAD or reinterpret old allocation/placement hashes as replacement authority.

## Creation and custody ordering

1. Before creation authorization: static review and synthetic tests only; no UUID, key, allocation directory, ledger or Pair generation.
2. After separate creation authorization: verify committed authority/consumer/manifest identities, fixed paths, protected historical ledger hashes, empty targets, current executable identity and quiescence. No old Phase A state is an input. Reject reused evaluation identities from all existing evaluations, including the failed disposable run.
3. Provision only the proposed new custody roots and isolated Codex home under the separately authorized operational scope. Do not copy old controller/scoring/checkpoint/key state. Authentication availability and ACL validation must be established before runtime use; this proposal neither supplies nor inspects credentials.
4. Generate one fresh controller key only in that authorized operation, after custody target checks and before Pair sealing. The key can precede evaluation ID generation; the order seal and its commitment cannot precede evaluation/Pair IDs. Never import the old key.
5. Generate a fresh evaluation ID at creation, publish genesis and independent binding create-once, then verify exact bytes/length/SHA-256, schema/protocol/contract/input identity and replacement placement/allocation. Carry the expected binding digest through the live creation result and retained owner-custody state, not a fresh untrusted recomputation.
6. Generate a fresh Pair only after genesis verification. Bind it to that evaluation, disposable frozen identities, authority-derived repository and new custody; seal order with the new key. Preserve existing create-once/no-retry rules. Interrupted publication reserves occupied targets and stops; do not clean up and recreate automatically.
7. Generate a new canonical OwnerPayloadPin using the new evaluation/Pair and measured installed payload bytes. Record exact canonical bytes/size/hash and STOP before readiness. Adoption is separate; an old pin must fail even when the executable bytes are identical.
8. On separately permitted readiness entry, validate the newly adopted record and current payload again, exact new Phase A/manifest/genesis/Pair/custody identities, frozen inputs and current host/quiescence conditions. Preserve one-shot RuntimeWindow and live pause/continue semantics; do not recover old readiness JSON. No Attempt or task exposure without separate execution authorization.

## Unavailable-cost boundary

The implementation can represent constrained unavailable metrics, but that capability is not an instance's permission to emit them. `CostAmendmentAuthority` and its adopted historical closure bind the old evaluation, Pair, genesis and four-event prefix. Keep that validator usable for historical verification only; reject it for the replacement and never rewrite its binding.

Proposed replacement default: ordinary available numeric costs, with no cost-extension authority. Do not add extension keys or invoke the old controller evidence root. Existing rules for optional aggregates remain unchanged; do not derive overlapping token totals. If a future failure needs a required metric represented as UNAVAILABLE, stop and obtain a separately reviewed/adopted instance binding before an append requiring it. This is an explicit remaining operational risk, not a reason to invent a general unavailable-cost entitlement now. A missing metric never becomes zero and a STOP never grants retry/replacement.

## Minimal implementation tranche and affected surfaces

Propose one immutable, closed placement binding carried from the verified creation/admission consumer through Pair publication and lifecycle append. It has only the existing disposable placement and this exact replacement placement, not caller-configurable paths or a registry. Preserve old constants and historical validation. New replacement entrypoints explicitly select and verify the replacement authority; they must never obtain it from caller agreement or module-global monkeypatching.

| File/surface | Concrete dependency and limited change |
| --- | --- |
| `governance_tools/solo_r2_disposable_profile.py` | Add only exact replacement authority/placement pins; preserve old pins. |
| `governance_tools/solo_r2_disposable_binding.py` | Verify replacement adoption, fixed custody and genesis binding; carry closed placement; collision check includes failed disposable identity without transferring its cost authority. |
| `governance_tools/solo_attempt_ledger_v2.py` | Permit replacement append only through verified fixed binding matching actual genesis/evaluation; retain existing path/link protection, schema and cost validation. Path membership alone is not authorization. |
| `governance_tools/solo_r2_pair_creation.py` | Thread verified placement through preconditions and append; keep fresh ID/order custody logic. |
| `governance_tools/solo_r2_lifecycle_integration.py` | Minimal optional binding pass-through to ledger append, only if needed by the existing shared writer; no admission/order/terminal semantic change. |
| `governance_tools/solo_r2_disposable_execution.py` | Attach to replacement binding rather than old global paths; verify exact genesis and two-event state; include changed consumers in existing source freeze coverage. Preserve live single consumption and repaired failure handling. |
| New launcher directory `controller.py`, `launch.ps1`, `manifest.json`, `test_launcher.py` | Fixed replacement roots and explicit replacement consumer; retain staged pin adoption, current-payload checks, one-shot readiness and terminal authorization wait. Pin reviewed committed dependencies before launch. No modification or migration of old launcher state. |
| Corresponding existing unit tests and `tests/test_solo_r2_replacement_binding.py` | Synthetic creation-to-attach coverage and negative cases below; all UUID/key/ledger fixtures isolated from real allocations. |

No materializer, packet, runtime-window or native-readiness redesign is proposed. If an additional production file is directly necessary, identify its precise consumer dependency before extending this list. Changes to R1-bound ledger/pair/lifecycle modules create a new post-implementation-commit refresh obligation; no refresh is performed in this design slice. Freeze/pin updates must follow final committed bytes, not pre-commit assumptions.

## Evidence plan and failure paths

Tests must use isolated synthetic roots and exercise real binding consumers; no actual evaluation creation or runtime execution is part of validation. Positive case: exact replacement authority -> one synthetic genesis/binding -> fresh Pair/order seal -> attach to the same authority and frozen subtree; verify old ledgers byte-for-byte unchanged. Retain directly affected existing v2/v2.1 regression checks. Include:

| Negative input/event | Required outcome |
| --- | --- |
| New evaluation + old payload pin, including identical payload bytes | Reject before readiness. |
| New evaluation + old unavailable-cost authority/prefix/receipt | Reject extension; retain old historical validation. |
| New ledger + old genesis binding/digest or old allocation/placement hashes | Reject before Pair creation. |
| New Pair + old Pair checkpoint, old key or order commitment | Reject before attach/Attempt; no seal reinterpretation. |
| Caller supplies old Phase A state or old manifest/state pair | Reject; no migration or fallback. |
| Both callers use the same wrong repository label | Reject against frozen authority source repository. |
| Wrong schema/input/decision/adoption identity, modified committed dependency | Reject before creation/consumption as applicable. |
| Arbitrary/aliased/overlapping path, hardlink, occupied target, duplicate ID | Reject; no writes to protected old paths and no automatic recreation. |
| Genesis/ledger/payload changes between creation, adoption and readiness | Reject stale binding; do not infer readiness from prior evidence. |
| Missing required metric without new cost authority | Stop; no zero, fabricated terminal or automatic retry. |

Also verify that missing creation or execution authorization cannot be bypassed by possessing a valid binding, that second creation cannot consume another allocation, and that a consumed/live-lost readiness object cannot be replayed. Expected test and independent-review evidence is not yet available.

## Open prerequisites, non-goals and claim ceiling

- Review/adopt these proposed custody paths and binding choices; implementation needs separate authorization.
- Verify new home provisioning and native custody conditions at the authorized operational stage. Their availability is not established by path design.
- Implement, test, independently review and commit the bounded consumers; refresh affected R1 pins and outer manifest against committed bytes before real admission.
- Separately authorize creation; after IDs exist, separately adopt the canonical new payload pin. Readiness and execution retain their explicit boundaries.
- A new unavailable-cost binding is conditional on actual need; old historical closure authority is never inherited. This proposal does not guarantee that every future harness failure can be terminalized without a further owner decision.

Non-goals: old state migration, old remaining-arm execution, generic multi-ledger support, retries, new schema/cost model, frozen input edits, Grimm, Formal/A1-A6, oracle/scoring/unblinding implementation, durable resume, platform expansion, push.

Claim ceiling: proposal only. Intended experiment ceiling remains NON_COUNTED / SOLO_CONTROLLED / MECHANISM_SHAKEDOWN_ONLY / DECISION_SUPPORT_ONLY. No production admission, runtime readiness or complete shakedown success is claimed. Next action is bounded review of this candidate; no implementation, commit or execution follows automatically.
