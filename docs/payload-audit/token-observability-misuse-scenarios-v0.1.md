# Token Observability Misuse Scenarios v0.1

## Scope
This document enumerates misuse scenarios for token observability artifacts.
It is a governance reference only and does not introduce runtime enforcement.

## Boundary Reminder
- Token observability outputs are non-authoritative.
- Token observability outputs are not decision inputs.
- Token observability outputs must not drive ranking, scoring, gating, or policy verdicts.

## Misuse Scenarios

### 1) Summary Overclaim
- Pattern: `"7 repos pass" => "system healthy"`
- Risk: turns slice-level evidence into full-system health claim.
- Guard: always attach scope and non-regression statement.

### 2) Direct Decision Consumption
- Pattern: `if token_observability_level == "coarse": block_release()`
- Risk: converts observational metadata into automated gate.
- Guard: prohibit decision path usage for token fields.

### 3) Soft Enforcement Proxy
- Pattern: `if provenance_warning != null: require_manual_review`
- Risk: hidden gating via mandatory routing.
- Guard: classify as forbidden consumer behavior.

### 4) Derived-Signal Bypass
- Pattern: `token_count -> cost_score -> ranking`
- Risk: bypasses source-field constraints through transformation.
- Guard: derived signals inherit non-authoritative constraints.

### 5) Citation Without Context
- Pattern: referencing pass/degraded/blocked without scope note.
- Risk: reviewer or management overreads confidence.
- Guard: citation requirement must include scope + non-authoritative + not-for-decision.

### 6) Environment Drift Blindness
- Pattern: no rerun because repo unchanged.
- Risk: provider/runtime drift silently changes observability behavior.
- Guard: run low-frequency sentinel validation every 7–14 days.

## Minimal Sentinel Policy
```yaml
sentinel_policy:
  frequency_days: 7-14
  scope: one representative repo per cycle
  purpose: detect environment drift only
  non_goal: full regression
```

## Citation Contract
Any external reference to token observability results MUST include:
- `distribution slice validation`
- `non-authoritative token observability`
- `not for decision usage`
