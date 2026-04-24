# AGENTS Rule Evidence Aggregation Contract

This document defines how evidence is aggregated for AGENTS rule-promotion
candidates.

It exists to prevent candidate-rule accumulation from turning into automatic
noise amplification.

## Scope

This contract defines:

- what evidence can be counted
- how evidence is deduplicated
- how the aggregation window is applied
- how rejected candidates are suppressed
- when resurfacing is allowed

It does not define extraction sources or generator output files.

## Core Rules

1. `aggregation_key = candidate_id`
2. `evidence_ref` must be unique
3. duplicate `evidence_ref` values must not be counted twice
4. only evidence observed between `first_seen_at` and `last_seen_at` counts
5. rejected candidates must not resurface before `suppression_until`
6. resurfacing requires `resurfacing_condition` to be satisfied
7. generic-only evidence must not raise `repo_specificity`

## Evidence Deduplication

Evidence counting is reference-based, not event-row-based.

If the same `evidence_ref` appears multiple times for the same `candidate_id`,
it contributes at most `1` to `evidence_count`.

This prevents:

- replaying the same event
- re-reading the same runtime artifact
- duplicated adapter emissions

from inflating promotion pressure.

## Aggregation Window

Evidence is only counted if:

- `observed_at >= first_seen_at`
- `observed_at <= last_seen_at`

`evidence_window_days` is interpreted as the bounded observation window for the
candidate, not as a loose advisory number.

The candidate artifact must therefore carry a coherent:

- `first_seen_at`
- `last_seen_at`
- `evidence_window_days`

triple.

## Rejection Suppression

If the latest ledger decision for a candidate is `rejected`, then:

- resurfacing is blocked until `suppression_until`
- the candidate must not re-enter `needs_human_review` before that point

This is a hard aggregation rule, not a UI hint.

## Resurfacing Conditions

v0.1 supports a minimal resurfacing condition:

- `material_evidence_increase`

Meaning:

- a rejected candidate may only re-enter review if the new unique counted
  evidence exceeds the evidence set referenced by the rejection ledger entry

This prevents “same weak candidate, new timestamp” loops.

## Repo Specificity Guard

Aggregation must not silently upgrade generic evidence into repo-specific
governance.

Minimum v0.1 rule:

- if all counted evidence is `generic_only`, aggregated `repo_specificity`
  must not be raised above `low`

Concrete evidence bases that may justify higher specificity:

- `real_path`
- `real_command`
- `irreversible_boundary`
- `concrete_side_effect`

## Example

```json
{
  "candidate_id": "must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
  "aggregation_key": "must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
  "counted_evidence_refs": [
    "session:end:2026-04-24:abc123",
    "review:thread:42"
  ],
  "duplicate_evidence_refs": [
    "session:end:2026-04-24:abc123"
  ],
  "evidence_count": 2,
  "first_seen_at": "2026-04-24T10:00:00Z",
  "last_seen_at": "2026-04-24T12:00:00Z",
  "evidence_window_days": 14,
  "repo_specificity": "high",
  "resurfacing_allowed": false,
  "resurfacing_reason": "suppressed_until_not_reached",
  "suppressed_by_ledger": true
}
```

## Authority Boundary

Aggregation result is still not promotion.

It may:

- update `evidence_count`
- determine whether resurfacing is blocked
- preserve or downgrade repo-specificity claims

It may not:

- declare promotion complete
- bypass rejection suppression
- raise repo specificity from generic-only evidence
