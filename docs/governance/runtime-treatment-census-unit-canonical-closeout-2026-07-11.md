# Census Unit Review — Canonical Closeout Producer (2026-07-11)

Unit: `runtime_hooks/core/_canonical_closeout.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Observed: this is the trust-boundary producer/validator for canonical closeout artifacts — it treats AI output as untrusted candidate input and normalizes it into the canonical record that session_end persists and the F-7 / P1-C external chain consumes. | Medium: 342 LOC, 3 matched suites; its trust-boundary docstring is explicit. | Intentional producer/validator pairing with session_end; layering, not duplication. | Machine-facing; human layer lives downstream in summaries. | `keep_observe` (audit-value anchor together with session_end) |

Evidence: focused canonical-closeout suites pass; downstream consumption is
the same F-7 / P1-C chain documented for session_end. As with the whole
closeout family, usage is observed but counterfactual value is unmeasured.
