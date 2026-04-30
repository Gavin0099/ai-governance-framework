# CLAIM_ENFORCEMENT_MINIMAL_SPEC

## Goal
Turn claim exaggeration into an automatically flaggable and decision-bound error with minimal process overhead.

## Scope
This spec applies to all reviewer closeout outputs that summarize governance A/B evidence.

## Required Fields
Every closeout must include exactly these fields:

```yaml
final_claim: string
claim_level: bounded | parity | strong | unbounded
semantic_drift_risk: true | false
checker_status: pass | fail
enforcement_action: allow | downgrade | block
reviewer_override_required: true | false
reviewer_override_applied: true | false
reviewer_override_reason: string | null
publication_scope: public | local_only
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

## Minimal Enforcement Rules (Graded)

### Rule 1: Drift Detection
- Checker computes `semantic_drift_risk=true` when:
  - disallowed strong phrase appears, or
  - same-evidence strengthening is detected, or
  - claimed certainty is stronger than evidence boundary.

### Rule 2: Ambiguity Downgrade
- If wording is ambiguous between weak vs strong certainty, downgrade wording.
- Operationally: when unsure, force `claim_level=bounded`.

### Rule 3: Enforcement Action Mapping
- If `semantic_drift_risk=false` -> `enforcement_action=allow`.
- If `semantic_drift_risk=true` and `claim_level in [bounded, parity]` -> `enforcement_action=downgrade`.
- If `semantic_drift_risk=true` and `claim_level in [strong, unbounded]` -> `enforcement_action=block`.

### Rule 4: Reviewer Decision Coupling
- Reviewer must explicitly respond to `enforcement_action`.
- If `enforcement_action in [downgrade, block]`, then:
  - `reviewer_override_required=true`.
- If reviewer overrides, must set:
  - `reviewer_override_applied=true`
  - `reviewer_override_reason` with explicit rationale.

### Rule 5: Local-Only Publication Boundary
- If `publication_scope=local_only`, then `claim_level` must not exceed `bounded`.
- Violation forces `enforcement_action=block`.

### Rule 6: Same-Evidence Posture Guard
- If `same_evidence_as_previous=true` and posture is upgraded, mark drift risk.
- If upgrade implies stronger claim level, map to `downgrade` or `block` per Rule 3.

## Closeout Validity (Fail-Closed)
- Invalid closeout conditions:
  - checker artifact missing
  - `checker_status` missing
  - `enforcement_action` missing
  - reviewer response to `enforcement_action` missing
  - override applied without reason
- Valid closeout:
  - checker fields complete, and
  - enforcement action resolved (`allow`, `downgrade` applied, or justified override).

## Design Principle
Do not rely on subjective reviewer checkbox discipline.
Use deterministic fields, graded enforcement, and decision coupling.
