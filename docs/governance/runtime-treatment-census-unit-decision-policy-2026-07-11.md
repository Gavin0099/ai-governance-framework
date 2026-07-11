# Census Unit Review — Decision Policy v1 Runtime (2026-07-11)

Unit: `runtime_hooks/core/decision_policy_v1_runtime.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Unmeasured. Defines the runtime decision vocabulary (RiskTier, DecisionAction, PremiseStatus, EvidenceAlignment, ExecutionScope, Reversibility, CorrectnessMode) and policy-input dataclasses consumed by pre_task_check and the surface manifest; also referenced by the reliability-observation test. It shapes what advisories can say, but no trace shows a tier or action changing a real decision. | Medium: 595 LOC of mostly type/dataclass definitions; **coverage gap confirmed — zero direct filename-containment tests**; behavior is exercised only indirectly through consumer suites. | Vocabulary-definition role is unique; no overlap found. | Machine-facing type layer; not user-facing. | `keep_observe` with an explicit coverage-gap note: if this vocabulary is ever revised, direct contract tests should precede the change |

Evidence: consumer identification (pre_task_check, runtime_surface_manifest,
reliability-observation test) and passing consumer suites
(test_runtime_pre_task_check, test_runtime_surface_manifest) are the only
executable coverage. The census focused-review flag is resolved as
"documented coverage gap on a live type-vocabulary unit", not as dead code
and not as verified-correct code.
