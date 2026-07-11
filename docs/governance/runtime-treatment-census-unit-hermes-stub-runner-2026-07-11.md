# Census Unit Review — Hermes Stub Runner (2026-07-11)

Unit: `runtime_hooks/examples/hermes/stub_runner.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: example/stub driver that exercises the hermes adapter path with fixture payloads for development and smoke purposes. | Medium-low: 244 LOC, the largest adapter-family artifact; exists only to simulate a not-yet-real integration. | None beyond its role as the hermes accepted-input exerciser. | Not user-facing. | `keep_observe`, revisit when the Hermes real-integration line resolves |

Evidence: dedicated stub-runner tests pass. This unit's justification is
wholly derivative of the pending Hermes real-integration design line; if
that line is ever abandoned, this stub and the hermes adapter trio should
be re-evaluated together as one cluster, not piecemeal.
