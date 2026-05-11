# Round A Next-Phase Test Playbook

Date: 2026-05-11  
Scope: Copilot / Claude / ChatGPT lanes

## 1) Purpose

Validate engineering outcome value, not language-style convergence only.

## 2) Source of Truth

- Runtime session existence: `docs/status/*-session-index.md`
- Run-level outcome and mapping: `docs/status/*-run-ledger.md`
- Summary metrics: must be generated from detail-level records, not manually overridden

## 3) Gate Model

### Gate A: Data Consistency (blocking)

All must pass before merge/rollout decision:

1. Summary/detail counts are consistent
2. Every mapped session id exists in runtime session index
3. Mapping confidence rule is reproducible with the same inputs

### Gate B: Closed-Loop Quality (monitoring)

Track continuously; block expansion if sustained degradation is detected:

1. Completion contract pass ratio
2. Native closeout ratio
3. Mapped-high ratio

### Gate C: Outcome Value (decision gate)

Periodic decision review:

1. Reviewer edit effort trend
2. Reopen/revert rate trend
3. Integration stability trend

## 4) Metric Definitions (fixed across lanes)

Use the same denominator and time window across Copilot / Claude / ChatGPT.

1. `completion_contract_pass_ratio = pass_runs / eligible_runs`
2. `native_closeout_ratio = native_source_runs / total_runs`
3. `mapped_high_ratio = high_confidence_runs / total_runs`
4. Reviewer effort unit: minutes, same start/end timing rule
5. `reopen_revert_rate = (reopen_count + revert_count) / total_changes`

## 5) Minimum Test Package Execution Order

1. Cross-agent 3x3 comparable task set
2. Small high-ambiguity stress set
3. Ablation set

### 5.1 Cross-agent 3x3 Comparable Task Set

- Docs consistency patch
- Claim-boundary wording patch
- Small cross-file sync patch

### 5.2 High-Ambiguity Stress Set (small)

- Authority-conflict phrasing
- Stale-evidence reference
- Lifecycle-ambiguity phrasing

### 5.3 Ablation Set

- No governance vocabulary
- Docs governance only
- Runtime hooks only
- Full governance contract

## 6) Expansion vs Pause Criteria

### Expand rollout only when all are true

1. Data consistency checks continue to pass without manual repair
2. Closed-loop quality ratios remain at/above target thresholds
3. Reviewer burden is flat or lower
4. No evidence of cosmetic-language gains masking process drift

### Pause and fix process when any is true

1. Summary/detail mismatch reappears
2. Native closeout ratio drops below threshold
3. Reviewer burden rises with no outcome improvement

## 7) Alerting Rule (recommended defaults)

1. Any summary/detail mismatch: immediate red alert
2. Native closeout below threshold:
   - 2 consecutive runs: yellow
   - 3 consecutive runs: red and pause expansion
3. Reviewer effort up + no outcome gain for one observation window: pause expansion

## 8) Round A Review Template (fill this directly)

### 8.1 Window

- Window id: `round-a-chatgpt-native-window-2026-05-11`
- Start run: `run-06`
- End run: `run-15`
- Lanes covered: `ChatGPT` (Copilot/Claude pending same-form ingest)

### 8.2 Gate A: Data Consistency

1. Summary/detail count consistency: pass
2. Session-id existence integrity: pass
3. Mapping-confidence reproducibility: pass
4. Notes: Observation-window detail rows (run-06..run-15) align with summary aggregates; mapped session ids exist in `chatgpt-lane-session-index.md`; all rows are `closeout_covered=yes` and `mapping_confidence=high` with consistent rule outcome.

Gate A result: pass

### 8.3 Gate B: Closed-Loop Quality

1. Completion contract pass ratio: `1.00` (10/10)
2. Native closeout ratio: `1.00` (10/10)
3. Mapped-high ratio: `1.00` (10/10)
4. Thresholds met: yes
5. Notes: Matches `enumd-chatgpt-lane-15-run-summary.md` gate checks for run-06..run-15 (`closeout_valid_ratio >= 0.85`, `mapped_high_ratio >= 0.80`, native requirement `>= 8/10`).

Gate B result: pass

### 8.4 Gate C: Outcome Value

1. Reviewer effort trend: unknown (not captured in this window)
2. Reopen/revert trend: unknown (not captured in this window)
3. Integration stability trend: flat (no instability signal recorded in current status artifacts)
4. Outcome uplift evidence: partial
5. Notes: Current repo artifacts provide strong closure/mapping quality evidence, but reviewer-effort and reopen/revert baselines are not yet instrumented per lane for a full outcome-value decision.

Gate C result: provisional-pass (data gap)

### 8.5 Ablation Readout

1. No governance vocabulary vs full contract:
2. Docs-only governance vs full contract:
3. Runtime-hooks-only vs full contract:
4. Main uplift driver inference:
5. Cosmetic-gain risk detected: yes/no

### 8.6 Final Decision

1. Decision: expand/pause
2. Decision date:
3. Owner:
4. Rationale (short):
5. Required follow-up actions:
