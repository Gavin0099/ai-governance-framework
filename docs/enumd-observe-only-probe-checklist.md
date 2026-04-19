# Enumd Real-Data Observe-Only Probe Checklist

Status: probe-planning artifact (not integration approval).

## Scope

This checklist is for validating whether real Enumd reports can be safely
observed without contaminating the current observation-only regime.

This checklist does **not** authorize:
- lifecycle classification usage
- gate decision usage
- reviewer decision-support usage
- canonical-path merge

## Required Probe Questions

1. Field stability
- Are critical fields stable across real reports (`run_id`, `semantic_boundary`,
  `calibration_profile`, provenance fields)?

2. Boundary metadata consistency
- Is `semantic_boundary` consistently present and semantically aligned with
  observation-only constraints?
- Is `represents_agent_behavior=false` stable and not contradicted by payload?

3. Runtime isolation check
- Does `is_runtime_eligible()` consistently reject Enumd external artifacts in
  all probe samples?

4. Semantic-induction pressure
- Do `advisories` / `calibration_profile` / presentation patterns induce
  interpretation or decision-support behavior in reviewers/agents?

5. Consumer misread pressure
- When downstream consumers ingest artifacts, do they transform observation
  payload into readiness/promotion/stability support signals?

## Probe Output Requirements

- Machine-readable probe log (`json`)
- Human-readable summary (`md` or `txt`)
- Explicit pass/fail per question above
- Explicit caveat:
  - "Probe pass means containment under observe-only scope; it does not imply
    integration-ready value justification."

## Exit Criteria

Probe can be marked "observe-only contained" only when all required questions
pass within the declared sample window.

Even when contained, integration remains blocked until value-case evidence is
separately established.
