# Enumd P1.5 Milestone Note (2026-04-21)

## Scope

This note records the P1.5 advisory-only chain completion for runtime/summary/consumer surfaces.

## Commits

- origin/main: `9c7ebb1` (`Expose review-required visibility in cross-repo summary`)
- gitlab/main mirror: `9f82dea` (same scope, GitLab-author mirror)
- upstream baseline in this chain: `dfa191a` / `b867605` (`P1.5 runtime advisory instrumentation landed`)

## Landed Scope

- cross-repo summary visibility only for:
  - `review_required_sample_count`
  - `review_required_sample_ids`
  - `review_required_advisory_only`
- consumer-side anti-escalation guard tests added
- no `risk_tier` change
- no gate/verdict promotion
- no `closure_gate` semantic rewrite

## Excluded From This Milestone

- `artifacts/md_noise_test_report_2026-04-20.json` (untracked, intentionally excluded)

## Interpretation Guard

`review_required_sample_count` is a visibility metric, not a severity metric and not an escalation metric.
This milestone does NOT introduce semantic reclassification or gate enforcement.
