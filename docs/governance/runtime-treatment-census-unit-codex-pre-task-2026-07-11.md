# Census Unit Review — Codex Pre-Task Adapter (2026-07-11)

Unit: `runtime_hooks/adapters/codex/pre_task.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: CLI wrapper routes Codex-normalized pre-task payloads to shared runner/core policy. | Low: 21 LOC; harness/event arguments must remain correct. | Intentional platform/event wrapper pattern. | Not user-facing. | `keep_observe` |

Evidence: shared runner and Codex normalizer imports; adapter structural test
includes this entrypoint. This does not prove current Codex hook delivery.
