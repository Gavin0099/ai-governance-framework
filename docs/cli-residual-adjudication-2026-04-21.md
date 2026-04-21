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

## Boundary Evidence Requirement

For the reference-exemption family, evidence must cover:

1. canonical exempt case: pass
2. near-boundary case: explicit pass/fail decision
3. abusive reference case: fail

## Status

- current leading interpretation exists per file
- competing interpretation remains plausible
- boundary-evidence pack is now available in `tests/test_md_noise_oracle_harness.py`
  (`6 passed`)
- final attribution remains pending same-contract replay after adjudication
  decision
