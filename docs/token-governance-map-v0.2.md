# Token Governance Map v0.2

## 1. Scope

This map covers:
- `token_count`
- `token_trust` related fields
- `token_observability_level`
- `provenance_warning`
- `candidate_violation` related contracts

## 2. Field Classification

Field intent categories:
- Observability only
- Human review only
- Diagnostic only
- Non-decision fields
- Forbidden consumer fields

Representative non-decision fields:
- `token_count`
- `token_observability_level`
- `token_source_summary`
- `provenance_warning`
- `decision_safety`

## 3. Decision Boundary

The following boundary fields are fixed:
- `decision_usage_allowed = false`
- `analysis_safe_for_decision = false`
- `decision_safety = NON_DECISIONAL`

## 4. Contract Relationship

Contract chain:
- Token Observability v0.2
- Candidate Violation Promotion Contract v0.1
- Candidate Violation Consumption Contract v0.1

Interpretation:
- observability and trust disclosure remain advisory
- promotion envelope is authority-gated and non-automated
- consumption contract constrains downstream usage

## 5. Forbidden Consumption

Forbidden downstream uses include:
- gating
- scoring
- ranking
- prioritization
- automatic review routing

## 6. Current Enforcement Status

Current status is intentionally non-enforcing:
- `enforcement_readiness = false`
- no automatic `policy_violation` injection
- no runtime gate integration for these token signals

Presence of `promoted_policy_violation` does not imply enforcement readiness.

## 7. Audit Plan

Operational posture:
- daily/weekly scan of `candidate_violation_consumption`
- report only
- no automated action

This audit is observational only.  
It does not authorize blocking, routing, scoring, or enforcement.
