# Context-Cost Budget Design - 2026-07-06

Status: design/reference note
Runtime behavior change: no
Enforcement change: no
Consumer repo change: no
Skill install: no

## Purpose

This note defines a context-cost budget model for AI Governance work. It exists
because governance can become self-defeating when agents spend more context on
reading, re-reading, and reconciling governance surfaces than the decision can
justify.

This is a design artifact only. It does not install `fable-skills`, change
baseline instructions, change the decision-change ledger schema, add a hook, or
prove token savings.

## Problem

The decision-change ledger answers a defense-output question:

> Did a governance output change a later decision?

Context-cost accounting answers a different agent-work question:

> Did the context read for this slice have a clear decision purpose?

These are different populations. A defense emits signals, warnings, reports, or
receipts. An agent consumes context by reading files, search output, prior
reviews, and external references. Mixing both into one ledger would pollute the
decision-change ledger with agent-read telemetry and make both analyses harder
to interpret.

## Current Repo Truth

- `docs/governance/decision-change-ledger.seed.json` records defense outputs
  and their decision effects.
- `docs/governance/agent-instruction-surface-map.md` records where instructions
  can reach active agent surfaces, but does not prove loading or compliance.
- `AGENTS.md` already contains scope-matched validation, hard-stop, dirty-tree,
  and router rules that prevent broad default reads when a narrow slice is
  approved.
- `governance/REVIEW_CRITERIA.md` already requires reviewers to inspect
  relevant prior-review surfaces, but it does not define a context budget.
- `fable-context-thrift` is treated as an external reference only. It is not
  installed and is not authority for this repository.

## Design Boundary

Keep two records separate:

| Record | Population | Question | Example |
|---|---|---|---|
| Decision-change ledger | Governance outputs | Did this output change a decision? | A warning caused a follow-up slice. |
| Context-cost companion record | Agent slice context reads | Did this context read have a decision purpose? | A protocol read changed validation scope. |

The context-cost record may reuse the same `decision_effect` vocabulary as the
decision-change ledger, but it must not be appended to the ledger as another
entry type unless a future schema explicitly separates populations.

## Per-Slice Granularity

The budget should be recorded per slice, not per file read.

Per-read telemetry is too expensive and would defeat the purpose of context
thrift. A per-slice companion record should summarize the few surfaces that
materially shaped the work:

```json
{
  "schema": "governance_context_cost_companion.v0.1",
  "slice_id": "<commit-or-session-slice-id>",
  "surfaces_read": [
    {
      "surface": "governance/REVIEW_CRITERIA.md",
      "read_type": "targeted_or_required_protocol",
      "expected_decision": "review output must be evidence-bound",
      "decision_effect": "validation_changed",
      "context_cost_class": "low",
      "reuse_possible": false,
      "frequency_class": "routine"
    }
  ],
  "claim_ceiling": [
    "self-reported context-cost companion only",
    "does not measure token savings",
    "does not prove model compliance"
  ]
}
```

The companion record is a future candidate. This note does not create it.

## Context-Cost Rules

### Rule 1: Read for a decision

Read a governance surface when it can change the next decision: scope,
validation, claim ceiling, review verdict, commit boundary, push boundary, or
next slice.

If the read cannot name a plausible decision effect, it is context-expensive
noise.

### Rule 2: Locate before widening

Use targeted search or section reads first. Widen to full-file reads only when
the target section is insufficient or when the file itself is the review or edit
target.

### Rule 3: Do not reread duplicate carriers by default

If a canonical or managed surface is sufficient, do not also read every design
note, historical note, and baseline copy that carries the same rule. Duplicate
surfaces should be read only when investigating drift, conflict, or provenance.

### Rule 4: Established facts stay established, with drift exceptions

Previously verified low-drift facts can be reused. High-drift facts must be
checked again when they affect a claim.

High-drift examples:

- current git head;
- remote-tracking head;
- dirty tree;
- framework lock vs checkout state;
- whether a generated block is current.

### Rule 5: Edit or review targets must be reread

If a file is about to be edited, reviewed, or used as direct evidence for a
verdict, reread it in the current slice even if it was inspected earlier. This
repo has multi-agent same-day handoffs; prior reads can become stale quickly.

### Rule 6: Rare-critical surfaces are exempt from frequency-only downgrade

Human-only gates, destructive-operation checks, safety escalation paths, and
authorization boundaries may be low-frequency by design. Do not downgrade them
solely because they are rarely read or rarely fire.

### Rule 7: Output that does not change decisions should lose prominence

Warnings, summaries, or reports that fire often but do not change scope,
validation, claim ceiling, or follow-up action should be candidates for lower
salience, aggregation, or merge. They should not be promoted into gates only to
make them feel useful.

## Decision-Changing Context Examples

| Context read | Why it is decision-changing |
|---|---|
| `governance/REVIEW_CRITERIA.md` for a review slice | Changes verdict structure, evidence requirement, and open-finding carry-forward. |
| `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` for an update request | Prevents manual submodule bumps from being reported as completed governed updates. |
| `docs/governance/decision-change-ledger.seed.json` for defense triage | Separates decision-changing, noisy, duplicate, and zombie defense candidates. |
| `AGENTS.md` before implementation in this repo | Defines hard stop, dirty tree, scope-matched validation, and update-trigger boundaries. |
| `git status --short --branch` before commit or push | Changes whether the slice can claim a clean committed scope. |

## Non-Decision-Changing Context Examples

| Context read | Why it is not enough to justify cost |
|---|---|
| Re-reading all governance protocols for a single docs-only typo | The extra reads do not change scope, validation, or claim ceiling. |
| Reading every historical design note after a consolidation summary exists | The summary is the intended entrypoint unless provenance or drift is under review. |
| Re-running broad inventory after no file or remote state changed | The output is unlikely to change the next action. |
| Surfacing the same legacy warning every session without follow-up | The output is noisy unless it changes a decision or is baseline-aggregated. |
| Installing an external skill for behavior already covered by repo governance | Adds an instruction surface without proving decision improvement. |

## Candidate Metrics

Future context-cost companions could track:

- `surfaces_read_count`: number of distinct instruction or evidence surfaces read;
- `full_file_reads`: count of full-file reads in the slice;
- `targeted_reads`: count of search or section reads;
- `duplicate_surface_reads`: surfaces read that carry the same rule;
- `high_drift_rechecks`: rechecks for git, lock, remote, dirty tree, or generated block state;
- `decision_changing_reads`: reads that changed scope, validation, claim ceiling, or next action;
- `non_decision_changing_reads`: reads with no recorded decision effect;
- `rare_critical_reads`: rare-critical surfaces read despite low frequency;
- `context_cost_class`: low, medium, or high for the slice;
- `budget_disposition`: acceptable, noisy, duplicate_heavy, or over_budget_candidate.

These metrics are advisory candidates only. They should not become a gate
without a separate design and review.

## Future Canonical Landing Point

The behavior rule should eventually have one canonical loaded surface, not many
copies.

Recommended landing path:

1. Keep this note as the detailed design/reference.
2. If the rule proves useful, add one short behavior rule to
   `governance/REVIEW_CRITERIA.md` for review/audit slices:
   read surfaces for decisions, not for comfort; reread edit/review targets.
3. For implementation slices, consider a minimal AGENTS managed-block sentence
   only after there is evidence that review-only placement is insufficient.

Do not add the same prose to every protocol, baseline, and managed block.

## Non-Claims

This note does not claim:

- context savings were measured;
- agents will comply;
- `fable-skills` improves this repository;
- the decision-change ledger schema changed;
- any hook, gate, runtime behavior, or baseline changed;
- any noisy surface was downgraded;
- any duplicate surface was merged.

## Evidence Plan for a Future Slice

A future implementation or data slice should provide evidence for:

- whether per-slice context-cost summaries can be filled without meaningful
  extra work;
- whether the summaries identify duplicate or noisy reads;
- whether context-cost summaries change any review, implementation, or
  consolidation decision;
- whether rare-critical surfaces remain protected from frequency-only
  downgrade.
