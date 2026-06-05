# Copilot UI Credit Observation Classification Summary

## Scope

This artifact records a manual classification baseline for visible Copilot UI
credit observations pasted by the user for 2026-06-01 through 2026-06-03.

Source attachments:

- `C:\Users\reiko\.codex\attachments\0ac15e9c-3e35-4f5b-9dcf-ccaec5fa8779\pasted-text.txt`
- `C:\Users\reiko\.codex\attachments\368b6bd2-5cb7-4dfd-9eb4-c71c7421a9dc\pasted-text.txt`
- `C:\Users\reiko\.codex\attachments\e4e9c96a-7809-460e-a708-274783e3123d\pasted-text.txt`

## Claim Ceiling

CLAIMED:

- 59 visible `GPT-5.3-Codex ... credits` UI observations were extracted.
- A manual observation-level classification baseline was created.
- The classification separates formal-test candidates from checkpoint,
  artifact-generation, diagnostic, state-reconstruction, implementation, and
  build/test-loop observations.

NOT CLAIMED:

- GitHub billing truth.
- Token count.
- Final invoice mapping.
- One-to-one mapping between 31 formal test runs and the 32 visible 2026-06-01
  observations.
- Workflow threshold.
- Budget policy.
- Automated classifier correctness.

## Aggregate Statistics

| Date | Observations | Total credits | Average | Median | Max | >=50 | >=100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-06-01 | 32 | 1503.8 | 46.99 | 34.45 | 156.3 | 10 | 4 |
| 2026-06-02 | 10 | 478.1 | 47.81 | 48.45 | 100.8 | 5 | 1 |
| 2026-06-03 | 17 | 686.9 | 40.41 | 30.60 | 147.7 | 4 | 1 |
| Total | 59 | 2668.8 | 45.23 | 37.30 | 156.3 | 19 | 6 |

## High-Cost Observations

The visible >=100 credit observations are:

- 2026-06-01 #5: 152.8, driver diagnostic, cross-layer driver/preflight analysis.
- 2026-06-01 #7: 108.8, implementation multi-layer, Slice 1 service/tests/contracts.
- 2026-06-01 #11: 156.3, qualification readiness, compacted broader qualification.
- 2026-06-01 #15: 112.0, state reconstruction, compacted Slice 2 context.
- 2026-06-02 #5: 100.8, implementation multi-layer, Avalonia/Electron/driver build context.
- 2026-06-03 #3: 147.7, state reconstruction, compacted build/driver/governance context.

## Current Reading

The visible cost concentration is not evenly distributed across all usage. The
highest observations cluster around long-context or compacted continuations,
cross-layer driver/Avalonia/Electron diagnostics, implementation plus tests and
evidence, and qualification/readiness artifact work.

The manual classification table should be treated as a baseline for deciding
where to spend deeper analysis effort. It is not sufficient for billing
thresholds or workflow policy.

## Next Analysis Step

Recommended next step:

1. Compute per-`task_class` median and p90.
2. Separate `is_formal_test_run=yes` from `no` and `unknown`.
3. Inspect only the `>=100` rows for useful-outcome value before proposing any
   cost-reduction policy.
