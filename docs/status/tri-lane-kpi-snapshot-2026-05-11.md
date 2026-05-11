# Tri-Lane KPI Snapshot (2026-05-11)

Date: 2026-05-11  
Window: Round A close window  
Owner: governance review

## 1) Same-Schema KPI Table

| Repo | Agent lane | engineering_runs_total | closeout_valid_total | closeout_missing_total | closeout_valid_ratio | mapped_high_total | mapped_high_ratio | triplet_complete_total | triplet_complete_ratio | scope_violation_total | claim_overreach_total | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `gl_electron_tool` | Copilot | 20 | 20 | 0 | 1.00 | 20 | 1.00 | N/A | N/A | 0 | 0 | Round A evaluator repaired (legacy normalization + 3 missing detail blocks backfilled); gate now PASS |
| `verilog-domain-contract` | Claude | 37 | 37 | 0 | 1.00 | 37 | 1.00 | 37 | 1.00 | 0 | 0 | run-028..037 pack completed; 37/37 accepted; Gate C still provisional |
| `Enumd` | ChatGPT | 15 | 15 | 0 | 1.00 | 15 | 1.00 | N/A | N/A | 0 | 0 | run-06..15 native closeout 10/10; window close criteria met |

## 2) P0 Gate A (Data Consistency) Check

| Check | Copilot | Claude | ChatGPT | Result |
|---|---|---|---|---|
| summary/detail counts consistent | pass | pass | pass | pass |
| mapped session id exists in session index | pass | pass | pass | pass |
| mapping-confidence reproducible with same inputs | pass | pass | pass | pass |

P0 status: **PASS**

## 3) Gate C Data Gap Register (Outcome Layer)

| Metric | Copilot | Claude | ChatGPT | Status |
|---|---|---|---|---|
| reviewer_edit_minutes | missing | missing | missing | open |
| reopen_count | missing | missing | missing | open |
| revert_count | missing | missing | missing | open |
| integration_stability_notes | partial | partial | partial | open |

Interpretation:
- Closed-loop quality is strong across lanes.
- Outcome-value decision remains provisional until Gate C measurements are instrumented.

## 4) Immediate P0 Follow-up Actions

1. Add lane-level reviewer effort capture (`minutes`) with fixed start/end rule.
2. Add reopen/revert counters per lane with same denominator (`total_changes`).
3. Publish next snapshot only if Gate A remains green.

