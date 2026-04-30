# CodeBurn — Agent Navigation

> Phase 1: **CLOSED** (2026-04-30)
> Next: Phase 2 Token Observability Upgrade (entry criteria below)

---

## Entry Points (Phase 1)

| Purpose | File |
|---|---|
| Start here | `phase1/CODEBURN_PHASE1_STATUS.md` |
| Run analysis | `python phase1/codeburn_analyze.py --db <db>` |
| Run report | `python phase1/codeburn_report.py --db <db>` |
| Full gate | `python phase1/validate_phase1_data.py --db <db> --include-analysis` |
| Contract | `phase1/CODEBURN_PHASE1_ANALYSIS_CONTRACT.md` (v1.0.0) |
| Phase 2 limits | `phase1/CODEBURN_PHASE2_ENTRY_CONSTRAINTS.md` |
| Final closeout | `phase1/CODEBURN_PHASE1_FINAL_CLOSEOUT_2026-04-30.md` |

---

## What Phase 1 Can and Cannot Do

**Can observe:**
- Command execution lifecycle (start / end / step / recovery)
- Git-visible file changes per step
- Retry patterns (advisory signals only)
- Post-job analysis summary

**Cannot claim:**
- Waste detection or redundancy
- Token usage (unknown)
- Correctness or effectiveness judgment
- Optimization recommendations

---

## Permanent Phase 1 Invariants

These two fields are **always `false`** in all Phase 1 JSON output.
Do not change them without creating `CODEBURN_DECISION_AUTHORITY_CONTRACT.md`.

```json
"analysis_safe_for_decision": false
"decision_usage_allowed": false
```

Every CLI prints this to stderr on invocation:
```
CodeBurn Phase 1 | Status: CLOSED | Decision usage: NOT ALLOWED (analysis_safe_for_decision=false)
```

---

## Analysis Contract Summary (v1.0.0)

| § | Layer | Core Rule |
|---|---|---|
| 2 | Semantics | Observation-only; boundary footer mandatory |
| 3 | Signal | `derived_from_steps` required; advisory-only, no blocking |
| 4 | Determinism | Byte-for-byte; 4 ORDER BY rules; no runtime timestamp |
| 5 | Observability | `token_usage/file_reads/file_activity` declared in every output |
| 6 | Non-Claims | No waste/efficiency/correctness/cross-session claims |
| 7 | Amendment | Name + version + evidence; silent change = violation |

Enforcement (`codeburn_validate_analysis.py`) is fail-closed: exit 1 on any violation.

---

## Phase 2 Entry Criteria

All four must be satisfied before Phase 2 work begins:

- **P1** — 7 pytest test files pass in a clean environment
- **P2** — Forbidden phrase scanner excludes user metadata fields (L1 fix)
- **P3** — All Phase 2 extensions follow §7 amendment process
- **P4** — `validate_phase1_data.py --include-analysis` is the CI gate

Phase 2 may NOT change guard fields or add decision/recommendation output
without first creating a decision-authority contract.
See `phase1/CODEBURN_PHASE2_ENTRY_CONSTRAINTS.md` for full constraints.
