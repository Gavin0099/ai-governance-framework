# Provenance Boundary Enforcement Slice Spec (2026-05-05)

> Status: Proposed next slice
> Scope: observability and violation detection for report-surface provenance misuse
> Depends on: `CODEBURN_PHASE2_REPORT_TOKEN_PROVENANCE_SLICE_SPEC_2026-05-05.md`
> Does not change: report field semantics, gate behavior, or analyze authority

---

## 1. Why This Slice Exists

The prior provenance slice established semantic boundaries:

- report provenance is disclosure-only
- report is not analyze
- machine use requires a separate contract

That is necessary but not sufficient.

Spec text alone does not close the risk if a consuming repo can still read report-level provenance fields and feed them into machine logic without leaving any observable trace.

This slice exists to make that misuse observable.

---

## 2. Problem Statement

The failure mode is not only direct spec violation.

The harder failure mode is silent boundary erosion, including:

- a consumer repo reading report provenance fields inside automated checks
- analyze logic taking report provenance as a side input
- advisory ranking drifting into implicit gating later

These can happen without changing the original provenance spec, schema, or field names.

---

## 3. Goal

The goal of this slice is not hard enforcement yet.

The goal is to provide a bounded, reviewer-visible evidence surface for possible provenance boundary violations.

This slice is successful if the system can answer:

1. was report-level provenance consumed by a machine-facing surface?
2. where was the suspected consumption observed?
3. what field or namespace was involved?
4. is this a candidate violation, a confirmed violation, or only a weak signal?

---

## 4. Non-Goals

This slice does not:

- prove complete absence of misuse in every repo
- turn provenance misuse into a blocking gate by default
- extend `codeburn_analyze.py` semantics
- authorize machine use of report provenance
- replace review or code audit

---

## 5. Core Boundary

### 5.1 Protected fields

The protected report-surface provenance fields are:

- `token_source_summary`
- `provenance_warning`

The protected namespace may later expand, but this slice starts with those two fields only.

### 5.2 Protected rule

Any machine-facing read of these report-surface fields by automated decision, analysis, ranking, scoring, or gating logic is a provenance boundary violation unless a separate contract explicitly authorizes that use on a different surface.

### 5.3 Interpretive caution

This slice must distinguish between:

- `candidate_violation`
- `confirmed_violation`
- `no_observation`

Weak detection signals must not be mislabeled as proof.

---

## 6. Detection Model

### 6.1 Detection posture

Observability-first.

This slice should initially produce an advisory evidence artifact, not a gate.

### 6.2 Detection target

The system should detect suspected reads from report provenance fields into machine-facing logic, especially when data flows from:

```text
report surface -> analyze surface
report surface -> decision helper
report surface -> ranking or scoring helper
report surface -> gate condition
```

### 6.3 Minimum observable event

The minimum event to capture is:

- the machine-facing module or surface
- the report field referenced
- the observed basis for the claim

---

## 7. Suggested Hook Placement

This slice is designed to fit existing runtime surfaces rather than invent a new authority layer.

### 7.1 `pre_task_check`

Not the primary detector.

Use only for static declarations or policy visibility if needed.

Reason: `pre_task_check` runs before the relevant report consumption occurs.

### 7.2 `post_task_check`

Primary placement for near-term observability.

Reason: it is the most natural place to summarize which data sources were consumed during the just-finished machine-facing path and emit a reviewer-visible audit result.

### 7.3 `analyze`

Secondary placement for future stronger evidence.

Reason: if machine reasoning is the suspected sink, analyze is the closest semantic surface to record direct input provenance.

### 7.4 `session_end`

Aggregation only.

Reason: it may summarize violation observations or trend risk, but must not become the primary producer of the signal.

---

## 8. Evidence Schema

The evidence surface for this slice should be a dedicated result key, for example:

```json
{
  "provenance_boundary_audit": {
    "status": "candidate_violation",
    "advisory_only": true,
    "producer_identity": {
      "module": "runtime_hooks.core.post_task_check",
      "role": "report_provenance_boundary_observer"
    },
    "observed_surface": "post_task_check",
    "suspected_consumer": "analysis_module_x",
    "protected_field": "provenance_warning",
    "protected_namespace": "report",
    "observation_basis": {
      "type": "execution_trace_fragment",
      "note": "observed machine-facing read from report namespace"
    },
    "non_proof_declaration": {
      "not_proof_of_compliance": true,
      "not_verdict_bearing": true
    },
    "basis": "provenance boundary consumption observation",
    "internal_error": false
  }
}
```

Required fields:

- `status`
- `advisory_only`
- `producer_identity`
- `observed_surface`
- `protected_field`
- `protected_namespace`
- `observation_basis`
- `non_proof_declaration`
- `basis`

Recommended fields:

- `suspected_consumer`
- `source_location`
- `internal_error`
- `usage_note`

---

## 9. Status Semantics

Allowed initial statuses:

- `no_observation`
- `candidate_violation`
- `confirmed_violation`
- `audit_unavailable`

Meaning:

- `no_observation`: no suspicious consumption was observed on the available surface
- `candidate_violation`: suspicious machine-facing use was observed, but evidence is not yet strong enough to claim proof
- `confirmed_violation`: the system has direct enough evidence to say the boundary was crossed
- `audit_unavailable`: the observer could not run or degraded internally

`candidate_violation` is not enforcement evidence. It indicates boundary-risk observation only.

---

## 10. Fail-Open vs Fail-Closed

### 10.1 Initial policy

Fail-open, advisory-only.

Rationale:

- this is a new observability slice
- false positives are still possible
- existing consuming repos may not yet provide stable evidence quality

### 10.2 Hard invariant

In the initial slice, `advisory_only=True` is literal.

Any path that feeds `provenance_boundary_audit` directly into `gate.blocked` is a contract violation.

### 10.3 Future tightening

Any future shift toward fail-closed requires a separate authority decision supported by:

- stable producer quality
- false-positive analysis
- consuming repo evidence quality
- explicit policy adoption

---

## 11. Relationship to Existing Advisory Doctrine

This slice must follow existing advisory discipline:

- not every observation is proof
- reviewer-visible is not verdict-bearing
- aggregation does not create authority

This slice is closest to an advisory evidence producer with a protected-boundary focus.

---

## 12. Minimum Acceptance Criteria

Before implementation can be considered complete, the slice should define and validate at least:

1. one normal path where no misuse is observed
2. one direct violation path where a report provenance field is consumed by machine logic
3. one ambiguous path that remains `candidate_violation`, not false proof
4. one degraded path where the audit cannot run and returns `audit_unavailable`

---

## 13. Decision Statement

This slice assumes the boundary should be guarded, not merely described.

The immediate requirement is observability, not expansion.

In other words:

```text
semantic boundary without observability = incomplete control
observability before enforcement = required next step
```