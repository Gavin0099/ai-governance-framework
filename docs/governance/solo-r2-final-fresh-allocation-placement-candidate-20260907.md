# Solo R2 final fresh disposable allocation and placement candidate

Status: CANDIDATE / NOT REVIEWED / NOT OWNER ADOPTED / NOT IMPLEMENTED
Baseline commit: `609d8b1eddd8b1c6eeed707add3218dfb6a8cb17`
Source: explicit main-session owner direction to prepare this candidate only.
The conversation is the source of proposed intent, not an independently witnessed signature.

## Problem, scope and target outcome

The existing replacement profile and launcher bind an already-used evaluation, Pair and custody namespace. They cannot faithfully represent a final fresh allocation by rerunning Phase A or changing caller labels. The collector allowed-change repair is committed, but does not authorize another experiment.

DONE = one reviewable candidate defining the final allocation, fixed placement, history preservation, authority dependencies, minimal consumer changes, negative tests and open prerequisites; publish exact document identity and STOP for review.

Current writing scope is this document and necessary canonical memory/evidence. No creation, implementation, launcher edits, runtime, commit or push is authorized by drafting it. Review ACCEPT is not owner adoption. Adoption of these bytes would authorize only the disposition/allocation/placement described here; each operational stage still needs its separate authorization.

## Current repository truth

- `governance_tools/solo_r2_disposable_profile.py:18-28` fixes the prior replacement ledger, binding, runtime root and committed allocation documents.
- `governance_tools/solo_r2_disposable_binding.py:479-516` verifies the fixed path, exact genesis/evaluation and binding bytes; path membership alone is insufficient. Its creation path rejects occupied publication targets.
- `governance_tools/solo_attempt_ledger_v2.py:884-910` dispatches replacement appends through exact `ReplacementLedgerBinding` type and rechecks the prefix; it rejects historical cost-extension authority on this branch.
- `governance_tools/solo_r2_pair_creation.py:739` and `governance_tools/solo_r2_disposable_execution.py:95` select the previous fixed replacement paths. `governance_tools/solo_r2_lifecycle_integration.py:497-499` passes the binding to the writer.
- `artifacts/experiments/solo-r2-replacement-disposable-launcher-20260906/controller.py:24-25` names the existing evaluation/Pair. Its `launch.ps1` pins controller, manifest and dependencies. These are historical entrypoint identities, not final-run defaults.
- Collector fix `609d8b1e` permits only `queue_range.py` and `test_queue_range.py`; targeted and independent tests each passed 54 cases. Evidence: `memory/evidence/solo-r2-collector-allowed-change-fix-20260907/review.json`. This does not establish the historical first throw site or reclassify the terminal.
- Proposal-time architecture preview used `architecture_impact_estimator.py` with the same existing binding file as before/after, scope governance, rules common: medium risk, review-required, architecture-review evidence. This is provisional routing of an unchanged surface, not validation of an implementation diff.

## Preserved history and proposed disposition

Both following ledgers were read-only rehashed at drafting; each has five events, one initiated Attempt and one terminal. Preserve their entire bytes, not only these digests.

| Historical identity | First disposable | Previous replacement disposable |
| --- | --- | --- |
| Evaluation | `1ebfbc48-d2fe-459d-bab7-b9fd75a5810b` | `8e3fb9fe-d94b-45d5-897c-3a3e75849bd8` |
| Pair | `747c09b2-56d0-42d0-bc34-d505e23e311e` | `eef1c2f5-91d7-4d8d-b765-251340f35d67` |
| Ledger under `artifacts/evidence/` | `solo-r2-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson` | `solo-r2-replacement-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson` |
| SHA-256 | `649b2d40c25460647247601ea18e7f2465a07280d58fad8ff7e96c003e0a0836` | `33e291c2018aabaa004ca7998ee87a5cbfefefc81b53e77374ae694c1e42f3d8` |
| Existing outcome | `HARNESS_FAILURE / TERMINAL` | `UNCLASSIFIED / TERMINAL` |

On exact-byte adoption, record both evaluations/Pairs as PRESERVED / NO_FURTHER_ARM / NOT_COMPLETE_AB. This is an owner disposition alongside historical evidence, not an invented ledger terminal event. Do not mutate any ledger, classification, Attempt count, trace, output, failure record, Phase A state, key, seal, checkpoint, payload-pin adoption or readiness evidence. Do not migrate, reset, retry, run the remaining arm, or reinterpret either failed attempt as unconsumed. The original and earlier replacement v2 evaluations also remain untouched.

## Final allocation and hard stop

Propose a bounded additional exception to the already-adopted disposable allocation decisions, not reuse of their consumed allowance:

- Exactly one additional final fresh disposable evaluation and one dedicated ledger.
- Exactly one new `R2-SHAKEDOWN` Pair and two fresh-context arm Attempts, one per arm, not two retries of one arm.
- No transfer or pooling of unused historical capacity; no generic new-ledger capability.
- If this final run cannot complete because of another newly discovered harness/infrastructure defect, STOP and reassess cost/benefit. No further replacement is automatically authorized. Repair capability, remaining slots and STOP do not confer another allocation.

`ATTEMPT_CEILING_BREAKDOWN` is per ledger, not a global counter. Two historical initiated disposable Attempts plus up to two final arms can total four across these three ledgers. That aggregate limit comes from owner allocation, not the per-ledger schema. Implementation must reject a second final creation, including after an interrupted publication; never delete occupied targets and recreate to regain allowance.

## Proposed sole placements

Repository root is exactly `D:/ai-governance-framework`. These paths are proposed, not adopted or provisioned. All four new namespace roots below were absent at drafting; this is not proof of later availability or acceptable ACLs.

| Purpose | Exact path |
| --- | --- |
| Dedicated ledger | `D:/ai-governance-framework/artifacts/evidence/solo-r2-final-disposable-mechanism-shakedown-20260907/attempt-ledger.v2.1.ndjson` |
| Independent genesis binding | `D:/ai-governance-framework/memory/evidence/solo-r2-final-disposable-mechanism-shakedown-20260907/genesis-binding.json` |
| Launcher directory | `D:/ai-governance-framework/artifacts/experiments/solo-r2-final-disposable-launcher-20260907` |
| Runtime custody root | `D:/r2-final-disposable-shakedown-20260907` |

Within the sole runtime root, controller is `controller/`; use `consumer/`, `materialization/`, `execution/`, `scoring/`, `keys/`, `commitments/` and `temp/` for the existing custody roles. Phase A state is `phase-a.json`; the fresh controller key is `keys/controller-key.json`; the order commitment is `commitments/sealed-package-digest.commitment`. Pair-derived filenames are resolved only after actual creation. No evaluation ID, Pair ID, key, genesis digest, order seal or payload pin is assigned here.

Reject caller-selectable paths, substitutions, aliases, reparse points, hardlinks where forbidden by existing custody rules, protected-root overlap and occupied create-once targets. Existing historical roots are never fallback locations. Preserve historical create-once evidence; any later explicitly authorized archive uses same-volume rename, not deletion/overwrite. Archiving never restores a consumed allocation.

The dedicated Codex HOME is a separate operational prerequisite, not a newly authorized setup action. Existing HOME `C:/Users/daish/.codex-r2-replacement-canary` is only a possible authentication/runtime facility: this candidate does not attest its current cleanliness or authorize copying credentials. Before reuse, prove native isolation and E02 fresh-context exclusion of prior-arm conversations/artifacts; otherwise obtain separate bounded HOME disposition. No historical controller state or readiness object may be imported through it.

## Shared materials and instance-bound authority

Reuse exact committed input authority at `d4d8e0f6b41d7c1837edd70f77214212d99ae372:artifacts/experiments/solo-r2-disposable-input-definition-20260906/input-authority.owner-adopted.json`, SHA-256 `5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb`. Resolve its exact task, reused rubric, snapshot subtree, oracle, reference repair and qualification bytes. Do not reserialize or refreeze those materials. Repository identity comes only from `base_snapshot.source_repository`.

Reuse schema `solo_attempt_ledger.v2.1@sha256:ced964f9166aa59a878faa3afdd96c19fe8accaf60a2788c4aaf5a8dbb4680ab`, protocol SHA-256 `1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff`, execution-contract SHA-256 `3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea`. No new schema or cost model is proposed.

After adoption, the independent final genesis-binding record must reference this candidate's externally resolved exact adopted SHA-256 for both allocation and placement, plus verify its committed owner-adoption record. Do not embed a self-referential hash here, derive authority from mutable HEAD, or substitute old allocation digests. Actual genesis bytes/digest/schema/input/evaluation must be verified before Pair publication; retain the creation-produced expected binding identity in owner custody rather than trusting an arbitrary read-back file as authority.

Do not inherit old Pair-specific payload pins, execution authorization, live readiness, checkpoints or unavailable-cost closure. Existing constrained cost representation capability remains distinct from old instance-bound permission. Final-run default retains ordinary numeric cost validation and no cost-extension authority. A required unavailable metric may still require separate authority before lawful terminal append; no zero, estimate or invented total is permitted. This known limitation is not repaired or generalized here.

The disposable task has been exposed previously; fresh arms do not make the task pristine. E02 requires fresh application contexts without prior-arm artifacts/conversation; provider/cache equivalence remains unclaimed. Do not expose Grimm or treat this as Grimm evidence.

## Boundary and creation ordering

1. Candidate review, separate exact-byte owner adoption and separately authorized scoped commit.
2. Separately authorized minimal production implementation, isolated tests, independent review and commit; refresh R1 only if its bound modules actually change.
3. Separately authorized final launcher wiring/pins against reviewed committed consumers, including the collector repair. Preserve the historical launcher. Static verification is not real readiness.
4. Separate real creation authorization: recheck current identities, fixed custody, historical preservation and vacant targets; only then create the fresh custody key and evaluation ID. Create-once genesis/binding publication and exact verification precede Pair publication. Pair seal/commitment must bind the new IDs and new key.
5. Generate a new canonical Pair-specific OwnerPayloadPin candidate from measured payload bytes; STOP before readiness. Separate owner adoption must cover its entire canonical record, even if executable bytes match an old pin.
6. Separately authorized readiness revalidates current payload, HOME/auth, ledger/genesis, frozen inputs, consumer pins and quiescence, then pauses with live same-process handoff, Attempt 0 and exposure NONE. It does not exit into a resumable JSON claim.
7. Only separate one-use owner execution authorization may admit/expose arms. No second readiness invocation, implicit retry, old-state migration or cross-process resume. Oracle, scoring and unblinding remain separately controlled.

## Required implementation allowlist and concrete dependencies

This list bounds a future proposal for implementation; it authorizes no edits now. Preserve historical constants/entrypoints and avoid a generic registry. A verified closed final binding must determine path plus genesis/evaluation/authority; accepting a path from a set is insufficient.

| File | Minimum dependency-driven change |
| --- | --- |
| `governance_tools/solo_r2_disposable_profile.py` | Add final-only placement and committed adoption pins without replacing prior pins. |
| `governance_tools/solo_r2_disposable_binding.py` | Verify final adoption, fixed custody, one creation and exact genesis binding; collision checks include both failed disposable evaluations and existing v2 evaluations. |
| `governance_tools/solo_attempt_ledger_v2.py` | Route final append only through the verified final binding; retain schema/cost/link/prefix protections and old writer behavior. |
| `governance_tools/solo_r2_pair_creation.py` | Carry final binding to fresh Pair creation with exact authority-derived inputs/custody. |
| `governance_tools/solo_r2_disposable_execution.py` | Attach using final ledger/binding rather than the previous Boolean old/replacement path selection; preserve collector fix, pre-Attempt checks and live handoff. |
| `governance_tools/solo_r2_lifecycle_integration.py` (conditional) | Only binding pass-through if the existing pass-through cannot carry the final verified binding; no lifecycle semantic change. |
| `tests/test_solo_r2_disposable_binding.py`, `tests/test_solo_r2_replacement_binding.py`, `tests/test_solo_r2_disposable_execution.py` | Direct synthetic binding/creation/attach and negative regression coverage; no real allocations or arms. |
| Final launcher directory: `controller.py`, `launch.ps1`, `manifest.json`, `test_launcher.py` | Subsequent launcher slice only: final authority, fixed roots, creation state/genesis custody and dependency hashes. Bind runtime-generated final IDs after creation; never copy old hardcoded IDs/pin adoptions. Preserve staged creation, readiness pause and exact single-use EXECUTE. |

Any additional file requires a concrete dependency and scope decision first. Exclude `external_tree_inventory_guard.py`, its tests, unrelated dirty workflow tests and all other unreviewed work. No materializer, runtime-window, native sandbox or packet redesign. Updating a bound ledger/pair/lifecycle module would require a separate post-implementation-commit R1 refresh; no refresh during this candidate slice.

## Evidence plan and rejection requirements

Use isolated synthetic fixtures and production consumers. Positive case proves exactly one final genesis/binding and Pair, exact frozen input references, and two distinct fresh arms as allocation, without running Codex. Historical ledgers/state remain byte-identical. Keep directly affected old v2/v2.1 regression behavior.

| Negative case | Required result |
| --- | --- |
| Old binding with final ledger, or final binding with either old ledger | Reject before write. |
| Wrong genesis, evaluation ID, Pair ID, decision/adoption digest, schema or input authority | Reject at first applicable consumer. |
| Both callers agree on an incorrect repository | Reject against frozen source repository. |
| Historical evaluation ID collision or old key/seal/checkpoint/Phase A state | Reject; no migration or inferred final authority. |
| Old launcher/controller/manifest identity presented for final allocation | Reject before final creation/readiness; old launcher remaining callable is not final-run authority. |
| Old payload-pin adoption with identical executable bytes | Reject wrong evaluation/Pair binding. |
| Old cost-extension authority | Reject for final instance; historical validation remains unchanged. |
| Arbitrary/wrong/redirected path, occupied namespace or second final creation | Reject without overwrite, extra allocation or touching old roots. |
| Ledger/payload/dependency drift or reconstructed/consumed live handoff | Reject; no retry or readiness replay. |
| Missing creation/execution authorization; blank, stale or malformed EXECUTE | No creation or Attempt/task exposure, respectively. |

## Open prerequisites and recommended next tranche

- Independent review and exact-byte owner adoption of this allocation/placement remain pending. Candidate text is not operative authority.
- New paths are proposed and currently absent; custody ACLs, link conditions and create-once capability must be rechecked during authorized preparation. Dedicated HOME reuse/isolation is not yet proven for fresh contexts.
- Minimum production implementation and launcher binding have not occurred. Later reviewed committed revisions, genesis identity and new Pair-specific payload adoption do not yet exist.
- Cost-extension permission is not inherited; missing measurement remains a conditional terminalization risk. The separate child missing-Python observation is not established as the historical MaterializationError cause and is not turned into a repair task here.
- Next tranche is review of these exact candidate bytes, then owner adoption/local durability if separately authorized. Do not start implementation or creation automatically.

Non-goals: new schema/cost model, old ledger/state edits, retry, remaining-arm execution, generic ledger/launcher framework, durable resume, frozen input changes, Grimm, Formal, A1-A6, unrelated hardening, commit/push or live execution in this slice.

Claim ceiling: CANDIDATE ONLY; no enforcement, admission or full A/B success is claimed. Intended experiment remains NON_COUNTED / SOLO_CONTROLLED / MECHANISM_SHAKEDOWN_ONLY / DECISION_SUPPORT_ONLY. It neither constitutes nor replaces E12 qualification shakedown, authorizes A1-A6 progression, nor proves Skill effectiveness. STOP after exact identity reporting.
