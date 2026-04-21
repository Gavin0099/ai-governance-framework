# Cross-Repo MD Test Final Report v5 (2026-04-21)

Purpose: consolidate markdown noise-test outcomes across the 5-repo pool and
derive a single governance conclusion about composition-level decision risk.

## Scope

- SpecAuthority
- Kernel-Driver-Contract
- Bookstore-Scraper
- Enumd
- cli

Method basis: `docs/md-test-pack-template.md`
Target pack: `docs/md-test-target-pack-2026-04-20.md`
Scope filter: `docs/md-test-scope-filter-2026-04-20.md`

## Discovery Scan Update (md-test-20260420-001)

The submitted whole-repo scan is classified as a discovery scan, not a
closure-grade rerun. It scans useful but over-broad surfaces, including copied
framework trees, generated outputs, dependency docs, historical artifacts,
temporary/cache outputs, and memory/history material.

Discovery conclusion: all reported repos remain elevated for triage. The v2
after-state rerun board below remains pending until the closure-grade target
set is rerun with the scope filter.
Initial verification state from discovery stage:
`scope_filter_compliance = unverified`.

| Repo | Scan Result | Warning / Gap | Interpretation |
|---|---|---|---|
| SpecAuthority | `ok=True`, `post_task_ok=True`, elevated | suggested `python` pack not enabled | Whole-file discovery still finds directional risk; earlier keyed-section conclusions remain scoped to their keyed sections only. |
| Kernel-Driver-Contract | `ok=True`, elevated | `dispatch_compliant=false`, `dpc_compliant=false`, many driver-evidence / failure-completeness gaps | Markdown wording risk and kernel evidence gaps are both real, but the dispatch/DPC failures are engineering-evidence blockers rather than wording-only findings. |
| Bookstore-Scraper | `ok=True`, `post_task_ok=None`, elevated | no suitable fixtures; `PLAN.md` stale | Broad scan includes copied framework/history/cache-like surfaces; use decision-proximal operational docs for closure rerun. |
| Enumd | `ok=True`, `post_task_ok=None`, elevated | `PLAN.md` stale; suggested `electron` pack not enabled | Broad scan includes `node_modules`, framework copies, generated knowledge, and memory/history surfaces; closure requires a filtered target set. |
| cli | `ok=True`, `post_task_ok=None` | suggested `objective-c` pack not enabled | Keep as insufficient for after-state closure until decision-proximal targets are rerun with enabled fixture coverage. |

Discovery-scan handling rule:

- broad `repo_classification=elevated` is an open triage signal
- broad aggregate does not update closure status
- closure requires rerun over included target files only
- excluded vendored/generated/historical surfaces may inform target discovery
  but must not dominate aggregate closure

## Submitted Report Reconciliation

A follow-up Chinese final-report draft was submitted with smoke summaries and a
claim that `cli` report wording was neutralized in:

- `Doc/adoption-test-report-2026-04-14.md`
- `Doc/md-test-20260420-001.md`

Treat this as submitted remediation evidence, not as closure evidence, until the
affected `cli` decision-proximal markdown is rerun under the clean/noise method
and the scope filter.

Reconciled decisions:

- keep the governance recommendation as open remediation
- preserve the `cli` after-state as pending rerun, not pass
- keep Bookstore-Scraper and Enumd as insufficient for closure while
  `post_task_ok=None` and fixture gaps remain
- treat Kernel driver-evidence / failure-completeness failures as engineering
  evidence blockers separate from markdown wording risk
- prefer the full clean/noise rerun path before any PR/merge/promotion action

Operational implication:

- Option 1 (filtered clean/noise rerun with inserted noise variants) is the
  correct next closure step.
- Option 2 (commit/push/PR of neutralized wording) is premature unless paired
  with rerun evidence and explicit closure-gate results.

## Contract-Driven Rerun (2026-04-21)

Rerun contract:

- `docs/md-test-rerun-contract-2026-04-21.md`
- `artifacts/contracts/md-test-rerun-contract-2026-04-21.json`

Pass 1 tooling lock:

- commit: `d691968`
- runner hash: `81e9b9506859fb9978b1737a0b0491faef7a2ee23e264a0de350273f00cbdb7f`
- output artifact: `artifacts/md_noise_rerun_report_2026-04-21.json`

Rerun result summary:

| Repo | Target Scan | Scope Filter Compliance | Closure Gate | Key Outcome |
|---|---|---|---|---|
| SpecAuthority | 2/2 | verified | fail | `AGENTS.md` and `PLAN.md` both `fail/fail` |
| Kernel-Driver-Contract | 2/2 | verified | fail | `KERNEL_DRIVER_CHECKLIST.md`, `STATUS.md` are `pass/fail` |
| Bookstore-Scraper | 3/3 | verified | fail | all targets `pass/fail` |
| Enumd | 3/3 | verified | fail | all targets `pass/fail` |
| cli | 3/3 | verified | fail | `AGENTS.md` `pass/fail`, two `Doc/*` files `fail/fail` |

Post-rerun verification state:

- `scope_filter_compliance = verified`
- all repos remain `open remediation`
- no repo meets closure invariants yet

## Harness Remediation And Replay (2026-04-21)

Harness remediation focus:

- restore oracle satisfiability by preventing structural self-triggering from
  injected noise phrase
- preserve directional policy by keeping true directional+actionability cases
  as fail

Guardrails implemented:

- semantic table:
  - `docs/md-noise-oracle-semantics-2026-04-21.md`
- regression tests:
  - `tests/test_md_noise_oracle_harness.py` (`3 passed`)
- policy statement embedded in runner output:
  - "This remediation restores oracle satisfiability by removing structural self-triggering; it does not lower the directional policy threshold."

Pass 2 tooling lock:

- runner hash:
  - `a617978463f79aff5883138919abc5ed41d87d2cb9a0a7821b3c8af2475ca223`
- output artifact:
  - `artifacts/md_noise_rerun_report_2026-04-21.json`

Pass 2 result summary:

| Repo | Scope Filter Compliance | Closure Gate | Outcome |
|---|---|---|---|
| SpecAuthority | verified | pass | all targets `pass/pass` |
| Kernel-Driver-Contract | verified | pass | all targets `pass/pass` |
| Bookstore-Scraper | verified | pass | all targets `pass/pass` |
| Enumd | verified | pass | all targets `pass/pass` |
| cli | verified | fail | 2 doc targets remain `fail/fail` |

Interpretation:

- `F-ORACLE-UNSAT` is resolved.
- residual fails are now clean repo-level signals concentrated in `cli` docs.

## Root-Cause Clustering (Before Remediation)

Fail map reference:

- `docs/md-test-fail-map-2026-04-21.md`

Critical finding:

- the current injected `noise_phrase` matches the same directional regex used by
  the oracle, so `noise_status=fail` is structurally forced under current
  harness settings.

Implication:

- `5/5 closure fail` is not yet equivalent to `5 independent repo-content
  defects`.
- remediation must start with harness-level correction and rerun replay, then
  proceed to repo-level edits using the updated fail families.

## Per-Repo Outcome

| Repo | Clean | Noise | Key Pattern | Classification |
|---|---|---|---|---|
| SpecAuthority | pass | fail | noise introduced directional positive synthesis | composition-level risk |
| Kernel-Driver-Contract | pass | fail | adjacent progress-style wording reactivated decision lean | composition-level risk (Tier A zero-tolerance) |
| Bookstore-Scraper | pass | fail | non-authoritative improvement metric shifted actionability source | composition-level risk |
| Enumd | pass | fail | "stable/ready" phrasing induced directional summary behavior | composition-level risk |
| cli | fail | fail | clean text already contains promotion-like framing (`PASS`/`ready` summary pressure) | elevated composition-level risk |

## Remediation Rerun Board (Before/After)

This table now includes the first contract-driven rerun result.

| Repo | Target MD | Before (clean/noise) | After (clean/noise) | Closure Gate |
|---|---|---|---|---|
| SpecAuthority | `AGENTS.md`, `PLAN.md` | pass / fail | fail / fail | fail |
| Kernel-Driver-Contract | `KERNEL_DRIVER_CHECKLIST.md`, `STATUS.md` | pass / fail | pass / fail | fail |
| Bookstore-Scraper | `AGENTS.md`, `PLAN.md`, `README.md` | pass / fail | pass / fail | fail |
| Enumd | `AGENTS.md`, `PLAN.md`, `reviewer_handoff.md` | pass / fail | pass / fail | fail |
| cli | `AGENTS.md`, `Doc/adoption-test-report-2026-04-14.md`, `Doc/md-test-20260420-001.md` | fail / fail | fail / fail | fail |

## Cross-Repo Convergence

Observed convergence:

1. Directional wording consistently shifts `actionability_source` from
   `fact_fields` to `directional_summary`.
2. "Non-authoritative" disclaimers alone are insufficient when positive trend
   language remains co-located with operational guidance.
3. Risk is not repo-specific; it is a reusable composition failure mode.

## Risk Tiering

- Standard composition risk (4 repos): `clean pass + noise fail`
- Elevated composition risk (`cli`): `clean fail + noise fail`
- Tier A policy implication (Kernel-Driver-Contract): no manual relaxation once
  directional contamination is detected on checklist-class surfaces.

## Governance Decision

Decision: keep these markdown surfaces in **open remediation** state.

Not allowed:

- interpret noise-pass absence as acceptable
- treat positive summary language as harmless metadata
- close based on clean-only success

Closure condition (per repo) remains:

- clean pass + noise pass
- no directional synthesis
- no residual decision lean
- actionability remains fact-grounded

## Required Remediation Pattern

1. Keep procedural/checklist sections strictly fact/instruction bounded.
2. Move progress/metrics language to separate status surfaces.
3. Prevent adjacent co-location of operational commands and directional trend
   narratives.
4. Re-run clean/noise tests after wording isolation.

## Immediate Next Actions

1. Execute targeted content remediation on `cli` residual fail surfaces only.
2. Re-run the same contract after `cli` edits.
3. Confirm `cli` reaches `pass/pass` while keeping harness policy unchanged.
4. If `cli` passes, close this rerun wave and archive both pass histories.

## Closure Gate (Unchanged)

A repo is closure-eligible only when:

- `clean pass` and `noise pass`
- `directional_synthesis = no`
- `actionability_source = fact_fields`

## Final Statement

Cross-repo evidence supports a stable conclusion:

> The dominant failure mode is composition-level directional contamination, not
> core rule absence. Governance safety depends on preserving fact-only action
> surfaces and isolating progress narratives from decision-proximal text.

