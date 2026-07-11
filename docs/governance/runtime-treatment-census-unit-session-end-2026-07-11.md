# Census Unit Review — Session End (2026-07-11)

Unit: `runtime_hooks/core/session_end.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Observed, the strongest in the census: its closeout lifecycle feeds the canonical closeout artifacts and receipts that the F-7 / P1-C external-evidence chain actually consumes, and receipt schema evolution (1.1 → 1.2 → 1.3) was driven by real consumer needs (meiandraybook memory_workflow fields). | Highest LOC in census (1,366) but also best-tested (7 matched suites). | Works with `_canonical_closeout.py` as a producer/validator pair; the split is intentional trust-boundary layering, not duplication. | Closeout receipts are machine-facing; their human-facing layer is the maturity/F-7 summaries downstream. | `keep` posture in practice (recorded as `keep_observe` for vocabulary consistency); this is the census's clearest audit-value anchor |

Evidence: focused session-end suite passes; downstream consumption is
documented in the P1-C pending-validation chain and the 21 meiandraybook
closeout receipts observed on 2026-07-10. What remains unproven is not
usage but counterfactual value: no measurement shows decisions would worsen
without it.
