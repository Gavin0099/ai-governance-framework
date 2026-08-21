# Gate 3 first-Skill Route C natural-pilot amendment

Status: **CANDIDATE — DORMANT PILOT ONLY; NOT ACTIVATED OR ACCEPTED.**

## Problem

The natural-pilot decision recorded in `memory/2026-07-17.md` already defines
the smallest useful observation: wait for one naturally occurring consumer
bug, run the eight-step bug-fix workflow card without changing the framework
during execution, write one post-case record, and choose `STOP`, `MERGE` or
`SECOND_OBSERVATION`.

That decision does not provide a durable record shape or a machine-checked
claim ceiling.  Without those two constraints, a bounded observation can drift
into a Gate 3, countability, promotion or causal conclusion that its evidence
does not support.

## Current repository truth

- `memory/2026-07-17.md` is the authority for the dormant natural pilot.  One
  case supports reviewer-counterfactual judgment only, not measured
  effectiveness.
- The original eight-step workflow-card bytes are not retrievable from that
  record.  Later reconciliation aligned the remembered card with program
  Section 3 steps 1–7 and 9, but that prose reconciliation is not the original
  byte artifact.
- Gate 2 process integrity remains `NOT_ESTABLISHED`.  Route B is stopped and
  no Route C observation qualifies for counting or promotion evidence.
- No natural bug, observation record or Route C execution is authorized by
  this amendment.

## Material amendment to the expiry decision

The 2026-07-17 authority said the dormant plan **expires for re-review** on
2026-09-11 if no natural case appears.  This amendment deliberately changes
that semantics: if no qualifying natural bug has been admitted by the end of
2026-09-11, this Route C pilot reaches terminal `STOP`.

This is a material amendment, not an interpretation of the earlier wording.
There is no automatic extension, manufactured bug, conversion to deliberate
observation or automatic re-review.  Any later pilot is a new proposal that
requires fresh authority; it is not a continuation of this one.

## Target outcome

Define one small post-case record shape and one test-local guard that keep any
future natural observation inside its evidence boundary.  The amendment does
not recreate the workflow card or build reusable validation infrastructure.

## Record schema

A future post-case record has schema
`gate3-route-c-natural-observation.v1` and exactly these top-level fields:

| Field | Requirement |
| --- | --- |
| `schema` | Literal `gate3-route-c-natural-observation.v1` |
| `observation_id` | Stable identifier for this one natural case |
| `observed_at` | Recorded observation time |
| `consumer_repository` | Repository in which the bug arose naturally |
| `natural_bug_reference` | Durable reference to the pre-existing consumer bug |
| `natural_bug_basis` | Why the case was not manufactured for the pilot |
| `workflow_card_sha256` | SHA-256 of the exact workflow-card bytes actually executed |
| `workflow_card_retained_path` | Durable path containing those exact card bytes |
| `workflow_steps` | Per-step completion and evidence references |
| `outcome` | Observed engineering result, without causal upgrade |
| `reviewer_counterfactual` | Reviewer judgment about what likely differed without the card |
| `owner_interventions` | Ordered steering/intervention records, including an empty list |
| `claims` | Exact fixed claim block below |
| `disposition` | Exactly `STOP`, `MERGE` or `SECOND_OBSERVATION` |

`workflow_card_sha256` and `workflow_card_retained_path` are both mandatory.
The card reference from memory is insufficient.  If the exact card bytes are
not frozen and retained before execution, the case cannot become a Route C
observation under this amendment.

`MERGE` means only that an observed practice may be merged into an existing
surface under a separately authorized change.  It does not mean Skill
promotion, Gate 3 completion or countability.

`SECOND_OBSERVATION` means only that the reviewer judges a further case would
be informative.  It does not authorize one.  A second observation is a new
proposal requiring fresh authority, consistent with the expiry amendment
above.

The canonical claim block is:

<!-- route-c-claim-block:begin -->
```json
{
  "countability": "NOT_CLAIMED",
  "process_integrity": "NOT_ESTABLISHED",
  "promotion_evidence": false,
  "skill_effectiveness": "NOT_CLAIMED"
}
```
<!-- route-c-claim-block:end -->

No other claim key is admitted.  Narrative fields may describe the observed
case but cannot override or enlarge this block.

## Scope

- This one-page amendment.
- One experiment-local test that locks the record fields, claim block, expiry
  amendment and selected positive-claim prose patterns.

## Non-goals

- Activating the pilot, selecting or manufacturing a bug, or creating an
  observation record.
- Reconstructing the missing 2026-07-17 workflow-card bytes.
- Adding a reusable validator, runtime module, schema-registry entry, hook, CI
  gate, wire format, proof bundle or error table.
- Editing Plan B rev5, `PLAN.md`, memory, M3-b-2A, B-1 or existing evidence.
- Establishing process integrity, countability, promotion evidence, causal
  effect or Skill effectiveness.

## Affected surfaces

This slice adds only this document and
`artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/
test_gate3_route_c_claim_guard.py`.

The helper in that test is intentionally test-local and is not a reusable
validator.  If a real observation JSON is later authorized, validator
extraction is decided from that observed need rather than promised here.

## Boundary and API considerations

There is no runtime or public API.  The document is the candidate authority;
the test parses only its marked claim block and checks its declared fields and
expiry language.  It does not validate a future observation artifact.

## Failure paths and risks

- Missing workflow-card bytes make the observation inadmissible rather than
  reconstructable from memory.
- Missing owner-intervention data hides steering contamination.
- A changed claim value, extra claim key or selected positive-claim prose must
  fail the test.
- A `MERGE` disposition can be misread as promotion unless its narrow meaning
  remains explicit.
- Expiry can restart a decision loop unless terminal `STOP` remains explicit.

## Evidence plan

1. Parse exactly one marked JSON claim block with Python stdlib `json`.
2. Assert the four exact claim keys and values.
3. Mutate process integrity, countability, promotion evidence, Skill
   effectiveness and add an extra Gate 3 success key; every mutation must be
   rejected by the test-local helper.
4. Inject selected positive causal/effectiveness prose; every case must be
   rejected while the candidate document remains accepted.
5. Assert both workflow-card digest and retained-path fields.
6. Assert the original `expires for re-review` wording and the material change
   to terminal `STOP` are both disclosed.
7. Run scoped pytest and `git diff --check`, then commit the exact two-file
   bytes before independent review.

## Implementation tranche recommendation

This two-file candidate is the complete tranche.  After exact-byte review, any
PLAN or memory reconciliation is a separate slice.  Pilot activation remains a
separate decision triggered only by a natural consumer bug and available exact
workflow-card bytes.

## Claim ceiling

This candidate may claim only that a record shape, fixed claim block, expiry
amendment and test-local drift guard have been proposed and committed for
review.  It may not claim that the amendment is accepted, the pilot is active,
a natural case exists, an observation has been validated, Gate 3 is complete,
or the Skill has an established effect.
