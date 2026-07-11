# Census Unit Review — Evidence Integrity Gate (2026-07-11)

Unit: `runtime_hooks/core/evidence_integrity_gate.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No retained real-session decision-effect receipt was found. It is invoked by `pre_task_check` and can reject evidence-invalid `proceed` choices in its structured output. | Medium: 136 LOC, three evidence/proceed rules, and a hard-fail classification must remain aligned with pre-task semantics. | No same-runtime duplicate found; related evidence checks elsewhere validate receipt shape rather than decision-candidate evidence. | Violation codes are engineering-readable, not a plain-language risk explanation. | `keep_observe` |

Evidence: `pre_task_check.py` imports and records the gate; focused tests cover
direct-evidence mismatch, wrong/no-evidence proceed, and weak-evidence-only
proceed. This review does not prove gate firing in a natural task or its
behavioral effectiveness.
