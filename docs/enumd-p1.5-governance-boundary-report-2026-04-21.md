# Enumd P1.5 Governance Boundary Report (2026-04-21)

## Scope

This report evaluates the governance boundary for `schema_evolution (domain_advisory)` events under P1.5.

Purpose is boundary locking, not final policy enforcement.

All conclusions are:

- evidence-based
- contract-scoped
- non-final unless explicitly stated

## Task 1: `nodeSignals` Downstream Consumption Classification

### Input

- `governance_report.json`
- `schema-evolution-2026-04-21-domain-advisory.json`
- event: `schema_evolution (domain_advisory)`

### Current Consumers

| Consumer | Classification | Notes |
|---|---|---|
| none | `record_only` | `nodeSignals` currently not consumed downstream |

### Latent Consumption Paths

| Potential Path | Risk Type | Description |
|---|---|---|
| routing layer | `routing_affecting` (latent) | `nodeSignals` may be used for filtering or routing decisions |
| policy engine | `escalation_affecting` (latent) | `nodeSignals` could be used for escalation heuristics |
| promotion logic | `promotion_affecting` (latent) | if integrated into promotion scoring |

### Risk Assessment

Current: non-semantic surface.

Latent risk: escalation path exists if downstream consumers are introduced.

Conclusion:

- `nodeSignals` is currently a non-semantic surface (`record_only`)
- latent semantics-escalation potential exists

## Task 2: `instrumentation_version` Contract Decision

### Decision

Selected: Option B, versioned contract marker (advisory-level).

### Rationale

- evidence traceability requires version binding
- future schema evolution depends on compatibility awareness
- system is not ready for hard enforcement

### Contract Definition (Minimal)

```json
{
  "instrumentation_version": {
    "major": "int",
    "minor": "int"
  }
}
```

### Compatibility Policy

- minor version:
  - backward compatible
  - no gate impact
- major version:
  - potential breaking change
  - triggers advisory (not gate yet)

### Enforcement Level

- current: advisory-only (non-gating)
- future: may escalate to gate condition

### Migration Requirement

- not required at P1.5
- required before P2 enforcement phase

## Task 3: Evidence Pack Validation

Evaluation focus: decision sufficiency, not field completeness.

### Evidence Completeness

- required fields: present
- source annotation: traceable
- event classification: consistent

### Decision Sufficiency

Evidence is sufficient to support:

- `schema_addition` (verdict-neutral)
- `gate_result: pass`

### Gap Analysis

No blocking gaps detected.

Minor observation:

- `instrumentation_version` is not yet enforced (expected at this stage)

Conclusion:

- `evidence_pack_valid: true`

## Task 4: Gate Robustness Review

### Current Gate Behavior

- `schema_addition -> pass` (verdict-neutral)

### Counterfactual Analysis

Case 1: `nodeSignals` becomes consumed.

- risk: `routing_affecting` / `escalation_affecting`
- current gate would still pass
- this may become incorrect

Case 2: advisory impacts routing/filtering.

- risk: silent semantic shift
- not currently captured by gate

### Assessment

Gate is currently sufficient under non-consumed `nodeSignals`.

However, future semantic escalation is possible if downstream consumption appears.

### Recommendation

Do not tighten gate immediately.

Introduce conditional guard:

- if `nodeSignals_consumed == true`
- require re-evaluation (`schema + semantics`)

## Task 5: Integration Readiness for P2

### Evaluation

| Dimension | Status |
|---|---|
| event classification | stable |
| evidence pack | reusable |
| gate logic | partially robust |
| intervention hooks | clear |

### Critical Constraint

`nodeSignals` semantic boundary is not yet fully enforced.

### Verdict

- `conditionally_ready_for_P2`

### Remaining Blocking Factors

- latent semantic path for `nodeSignals` not guarded
- `instrumentation_version` not enforced at consumer level
- gate lacks downstream-awareness condition

### Recommended Next Event for P2

- `authority_upgrade`

Reason:

- exercises semantic boundary
- tests escalation path
- validates versioned contract

## Final Summary

P1.5 outcome:

- `schema_evolution` semantic boundary is now defined
- evidence-to-decision contract is sufficient
- gate is stable under current assumptions
- latent semantic escalation paths are identified

System is conditionally ready for P2, with explicit boundary constraints.

## Important Notes

This report is boundary locking, not policy finalization.

No irreversible enforcement decisions are made at this stage.

## Contract Scope Declaration

All conclusions are valid under current:

- event classification model
- evidence schema
- non-consumed `nodeSignals` assumption

Any change to these assumptions must trigger re-evaluation.

## Runtime Advisory Mapping (P1.5 Instrumentation)

The following runtime surfaces are now emitted as advisory-only signals:

| Signal | Surface | Meaning | Gate Effect |
|---|---|---|---|
| `nodeSignals_consumed` | `enumd_provenance.nodeSignals_consumed` | downstream consumption status observed from source payload | none |
| `reevaluation_required` | probe sample + batch summary (`review_required_sample_*`) | semantic boundary re-check required before policy advancement | none (review-required advisory only) |
| `instrumentation_version_change` | probe sample (`current`, `baseline`, `major_changed`, `minor_changed`) | compatibility-aware change signal for schema evolution tracking | major: advisory re-evaluation; minor: no escalation |

Interpretation guard:

- advisory visibility does not imply gate promotion/block semantics
- this mapping is boundary instrumentation, not policy finalization
- `review_required_sample_count` is a visibility metric, not a severity/escalation metric
- `review_required_sample_count` must not be used for ranking, prioritization, or escalation decisions

## Validation Environment Note

Current local validation in this workspace has a known pytest filesystem constraint:

- execution used `-p no:tmpdir` and targeted subsets where needed
- this is an environmental test constraint
- this is not a semantic limitation of the advisory instrumentation contract

## Next Step (Execution-Oriented)

1. Add `nodeSignals_consumed` as an explicit runtime condition in gate inputs (advisory-only at first).
2. Add a P2 `authority_upgrade` test case that toggles consumed/unconsumed `nodeSignals`.
3. Bind `instrumentation_version.major` to an advisory escalation signal before moving to hard gate.
4. Re-run this boundary report after first downstream consumer is introduced.
