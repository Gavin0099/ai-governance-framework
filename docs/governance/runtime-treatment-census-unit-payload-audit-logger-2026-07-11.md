# Census Unit Review — Payload Audit Logger (2026-07-11, cross-reference)

Unit: `runtime_hooks/core/payload_audit_logger.py`.

This unit was evaluated earlier on 2026-07-11 in the dedicated read-only
log-consumer review (receipt
`receipt-payload-audit-consumer-review-20260711.json`) plus a reviewer
correction; this document records the census-format result so all 33 units
carry one.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Observed (historical): the 2026-03 L0/L1 jsonl outputs of this measurement family fed the L0/L1 baseline analyses, and the May codeburn token-provenance line consumed the family for context-cost work. No current tool reads its outputs. | Low-medium: 240 LOC, 2 matched suites. | **Naming collision, corrected causal claim**: `governance_tools/payload_audit_logger.py` (token measurement, gated by default-off `GOVERNANCE_PAYLOAD_AUDIT=1`) and this runtime-core module (per-invocation jsonl appender, **called unconditionally inside a non-blocking try in session_start**) are two different modules sharing one name. The default-off gate explains only the governance_tools writer's silence; the runtime-core writer's lack of later tracked JSONL has a separate, not-yet-verified explanation. | Machine-facing telemetry. | `keep_observe`; the two same-named modules are a rename/merge candidate for a future owner slice |

Evidence, by reference: the consumer-review receipt (no current reader,
outputs frozen at 2026-03-23, 40 focused tests passing) and the reviewer
correction that split the two writers' causal stories. "Historical decision
use" is bounded to "historical analysis artifacts exist"; no reproducible
raw-jsonl-to-baseline derivation is retained.
