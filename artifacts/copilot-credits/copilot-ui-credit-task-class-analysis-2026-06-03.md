# Copilot UI Credit Task-Class Analysis

## Scope

This artifact analyzes the 59-row manual classification baseline in:

`artifacts/copilot-credits/copilot-ui-credit-observations-2026-06-01_to_2026-06-03.csv`

The analysis is observation-level only. It does not use GitHub billing export,
invoice data, token counts, or provider-side attribution.

## Claim Ceiling

CLAIMED:

- Per-`task_class` observation statistics were computed from the 59-row CSV.
- `>=100 credits` observations were reviewed for useful-outcome classification.
- Compacted versus non-compacted observation statistics were compared.
- Formal-test-run candidates were separated from non-test and unknown rows.

NOT CLAIMED:

- Billing truth.
- Token count.
- Final invoice mapping.
- Exact 31-test-run mapping.
- Automated classification correctness.
- Workflow policy.
- Budget threshold.

## Per-Task-Class Statistics

P90 uses nearest-rank selection on each sorted task-class sample. Small groups
should be treated as directional only.

| task_class | n | sum | avg | median | p90 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| artifact_generation | 9 | 345.1 | 38.34 | 32.80 | 73.4 | 73.4 |
| build_test_loop | 17 | 600.5 | 35.32 | 30.60 | 60.4 | 63.0 |
| closeout_or_checkpoint | 4 | 55.4 | 13.85 | 5.85 | 41.8 | 41.8 |
| commit_push | 3 | 103.8 | 34.60 | 52.80 | 52.8 | 52.8 |
| docs_governance | 3 | 57.5 | 19.17 | 24.10 | 24.1 | 24.1 |
| driver_diagnostic | 8 | 385.6 | 48.20 | 38.25 | 152.8 | 152.8 |
| implementation_multi_layer | 4 | 372.5 | 93.12 | 99.65 | 108.8 | 108.8 |
| implementation_single_slice | 3 | 127.2 | 42.40 | 45.40 | 45.4 | 45.4 |
| qualification_readiness | 4 | 282.9 | 70.72 | 49.05 | 156.3 | 156.3 |
| state_reconstruction | 4 | 338.3 | 84.57 | 79.50 | 147.7 | 147.7 |

## Formal-Test-Run Split

| is_formal_test_run | n | sum | avg | median | max |
| --- | ---: | ---: | ---: | ---: | ---: |
| no | 30 | 1083.7 | 36.12 | 29.85 | 152.8 |
| unknown | 6 | 524.2 | 87.37 | 75.65 | 156.3 |
| yes | 23 | 1060.9 | 46.13 | 45.40 | 108.8 |

## Compacted Split

| compacted | n | sum | avg | median | max |
| --- | ---: | ---: | ---: | ---: | ---: |
| no | 54 | 2112.4 | 39.12 | 32.65 | 152.8 |
| yes | 5 | 556.4 | 111.28 | 112.00 | 156.3 |

## >=100 Credit Observations

| date | seq | credits | task_class | compacted | useful_outcome | reading |
| --- | ---: | ---: | --- | --- | --- | --- |
| 2026-06-01 | 5 | 152.8 | driver_diagnostic | no | useful_high_cost | Cross-layer Electron/Avalonia/driver preflight analysis established the slice direction. High cost, but not obviously waste. |
| 2026-06-01 | 7 | 108.8 | implementation_multi_layer | yes | useful_high_cost | Implemented Slice 1 service/tests/contracts. High cost with direct delivery value. |
| 2026-06-01 | 11 | 156.3 | qualification_readiness | yes | mixed_cost | Compacted broader qualification and memory context. Useful governance state, but likely too much mixed context in one turn. |
| 2026-06-01 | 15 | 112.0 | state_reconstruction | yes | review_for_reduction | Compacted Slice 2 reconstruction. Cost driver is likely context recovery rather than direct code delivery. |
| 2026-06-02 | 5 | 100.8 | implementation_multi_layer | no | useful_high_cost | Cross-layer Avalonia/Electron/driver build context with implementation value. |
| 2026-06-03 | 3 | 147.7 | state_reconstruction | yes | review_for_reduction | Compacted build/driver/governance reconstruction. Strong candidate for cheaper state-reconstruction protocol. |

## Reading

The most important signal is not "tests are expensive." In this sample,
`build_test_loop` has 17 observations but a median of 30.6 and max of 63.0.
The larger cost concentration is in:

- `implementation_multi_layer`: median 99.65, avg 93.12.
- `state_reconstruction`: median 79.50, avg 84.57.
- `qualification_readiness`: max 156.3, avg 70.72.
- compacted observations overall: median 112.00, avg 111.28.

The 12 observations in `implementation_multi_layer`,
`state_reconstruction`, and `qualification_readiness` account for 993.7
credits, or about 37.2% of the 2668.8 visible credits.

## Practical Cost-Control Target

Do not optimize for low credits alone. The better first target is:

`high credits + low or indirect useful outcome`

Current candidates for reduction are:

- Compacted state reconstruction turns.
- Mixed qualification/readiness turns that combine context recovery, artifact
  generation, validation interpretation, memory, and push decision framing.

Current candidates to preserve are:

- High-cost implementation turns that produce tested code or concrete
  diagnostic artifacts.
- Build/test loops when they directly close a live failure.

## Candidate Workflow Adjustment

This is an advisory observation, not a policy:

1. After compaction, run a `state_reconstruction_only` turn.
2. For cross-layer bugs, separate diagnostic direction from implementation.
3. Keep implementation + focused tests together when they close one concrete
   slice.
4. Keep closeout, memory, commit, and push separate from heavy reconstruction
   when possible.
