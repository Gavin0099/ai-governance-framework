# Decision Path Lineage Visibility v0.1

## Intent

Add observability for how decisions are constructed so hidden misuse and
classification leakage can be traced and audited.

## Scope

Report-only visibility layer.

Out of scope:
- runtime blocking
- authority integration
- gate enforcement

## Core Principle

Lineage visibility does not imply enforcement.  
It exists only for observability and audit.

## Minimal Trace Shape

```json
{
  "decision_trace": [
    {
      "node": "final_score",
      "derived_from": ["cost_estimate", "latency"]
    },
    {
      "node": "cost_estimate",
      "derived_from": ["token_count"]
    }
  ]
}
```

## Classification Overlay

```json
{
  "decision_trace_classification": [
    {
      "node": "final_score",
      "effective_classification": "non_authoritative"
    },
    {
      "node": "cost_estimate",
      "effective_classification": "non_authoritative"
    },
    {
      "node": "latency",
      "effective_classification": "semi_authoritative"
    }
  ]
}
```

## Governance Interpretation

- Missing lineage is an observability gap, not automatic violation.
- Classification overlay reveals contamination risk even when explicit
  consumption violations are absent.
- Trace visibility is prerequisite for future enforcement discussion.

## Expected Use

- post-hoc investigation
- reviewer audit
- pattern analysis across decisions

## Non-Goal

This spec does not authorize:
- blocking
- routing
- scoring actions
- policy-violation auto injection
