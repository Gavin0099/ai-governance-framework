# R49.2 Harness Adapter Smoke (2026-05-15)

As-of: 2026-05-15
Scope: adapter contract shape verification
Decision: `adapter_smoke_only`

## Boundary Statement

> **adapter validates R49.2 harness contract shape, not real reviewer substitution evidence**

This smoke does NOT constitute R49.2 evidence collection.
Running this smoke does NOT advance any R49.x task toward completion.
Running this smoke does NOT change `scaffold_state` from `scaffold_validated` to `evidence_collected`.

The adapter (`scripts/r492_harness_adapter.py`) emits stub metric values.
These values are shape-correct but carry no governance signal.

## Why This Smoke Exists

R49.x-5 (null semantics audit) confirmed that null_type/null_status are correctly
propagated through the PS1 runner in stub and dryrun modes.

Before any real harness run, we need to verify:
1. The PS1 runner correctly handles a harness that outputs valid JSON with all R49.2 fields
2. NT-05 path fires correctly when `evaluator_confidence` is absent from harness output
3. No null value leaks into pass/fail/degraded/finding when it should stay as null_status

The adapter provides a controlled environment for these three verifications.

## Test Cases

### Case A: NT-05 Path (missing provenance)

**Invocation:**
```powershell
.\run_r492_reviewer_substitution.ps1 `
    -Mode harness `
    -HarnessScript scripts/r492_harness_adapter.py `
    -HarnessExtraArgs "--case","nt05"
```

**Adapter output (stdout):**
```json
{
  "adapter_smoke": true,
  "adapter_case": "nt05",
  "scenario_id": "...",
  "seed": ...,
  "reviewer": "...",
  "observe_only": true,
  "claim_discipline_drift": 0.0,
  "unsupported_count": 0,
  "replay_deterministic": true,
  "reviewer_override_frequency": 0,
  "intervention_entropy": 0.35,
  "drift_result": "not_measured"
}
```
Note: `evaluator_confidence` field is **absent**.

**PS1 behavior (Invoke-HarnessRun):**
- `$hasOwnConfidence` = false → `evaluator_confidence = "medium"`, provenance = `"harness_default_NT-05"`

**Get-SubstitutionInterpretation result:**
- `evaluator_confidence_provenance == "harness_default_NT-05"` → returns `"untrusted_evaluator"`

**Completion counter:** `untrusted_evaluator` is in `$NULL_STATUSES` → NOT counted as completed

**Expected checkpoint entry:**
```json
{
  "interpretation": "untrusted_evaluator",
  "evaluator_confidence": "medium",
  "evaluator_confidence_provenance": "harness_default_NT-05",
  "null_type": null,
  "null_status": null
}
```

---

### Case B: Normal Path (self-reported provenance)

**Invocation:**
```powershell
.\run_r492_reviewer_substitution.ps1 `
    -Mode harness `
    -HarnessScript scripts/r492_harness_adapter.py `
    -HarnessExtraArgs "--case","normal"
```

**Adapter output (stdout):**
```json
{
  "adapter_smoke": true,
  "adapter_case": "normal",
  "claim_discipline_drift": 0.0,
  "unsupported_count": 0,
  "replay_deterministic": true,
  "reviewer_override_frequency": 0,
  "intervention_entropy": 0.35,
  "drift_result": "not_measured",
  "evaluator_confidence": "low",
  "evaluator_confidence_provenance": "harness_self_reported"
}
```

**PS1 behavior (Invoke-HarnessRun):**
- `$hasOwnConfidence` = true → `evaluator_confidence = "low"`, provenance = `"harness_self_reported"`
- `null_type = null`, `null_status = null` (harness ran cleanly)

**Get-SubstitutionInterpretation result:**
- No run-level null_type → proceeds to metric checks
- `claim_discipline_drift = 0.0` → not null → does not return "undecidable"
- `evaluator_confidence_provenance != "harness_default_NT-05"` → NT-05 guard does not fire
- `claim_discipline_drift = 0.0`, `unsupported_count = 0` → not "tacit_dependency_detected"
- `replay_deterministic = true` → not "runtime_consistency_broken"
- `reviewer_override_frequency = 0` → not "substitutable_higher_cost"
- `intervention_entropy = 0.35` → not < 0.2 → not "silo_risk_flagged"
- Returns `"stable_candidate"`

**Completion counter:** `stable_candidate` is NOT in `$NULL_STATUSES` → counted as completed

**Expected checkpoint entry:**
```json
{
  "interpretation": "stable_candidate",
  "evaluator_confidence": "low",
  "evaluator_confidence_provenance": "harness_self_reported",
  "null_type": null,
  "null_status": null,
  "measurement_source": "harness"
}
```

---

### Case C: NT-01 Path (existing R48 harness CLI mismatch)

**Invocation:**
```powershell
.\run_r492_reviewer_substitution.ps1 -Mode harness
```
(uses default `$HarnessScript = "governance_harness.py"`)

**Behavior:**
- `governance_harness.py` receives `--scenario / --seed / --reviewer / --observe-only`
- R48 harness only accepts `--output-dir` → exits with non-zero code
- PS1 catches → `measurement_source = "harness_error_fallback"`, `null_type = "NT-01"`, `null_status = "not_measured"`

**Interpretation:** `not_measured`
**Governance implication:** NT-01 = infrastructure failure, NOT governance fragility.

---

## What This Smoke Verifies

| Verification | Covered by |
|---|---|
| NT-05 fires when evaluator_confidence absent | Case A |
| NT-05 produces untrusted_evaluator, not counted as completed | Case A |
| Normal path resolves to stable_candidate when metrics are clean | Case B |
| harness_self_reported provenance flows through correctly | Case B |
| NT-01 fires on harness CLI mismatch | Case C |
| NT-01 is not counted as governance fragility | Case C |
| No null leaks into pass/fail/degraded/finding | All cases |

## What This Smoke Does NOT Verify

- Real reviewer substitution signal (requires live harness with actual scenario execution)
- `evaluator_confidence_unknown_rate < 100%` R50 entry criterion (no real evidence collected)
- Any R49.x-1/2/3/4 task progress (those require harness runs with non-null metrics from real measurement)

## R50 Entry Impact

This smoke does NOT change any R50 entry criteria.
All criteria remain as before:

| Criterion | Status |
|---|---|
| null_ontology_instantiated | true (R49.x-6 complete) |
| null_semantics_audit_passed | true (R49.x-5 complete) |
| metric_usefulness_ranking_completed | false |
| epistemic_compression_test_passed | false |
| at_least_one_genuine_signal_found | false |
| evaluator_confidence_unknown_rate_below_100pct | false |

## Artifacts

- Adapter: `scripts/r492_harness_adapter.py`
- PS1 runner (with HarnessScript/HarnessExtraArgs): `run_r492_reviewer_substitution.ps1`
- This document: `docs/status/ab-causal-r492-adapter-smoke-2026-05-15.md`
