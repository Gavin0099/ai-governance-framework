---
audience: agent-on-demand
authority: reference
can_override: false
overridden_by: AGENT.md
default_load: on-demand
---

# F-7 Full Update

Status: extracted from AGENTS.md
Semantic change: no
Runtime behavior change: yes — submodule consumer apply path now refreshes memory workflow router coverage and managed hook advisory coverage.
Enforcement change: no

## Purpose

F-7 is the AI Governance Full Update workflow. A governed submodule pointer
update is Stage 1 of F-7, not the whole workflow.

When the user asks to update or adopt the latest AI Governance through F-7, F-7
must execute the full adoption/update workflow or explicitly report a blocker.

A submodule pointer update alone is insufficient and must be reported as
`partially_updated`, not completed.

## Required Stages

1. framework pointer update
2. repo-local instruction refresh
3. memory writer coverage check
4. hook / validator coverage check
5. existing memory normalization status check
6. final adoption status report backed by `governance_maturity_summary`

## Layered Status Fields

```text
framework_pointer: updated | already_current | blocked | not_present | not_verified
repo_local_instruction: updated | already_current | blocked | missing | not_verified
memory_writer_coverage: verified | updated | blocked | missing | not_applicable | not_verified
hook_validator_enforcement: verified | updated | blocked | missing | not_applicable | not_verified
existing_memory_normalization: completed | needed | blocked | not_applicable | not_verified
governance_maturity_summary: present | not_available | not_run
human_readable_adoption_summary: reported | not_reported
final_status: full_update_completed | already_current | partially_updated | blocked | not_submodule_consumer | not_verified
```

`full_update_completed` may be used only when every required stage is
`updated`, `already_current`, `verified`, `completed`, or `not_applicable`.

If any required surface is `missing`, `needed`, `blocked`, or `not_verified`,
the final status must not be `full_update_completed`.

The final adoption status report must be operator-facing, not only a raw
submodule or build summary. It must surface the report-only
`governance_maturity_summary` fields, including user-facing adoption status,
framework topology, static self-contained status, runtime capable status, hook
framework root, framework pin freshness, repo-specific rules, domain contract,
validator surface, memory workflow surface, and cannot-claim / claim-boundary
summary.

When `human_readable_adoption_summary` is present, the final F-7 report must
relay that section as a readable Chinese table, not only as machine-readable
status fields. The report must include the marker
`[human_readable_adoption_summary]` and the table header:

```text
| 功能 | 狀態 | 這個功能是做什麼 |
```

It is valid to preserve the table verbatim from the tool output or to restate it
faithfully in the final report. It is not valid to report only
`user_facing_status`, `framework_topology`, or other machine field names while
omitting the Chinese feature/status/explanation table.

`adoption_doctor: findings 0`, `governance_version_check: compatible`, a clean
build, or a framework pointer update is not a substitute for the final adoption
status report. If `governance_maturity_summary` cannot be produced, F-7 must
report `governance_maturity_summary: not_available` or
`governance_maturity_summary: not_run` with the reason and must not claim that
the operator was shown complete adoption status.

If the machine-readable summary is available but the Chinese table cannot be
relayed, F-7 must report `human_readable_adoption_summary: not_reported` with
the reason and must not claim that the operator was shown the complete
human-readable feature adoption table.

## Implemented Automation

For `submodule_consumer` apply mode, the updater now performs these scoped
surfaces:

- refreshes `AGENTS.base.md`
- refreshes / appends AI Governance update rules in `AGENTS.md`
- ensures an `AGENTS.md` `governance:key=memory_workflow` router section
- installs managed hook advisory files from the governance submodule checkout
- surfaces `governance_maturity_summary` as a report-only adoption visibility
  stage for consuming-repo operators
- reports `full_update_completed` only when memory workflow coverage, hook
  advisory coverage, and normalization status are all eligible

## Non-Claims

This protocol defines the required F-7 reporting contract. It does not by
itself implement updater automation for all stages.

Not claimed unless separately implemented and validated:
- updater automation performs all F-7 stages for all repo roles
- validators changed
- artifact schema changed
- existing memory was normalized
