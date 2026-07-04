# Self-Governance Markerless Claim Semantic Drift Design

Status: DESIGN ONLY / REPORT ONLY
Date: 2026-07-04
Scope: R2 markerless claim semantic drift

## DONE

DONE = markerless claim semantic drift is documented as a remaining
`VULNERABLE baseline`, with future report-only design options and claim
ceilings, without changing `claim_enforcement_checker`, tests, hook, CI, schema,
runtime, or gate policy behavior.

## Problem

`claim_enforcement_checker.evaluate` now catches one class of claim-label drift:
a restrained `claim_level` such as `bounded` or `parity` paired with known
absolute / universal lexical markers such as `guarantee`, `completely safe`, or
`all inputs`.

The remaining gap is `Markerless Strong Claim`:

- the final claim is semantically stronger than the evidence supports;
- the text avoids every known `CLAIM_STRENGTH_MARKERS` token;
- the caller self-labels `claim_level: bounded`;
- the checker returns `semantic_drift_risk: false` and
  `enforcement_action: allow`.

This is not a bug in the lexical proxy. It is the documented limit of using word
markers as a structural stand-in for semantic judgment.

## Current Baseline

Existing status is already registered:

- contract: `docs/governance/self-governance-claim-label-mutation-contract-2026-07-04.md`
- catalog row: `Markerless Strong Claim`
- status: `VULNERABLE baseline`
- surface: `governance_tools/claim_enforcement_checker.py`

This design does not update the catalog because the current catalog status is
still accurate. It refines the next-slice choices before any enforcement or
runtime change.

## Threat Model

Adversarial pattern:

```yaml
final_claim: "The validator covers unsupported production conditions across the
  full workflow."
claim_level: bounded
publication_scope: public
same_evidence_as_previous: false
posture: bounded_support
```

The wording is strong in effect, but it avoids the current marker list. A
lexical detector cannot reliably know whether this claim is too strong without
structured evidence about what was actually tested, reviewed, or bounded.

## Design Principle

Do not solve markerless semantic drift by silently adding a broad semantic
classifier to an enforcement path.

Reason:

- classifier output would be hard to reproduce in focused tests;
- false positives could block valid bounded claims;
- false negatives could create an inflated `PROTECTED` claim;
- it would blur the line between advisory review aid and policy enforcement.

The safer path is structured support first, advisory comparison second,
enforcement only after a separate policy RFC and mutation contract.

## Future Slice Options

### Option A: Structured Claim Support Envelope

Add an optional report-only input / artifact that separates the final claim from
its evidence support:

```yaml
claim_support:
  supported_claim_level: bounded | parity | strong | unbounded
  support_source: tests | review | artifact | manual
  evidence_refs:
    - <command, artifact, or source>
  scope_boundaries:
    - <what was actually covered>
  residual_risks:
    - <what remains unproven>
```

Report-only comparison:

- if `claim_level` is stronger than `supported_claim_level`, emit
  `claim_level_exceeds_structured_support`;
- if `claim_support` is missing for a public strong-looking claim, emit only a
  documentation warning, not a block;
- if evidence refs are missing, reuse evidence-provenance concepts rather than
  inventing a semantic truth claim.

Claim ceiling:

- can show mismatch between self-label and structured support;
- cannot prove the final claim is semantically correct.

### Option B: Reviewer Semantic Attestation Receipt

Add a candidate review artifact where a reviewer explicitly records that the
claim wording matches the evidence boundary.

Candidate fields:

```yaml
receipt_schema: claim_semantic_attestation.v0.1
status: report_only
reviewed_claim: <final claim text or stable digest>
reviewed_claim_level: bounded | parity | strong | unbounded
evidence_refs:
  - <command, artifact, or source>
attested_support_level: bounded | parity | strong | unbounded
attestation_result: aligned | overstated | unclear
cannot_claim:
  - <unverified implication>
```

Report-only comparison:

- if final output claims semantic review occurred but no attestation artifact is
  linked, warn `claim_semantic_attestation_missing`;
- if attestation says `overstated`, warn
  `claim_semantic_attestation_overstated`;
- do not treat `aligned` as proof of truth.

Claim ceiling:

- can prove a reviewer recorded a semantic-boundary judgment;
- cannot prove the reviewer was right.

### Option C: Expand Lexical Markers Only

The smallest code slice would add more `CLAIM_STRENGTH_MARKERS`.

This is allowed only as a narrow advisory hardening step, but it does not solve
R2:

- marker lists always have bypass phrasing;
- adding markers increases false-positive risk;
- it should never convert `Markerless Strong Claim` to `REMEDIATED baseline`.

Claim ceiling:

- can reduce known lexical misses;
- cannot fix markerless semantic drift.

## Recommended Next Implementation Path

Prefer Option A first.

Reasoning:

- it stays machine-checkable;
- it avoids opaque classifier behavior;
- it gives future reviewers a concrete evidence boundary;
- it can remain advisory while creating useful mutation fixtures.

Only after Option A exists should Option B be considered for human / agent
review attestation. Option C can be used for small known misses, but it should
not be framed as the R2 fix.

## Mutation Contract Shape For Future Work

Scenario: `Markerless Strong Claim`

Adversarial input:

- `final_claim` implies broader support than the evidence;
- no known `CLAIM_STRENGTH_MARKERS` appear;
- `claim_level: bounded`;
- `claim_support.supported_claim_level: bounded` or missing;
- evidence refs do not support the stronger implication.

Current expected observation:

- `evaluate` returns `enforcement_action: allow`;
- `semantic_drift_risk: false`;
- this remains `VULNERABLE baseline`.

Future report-only target:

- with structured support present, a checker can emit
  `claim_level_exceeds_structured_support` when labels disagree;
- without structured support, first implementation should emit at most a
  report-only missing-support warning for declared public claims;
- no `PROTECTED` claim is allowed until focused tests prove the intended
  mutation is detected through a stable, reviewable surface.

## Non-Goals

This design does not:

- modify `claim_enforcement_checker.py`;
- add markers to `CLAIM_STRENGTH_MARKERS`;
- add tests;
- change hook, pre-push, CI, schema, runtime, or gate policy behavior;
- introduce an LLM semantic classifier;
- validate the truth of `final_claim`;
- verify evidence-vs-claim correctness;
- turn any `allow` into `block`;
- update `docs/e1-mutation-catalog.md`;
- claim `Markerless Strong Claim` is fixed.

## Claim Ceiling

This design can claim:

- R2 remains a `VULNERABLE baseline`;
- structured claim support is the preferred future report-only path;
- lexical marker expansion is insufficient as a semantic fix;
- no enforcement behavior changed.

This design cannot claim:

- markerless strong claims are detected;
- semantic-vs-label verification exists;
- evidence supports the final claim;
- claim-label surface is `PROTECTED`;
- red-team audit is fully fixed;
- Phase E enforcement is complete.
