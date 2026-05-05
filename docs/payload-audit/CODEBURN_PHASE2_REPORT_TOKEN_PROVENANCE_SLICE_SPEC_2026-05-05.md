# CodeBurn Phase 2 Report Token Provenance Slice Spec (2026-05-05)

> Status: Active
> Scope: `codeburn_report.py` report-surface provenance disclosure only
> Base implementation anchor: commit `7aa5761`
> Authority: report disclosure boundary for controlled exposure

---

## 1. Purpose

This slice adds limited provenance disclosure to the report surface so human reviewers can understand how token numbers were derived.

This slice does not expand decision authority.

The goal is disclosure accuracy, not machine reasoning.

---

## 2. In Scope

This slice is limited to report-surface provenance disclosure fields emitted by `codeburn_report.py`:

- `token_source_summary`
- `provenance_warning`

These fields may appear in:

- JSON report output
- text report output

This slice does not change:

- gate behavior
- decision eligibility
- `codeburn_analyze.py`
- any policy or enforcement path

---

## 3. Report Fields

### 3.1 `token_source_summary`

Human-readable summary of token provenance.

Allowed values in this slice:

- `provider`
- `estimated`
- `mixed(...)`
- `unknown`

### 3.2 `provenance_warning`

Human-readable warning about provenance certainty.

Allowed values in this slice:

- `mixed_sources`
- `provenance_unverified`
- `none`

---

## 4. Boundary Contract

### 4.1 Forward Constraints

The report provenance fields are disclosure-only.

They MUST NOT:

- change gate outcomes
- change decision posture
- modify `decision_usage_allowed`
- modify `analysis_safe_for_decision`
- silently influence `codeburn_analyze.py`

### 4.2 Reverse Constraint

Report-level provenance fields (`token_source_summary`, `provenance_warning`) MUST NOT be consumed by any automated decision, analysis, ranking, scoring, or gating logic.

They are strictly human-facing disclosure artifacts.

Report output MUST NOT be treated as a machine-consumable substitute for an analyze surface.

Any machine-level use of provenance requires a separate contract, separate surface, and separate authority path, such as a future dedicated analyze provenance signal.

### 4.3 Authority Separation

The authority model for this slice is:

```text
report  -> human-facing disclosure only
analyze -> not extended by this slice
decision flags -> unchanged
```

This slice exists to reduce overclaim, not to create a new machine input.

---

## 5. Controlled Exposure Rules

This slice is released under controlled exposure, not broad rollout.

Exposure is limited to repos where:

- a human reviewer reads the report output
- mixed or estimated token provenance actually occurs
- provenance context helps debug interpretation risk

If a consuming repo starts using these report fields as automation inputs, exposure must pause until the misuse is documented and corrected.

---

## 6. Non-Goals

This slice does not attempt to:

- establish token optimization baselines
- prove decision-safe provenance semantics
- extend `codeburn_analyze.py`
- create a new gate signal
- define machine reasoning over provenance

---

## 7. Acceptance Conditions

This slice is correctly adopted only if all of the following remain true:

1. report output discloses provenance more truthfully than before
2. no automated path consumes the report provenance fields
3. decision flags remain unchanged
4. existing report consumers remain non-breaking

---

## 8. Future Extension Rule

If provenance is ever needed for machine reasoning, it must be introduced through a new surface with its own:

- spec
- semantics
- evidence plan
- misuse analysis
- governance authority

Reusing `report.provenance_warning` or `report.token_source_summary` for that purpose is explicitly forbidden.