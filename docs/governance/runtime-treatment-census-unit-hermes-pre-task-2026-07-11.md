# Census Unit Review — Hermes Pre-Task Adapter (2026-07-11)

Unit: `runtime_hooks/adapters/hermes/pre_task.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: CLI wrapper routes Hermes-normalized pre-task payloads to the shared runner/core policy. | Low: 21 LOC; harness/event arguments must remain exact. | Intentional platform/event wrapper pattern. | Not user-facing. | `keep_observe` |

Evidence: shared runner and Hermes normalizer imports; dedicated hermes
adapter tests pass. The Hermes real integration remains a pending design
line; no real Hermes pre-task delivery is proven.
