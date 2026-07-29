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
- fails closed on missing, reordered, altered or digest-inconsistent evidence.

## Scope

### Primary Skill study

- At least three separately originated natural bug tasks.
- At least two consumer repositories.
- No duplicated root-cause family.
- Two initial A/B pairs per task, with a fresh context for every run.
- A third pair is mandatory when either initial pair contains a non-completed
  run or the qualifying-success counts are tied after two pairs.
- Maximum primary sample: three tasks x two arms x three pairs = 18 runs.
- Within each pair, A and B share the same baseline, task packet, model build,
  permissions, budget, scorer rubric and frozen harness contract. Only the
  presence of the Bug Fix Skill differs.
- Pair order is randomized from a task-specific seed frozen before the first
  run.

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
5. Across pairs where both runs report a positive denominator, the median
   B/A wall-clock ratio and median B/A tool-call ratio are each at most 1.20.
6. The wins are not all from one repository or one reused agent context.

Token counts are reported when the provider exposes them consistently. Missing
token telemetry must carry a reason and is not silently converted to zero.

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
- `gate3-runtime/gate3_evidence_chain.py`: experiment-local metric validator,
  create-once chain writer and verifier.
- `gate3-runtime/test_gate3_evidence_chain.py`: failure-path regression tests.
- `candidate/gate3-preregistration-amendment-v1-candidate-manifest.json`:
  exact review/signature target.
- `.gitattributes`: exact-byte preservation for the candidate set.

No shared runtime hook, gate policy, schema registry, consumer contract or CI
workflow is changed by this candidate.

The candidate manifest pins the five implementation/specification inputs; its
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

Method-adoption observations require digest-bearing event evidence when marked
observed. They may show that the Skill changed behavior, but they do not by
themselves establish product benefit.

### Blind score

Each scorer submission must cover the exact closed anonymous set. Completed
runs require all conditional-quality fields. Non-completed runs require those
fields to be null. This prevents a timeout from being presented as a known
zero-quality fix.

### Ordering chain

Each comparison unit has this fixed event order:

1. two anonymous outcomes sealed;
2. blind set closed;
3. primary scorer submission sealed;
4. second scorer submission sealed;
5. mapping release sealed.

Every event is canonical UTF-8 JSON, is published create-once, and contains the
SHA-256 of the exact previous event bytes. Mapping release is refused until the
two scorer events and their source files verify.

This is a local fail-closed evidence chain. It detects missing, reordered and
byte-altered retained artifacts and prevents the provided writer from
overwriting an event. It does not authenticate the writer or prevent an actor
with direct filesystem control from deleting and coherently rebuilding the
whole chain. The final head digest must therefore be copied into the
reviewer/owner receipt or another separately controlled append-only surface.

### Harness boundary

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
- A scorer submission with a missing anonymous ID, wrong role, duplicate
  output or timeout represented as scored quality fails.
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
- inconsistent completion/quality state;
- missing token reason and invalid timestamp order;
- create-once refusal;
- packet/metrics digest mismatch;
- scorer population and role mismatch;
- timeout quality coercion;
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
failure-path tests and exact candidate manifest. Harness implementation,
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
