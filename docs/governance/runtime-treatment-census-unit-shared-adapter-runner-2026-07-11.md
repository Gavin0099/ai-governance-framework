# Census Unit Review — Shared Adapter Runner (2026-07-11)

Unit: `runtime_hooks/adapters/shared_adapter_runner.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No direct natural-session decision effect is retained. It is the shared path for harness normalizers to invoke core checks and can turn a non-trivial post-task response without a contract block into an error. | Medium: all adapter payload shapes and post-task contract semantics converge here. | Not duplicate of dispatcher: it owns native-normalized payload provenance, placeholder suppression, and adapter contract handling. | CLI output exposes harness/event/ok and errors, but no operator-level explanation of why a contract is required. | `keep_observe` |

Evidence: smoke and Hermes-stub callers; focused adapter-runner tests cover
pre-task, placeholder suppression, session-start, snapshot, and missing contract.
This does not prove every harness delivers events through this shared runner.
