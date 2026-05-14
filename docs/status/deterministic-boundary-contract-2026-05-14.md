# Deterministic Boundary Contract

As-of: 2026-05-14  
Goal: define exactly which layers require deterministic behavior.

## Determinism Levels

| layer | requirement | rationale |
|---|---|---|
| prompt parsing | weak | model variability tolerated |
| plan graph | medium | structure should be mostly stable |
| execution order | strong | avoid race/ordering side effects |
| side-effect application | very_strong | external impact must be bounded |
| authority decision | extreme | no ambiguity on allow/deny |
| replay outcomes | extreme | audit and diagnosis depend on reproducibility |

## Contract Rules

- weak/medium layers may vary, but must not bypass strong+ boundaries.
- strong+ boundaries must be machine-checkable and logged.
- any `authority decision` mismatch across identical inputs => determinism incident.
- replay divergence at extreme boundary => block closeout until reconciled.

## Required Deterministic Artifacts

- execution lineage id
- authority decision trace
- side-effect journal link
- checkpoint id
- replay verdict

## Validation Checklist

1. same inputs => same authority decision
2. side-effect order stable under replay
3. checkpoint restore deterministically re-enters valid state
4. deterministic boundary violations generate incident records
