# Self-Governance F6 Non-Daily Memory Remediation Design

Status: REPORT-ONLY IMPLEMENTED / NON-BLOCKING
Date: 2026-07-05
Scope: F6 residual from the B0 blocking surface red-team round 2

## DONE

DONE = the intended remediation semantics for non-daily `memory/*.md` files are
chosen and the first report-only detector is implemented without changing
blocking policy, hooks, or enforcement behavior.

## Problem

F6 showed a scan-scope bypass: a session-shaped entry can be placed in a
non-daily memory file such as `memory/notes.md`. `memory_workflow` and CI still
classify the diff as governed memory work because it touches `memory/**`, but
`memory_authority_guard` scans daily `YYYY-MM-DD.md` files for B0. The report-only
F6 detector now classifies this placement separately without expanding B0.

This is not the same as ordinary historical debt. It is a placement bypass:
session-derived operational records can leave the canonical daily-file lane.

## Current Data Point

A read-only scan of current non-daily memory files found:

| File | Session-shaped field count | Interpretation |
| --- | ---: | --- |
| `00_long_term.md` | 2 | structural long-term metadata contains `memory_type` / `commit` text, not a session entry |
| `01_active_task.md` | 0 | no session-shaped fields |
| `02_workflow.md` | 0 | no session-shaped fields |
| `03_knowledge_base.md` | 0 | no session-shaped fields |
| `04_review_log.md` | 0 | no session-shaped fields |
| `governance_statefulness_risk.md` | 0 | no session-shaped fields |
| `README.md` | 0 | no session-shaped fields |

The scan argues against a blunt ban on non-daily memory files. They are valid
structural memory surfaces. The bypass is specifically session-shaped entries
inside those files.

## Decision

Chosen option: add a report-only warning first.

Rejected for this slice:

- **Ban all session-shaped content in non-daily `memory/*.md` immediately**:
  too broad for structural memory files and likely to create wording-level false
  positives.
- **Add non-daily entries directly to B0 selective blocking**: too early because
  the daily-file contract and structural-memory contract need separate false
  positive rules.

Chosen semantic:

- Non-daily memory files remain allowed for structural memory, active task
  notes, review logs, knowledge base, and other explicit non-session surfaces.
- New session-derived operational records must stay in daily
  `memory/YYYY-MM-DD.md` and use the canonical writer.
- A non-daily memory file that contains an actual session-entry block is a
  report-only placement warning, not a blocker.
- The warning is evidence of a scan-scope bypass until a later RFC promotes it.

## Proposed Warning Contract

Candidate code:

`non_daily_session_shaped_memory_entry`

Plain-language meaning: a non-daily `memory/*.md` file contains a block that
looks like a daily session-derived memory entry.

Detection shape:

- scan non-daily `memory/*.md`;
- ignore daily `YYYY-MM-DD.md`;
- ignore known structural comment metadata in `00_long_term.md`;
- only classify Markdown list blocks that begin like an entry, for example
  `- memory_type:`, `- what_changed:`, or `- what changed:`;
- require at least two session-shaped fields from the existing B0 field set
  (`record_format_version`, `writer`, `commit`, `session_id`,
  `memory_binding`, `test_evidence`, `next_step`, `plan_reconciliation`) before
  warning.

This deliberately avoids warning on prose that merely mentions `commit` or
`memory_type`.

## Gate Semantics

Initial implementation is report-only:

- raw `memory_authority_guard`: include the warning in
  `report_only_violation_codes`;
- `memory_workflow`: surface the warning in `warnings`, keep
  `completion_claim_allowed=True` unless some other blocker fires;
- CI: surface the warning for current-diff non-daily memory files, keep
  `clean=True`;
- `governance/memory_blocking_policy.json`: unchanged.

No `blocking_codes` entry is added for this code in the first slice.

## Promotion Conditions

Promotion to blocking requires a separate RFC and should not borrow B0's claim.
Minimum preconditions:

1. A focused mutation fixture proves `memory/notes.md` style placement is
   detected as report-only.
2. A current-repo scan shows existing non-daily memory files do not produce
   noisy warnings.
3. The contract names explicit exemptions or dispositions for structural memory
   files such as `00_long_term.md`, `03_knowledge_base.md`, and
   `04_review_log.md`.
4. CI behavior is decided: current-diff only vs. repo-state gate.
5. `authority_override` interaction is defined before any blocker promotion.

## Non-Goals

This slice does not:

- modify hooks, `.github` workflow files, or policy files;
- block `memory/notes.md`;
- ban non-daily memory files;
- promote F6 to blocking;
- claim the blocking surface is bypass-proof.

## Claim Ceiling

This document can claim:

- the F6 remediation direction is selected and implemented as report-only first;
- the warning semantics and false-positive boundaries are defined;
- blocking promotion is deferred behind a separate RFC.

This document cannot claim:

- F6 is fully fixed;
- any new enforcement exists;
- B0 has expanded beyond daily-file semantics;
- Phase E enforcement is complete.
