# Runtime Treatment Census — Human-Summary Helper Tranche 5 (2026-07-11)

Status: read-only assessment of the pinned runtime helper and its adjacent
governance-tools counterpart. This document proposes no import change, shared
module extraction, output contract change, or user-facing report redesign.

## Problem

`runtime_hooks/core/human_summary.py` is only 19 LOC, but it represents the
claimed bridge from runtime fields to human-facing output. The census must
separate two questions:

1. Is there duplicated implementation worth consolidating?
2. Does this helper itself make governance understandable to a human?

## Current implementation and callers

| Surface | Function | Callers / scope | Finding |
| --- | --- | --- | --- |
| `runtime_hooks/core/human_summary.py` | `build_summary_line()` and runtime-only `format_contract_summary_label()` | runtime `session_start`, `pre_task_check`, and `post_task_check` | Runtime helper has a small domain-specific companion function. |
| `governance_tools/human_summary.py` | `build_summary_line()` | 20+ governance-tool readers/writers, including closeout audit, change-control, release, reviewer-handoff, and Round A output | `build_summary_line()` is semantically identical to the runtime implementation: discard empty values, join with ` | `, prefix `summary=`. |

## Assessment

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition candidate |
| --- | --- | --- | --- | --- |
| **None directly observed.** Many tools emit the helper's line, but this tranche found no evidence that this formatting helper alone changed a decision. | Low per copy, but every change to compact-summary formatting must now be duplicated and separately tested. | **Confirmed implementation duplicate** for `build_summary_line()`. The runtime-only contract-label formatter is not duplicated. | Limited. `summary=key=value | key=value` is compact and scannable for engineers, but it does not explain meanings, risk, or next action in plain language. | `merge_candidate`: consolidate only the duplicate formatter after a narrow import-boundary review; preserve runtime-only labeling and all existing output strings. |

## Human-understanding boundary

E2's observed usability failure was that an engineer could not tell whether
adoption was complete. The reported remediation was the F-7 adoption-status
table, not this helper. Therefore:

- this helper may reduce visual noise in engineering output;
- it does not by itself produce the four-layer explanation (engineering,
  governance, risk, plain language) needed for non-engineer readers;
- no causal usability claim is available for it.

## Merge boundary

The duplicated formatter is a plausible low-cost consolidation target, but
this tranche does not implement it. The next slice must first verify that
runtime hooks may depend on the proposed canonical helper without changing
startup/import behavior, and must pin byte-for-byte output compatibility.
The change must not bundle a rewrite of F-7 tables, operator reporting, or
human-summary semantics.

## Evidence checked

- `runtime_hooks/core/human_summary.py` and
  `governance_tools/human_summary.py` — identical formatter behavior.
- `tests/test_runtime_human_summary.py` and
  `tests/test_governance_tool_human_summary.py` — separate behavioral pins.
- repository caller search — runtime has three direct callers; the
  governance-tools helper has broad reuse.
- `docs/governance/e2-retrospective-adoption-evidence-2026-07-11.md` — the
  observed human-understanding remediation was the F-7 table, not helper use.

## Claim ceiling

This tranche proves a local implementation duplicate and identifies a
`merge_candidate`. It does not prove a safe import direction, human
understanding improvement, output consumer compatibility, or any completed
consolidation.
