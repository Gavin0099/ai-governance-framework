# Census Unit Review — Runtime Dispatcher (2026-07-11)

Unit: `runtime_hooks/dispatcher.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent policy decision: it routes `pre_task`, `session_start`, and `post_task` events to their core handlers. External replay/smoke evidence shows it is an integration entrypoint, not that routing itself changed a decision. | Medium: event payload mapping and CLI path overrides must stay aligned with all three core handler contracts. | No duplicate dispatcher found; `smoke_test.py` is a caller/exercise surface, not a second router. | Human envelope lists event type, result, warnings, and errors; compact but engineering-oriented. | `keep_observe` |

Evidence: direct core-handler imports, `smoke_test.py` caller, external shared
session-start replay documentation, and `tests/test_runtime_dispatcher.py`.
This does not prove every adapter reaches the dispatcher or that the routed
governance advice is behaviorally effective.
