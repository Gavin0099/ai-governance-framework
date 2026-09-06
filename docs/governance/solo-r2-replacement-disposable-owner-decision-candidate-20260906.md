# Solo R2 replacement disposable shakedown — owner-decision candidate

Status: CANDIDATE / NOT REVIEWED / NOT OWNER ADOPTED

## Problem and current repository truth

The first disposable evaluation reached task exposure and real tool use, then
failed because the launcher catalog omitted permitted file_change. Its missing
post-exposure terminal was subsequently closed under the adopted cost amendment.
Failure accounting is preserved; this proposal does not erase that initiated arm.

- Failed evaluation: `1ebfbc48-d2fe-459d-bab7-b9fd75a5810b`.
- Existing Pair: `747c09b2-56d0-42d0-bc34-d505e23e311e`.
- Durability commit: `c4ec6e4323a4ce941564f3331fce8695b26ede3e`.
- Ledger: `artifacts/evidence/solo-r2-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson`.
- Five-event SHA-256: `649b2d40c25460647247601ea18e7f2465a07280d58fad8ff7e96c003e0a0836`.
- Prior four-event prefix SHA-256: `ee51b11bdaa746e6cb338ca6245029563de858653b5062bfeab9ca1c83faf0da`.
- Initiated = 1; terminal = 1; outcome = HARNESS_FAILURE / TERMINAL.
- Repair revision: `0402b7937cfcfce8af55d50cb56744d8e1a8adfd`.
- Repair evidence: `memory/evidence/solo-r2-harness-repair-20260906/review.json`
  (77 direct tests, 10 independent tests, Blocking 0).
- Outer-binding evidence: `memory/evidence/solo-r2-harness-delivery-20260906/review.json`
  (6 outer checks; static binding only, not live admission).

The existing placement contract P05 allocates two arm Attempts, not two retries
of one arm. Execution contract E02/E09 forbids inferring retry from terminal or
STOP; E12 requires a new revision-bound owner decision for replacement.

## Target outcome and proposed owner disposition

On separate exact-byte owner adoption, record the old evaluation as
FAILED_MECHANISM_SHAKEDOWN / PRESERVED / NO_FURTHER_ARM. This is an authority
disposition alongside the evidence, not a new ledger event or a schema value.
Preserve all five ledger events, Phase A state, payload-pin adoptions, sealed
checkpoints, execution-started marker, raw outputs and failure evidence unchanged.
Do not execute its remaining arm, reuse its handle, reset counts or migrate state.

Propose exactly ONE additional replacement disposable evaluation, ONE dedicated
ledger and ONE new R2-SHAKEDOWN Pair, with two fresh-context arms, one per arm.
This is a bounded exception to D2's one-disposable allocation, not cancellation
of that limit. The failed disposable and the earlier original/replacement
evaluations remain separate; their capacities are not pooled or transferred.
No failure of this proposed replacement grants another replacement or retry.

## Proposed fixed placement and identity boundary

Repository root: `D:/ai-governance-framework`.

- New ledger: `artifacts/evidence/solo-r2-replacement-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson`.
- New genesis binding: `memory/evidence/solo-r2-replacement-disposable-mechanism-shakedown-20260906/genesis-binding.json`.
- New evaluation ID, Pair ID, genesis digest and controller identities: NOT CREATED.

These are sole proposed destinations, not caller-selectable paths. Occupied or
redirected destinations must reject without overwrite or fallback. IDs are
generated only during separately authorized creation, never by this candidate.
New controller custody, keys, payload pin and runtime-root placement require
explicit binding before creation/admission; no old live object or state is reused.

## Scope and authority relationships

The repair revision above is the minimum reviewed repair baseline, not a claim
that future placement wiring already exists. Later implementation must identify
its exact committed revision and preserve those fixes before admission.

Proposed input reuse is the exact disposable authority at `d4d8e0f6b41d7c1837edd70f77214212d99ae372`,
SHA-256 `5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb`.
Do not change frozen task/rubric/snapshot/oracle bytes or use Grimm. The disposable
task has already been exposed in run 1; do not describe it as pristine. Fresh
contexts must exclude prior-arm artifacts and conversation; provider cache
equivalence remains unclaimed. No new qualification result is claimed here.

Existing v2.1 schema and parent rules remain the starting contract. This proposal
does not relabel old genesis or transfer its allocation/placement identities.
The unavailable-cost adoption is bound to the old evaluation and prefix: do not
silently apply that authority to a new ledger. Any necessary new binding requires
separate review/adoption before use; old schema and authority bytes stay unchanged.

## Non-goals and claim ceiling

NON_COUNTED / SOLO_CONTROLLED / MECHANISM_SHAKEDOWN_ONLY; retain
DECISION_SUPPORT_ONLY. No Formal, A1-A6 progression, counted qualification or
Skill-effectiveness evidence. The replacement does not constitute or replace
the E12 qualification shakedown. Its purpose is an end-to-end mechanism run.

Adoption would approve only the disposition, bounded allocation and proposed
fixed placement. It does not authorize production changes, ID/ledger/Pair creation,
Attempt admission, task exposure, arm execution, oracle, scoring, unblinding,
commit or push. Those controlled actions require their own explicit authority.

## Affected surfaces, failure paths and evidence plan

Current writing scope: this candidate and canonical memory/evidence only.
Later binding work is expected to touch disposable profile/binding and launcher
consumers; no generic ledger registry or resume framework is proposed.

Before any separately authorized creation, establish available exact input and
authority bytes, fixed placement, new genesis binding, controller custody and
committed consumer identity. Validate wrong path/evaluation/authority rejection,
occupied target rejection and preservation of every prior ledger and state.
Do not weaken zero-Attempt checks to make the old Pair reusable.

## Next tranche and stop

Review this exact candidate, then obtain separate owner adoption if accepted.
Only afterward define the minimum replacement binding implementation tranche
and its remaining custody prerequisites. Do not implement or create anything
while preparing this candidate. STOP after candidate identity is recorded.
