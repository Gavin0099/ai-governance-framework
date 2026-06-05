# Copilot UI Credit Outlier Review

## Scope

This artifact reviews only the six visible Copilot UI observations at or above
100 credits from the 59-row manual baseline:

`artifacts/copilot-credits/copilot-ui-credit-observations-2026-06-01_to_2026-06-03.csv`

The purpose is to separate high-cost useful work from high-cost context
overhead. This is not a threshold policy.

## Claim Ceiling

CLAIMED:

- Six `>=100 credits` UI observations were reviewed.
- Each high-cost observation was classified as `useful_high_cost`,
  `mixed_context_cost`, or `avoidable_context_cost_candidate`.
- The review identifies where cost reduction should be explored first.

NOT CLAIMED:

- Billing truth.
- Token count.
- Final invoice mapping.
- Provider-side attribution.
- Exact cause of each credit amount.
- Workflow policy.
- Budget threshold.
- Proof that any single observation was waste.

## Outlier Set

| bucket | rows | credits | share of all visible credits |
| --- | ---: | ---: | ---: |
| all observations | 59 | 2668.8 | 100.0% |
| >=100 outliers | 6 | 778.4 | 29.2% |
| useful_high_cost | 3 | 362.4 | 13.6% |
| mixed_context_cost | 1 | 156.3 | 5.9% |
| avoidable_context_cost_candidate | 2 | 259.7 | 9.7% |

## Row Review

| date | seq | credits | task_class | compacted | classification | useful outcome | reduction reading |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| 2026-06-01 | 5 | 152.8 | driver_diagnostic | no | useful_high_cost | Established cross-layer Electron/Avalonia/driver preflight direction. | Preserve as diagnostic investment unless repeated without narrowing scope. |
| 2026-06-01 | 7 | 108.8 | implementation_multi_layer | yes | useful_high_cost | Implemented Slice 1 service/tests/contracts with evidence. | Preserve when implementation and focused tests close one concrete slice. |
| 2026-06-01 | 11 | 156.3 | qualification_readiness | yes | mixed_context_cost | Produced useful governance/readiness state. | Candidate to split: reconstruction, qualification decision, memory, and commit framing should not be merged in one turn. |
| 2026-06-01 | 15 | 112.0 | state_reconstruction | yes | avoidable_context_cost_candidate | Reconstructed Slice 2 context. | Strong candidate for a cheaper `state_reconstruction_only` protocol after compaction. |
| 2026-06-02 | 5 | 100.8 | implementation_multi_layer | no | useful_high_cost | Cross-layer Avalonia/Electron/driver build context with implementation value. | Preserve if tied to code movement or concrete failure closure. |
| 2026-06-03 | 3 | 147.7 | state_reconstruction | yes | avoidable_context_cost_candidate | Reconstructed build/driver/governance state. | Strong candidate to split from build interpretation and governance planning. |

## Interpretation

The outlier set does not support a rule like "high credits are bad." Half of
the outlier rows are high-cost useful work with direct diagnostic or
implementation value.

The first reduction target should be narrower:

- Compacted state reconstruction that does not directly change code or produce
  a durable diagnostic artifact.
- Mixed qualification/readiness turns that combine context recovery, decision
  framing, artifact generation, memory, validation interpretation, and push
  planning.

## Advisory Workflow Test

This is an experiment candidate, not a policy:

1. When a conversation is compacted, the next turn should be
   `state_reconstruction_only`.
2. That turn may produce a short state summary and a narrow next DONE.
3. It should not edit files, run broad tests, commit, push, write memory, or
   produce governance artifacts unless explicitly requested.
4. The next turn can then perform implementation, qualification, or closeout
   with a smaller context target.

## Non-Goals

- Do not set a max-credit threshold from this sample.
- Do not suppress useful implementation turns just because they exceed 100
  credits.
- Do not treat UI observation credits as billing ground truth.
- Do not claim the two avoidable candidates were valueless; the claim is only
  that their task shape is the best first target for reduction.
