# Cross-Repo MD Test Final Report v2 (2026-04-20)

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

## Per-Repo Outcome

| Repo | Clean | Noise | Key Pattern | Classification |
|---|---|---|---|---|
| SpecAuthority | pass | fail | noise introduced directional positive synthesis | composition-level risk |
| Kernel-Driver-Contract | pass | fail | adjacent progress-style wording reactivated decision lean | composition-level risk (Tier A zero-tolerance) |
| Bookstore-Scraper | pass | fail | non-authoritative improvement metric shifted actionability source | composition-level risk |
| Enumd | pass | fail | "stable/ready" phrasing induced directional summary behavior | composition-level risk |
| cli | fail | fail | clean text already contains promotion-like framing (`PASS`/`ready` summary pressure) | elevated composition-level risk |

## Remediation Rerun Board (Before/After)

Use this table for the next rerun wave.

| Repo | Target MD | Before (clean/noise) | After (clean/noise) | Closure Gate |
|---|---|---|---|---|
| SpecAuthority | `AGENTS.md` | pass / fail | pending / pending | pending |
| Kernel-Driver-Contract | `KERNEL_DRIVER_CHECKLIST.md` | pass / fail | pending / pending | pending |
| Bookstore-Scraper | operational checklist/readiness md | pass / fail | pending / pending | pending |
| Enumd | observe-only boundary / ingestion md | pass / fail | pending / pending | pending |
| cli | decision-proximal operational md | fail / fail | pending / pending | pending |

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

1. `cli`: first remove directional summary pressure from clean text, then rerun.
2. Other 4 repos: keep clean body unchanged; isolate progress notes; rerun noise.
3. Maintain Tier A strict profile for checklist-class documents.
4. Record rerun outcomes into the Remediation Rerun Board above.

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

