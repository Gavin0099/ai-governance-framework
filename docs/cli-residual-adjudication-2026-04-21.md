# CLI Residual Adjudication Note (2026-04-21)

Purpose: adjudicate residual family attribution before remediation.

Input:

- `docs/cli-residual-classification-2026-04-21.md`
- `artifacts/md_noise_rerun_report_2026-04-21.json`

## Adjudication Matrix

| File | Preferred Interpretation | Competing Interpretation | Why Not Concluded Yet |
|---|---|---|---|
| `Doc/adoption-test-report-2026-04-14.md` | `F-REFERENCE-EXEMPTION-GAP`: `ready=False` appears as status-key literal in output/table contexts | `F-CLEAN-LEXICAL-RESIDUAL`: lexical token may still act as directional cue under actionability context | Need boundary evidence proving status-key literal contexts are exempt while abusive reference wrappers still fail |
| `Doc/md-test-20260420-001.md` | mixed: `F-REFERENCE-EXEMPTION-GAP` for rubric/schema literals + possible `F-CLEAN-LEXICAL-RESIDUAL` for policy-meta wording | pure content defect only | Need phrase-level adjudication after boundary tests; current trigger set includes prompt/schema literals and policy-note wording in same file |

## Trigger-Level Adjudication

### A) `Doc/adoption-test-report-2026-04-14.md`

| Trigger (Observed) | Evidence | Family Decision | Rationale |
|---|---|---|---|
| `ready = False` in fenced output block | file lines around `74` (`ready = False`) | `reference-exemption gap` | status-key literal, not recommendation language |
| `readiness` in table label (`overall readiness status`) | file line around `87` | `mixed` (leaning content lexical) | table label word can be rewritten without changing fact payload |
| `closeout_*` tokens causing actionability context | file lines around `288`, `297` | `reference-exemption gap` | appears as log/status field names, not imperative instruction |

### B) `Doc/md-test-20260420-001.md`

| Trigger (Observed) | Evidence | Family Decision | Rationale |
|---|---|---|---|
| rubric literals (`improvement/stability/readiness/forward progress`) | file line around `486` | `reference-exemption gap` | prompt/rubric literal, should be treated as test text |
| schema labels (`Pass/Fail`, `classification_outcome`) | file lines around `514`, `546`, `550` | `reference-exemption gap` | result-schema literal, not directional recommendation |
| recommendation text (`proceed to merge`, `must be added before merge`) | file lines around `528`, `558` | `true content defect` | explicit action-pressure wording under actionability context |
| policy-meta sentence (`forward-progress signals`) | file line around `554` | `true content defect` | narrative framing that can bias decision interpretation |

## Adjudication Result (This Pass)

- `Doc/adoption-test-report-2026-04-14.md`:
  - primary family = `F-REFERENCE-EXEMPTION-GAP`
  - secondary residual = `F-CLEAN-LEXICAL-RESIDUAL` (table label wording)
- `Doc/md-test-20260420-001.md`:
  - mixed residual confirmed:
    - literal/schema portion = `F-REFERENCE-EXEMPTION-GAP`
    - recommendation/meta wording = `true content defect`

## Post-Remediation Replay (Same Contract)

- runner: `scripts/run_md_noise_test.py` (sha256 `5096758552b83d4ad4fbe4c2614cffcd968903d044a25e2c38c0c7779922babf`)
- artifact: `artifacts/md_noise_rerun_report_2026-04-21.json`
- replay outcome:
  - `SpecAuthority`: pass
  - `Kernel-Driver-Contract`: pass
  - `Bookstore-Scraper`: pass
  - `Enumd`: pass
  - `cli`: pass

Conclusion:

- under the current contract, residual attribution is now resolved enough to
  clear closure gates (`5/5 pass`).
- remaining future work is contract adequacy hardening, not current closure
  remediation.

## Boundary Evidence Requirement

For the reference-exemption family, evidence must cover:

1. canonical exempt case: pass
2. near-boundary case: explicit pass/fail decision
3. abusive reference case: fail

## Status

- current leading interpretation has been refined to trigger-level attribution
- competing interpretation was reduced by harness-side literal handling and
  minimal content-side cleanup
- boundary-evidence pack is now available in `tests/test_md_noise_oracle_harness.py`
  (`8 passed`)
- same-contract replay executed: closure gates now pass for all five repos

## Minimal Remediation Candidates (Not Applied Yet)

1. Harness-side candidate:
   - exempt fenced status/output blocks and schema-literal sections from
     directional/actionability extraction.
2. Content-side candidate (`cli` docs only):
   - replace table label wording like `readiness status` with neutral
     `status key/value`.
   - remove recommendation-pressure wording in
     `Doc/md-test-20260420-001.md` (for example `proceed to merge`, `must be
     added before merge`) while preserving blocker facts.
