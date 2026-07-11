# Census Unit Review — Hermes Normalizer (2026-07-11)

Unit: `runtime_hooks/adapters/hermes/normalize_event.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: reshapes accepted-input Hermes payloads into the shared event contract; policy stays in core. | Low: 29 LOC; own docstring declares the accepted-input boundary. | Intentional four-platform wrapper; slightly larger than peers because it documents the accepted-input caveat. | Not user-facing. | `keep_observe` |

Evidence: dedicated hermes adapter tests pass; the docstring itself declares
that "hermes" is an accepted-input target, not a verified external Hermes
event API, and points at the fixtures as the contract. The Hermes real
integration remains a pending design line
(`hermes-real-integration-contract-spec-2026-06-22.md`,
`hermes-real-model-run-evidence-plan-2026-06-30.md`); nothing here proves a
real Hermes runtime has ever delivered an event.
