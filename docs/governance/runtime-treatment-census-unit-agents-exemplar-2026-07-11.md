# Census Unit Review — Consumer AGENTS.md Exemplar (2026-07-11)

Unit: `examples/multi-validator-contract/AGENTS.md`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Observed, uniquely in the behavior_change class: during v3, Arm A voluntarily read this file in 1 of 3 runs before editing, and Arm B received it by injection in all runs. The observation shows exposure, not efficacy — v3 scored no stable governed-arm advantage on that task class. | Minimal: 9 lines. | Purpose-overlap with the copilot template (behavior overrides via a different channel); referenced by `contract.yaml` as `ai_behavior_override`, so it is also task substrate for the example contract. | It is itself the plain-language behavior contract for the example consumer. | `keep_observe`; it is load-bearing for the example contract and the v3 evidence chain, so any consolidation must preserve both roles |

Evidence: contract.yaml `ai_behavior_override` reference, v3 raw streams
(A1 voluntary read; Arm B injection treatment), and the frozen v3 scratch
recipes that pin this file's bytes in the seed tree hash.
