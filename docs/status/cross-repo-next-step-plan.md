# Cross-Repo Next Step Plan (Copilot + Claude)

Date: 2026-05-08  
Scope repos:
- `E:\BackUp\Git_EE\gl_electron_tool` (Copilot lane)
- `E:\BackUp\Git_EE\verilog-domain-contract` (Claude lane)

## Objective
Stabilize governance data quality first, then compare execution/audit maturity on the same KPI frame, then produce first ROI readout.

---

## Phase P0 — Data Consistency First (mandatory)

### P0.1 Single Source of Truth
- Treat **run-entry rows** as canonical source.
- Treat summary counters as derived output only.
- Do not manually edit summary counters.

### P0.2 Consistency Checks
For each repo, add/execute a check that validates:
- `summary.engineering_run_count == count(run_entry)`
- `summary.closeout_covered_runs == count(run_entry where closeout_covered=yes)`
- `summary.high_conf_mappings == count(run_entry where mapping_confidence=high)`

### P0 Exit Criteria
- No summary/detail mismatch.
- One rerun of the checker passes after a new run append.

---

## Phase P1 — Unified KPI Board (same schema for both repos)

## KPI Schema (weekly snapshot)
- `engineering_runs_total`
- `closeout_valid_total`
- `closeout_missing_total`
- `closeout_valid_ratio = closeout_valid_total / (closeout_valid_total + closeout_missing_total)`
- `mapped_high_total`
- `mapped_high_ratio = mapped_high_total / engineering_runs_total`
- `triplet_complete_total` (run-record + scorecard + diff.patch)
- `triplet_complete_ratio`
- `scope_violation_total`
- `claim_overreach_total`

## Interpretation
- Execution maturity: high `closeout_valid_ratio`
- Audit maturity: high `mapped_high_ratio` + high `triplet_complete_ratio`
- Governance quality: low `scope_violation_total` and `claim_overreach_total`

---

## Phase P2 — 1-Week Stability + ROI Readout

## Run Policy (freeze feature scope)
- No new governance features.
- No new enforcement gates.
- Run only operational stabilization and mapping completion.

## Minimum New Evidence
- `gl_electron_tool`: +5 semantic runs, each with same-repo valid closeout and ledger mapping attempt.
- `verilog-domain-contract`: +5 runs (or equivalent closeout/mapping updates) under same KPI schema.

## ROI Questions
- Did reviewer-facing uncertainty reduce?
- Did run-to-closeout-to-ledger latency improve?
- Is governance overhead bounded relative to auditability gains?

## Output Artifact
- `docs/status/cross-repo-governance-roi-week1.md`
  - KPI table (both repos)
  - key gains
  - friction costs
  - keep / adjust / drop decisions

---

## Repo-Specific Immediate Actions

## A) `gl_electron_tool`
1. Fix summary/detail counter mismatch in `docs/ab-v1.2-run-ledger.md`.
2. Add automated counter reconciliation script (or deterministic regeneration step).
3. Backfill existing runs that already have valid sessions but no high-confidence mapping.

## B) `verilog-domain-contract`
1. Maintain triplet completeness at 100%.
2. Increase proportion of runtime-native `valid` sessions where possible (reduce reliance on reconstructed sessions for new runs).
3. Keep dashboard and run-ledger aligned with session-index after each run.

---

## Governance Rule For This Week
- Prioritize **completion quality** over raw run volume.
- A run counts as “done” only when:
  - semantic slice commit exists
  - same-repo valid closeout exists
  - intent/time linkage is compatible
  - ledger has `closeout_covered=yes` and `mapping_confidence=high`

---

## After All Three Lanes Are Established (Copilot + Claude + ChatGPT)

Next step is **cross-agent outcome validation**, not new governance feature expansion.

1. Build one same-day KPI snapshot for all three lanes
- use one schema (`kpi-snapshot-template.md`)
- compare `closeout_valid_ratio`, `mapped_high_ratio`, `scope_violation_total`, `claim_overreach_total`, reviewer burden fields

2. Enforce summary/detail consistency checks in each lane (advisory first)
- summary counters must match detail rows
- mapped session ids must exist in session-index with compatible status/intent

3. Run a 3x3 comparable task set
- each lane executes the same three bounded task types:
  - docs consistency patch
  - claim-boundary wording patch
  - small cross-file sync patch

4. Produce first cross-agent ROI readout
- include reviewer time, reopen/revert signals, and integration stability
- decision output: `keep / adjust / drop`

Decision boundary:
- if mapping quality is unstable, fix process before adding governance features
- if quality stabilizes across all lanes, open Round B (hostile ambiguity + ablation)
