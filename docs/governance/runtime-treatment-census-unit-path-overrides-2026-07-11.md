# Census Unit Review — Runtime Path Overrides (2026-07-11)

Unit: `runtime_hooks/runtime_path_overrides.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent decision effect; it normalizes explicit CLI paths before dispatcher/smoke execution. | Low: 46 LOC, but incorrect inference can target the wrong repo/PLAN/contract. | Shared by dispatcher and smoke test; no duplicate override helper found. | Not user-facing; its value is predictable invocation. | `keep_observe` |

Evidence: dispatcher and smoke-test callers; focused tests cover contract-root
inference, PLAN inference, and explicit PLAN preservation. This does not prove
cross-repo safety under every filesystem layout.
