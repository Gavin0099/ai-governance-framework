# Gate 3 preregistration amendment v1 candidate — paired Skill screening

Status: **CANDIDATE ONLY — PENDING INDEPENDENT REVIEW AND OWNER SIGNATURE.**

This candidate does not authorize a Gate 3 run. It replaces no canonical
protocol until the owner signs the exact candidate manifest and a later
promotion commit records that decision.

## Problem

Gate 2 formal master `gate2-formal-20260728-115533` preserved four scorable
outcomes, two scorer submissions and a mapping release, but it did not preserve
an independently verifiable create-once receipt chain proving that both scorer
submissions preceded mapping release. Its process integrity is therefore
`NOT_ESTABLISHED`, and its scores cannot be used as the first Gate 3 promotion
sample.

The pilot also exposed three design limits:

1. one natural bug cannot distinguish a treatment effect from model variance;
2. A, B and D all reached the five-point ceiling, even though the scorers
   described quality differences;
3. timeout, conditional quality and execution cost were compressed into one
   score instead of being reported separately.

## Current repository truth

- `PLAN.md` records Gate 2 process integrity as `NOT_ESTABLISHED` and Skill
  effectiveness as `NOT_CLAIMED`.
- `docs/governance/evidence-backed-engineering-skill-program-2026-07-24.md`
  already requires at least three separately originated natural bugs across at
  least two consumer repositories for Gate 3.
- The same program defines `B-A` as the Skill effect, `C-B` as the Governance
  effect and `D-C` as the validator effect, but it does not require paired
  repeats or define a deterministic tie/timeout rule.
- The Gate 2 runner writes scorer submissions and mapping artifacts but does
  not bind them through create-once, previous-digest receipts.
- The base64-only write path changed producer behavior in live canaries. It is
  an observed common-mode channel effect, not a neutral transport assumption.

## Target outcome

Produce an exact-byte, reviewable Gate 3 protocol candidate that:

- treats Gate 2 only as rubric and harness calibration;
- makes repeated, paired A/B runs the only Skill-promotion comparison;
- separates B/C and C/D into non-promotional diagnostic studies;
- records completion, conditional quality, method adoption and raw cost as
  separate values;
- makes scorer submission-before-mapping order mechanically replayable through
  a create-once digest chain;
- binds the released A/B identity to a high-entropy preregistered mapping
  commitment created before either producer runs;
- binds every scored packet, retained diff and command receipt to an existing
  clean output commit through a portable Git bundle and the candidate common
  harness contract;
- records two scorer contexts, rubric digests and blind-input-set digests
  instead of treating two role labels as independence;
- fails closed on missing, reordered, altered or digest-inconsistent evidence.

## Scope

### Primary Skill study

- Exactly three separately originated natural bug tasks, frozen before the
  first counted run. Not a minimum: the promotion threshold below is written
  against three, and allowing the sample to grow afterwards would let a
  disappointing result be answered with more runs.
- At least two consumer repositories.
- No duplicated root-cause family.
- Two initial A/B pairs per task, with a fresh context for every run.
- A third pair is mandatory when either initial pair contains a non-completed
  run or the qualifying-success counts are tied after two pairs.
- Maximum primary sample: three tasks x two arms x three pairs = 18 runs.
- Within each pair, A and B share the same baseline, task packet, model build,
  permissions, budget, scorer rubric and frozen harness contract. Only the
  presence of the Bug Fix Skill differs.
- This is enforced, not merely stated. `comparison_controls` in the protocol
  contract names the one input digest a study kind may vary, and the blind set
  cannot be closed if the two arms differ in any other input digest, or if
  they do not differ in the studied one. A pair whose governance or validator
  inputs also varied would measure a mixture and could not be read as the
  Skill effect.
- Before either producer runs, the experimenter creates a canonical
  `gate3-randomization-record.v1` containing the two anonymous IDs, treatment
  input digests and `sha256(canonical mapping reveal + 256-bit nonce)`.
- The record's exact digest is common to both run metrics. Mapping release must
  reveal the mapping and nonce, reproduce the commitment and match the
  treatment and treatment-input digests admitted for each output.

### Diagnostic studies

- B/C may study Governance overhead or claim bounding.
- C/D may run only when validator applicability is frozen before any producer
  output is observed.
- Diagnostic results cannot add evidence to, rescue or overturn the A/B Skill
  promotion decision.
- Each diagnostic study uses its own preregistered comparison unit and the same
  evidence-chain mechanism.

### Qualifying success

A run is a qualifying product success only when all are true:

- `completed_under_cap`;
- independent `oracle_acceptance`;
- regression fails at baseline;
- regression passes after the fix;
- the original defect is caught by the frozen sensitivity check;
- no new scoped regression;
- zero critical correctness or safety residuals.

After two pairs, compare A and B qualifying-success counts for the task. If
they tie, or if any run did not complete, run the frozen third pair. After the
third pair, a remaining tie is a task tie; no further run may be added.

### Promotion threshold

The provisional Skill threshold is met only when all are true:

1. B wins at least two of the three task-level comparisons.
2. B's aggregate completion rate is not lower than A's.
3. B has no critical correctness or safety failure absent from A.
4. At least one B task win is caused by a qualifying product-success
   difference, not documentation volume or completion-claim style alone.
5. At least two pairs must contain valid positive wall-clock and tool-call
   telemetry for both arms. Their median B/A wall-clock and tool-call ratios
   must each be at most 1.20. For an even number of pairs, median is the
   arithmetic mean of the two middle ratios.
6. The wins are not all from one repository or one reused agent context.

Token counts are reported when the provider exposes them consistently. Missing
token telemetry must carry a reason and is not silently converted to zero.
Missing core cost telemetry makes the cost gate `INSUFFICIENT`; a zero
wall-clock or tool-call denominator is `INVALID`, not an excluded pair.

Failure to reach the threshold after the frozen sample is `NEGATIVE`, not
weakly positive. Missing diversity or an incomplete decision sample is
`INSUFFICIENT`. Broken isolation, identity, receipt, ordering or output binding
is `INVALID`.

## Non-goals

- Do not reinterpret or repair Gate 2 evidence.
- Do not count Gate 2 as a Gate 3 task.
- Do not start, provision or score a Gate 3 producer.
- Do not promote a Skill or Governance rule.
- Do not claim statistical power or population-level causal inference from
  three tasks.
- Do not modify the historical Gate 2 runner or evidence.
- Do not implement a generic workflow ledger, security log or
  cryptographically authenticated writer.
- Do not choose natural bugs after seeing which treatment they favor.

## Affected surfaces

- `candidate/gate3-protocol-contract-v1.json`: machine-readable candidate
  protocol and metric fields.
- `candidate/gate3-harness-contract-v1.json`: signed admission, packet,
  receipt, Git-bundle and equality requirements that a later common harness
  must implement without changing experiment semantics.
- `gate3-runtime/gate3_evidence_chain.py`: experiment-local metric validator,
  create-once chain writer and verifier.
- `gate3-runtime/test_gate3_evidence_chain.py`: failure-path regression tests.
- `candidate/gate3-preregistration-amendment-v1-candidate-manifest.json`:
  exact review/signature target.
- `.gitattributes`: exact-byte preservation for the candidate set.

No shared runtime hook, gate policy, schema registry, consumer contract or CI
workflow is changed by this candidate.

The candidate manifest pins the six implementation/specification inputs; its
own SHA-256 is the external review and signature target. Because the verifier
and its hard-coded candidate file list are themselves in that set, an
independent reviewer must inspect their source diff as well as run
`verify-candidate`. The verifier cannot prove the completeness of its own
declarations.

## Boundary and API considerations

### Run metrics

Every producer outcome must have one `gate3-run-metrics.v1` object. Objective
costs and lifecycle fields are recorded before blind scoring. A completed run
is conditionally quality-eligible; timeout and other terminal failures keep
quality fields `NA` rather than coercing them to zero.

Core wall-clock and tool-call metrics must either be positive integers or be
explicitly unavailable with a reason. Unavailable core telemetry is retained
but cannot satisfy the minimum-valid-pair cost gate.

Method-adoption observations require digest-bearing event evidence when marked
observed. They may show that the Skill changed behavior, but they do not by
themselves establish product benefit.

### Blind score

Each scorer submission must cover the exact closed anonymous set. Completed
runs require all conditional-quality fields. Non-completed runs require those
fields to be null. This prevents a timeout from being presented as a known
zero-quality fix.

Two scorers need a stated rule for disagreeing, or they are one scorer plus an
argument that whoever reads the result later gets to settle. The rule is
conservative intersection:

- A run is a qualifying success only if both scorers judge every scorer-judged
  field as passing.
- Any disagreement makes the run not a qualifying success. Both submissions and
  a conflict record are retained.
- The run stays in the denominator. A conflict must not shrink the effective
  sample, and must not be resolvable toward the larger effect.
- Objective fields are not voted on. Test outcomes, commits and receipts are
  determined by the verifier, which observed them; scorers judge only
  `oracle_acceptance`, `original_defect_caught` and `no_new_scoped_regression`.

No re-run, no third adjudicator, no primary-scorer override.

Each submission also binds `scorer_identity`, `scorer_context_id`,
`model_build`, the frozen rubric digest and the exact blind-input-set digest.
The primary and second scorer context IDs must differ, and each submission must
carry an independence declaration. This is retained context evidence, not
cryptographic proof that a human or model did not copy another score.

### Ordering chain

Each comparison unit has this fixed event order:

1. canonical randomization record and mapping commitment sealed;
2. two anonymous outcomes sealed;
3. blind set closed;
4. primary scorer submission sealed;
5. second scorer submission sealed;
6. mapping and 256-bit nonce released.

Every event is canonical UTF-8 JSON, is published create-once, and contains the
SHA-256 of the exact previous event bytes. Mapping release is refused until the
two scorer events and their source files verify.
The released mapping must reproduce the preregistered commitment and must equal
the treatment identity recorded in each outcome admission.

This is a local fail-closed evidence chain. It detects missing, reordered and
byte-altered retained artifacts and prevents the provided writer from
overwriting an event. It does not authenticate the writer or prevent an actor
with direct filesystem control from deleting and coherently rebuilding the
whole chain. The final head digest must therefore be copied into the
reviewer/owner receipt or another separately controlled append-only surface.

### Harness boundary

The exact `gate3-harness-contract-v1.json` bytes are part of the candidate
manifest and therefore part of any later owner signature. An owner signature is
forbidden when that file is absent or changed.

Every outcome admission must retain and bind:

- baseline and output commit;
- a portable Git bundle containing both commits and their ancestry;
- the exact `git diff --binary --full-index` bytes and tracked path inventory;
- a clean live worktree whose `HEAD` equals the output commit at sealing time;
- test/validator receipts whose `linked_commit` equals the output commit and
  whose retained output bytes match their digest;
- raw event-log bytes;
- baseline/task/treatment/Governance/validator/permissions/budget/harness/
  rubric/randomization input artifacts, with each digest recomputed from the
  retained source bytes rather than accepted as a digest-shaped assertion;
- a scorer packet whose commit, diff, receipt-set and harness identities equal
  the admission.

Gate 3 execution is blocked until one exact common A/B harness contract is
hash-frozen and passes a non-counted rehearsal. The preferred route is a safe
structured patch/write operation that returns stored byte count and SHA-256.
If the existing base64-only path is retained instead, the owner must explicitly
accept that results are limited to that unusual harness and that common-mode
exposure does not prove equal behavioral impact.

Changing the harness after the first counted run invalidates the complete Gate
3 sample.

## Failure paths and risk points

- Duplicate anonymous IDs, missing output packets or metrics/packet digest
  disagreement fail before blind-set closure.
- Missing or altered randomization records, short/non-hex nonces, swapped
  mapping, or treatment-input disagreement fail mapping release.
- Missing Git objects, non-ancestor output commits, dirty capture worktrees,
  diff/path disagreement, missing or digest-inconsistent retained input bytes,
  receipt/output-commit mismatch, altered command output, event-log mismatch or
  packet/admission disagreement fail sealing or replay.
- A scorer submission with a missing anonymous ID, wrong role, duplicate
  output or timeout represented as scored quality fails.
- A scorer submission with a reused context, wrong rubric or wrong blind-input
  digest fails.
- Second-scorer submission before the primary scorer fails.
- Mapping with the wrong study treatment set or anonymous population fails.
- Any existing target event makes the writer fail rather than overwrite.
- Sequence gaps, unexpected files, non-canonical bytes, contract drift,
  previous-event digest mismatch or source artifact tamper fail verification.
- Two repeats are a screening design, not a stable variance estimate.
- The third-pair rule is adaptive but frozen here before task selection; no
  fourth pair is permitted.

## Evidence plan

Targeted tests must cover:

- valid completed and timeout metrics;
- positive, unavailable and zero-denominator core-cost behavior plus the
  frozen even-sample median rule;
- inconsistent completion/quality state;
- missing token reason and invalid timestamp order;
- create-once refusal;
- packet/metrics digest mismatch;
- scorer population and role mismatch;
- copied scorer role with reused context;
- timeout quality coercion;
- preregistered mapping swap and admitted-treatment mismatch;
- output-commit, Git-bundle, dirty-worktree, retained-input and receipt-link
  failures;
- early or wrong mapping release;
- missing event, retained-file tamper and previous-digest mismatch;
- exact candidate-manifest verification.

Then run:

1. the focused Gate 3 tests;
2. JSON parse and Python compile checks;
3. `git diff --check`;
4. the repository's canonical focused precommit gate before a candidate commit.

A later non-counted harness rehearsal and independent review are required
before owner signature and canonical promotion.

## Implementation tranche recommendation

This candidate's single implementation tranche is limited to the
machine-readable protocol, metrics validator, create-once ordering chain,
signed common-harness contract, failure-path tests and exact candidate
manifest. Harness implementation,
natural-bug selection, resource admission and any Gate 3 run are separate
future slices.

## Claim ceiling

This candidate may claim only that its proposed protocol is explicit and that
its local validator/chain behavior passed the named tests. It may not claim
that:

- the candidate is independently approved, owner-signed or canonical;
- the create-once chain is an authenticated security boundary;
- a safe structured write harness exists;
- qualifying natural bugs or independent resources exist;
- Gate 3 may start;
- the Bug Fix Skill is effective.
