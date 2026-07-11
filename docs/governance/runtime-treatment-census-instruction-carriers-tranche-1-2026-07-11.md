# Runtime Treatment Census — Instruction Carriers Tranche 1 (2026-07-11)

Status: read-only assessment of two pinned census units. This document proposes
no retirement, merge, deployment, or runtime change.

## Problem

The census identifies two instruction-injection carriers as a possible
duplication cluster, but the manifest alone cannot establish whether either
carrier changes a decision, whether their content is actually redundant, or
whether a human can tell their purposes apart.

## Scope and method

Units assessed:

1. `governance/copilot-instructions-template.md`
2. `examples/multi-validator-contract/AGENTS.md`

For each unit, this review evaluates: a directly evidenced decision effect,
maintenance cost, substantive duplication, and a plain-language explanation.
`codex-review-fast` is the methodology precedent only. No-governance baseline
v3 is used only as the existing owner-adopted, task-class-scoped recalibration:
it is not efficacy, merge, or retirement evidence.

## Assessment

| Unit | Decision effect | Maintenance cost | Duplication assessment | Plain-language purpose | Disposition candidate |
| --- | --- | --- | --- | --- | --- |
| `governance/copilot-instructions-template.md` (154 LOC) | **Not observed.** The installer and validator establish that it can be placed in a consumer repo, but placement is not evidence that Copilot followed it or that it changed a later engineering decision. | Medium: it repeats the general DONE, validation, dirty-tree, and reporting doctrine in a separate consumer-facing format; it has no filename-containment test, though installer/validator integration coverage exists. | **Shared category, not proved duplicate.** It expresses cross-repository workflow and reporting boundaries for Copilot Workspace, whereas the example AGENTS file expresses domain-task obligations. No line-for-line or same-audience redundancy was found. | “This is the checklist shown to Copilot in a consumer repo so it knows when to stop, what to validate, and how to report.” | `keep_observe`: retain the deployment template; require a naturally occurring consumer-session example before asserting behavioral or decision effect. |
| `examples/multi-validator-contract/AGENTS.md` (9 LOC) | **Instruction visibility observed; decision effect not observed.** It was read in v3 Arm A Run 1 and injected for Arm B, but v3 found no stable advantage on that task class. The document also names four requirements that are exercised by the contract's fixture family, which is validator evidence rather than proof of agent compliance. | Low: one compact, domain-specific example; its four requirements must remain aligned with the four declared validators if either changes. | **No actionable duplication found.** It shares the broad purpose “guide an agent,” but its content is a multi-validator contract's domain evidence requirements, not the template's generic workflow rules. | “This tells an agent working in the example contract which evidence the four validators expect for each task type.” | `keep_observe`: retain as a concise contract exemplar; do not merge it into the Copilot template or claim that reading it changes outcomes. |

## Cross-unit conclusion

The census manifest's `dup` marker correctly identifies an overlap worth
checking, but this tranche finds an overlap of delivery mechanism, not a
demonstrated content duplicate:

- the Copilot template is a consumer-facing workflow carrier;
- the example AGENTS file is a contract-local, validator-specific carrier.

Merging them would either make the generic consumer template domain-specific or
remove the contract-local explanation. Neither outcome is justified by current
evidence. The appropriate shared status is therefore `keep_observe`, not
`merge`, `downgrade`, or `retire_candidate`.

## Evidence checked

- `docs/governance/runtime-treatment-census-manifest-2026-07-11.md` — pinned
  unit, LOC, test-containment, and v3 claim boundary.
- `governance/copilot-instructions-template.md` — workflow/reporting content.
- `examples/multi-validator-contract/AGENTS.md` and its `contract.yaml` — the
  four domain obligations and validator binding.
- `docs/governance/agent-instruction-surface-map.md` and
  `governance_tools/hook_installer.py` — Copilot deployment route and its
  placement-versus-compliance boundary.
- v3 A1 raw artifact — one direct read of the contract AGENTS file; not an
  outcome-effect measurement.

## Claim ceiling and next evidence

This tranche classifies the two carriers as `keep_observe` candidates only. It
does not prove that agents comply, that either carrier is effective, that the
contents are complete, or that their maintenance cost is justified.

The least-cost next evidence for the Copilot template is a naturally occurring
consumer session whose task decision can be traced to a specific instruction.
For the example AGENTS file, the least-cost next evidence is an independent
contract-user session that identifies whether its four requirements were
understood without owner intervention. Neither event should be manufactured.
