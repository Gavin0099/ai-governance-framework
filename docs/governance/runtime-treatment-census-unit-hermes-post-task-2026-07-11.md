# Census Unit Review — Hermes Post-Task Adapter (2026-07-11)

Unit: `runtime_hooks/adapters/hermes/post_task.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: CLI wrapper routes Hermes-normalized post-task payloads into the shared runner, where response/evidence contract checks occur. | Low: 21 LOC; harness/event arguments must remain exact. | Intentional platform/event wrapper pattern. | Not user-facing. | `keep_observe` |

Evidence: shared runner and Hermes normalizer imports; dedicated hermes
adapter tests pass. The Hermes real integration remains a pending design
line; no real Hermes post-task delivery is proven.
