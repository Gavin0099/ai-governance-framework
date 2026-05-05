# Decision Debug Case Pack v0.1

## Purpose

Operationalize the current decision-transparency stack for real debugging use.

This pack is report/analysis only.
It does not authorize enforcement, routing, scoring, or gate blocking.

## Current Limits (Important)

- Trace shows structure (`who is in the graph`).
- Current version does **not** quantify influence (`who actually matters`).
- Influence/contribution metadata is a future extension.

Suggested placeholder for future extension:

```json
{
  "node": "cost_estimate",
  "influence_hint": "unknown"
}
```

## Case Template

### Case ID
- ``

### Scenario Type
- `cost-sensitive` | `latency-sensitive` | `mixed-signal`

### Decision Context
- Goal:
- Constraints:
- Candidate decision:

### Inputs
- Signals used:
- Expected classifications:
- Any derived signals:

### Decision Trace
```json
{}
```

### Classification Overlay
```json
{}
```

### Consumption Misuse Signals
```json
{}
```

### Pattern Visibility Snapshot
```json
{}
```

### Debug Conclusion
- If decision is wrong, can we explain why from current observability?
- Missing observability pieces:
- Recommended non-enforcement follow-up:

---

## Case 1

### Case ID
- `case-001-cost-sensitive`

### Scenario Type
- `cost-sensitive`

### Decision Context
- Goal: reduce execution cost without introducing decision contamination.
- Constraints: token-derived signals are non-authoritative by default.
- Candidate decision: prefer path A due to lower `cost_estimate`.

### Inputs
- Signals used:
  - `token_count` (non-authoritative)
  - `cost_estimate` (derived from `token_count`)
  - `latency` (semi-authoritative)
- Expected classifications:
  - `token_count` -> `non_authoritative`
  - `cost_estimate` -> inherits `non_authoritative` (unless reclassified)
  - `latency` -> `semi_authoritative`
- Any derived signals:
  - `cost_estimate` derived from `token_count`

### Decision Trace
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

### Classification Overlay
```json
{
  "decision_trace_classification": [
    {
      "node": "token_count",
      "effective_classification": "non_authoritative"
    },
    {
      "node": "cost_estimate",
      "effective_classification": "non_authoritative"
    },
    {
      "node": "latency",
      "effective_classification": "semi_authoritative"
    },
    {
      "node": "final_score",
      "effective_classification": "mixed-inputs"
    }
  ]
}
```

### Consumption Misuse Signals
```json
{
  "candidate_violation_consumption": {
    "consumption_violation": true,
    "violation_type": "used_in_gating",
    "field": "cost_estimate",
    "consumer": "release_gate_router"
  }
}
```

### Pattern Visibility Snapshot
```json
{
  "consumption_pattern_visibility": {
    "total_violations": 1,
    "by_type": {
      "used_in_gating": 1
    },
    "by_field": {
      "cost_estimate": 1
    },
    "by_consumer": {
      "release_gate_router": 1
    },
    "visibility_only": true,
    "high_frequency_misuse_triggers_enforcement": false
  }
}
```

### Debug Conclusion
- If decision is wrong, we can explain that a non-authoritative derived signal (`cost_estimate`) entered decision path.
- Missing observability pieces: influence/contribution strength is unknown.
- Recommended non-enforcement follow-up: add influence placeholder tracking and collect repeated real-world cases before any authority discussion.
