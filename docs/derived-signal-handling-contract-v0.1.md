# Derived Signal Handling Contract v0.1

## Intent

Govern transformation-layer behavior so classification constraints cannot be bypassed through derived signals.

## Definition

A **derived signal** is any transformation, aggregation, composition, heuristic,
or model output computed from one or more source signals.

Examples:
- `token_count` -> `cost_estimate`
- `latency` + `retry_rate` -> `stability_score`
- `confidence` + `risk` -> `decision_priority`

## Core Rule

Derived signals inherit or escalate the governance constraints of their source signals.

## Constraint Inheritance

1. If source signal is `non_authoritative`:
   - derived signal is `non_authoritative` by default
   - derived signal must remain non-decisional unless explicitly reclassified

2. If multiple source signals are mixed:
   - effective class follows the strictest applicable constraint
   - inheritance must be explicit and reviewable

3. Reclassification of derived signals:
   - requires the same governance promotion path as base signals
   - reviewer confirmation + rationale + audit trail + versioned change

## Anti-Bypass Rule

It is forbidden to use derived signals to bypass classification constraints of source signals.

Forbidden pattern:
- source is non-authoritative
- derived signal is consumed for gating/ranking/scoring/prioritization/routing
- without explicit governance reclassification path

## Optional Machine-Readable Lineage Envelope

```json
{
  "derived_signal": "cost_estimate",
  "derived_from": ["token_count"],
  "inherits_classification": true,
  "effective_classification": "non_authoritative"
}
```

## Scope

This contract defines governance semantics only.
It does not introduce runtime enforcement behavior in this version.
