# MD Test Fail Map (2026-04-21)

Purpose: cluster first rerun failures before repo-level remediation.

Input evidence (pre-harness-fix):

- `artifacts/md_noise_rerun_report_2026-04-21.json`
- runner hash:
  - `81e9b9506859fb9978b1737a0b0491faef7a2ee23e264a0de350273f00cbdb7f`

## Fail Clustering (Pre-Harness Fix)

| Repo | Fail Surface | Suspected Root Cause Family | Recommended Remediation Layer |
|---|---|---|---|
| all 5 repos | all targets `noise_status=fail` | `F-ORACLE-UNSAT`: injected `noise_phrase` itself matches directional regex, so noise pass is structurally impossible in current harness | test harness fix |
| SpecAuthority | `AGENTS.md`, `PLAN.md` clean fail | `F-CLEAN-LEXICAL`: clean text contains directional tokens under current lexical rule | content fix (after harness fix) |
| cli | `Doc/adoption-test-report-2026-04-14.md`, `Doc/md-test-20260420-001.md` clean fail | `F-CLEAN-LEXICAL`: clean text still contains directional tokens under current lexical rule | content fix (after harness fix) |
| Kernel-Driver-Contract, Bookstore-Scraper, Enumd, cli(`AGENTS.md`) | clean pass but noise fail | `F-NOISE-SENSITIVITY` currently dominated by `F-ORACLE-UNSAT`; cannot separate real adjacency sensitivity until harness fix | test harness fix first, then rerun |
| all 5 repos | closure gates all fail | Composite projection of `F-ORACLE-UNSAT` + limited clean lexical fails | harness first, then repo content remediation |

## Interpretation

- Current 5/5 fail does not decompose cleanly into 5 independent repo problems.
- The dominant blocker is harness-level: unsatisfiable noise invariant with the
  current injected phrase and detection method.
- Repo content remediation done before harness correction will likely optimize
  for this test artifact instead of governance intent.

## Next Execution Order

1. Fix harness so injected noise can be present without forcing automatic fail.
2. Freeze updated harness/version hash.
3. Rerun the same contract.
4. Re-cluster fails into content/document-structure/policy families.
5. Only then execute repo-level wording remediation.

## Post-Harness Rerun Snapshot

Input evidence (post-harness-fix):

- `artifacts/md_noise_rerun_report_2026-04-21.json`
- runner hash:
  - `451995965f40a64cfa60e9d558f6e5c22bf6411be46bca2f4699a94cda6ef026`

Post-harness clustering:

| Repo | Fail Surface | Root Cause Family | Recommended Remediation Layer |
|---|---|---|---|
| SpecAuthority | none | cleared | none |
| Kernel-Driver-Contract | none | cleared | none |
| Bookstore-Scraper | none | cleared | none |
| Enumd | none | cleared | none |
| cli | `Doc/adoption-test-report-2026-04-14.md`, `Doc/md-test-20260420-001.md` (`fail/fail`) | `F-REFERENCE-EXEMPTION-GAP` (with possible `F-CLEAN-LEXICAL-RESIDUAL`) | residual classification first, then minimal harness/content fix by family |

Validation outcome:

- `F-ORACLE-UNSAT` no longer holds.
- true directional cases still fail under actionability context.
- residual failures are interpretable and currently concentrated in `cli`, but
  still require doc-level residual classification before final layer assignment.
