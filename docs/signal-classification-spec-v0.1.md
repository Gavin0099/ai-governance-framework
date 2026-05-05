# Signal Classification Spec v0.1

## Status

Phase: Signal Governance Pattern Extraction (single-domain validated)

Scope note:
- token-domain pattern has runtime validation
- cross-signal generalization is not yet proven

## Objective

Define signal classes before authority integration so governance patterns are not
misapplied across fundamentally different signal types.

## Classification Model

### 1) Non-Authoritative Signals (must be isolated)

Examples:
- `token_count`
- `token_observability_level`
- `token_source_summary`
- `provenance_warning`

Policy:
- observability + diagnostics + human review only
- must not be consumed by decision, gate, ranking, scoring, prioritization, or routing

### 2) Semi-Authoritative Signals (conditional authority)

Examples:
- latency
- cost

Policy:
- may be used in bounded operational contexts only after explicit authority contract
- requires additional eligibility rules, ownership, and replay/audit requirements
- default posture remains non-authoritative until promoted by contract

### 3) Decision-Authoritative Signals (decision-path eligible)

Examples:
- risk
- confidence

Policy:
- can be decision-relevant by design
- still requires explicit decision-policy ownership and verification
- cannot bypass governance policy precedence or evidence requirements

## Boundary Rules

1. No class auto-upgrades by convenience or frequency.
2. Presence of signal data does not imply authority.
3. Producer-side labels are insufficient without consumer constraints.
4. Promotion path must be explicit, reviewable, and auditable.

## Validation Requirement Before Generalization

Before claiming a reusable “layer”, each new signal type must pass:
- applicability check against this classification
- misuse surface analysis (consumer-side)
- authority-path decision (if any) with explicit ownership

## Cross-Signal Thought Experiment Anchor

Target signal for next reasoning pass:
- `confidence_score`

Question to answer:
- should confidence be isolated, conditionally authoritative, or decision-authoritative under current governance semantics?

## Non-Goal

This spec does not add runtime enforcement or authority integration.
It only defines classification and governance intent boundaries.
