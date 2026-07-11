# Census Unit Review — Pre-Task Check (2026-07-11)

Unit: `runtime_hooks/core/pre_task_check.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Unmeasured. Emits two distinct signal families: `behavioral_advisory` (behavior-shaping wording) and `evidence_advisory` / `degradation_advisory` (audit-facing). All are self-labeled "reviewer-visible advisory only; not verdict-bearing". No measurement of whether any advisory changed an agent or reviewer decision exists. | High relative to family: 1,063 LOC, one direct runtime test suite; consumes decision_policy_v1_runtime risk tiers and runtime-injection observation inputs. | Advisory-family overlap with post_task_check; the two share signal-class vocabulary and wiring. | Signal payloads carry `usage` glosses ("do not treat as gate or blocker"), which is the correct plain-language pattern. | `keep_observe`; the behavioral_advisory sub-family inherits the raised burden of proof from the v3 owner recalibration (task-class-scoped, owner-adopted) |

Evidence: focused runtime suite passes. The census-level judgment stands:
this is a `mixed` unit whose audit-facing advisories and behavior-shaping
advisories should be evaluated separately in any future disposition; the
unit must not be retired or trimmed as a single block.
