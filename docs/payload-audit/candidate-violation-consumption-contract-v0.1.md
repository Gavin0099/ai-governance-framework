# Candidate Violation Consumption Contract v0.1

This contract does not authorize automated escalation.

## Intent

Define consumer-side constraints for candidate-violation-related signals.

## Allowed Uses

- human review
- diagnostics
- investigation

## Forbidden Uses

- gating (hard or soft)
- ranking
- scoring
- prioritization
- automatic review routing

## Runtime Signal

`post_task_check` emits `candidate_violation_consumption`:

- `consumption_violation: true|false`
- `violation_type: used_in_<forbidden_use> | null`
- `field`
- `consumer`
- `enforcement_readiness: false`
- `enforcement_readiness_note`

## Critical Semantic Rule

Presence of `promoted_policy_violation` does not imply enforcement readiness.
