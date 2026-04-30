# CLAIM_ENFORCEMENT_MINIMAL_SPEC

## Goal
Turn claim exaggeration into an automatically flaggable error with minimal process overhead.

## Scope
This spec applies to all reviewer closeout outputs that summarize governance A/B evidence.

## Required Fields
Every closeout must include exactly these fields:

```yaml
final_claim: string
claim_level: bounded_support | stronger_than_allowed
semantic_drift_risk: true | false
posture: bounded_support | partial_falsification | major_falsification
previous_posture: bounded_support | partial_falsification | major_falsification | none
same_evidence_as_previous: true | false
```

## Allowed Language (Whitelisted)
Allowed to say:
- bounded_support
- reviewer-visible divergence
- authority-enforcement divergence

Not allowed to say:
- governance proven
- production-ready
- universally effective
- benchmark superiority

## Minimal Enforcement Rules

### Rule 1: Claim Level Gate
- `claim_level` must be `bounded_support`.
- If `claim_level != bounded_support`, set:
  - `claim_level = stronger_than_allowed`
  - `semantic_drift_risk = true`

### Rule 2: Ambiguity Downgrade
- If wording is ambiguous between weak vs strong certainty, downgrade wording.
- Operationally: when unsure, force `claim_level=bounded_support`.

### Rule 3: Same-Evidence Strengthening Check
- If `same_evidence_as_previous=true` and current wording/posture is stronger than previous, set:
  - `semantic_drift_risk = true`

### Rule 4: Disallowed Phrase Match
- If output contains any disallowed phrase, set:
  - `semantic_drift_risk = true`
  - `claim_level = stronger_than_allowed`

## Posture Consistency Guard
If posture is upgraded while `same_evidence_as_previous=true`, this is a drift signal by default.

## Pass/Fail
- PASS: `claim_level=bounded_support` and `semantic_drift_risk=false`
- FAIL: otherwise

## Design Principle
Do not rely on subjective reviewer checkbox discipline.
Use deterministic fields and simple auto-flag rules.
