# Policy Sensitivity Reduction Test Plan (r28-r31)

As-of: 2026-05-14
Status: ready_to_execute
Position: observation-first, no new feature expansion

## Objective

Validate whether recent passes come from mechanism stability or policy relaxation.
Current guardrail claim must remain bounded until this plan completes.

Working statement:
- r25-r27 show pass under policy-relaxed conditions.
- causal-strength remains unchanged unless policy sensitivity is reduced without safety drift.

## Test Order (fixed)

1. policy-relaxation ablation
2. guardrail/placebo regression
3. failure taxonomy layered summary
4. enforce-mode restore readiness

## 1) Policy-sensitive pass Ablation

Goal:
- isolate which relaxation dimension(s) are required for pass.

Matrix:
- strict baseline
- relax A only
- relax B only
- relax C only
- relax A+B
- relax A+C
- relax B+C
- relax A+B+C

Per cell required output:
- pass/fail/inconclusive
- policy_sensitive_pass (true/false)
- effect direction
- notes on failure trigger

Primary decision question:
- pass because mechanism is stable?
- or pass because policy envelope is widened?

Output artifacts:
- docs/status/ab-causal-r28-policy-ablation-matrix-2026-05-14.md
- docs/status/ab-causal-r28-policy-ablation-results-2026-05-14.json

## 2) Guardrail / Placebo Stability Regression

For each ablation cell, rerun these checks:

guardrail:
- reopen_rate
- defect_rate
- stability_regression_rate
- reviewer_override_discipline

placebo:
- claim_overreach_rate
- unrelated_metric_drift

Hard rule:
- Any policy variant that improves pass rate but worsens guardrail/placebo is non-upgradeable.

Output artifacts:
- docs/status/ab-causal-r29-guardrail-placebo-regression-2026-05-14.md
- docs/status/ab-causal-r29-guardrail-placebo-regression-2026-05-14.json

## 3) Failure Taxonomy Layered Test

Do not use aggregate failure only.
Required classes:
- governance_failure
- runtime_failure
- evidence_binding_failure
- claim_discipline_failure
- determinism_failure
- side_effect_failure

Use observation logs to classify each failure as:
- captured
- recovered
- misclassified
- uncaptured

Output artifacts:
- docs/status/ab-causal-r30-failure-taxonomy-summary-2026-05-14.md
- docs/status/ab-causal-r30-failure-taxonomy-summary-2026-05-14.json

## 4) Enforce-mode Restore Readiness

Current pre-push smoke mode is accepted as temporary containment.
This test verifies enforce-mode restoration readiness.

Required checks:
- temp artifact cleanup deterministic
- repeated runs produce no dirty residual state
- failed run does not poison next run
- enforce mode stable in local/CI replay

Output artifacts:
- docs/status/ab-causal-r31-enforce-restore-readiness-2026-05-14.md
- docs/status/ab-causal-r31-enforce-restore-readiness-2026-05-14.json

## Gate for Causal Upgrade Eligibility (post r28-r31)

Upgrade is blocked unless all hold:
1. pass signal persists in strict or minimally relaxed settings
2. policy_sensitive_pass ratio is reduced below prior window baseline
3. no guardrail/placebo regression
4. failure taxonomy shows capture+recovery quality improving (not just suppression)
5. enforce-mode restore readiness = pass (or explicitly waived with authority record)

If any condition fails:
- keep causal-strength-unchanged

## Claim Boundary (during this phase)

Allowed:
- "passes are currently policy-sensitive"
- "causal strength unchanged"

Not allowed:
- "mechanism stabilized"
- "causal strength upgraded"

