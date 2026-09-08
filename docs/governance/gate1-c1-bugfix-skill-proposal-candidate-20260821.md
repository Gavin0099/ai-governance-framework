# C1 Bug Fix Safety — Gate 1 Proposal Candidate

Status: **`PROPOSAL_ONLY` — NOT PREREGISTERED, NOT FROZEN, NO ARM AUTHORIZED**

Date: 2026-08-21

This document proposes the smallest reviewable Gate 1 design for C1. Merging
it would record a proposal, not approve or freeze the experiment. A later,
separately authorized preregistration would have to resolve every open item,
materialize and hash all inputs, and pass independent review before any arm
could exist or run.

## Problem

C1 is admitted at Gate 0 and has a reviewed `GO_TO_GATE1_PROPOSAL` decision.
The remaining design problem is whether a future four-arm comparison can
preserve a real `B-A` treatment contrast.

The previous pre-push common dispatch is not reusable. It told every producer
to create a regression that fails before the fix and after revert. Those are
central steps in the Bug Fix Safety packet. Reusing that wording would give
Arm A much of the treatment and make a small `B-A` difference
uninterpretable.

The opposite failure is also possible: a common "behavioral acceptance"
paragraph can disclose the identity tiers, fallback architecture, or expected
fix while appearing neutral. C1 therefore needs a product-level common task
surface and a separately controlled scorer-only oracle surface.

## Current repository truth

- C1 is `ADMITTED_AT_GATE0` in
  `docs/status/gate3-c1-gate0-admission-2026-08-21.md`.
- C1 is `GO_TO_GATE1_PROPOSAL` in
  `docs/status/gate3-c1-method-sensitivity-assessment-2026-08-21.md`.
- The exact baseline is
  `15d5d51356b4808e5fb12782961a94d9985b2ae6`; the historical fix is its
  direct child `a60756436095fb3b14aecbc9094dd88a8ab9ef16`.
- The generic Bug Fix Safety packet was frozen before C1 at framework commit
  `61b285b25e97872526057c6ab6b01637fbfa1d2b`; its SHA-256 is
  `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14`
  over 1,373 bytes.
- Attempt 01 preserved a real `ORACLE_DOES_NOT_DISCRIMINATE` result. Attempt
  02 later established a credible baseline-fail/fixed-pass pair with oracle
  SHA-256
  `702e0a78ec4d7e62abf57fd643bc068da559621428310fed2f22547b29ab9dad`.
- Candidate selection was informed, and the discriminating oracle was
  redesigned after attempt-01 failure. Neither is prospective evidence of a
  Skill effect.
- No C1 common task packet, hidden scorer bundle, task-specific Governance
  treatment, C1 validator, scoring rubric, randomization manifest, model
  stamp, budget, second-scorer subset, or receipt contract is frozen.
- No C1 Gate 1 preregistration exists and no C1 arm has been created or run.

## Target outcome

Produce a design that an independent reviewer can accept, revise, or reject
before preregistration work begins. The proposal must:

1. keep all task-specific producer-visible prose at product symptom and
   reproduction level;
2. keep root-cause-bearing cases and architecture-specific expectations on a
   scorer-only surface;
3. preserve the generic Bug Fix Safety packet as the proposed B/C/D treatment
   rather than copying its method into common instructions;
4. name unresolved inputs instead of silently freezing provisional choices;
   and
5. stop before preregistration, materialization, or execution.

## Scope

- Define the proposed producer/scorer information boundary.
- Give candidate producer-visible symptom and reproduction wording for review.
- Define scorer-only oracle coverage semantically, without creating its code
  or fixtures.
- Define the proposed A/B/C/D treatment separation.
- Define candidate outcome and cost dimensions.
- Define contamination, evidence, and fail-closed requirements that a later
  preregistration must resolve.
- Recommend one later preregistration tranche, conditional on proposal
  approval.

## Non-goals

- No Gate 1 approval, signature, preregistration, or freeze.
- No task packet, oracle bundle, treatment packet, validator config, rubric,
  arm manifest, dispatch packet, bundle, worktree, producer, or scorer is
  created.
- No A/B/C/D execution, rehearsal, canary, dry run, or model call.
- No modification to the frozen generic Skill packet.
- No historical fix, attempt evidence, consumer repository, runtime, schema,
  hook, CI, gate, or enforcement change.
- No C2, C3, Route C, Skill-effectiveness, promotion, countability, or process-
  integrity decision.

## Proposed information boundary

### Producer-visible common surface

The task-specific portion of a future common packet may contain only the
following two sections. The wording below is a review candidate, not frozen
input.

<!-- c1-producer-visible-candidate BEGIN -->

#### Product symptom

> During one bulk catalog import, two distinct books that share the same title
> and publisher can be linked to the same existing catalog book. The second
> book then loses its distinct catalog identity. Existing imports that have no
> catalog identifier and intentionally resolve by title and publisher must
> continue to work.

#### Reproduction

> Start from the supplied baseline and run the supplied black-box bulk-import
> reproducer. Its input contains an existing catalog book and a batch with two
> same-title/same-publisher items: one represents that existing book and the
> other represents a distinct catalog item. Observe that both results link to
> the existing book, although the second item should remain distinct.

<!-- c1-producer-visible-candidate END -->

The future common envelope may also state neutral environment, safety,
permission, time, and tool-budget metadata shared by every arm. It must not
add task-specific acceptance architecture or method instructions.

The producer-visible surface must not contain:

- `ISBN tier`, `URL tier`, `strong identity`, `soft identity`, `softMap`,
  `softMissBooks`, lookup-population, fallback-order, or mixed-batch language;
- file paths, function names, historical commit `a607564`, a diff, root-cause
  hypothesis, or fix hint;
- an instruction to write a regression test, demonstrate baseline failure,
  reintroduce or revert the defect, perform mutation/sensitivity checking, or
  make an evidence-bounded claim; or
- hidden-oracle case counts, expected internal branches, fixture construction,
  or scorer thresholds.

Those exclusions are treatment-integrity requirements. They do not prevent a
producer from independently discovering or choosing any of those methods.

### Producer-visible reproduction artifact

A later preregistration may propose one black-box reproducer shared by all
arms. Before freeze, review must establish that it:

- exercises only a public product-level import entrypoint;
- prints the observed incorrect product result without naming the internal
  matching mechanism;
- contains only the single common reproduction above;
- is byte-identical for every arm;
- is not itself a regression-test template; and
- contains none of the scorer-only variants below.

This proposal does not create that artifact or select its command.

### Scorer-only oracle surface

The future scorer-only bundle may encode architecture-specific coverage. It
must remain unavailable to every producer before output commit, except that a
future Arm D validator may emit separately approved treatment-time feedback
that does not reveal these cases.

At minimum, the hidden scorer oracle should distinguish:

1. a same-title/same-publisher collision where the incoming item has a
   different ISBN-like catalog identifier;
2. the corresponding collision where product-page identity is the relevant
   differentiator;
3. a book without catalog identifiers that should still match an existing
   book by title and publisher;
4. a mixed batch in which another item makes the title/publisher fallback map
   non-empty, so a partial one-site fix remains detectable; and
5. an unchanged exact-identity case that must continue resolving to its
   existing book.

The later oracle must use independent expected values and apply identically,
post-hoc, to A/B/C/D. This semantic list is not an oracle implementation,
fixture freeze, threshold, or proof that the cases are mutually sufficient.

## Proposed treatment separation

| Arm | Producer-visible condition | Proposal state |
|---|---|---|
| A | common product symptom/reproduction plus common baseline safety and permissions | proposed control |
| B | A plus the exact generic Bug Fix Safety packet | proposed Skill contrast |
| C | B plus a task-specific claim/evidence Governance packet | packet content not yet authored |
| D | C plus treatment-time output from an independent external validator | validator not yet selected |

The task-specific Governance packet for C may constrain evidence binding,
scope, and claim accuracy, but must not contain C1 root-cause or fix content.
Its exact bytes remain open.

### Arm D open blocker

No current evidence identifies a C1-relevant treatment-time validator that is
both independently useful and safe from leaking the hidden scorer variants.
Choosing a generic linter merely to fill the D cell would add cost without a
credible `D-C` mechanism. Giving D the hidden mutation cases would violate the
owner-authorized scorer-only boundary.

Validator selection is therefore
**`OPEN_BLOCKING_BEFORE_PREREGISTRATION`**. A later Gate 1 candidate must either:

- justify and freeze a validator whose treatment-time output does not expose
  the hidden oracle; or
- propose, for owner review, a narrower study design and reconcile that change
  explicitly with the program's four-arm authority.

This proposal does neither.

## Candidate scoring dimensions

A later preregistration may define objective measures for:

- hidden product-oracle correctness across the five scorer-only behavior
  families;
- whether a producer-authored regression actually discriminates baseline from
  the submitted correction when assessed post-hoc;
- preservation of identifier-free title/publisher matching;
- scoped regressions;
- change scope and minimality;
- completion-claim agreement with receipts; and
- owner interventions, rework, wall time, tool calls, and token cost.

Scores must measure outputs, not reward an arm for merely restating Skill
steps. Any post-hoc sensitivity or mutation scorer must run identically on all
four committed outputs and remain unavailable as producer feedback except for
a separately authorized Arm D treatment-time validator.

No weights, pass threshold, improvement threshold, second-scorer subset, or
disagreement procedure is selected here.

## Affected surfaces

This proposal changes only this document. If it is later approved, a separate
preregistration tranche would be expected to propose distinct, reviewable
surfaces for:

- the common product-level task/reproduction input;
- the scorer-only oracle bundle;
- the C Governance treatment;
- the D validator/config or an explicit four-arm authority amendment;
- scoring and decision thresholds;
- isolation, randomization, blinding, model, permissions, and budget;
- output, test-evidence, and receipt contracts; and
- an exact-digest preregistration decision document.

That list is an impact forecast, not authorization to create the files.

## Boundary and API considerations

- Producer and scorer surfaces are separate trust domains. A digest binding
  does not permit producer access to scorer-only bytes.
- All producers must receive the same common task bytes and baseline tree.
- Treatment packets are additive by arm; common bytes cannot silently absorb
  treatment content.
- The historical fix, this proposal, the Gate 0 records, both attempts, the
  method-sensitivity assessment, and all later framework analysis remain
  outside every producer environment. Producer history stops at the exact
  consumer baseline.
- A scorer oracle is measurement, not producer guidance. Arm D treatment-time
  feedback, if later justified, is a declared treatment exception rather than
  a reason to expose the scorer bundle.
- No repository API, runtime API, schema, or enforcement behavior changes in
  this proposal.

## Failure paths and risk points

| Risk | Fail-closed response required before preregistration |
|---|---|
| product wording reveals identity precedence or fix architecture | revise common wording and repeat independent leakage review |
| reproducer includes scorer-only variants or method scaffolding | reject and rebuild the reproducer under a new digest |
| Arm A receives regression/sensitivity instructions | reject the design because `B-A` is contaminated |
| hidden oracle can be read by a producer | invalidate the isolation design; do not run |
| hidden oracle only recognizes the historical fix shape | add independent behavioral variants before freeze |
| D validator has no credible independent mechanism | remain blocked; do not fill the arm with a ceremonial tool |
| D feedback reveals hidden cases | reject that validator/config |
| model, permissions, budget, or common inputs differ across arms | reject the preregistration candidate |
| informed selection or post-hoc redesign omitted from claims | reject the claim boundary |
| any arm runs before exact freeze and separate authority | exclude it; it is not a study result |

## Evidence plan for a later preregistration candidate

Before any Gate 1 freeze decision, a later tranche would need to provide:

1. exact SHA-256 and byte lengths for every proposed producer, scorer, Skill,
   Governance, validator, rubric, and receipt input;
2. an independent leakage review showing the common task/reproducer contains
   no treatment or hidden-oracle content;
3. black-box reproduction evidence on the exact baseline without disclosing
   scorer variants to producers;
4. hidden-oracle baseline discrimination and fixed-tree sensitivity evidence
   for every proposed behavior family;
5. validator relevance and non-leakage evidence, or an explicit authority
   decision changing the four-arm design;
6. identical baseline, common-input, model, permissions, and budget bindings;
7. frozen scoring, threshold, second-scorer, blinding, randomization, and
   invalid-run rules; and
8. commit/receipt bindings that fail closed rather than permit repair in
   place.

None of this evidence is produced by the present proposal.

## Claim ceiling

This document may claim only that a bounded C1 Gate 1 design is proposed for
review and that current repository evidence motivates its treatment contrast.

It does not claim that:

- the proposal is accepted;
- Gate 1 is preregistered, complete, or frozen;
- any packet, oracle, validator, environment, producer, scorer, or arm exists;
- C1 will produce a positive `B-A`, `C-B`, or `D-C` difference;
- the Skill is effective; or
- Gate 2, Gate 3, promotion, countability, process integrity, C2, or C3 is
  authorized or supported.

## Implementation tranche recommendation

If and only if this proposal is independently approved, the next smallest
tranche is a **Gate 1 preregistration candidate**, not execution. It should
materialize the proposed common task/reproducer and scorer-only oracle as
separate content-addressed review inputs, resolve the Arm D blocker, freeze the
remaining program-required decisions, and stop for another explicit owner
decision.

Until then, terminal state is: **`PROPOSAL_AWAITING_REVIEW`**.
