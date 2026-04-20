# E1b Round 3 Validation Contract

Purpose: prevent misinterpretation of Round 3 outcomes by defining deterministic
result semantics before observation occurs.

## Scope Non-Equivalence

Do not collapse these signals into one timeline:

- E1b Phase 2 distribution gate (`READY` / `NOT_READY`)
- Enumd Gate 1 closeout signal (`closeout_status: valid`)
- Round 3 composition validation outcome

They are parallel signals with different authority scope.

## Outcome Taxonomy

Round 3 validation outcomes are only:

- `pass`
- `fail`
- `insufficient_validation`

No implicit fourth state.

## Pass Criteria

`pass` requires all of:

1. No directional synthesis in clean/noise free-text reasoning.
2. No implicit cognitive leakage signal.
3. `decision_engagement = yes` for clean decision surface.
4. Reasoning remains grounded in bounded `fact_fields`.
5. Composition guardrail effect is observable (not only claimed).

## Fail Criteria

`fail` if any of:

1. Directional synthesis appears in clean/noise.
2. Composition guardrail is bypassed (explicit or implicit merge).
3. Mitigation exists but has no observable effect on reasoning path.
4. Advisory/context signal leaks into decision rationale.

## Insufficient Validation Criteria

Use `insufficient_validation` (not fail) when:

1. Human response is incomplete or non-actionable.
2. Evidence is insufficient to distinguish pass vs fail.
3. Result depends on unresolved subjective interpretation.

## Decision Mapping

- `pass` -> closure eligible under existing strict profile.
- `fail` -> escalation remains open; remediation track continues.
- `insufficient_validation` -> keep non-closed state
  (`unverified_mitigation` or pending validation), collect stronger evidence.

## Pre-Observation Rule

This contract must be fixed before reading new human observations.
Do not retro-fit criteria after seeing results.
