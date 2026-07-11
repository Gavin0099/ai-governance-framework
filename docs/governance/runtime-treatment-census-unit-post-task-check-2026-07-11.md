# Census Unit Review — Post-Task Check (2026-07-11)

Unit: `runtime_hooks/core/post_task_check.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Unmeasured for advisories; structurally strongest verdict machinery in the family (`verdict_impact` stop/escalate on invalid evidence schema, policy conflict, illegal override, domain-contract violation). Whether those verdicts changed real outcomes has never been traced. | Highest in family: 1,091 LOC, one direct runtime suite; consumes the decision-model loader for policy precedence and required evidence kinds. | Advisory-family overlap with pre_task_check (shared signal-class vocabulary). | `usage` glosses present on advisory payloads; verdict paths are machine-facing. | `keep_observe`; any future split should separate the evidence/verdict machinery (audit/integrity) from the behavioral_advisory sub-family before disposition |

Evidence: focused runtime suite passes. Census judgment: `mixed`, with the
integrity/verdict half being the closest thing this family has to
enforcement — it must not inherit the raised burden of proof that applies
only to the behavior-shaping half.
