# CodeBurn Copilot Real CSV Qualification Checkpoint (2026-06-02)

Purpose: define the next mandatory step before any Copilot billing observation can be claimed as operational.

This checkpoint does NOT add features or upgrade authority.
It records the current readiness ceiling and the qualification gate that must be passed.

Authority boundary unchanged:
- analysis_safe_for_decision=false
- decision_usage_allowed=false
- Decision authority: none

---

## Current Readiness Assessment

### Structural Readiness: YES
The ingestor has been verified to handle the following fixture categories:
- empty CSV
- all-quarantined rows
- missing required column (silent exit, known gap)
- negative aic_quantity (quarantine + admit split)
- date format variation (MM/DD/YYYY → YYYY-MM-DD normalization)
- multi-model mix (independently admitted, CP-2 boundary enforced at query layer)
- duplicate rows (dedup operational)

### Operational Readiness: NO
A real GitHub Copilot billing CSV has never been ingested.
The following are unknown until real CSV qualification is complete:
- actual export column names and order
- whether GitHub's export format matches ingestor column assumptions
- whether real data produces unexpected quarantine patterns
- whether any real rows trigger schema violations not covered by fixtures

### Correct Claim Ceiling (Current)
> CodeBurn Copilot ingestor is synthetic-fixture validated.
> Operational readiness is NOT claimed until real CSV format qualification is complete.

### Incorrect Claims (Still Forbidden)
- "Copilot billing tracking is working."
- "Copilot token usage is measurable."
- "Copilot cost attribution is available."
- "Copilot model-level cost analysis is supported."
- "ingestor is ready" (implies operational readiness)

---

## Next Step: Copilot Real CSV Qualification Pass

### DONE Definition

A real GitHub Copilot billing CSV has been ingested into
`artifacts/codeburn_copilot_real.db`, with a qualification receipt
(`artifacts/codeburn_copilot_real_qualification.json`) proving:

1. accepted row count
2. quarantined row count
3. observed column names
4. forbidden-column absence/presence result
5. model grouping behavior (models seen)
6. completions_excluded=1 on all accepted rows
7. aic_gross_amount not ingested
8. cross-model aic_quantity sum not produced
9. decision authority remains none

### Qualification Receipt Path
`artifacts/codeburn_copilot_real_qualification.json`
(skeleton committed in this checkpoint)

### Five Qualification Questions
After ingesting real CSV, answer only these five before proceeding:

1. Do real CSV column names match ingestor assumptions?
2. How many rows were accepted?
3. How many rows were quarantined?
4. Are quarantine reasons within expected categories (negative aic / missing login / non-numeric)?
5. Is decision_authority still none?

### Command
```bash
python codeburn/phase2/copilot_billing_ingestor.py \
  --csv <github_org_export.csv> \
  --db artifacts/codeburn_copilot_real.db
```

### How to Export from GitHub
GitHub Org → Settings → Billing & plans → Copilot → Export usage

---

## Hard Constraints (Unchanged)

| Constraint | Rule |
|---|---|
| CP-1 | aic_quantity is NOT a token count — no pricing rate may be applied |
| CP-2 | Cross-model aic_quantity aggregation is FORBIDDEN |
| CP-3 | billing_report_daily_aggregate schema only |
| C-1 | aic_gross_amount column FORBIDDEN from ingestion |
| completions_excluded | Enforced =1 on every accepted row |
| claim ceiling | analysis-only; no decision authority |

---

## Capability Status (This Checkpoint)

| Layer | Status |
|---|---|
| Ingestor structure | synthetic-fixture validated |
| Real CSV format | UNVERIFIED |
| Real column names | UNKNOWN |
| Real quarantine pattern | UNKNOWN |
| Operational readiness | NOT CLAIMED |
| Decision authority | none |

---

## After Qualification Pass

Only after qualification receipt is produced may the claim ceiling advance to:

> `real_csv_format_qualified_analysis_only`

The step after that (not in scope here) would be:

> Copilot Billing Observation Report v0.1

This requires at minimum 2-3 real billing export cycles and explicit semantic documentation
of what aic_quantity represents per model. Not to be started until qualification pass is complete.
