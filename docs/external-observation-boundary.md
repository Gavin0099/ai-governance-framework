# External Observation Boundary

This document defines the trust boundary for ingesting external observations
without coupling decision authority to external systems.

## Core Rule

External systems are **untrusted observation producers**.

- Allowed: evidence, observation, provenance
- Not allowed: verdict, closure, promotion authority

Canonical promotion authority remains internal:

- Phase 2 decision core: `governance_tools/phase2_aggregation_consumer.py`
- Phase 3 gate: `governance_tools/phase3_promotion_gate.py`

## Mandatory Ingest Semantics

All external input must pass normalization through:

- `governance_tools/external_observation_adapter.py`

Normalization is mandatory:

- legacy alias mapping (e.g. `none_observed -> not_observed_in_window`)
- schema validation
- source identity validation
- forbidden field stripping/rejection
- ambiguous/invalid degradation (never upgrade)

## Forbidden External Authority Fields

Any external payload containing authority-like fields must be degraded and
cannot grant decision authority:

- `verdict`
- `gate_verdict`
- `current_state`
- `closure_verified`
- `promote_eligible`
- `phase3_entry_allowed`
- `closure_review_approved`

## Degradation Policy

Invalid or ambiguous external input must degrade to advisory-only output.

- invalid status defaults to `not_tested`
- forbidden authority fields produce degradation warnings
- no external payload can directly emit closure/promote semantics

## Integration Constraint

External ingestion is one-way:

- external -> canonical observation envelope
- no bidirectional authority sync
- no direct phase promotion path from external payload

