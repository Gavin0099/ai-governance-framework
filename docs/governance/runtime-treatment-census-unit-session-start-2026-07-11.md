# Census Unit Review — Session Start (2026-07-11)

Unit: `runtime_hooks/core/session_start.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Unmeasured for injection; observed for continuity. This is the treatment-delivery unit: it assembles the governance context (instruction_capable / instruction_limited / wrapper_only modes), injects the domain summary and canonical closeout continuity block, runs pre-task checks, and calls both payload audit writers. The v3 owner recalibration (behavioral effect unproven on one task class) applies to the injected-instruction layer generally, owner-adopted only. Closeout-context continuity has observed consumption: next-day sessions read it (E2 engineer reported the plan/memory continuity workflow as useful — retrospective, self-reported). | High: 762 LOC, 5 matched suites; broadest import fan-in of the family (policy, contract, closeout, audit, risk-signal modules). | Unique orchestration role. | Emits reviewer-visible rendered output with human-summary glossing. | `keep_observe`; any future trimming must separate treatment delivery (injection) from continuity/audit assembly |

Evidence: three focused suites pass quickly
(test_runtime_session_start 4, test_session_start_l0 15,
test_session_start_output_and_audit 3). **Defect observed during this
review: `tests/test_session_start_risk_signal.py` hangs (no completion
within 45s while sibling suites finish in under a second); it is excluded
from this unit's receipt and flagged for its own focused investigation.**
The unconditional runtime-core payload-audit call and the default-off
governance_tools audit gate were established in the payload-audit consumer
review. Injection efficacy remains unmeasured; continuity utility is
retrospective/self-reported only.
