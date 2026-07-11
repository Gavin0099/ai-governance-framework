# Census Unit Review — Copilot Instructions Template (2026-07-11)

Unit: `governance/copilot-instructions-template.md`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Unmeasured. This is a pure behavior_change carrier: 154 lines of agent instructions installed into consumer repos as `.github/copilot-instructions.md` by hook_installer (when not `--hooks-only`). No measurement of whether these instructions change Copilot behavior exists; the v3 owner recalibration (injected instructions unproven on one task class, owner-adopted) raises this unit's burden of proof. | Medium: prose instructions must track framework reality; drift risk is content-staleness, checked by authority_metadata_consistency. | Purpose-overlap with the consumer AGENTS.md exemplar (both carry behavior overrides to consumers via different harness channels). | It IS the human/agent-readable layer for Copilot consumers. | `keep_observe`; first candidate if the owner ever opens a behavior-carrier consolidation slice |

Evidence: live install chain (hook_installer source), consistency checking
(authority_metadata_consistency plus its test), and the census
behavior_change classification. No efficacy evidence exists in either
direction.
