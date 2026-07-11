# Census Unit Review — Canonical Closeout Producer (2026-07-11)

Unit: `runtime_hooks/core/_canonical_closeout.py`.

> **Coverage-accounting note (2026-07-12):** this unit was already reviewed
> in `runtime-treatment-census-closeout-pair-tranche-2-2026-07-11.md` (with
> disposition `keep`). This file was added only because the 33/33 coverage
> receipt's filename glob did not match the pair-tranche doc; it is a
> coverage-accounting supplement, **not** a first-time review. The
> authoritative disposition is `keep` (per the pair tranche); the row below
> is aligned to it.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Observed: this is the trust-boundary producer/validator for canonical closeout artifacts — it treats AI output as untrusted candidate input and normalizes it into the canonical record that session_end persists and the F-7 / P1-C external chain consumes. | Medium: 342 LOC, 3 matched suites; its trust-boundary docstring is explicit. | Intentional producer/validator pairing with session_end; layering, not duplication. | Machine-facing; human layer lives downstream in summaries. | `keep` (per closeout-pair tranche-2; retire/merge needs replacement evidence and a safety review) |

Evidence: focused canonical-closeout suites pass; downstream consumption is
the same F-7 / P1-C chain documented for session_end. As with the whole
closeout family, usage is observed but counterfactual value is unmeasured.
