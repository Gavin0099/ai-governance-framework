# Census Unit Review — Codex Post-Task Adapter (2026-07-11)

Unit: `runtime_hooks/adapters/codex/post_task.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: CLI wrapper routes Codex-normalized post-task payloads into the shared runner, where response/evidence contract checks occur. | Low: 21 LOC; `codex` harness stamp and `post_task` event argument must remain exact. | Intentional platform/event wrapper pattern, not duplicate contract logic. | Not user-facing. | `keep_observe` |

Evidence: shared runner and Codex normalizer imports; adapter structural and
parity tests cover the shared behavior this wrapper routes into. This does
not prove a current Codex post-task hook run delivers events in production
sessions.
