# Runtime Ledger Milestone Export Path Design (Option B follow-up)

Status: design-only
Date: 2026-06-18
Runtime behavior change: no
Enforcement change: no
Implementation status: not implemented
Related commits: ffd9609, 56e1c9a

## Purpose

Option B made these runtime ledgers ignored-by-default and removed them from the
Git index:

- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson`
- `artifacts/session-index.ndjson`

That removes recurring dirty-state friction from normal validation and push
flows. It also means reviewer-facing durable evidence must not depend on the
live runtime ledger files being tracked directly.

This document defines the intended audit/reviewer milestone export path. It is a
specification only. It does not implement an exporter, change readers, change
writers, change hooks, or create a gate.

## Design intent

The live runtime ledgers stay local and ignored by default.

When a reviewer, release, or audit milestone needs durable evidence from those
ledgers, the operator must perform an explicit export step that creates a
bounded, reviewable snapshot artifact. The export artifact is the committed
review surface; the live runtime ledger files remain ignored.

This keeps normal development low-friction while preserving a deliberate path
for durable audit evidence.

## Trigger conditions

An export is appropriate only when at least one of these is true:

- a reviewer explicitly asks for claim/session runtime evidence;
- a release or audit milestone needs a durable receipt/session snapshot;
- a governance claim depends on runtime ledger contents;
- a handoff packet needs evidence beyond memory/PLAN/prose summaries;
- an incident investigation needs a point-in-time runtime-ledger capture.

An export is not appropriate for ordinary local validation, ordinary push hooks,
or routine session closeout.

## Proposed export artifact shape

A future implementation should create a timestamped milestone bundle under a
tracked reviewer/audit path, for example:

```text
artifacts/governance/runtime-ledger-exports/<export-id>/
  manifest.json
  summary.md
  claim-enforcement-receipts.ndjson        # optional raw snapshot
  session-index.ndjson                     # optional raw snapshot
```

The exact path is implementation-time detail. The key rule is that exported
snapshots must be distinct from the ignored live runtime ledgers.

## Manifest requirements

The export manifest should include at least:

- `export_id`
- `created_at_utc`
- `repo_head`
- `repo_branch`
- `export_reason`
- `reviewer_scope`
- `source_files`
- `source_present`
- `source_sha256`
- `source_line_count`
- `source_record_count`
- `included_raw_snapshots`
- `claim_ceiling_supported`
- `claim_ceiling_not_supported`
- `generated_by`

If a source ledger is absent, the exporter must record that absence explicitly
instead of fabricating an empty evidence trail.

## Summary requirements

The human-facing `summary.md` should state:

- why the export was created;
- which source ledgers were present or absent;
- which commit the snapshot is tied to;
- what evidence the snapshot can support;
- what it cannot support;
- whether raw snapshots were included.

The summary is a reader aid, not a replacement for the manifest or raw snapshot.

## Raw snapshot policy

Raw ledger snapshots should be optional.

Default recommendation:

- include manifest and summary for every export;
- include raw `ndjson` snapshots only when the reviewer/audit milestone needs
  row-level evidence.

This avoids turning every milestone into a large artifact dump while preserving
an explicit path for durable evidence when needed.

## Reader and absence behavior

Existing readers tolerate missing runtime ledgers. The export path should retain
that principle:

- missing source file -> export warning / `source_present=false`;
- malformed source file -> export warning with parse failure evidence;
- exporter should not silently skip a source that was requested;
- exporter should not exit non-zero for ordinary missing-ledger cases unless the
  operator explicitly requested strict export mode.

## Relationship to reviewer handoff

The existing reviewer handoff surface is a summary and navigation layer. A
runtime-ledger export should be consumable by reviewer handoff tooling in a later
implementation slice, but this design does not wire that integration.

Future integration may let reviewer handoff summaries point at the latest
runtime-ledger export bundle. It must not make handoff summary itself the source
of truth.

## Claim ceiling

Supported after a future export implementation:

- a specific export bundle captures local runtime ledger state at a specific
  commit and time;
- source file presence, hashes, counts, and inclusion status are recorded;
- reviewer/audit can inspect the exported bundle without requiring live ignored
  ledger files to be tracked.

Not supported:

- full historical runtime evidence is complete;
- every session has a valid receipt;
- ignored live ledgers are themselves durable reviewer evidence;
- runtime ledger schema is validated beyond the exporter checks;
- semantic correctness of claims is proven;
- Gate 3 is opened;
- any new CI, hook, closeout, or enforcement behavior exists.

## Non-goals

This design does not:

- re-track the live runtime ledgers;
- implement an exporter;
- change `.gitignore`;
- change runtime ledger writers;
- change session closeout behavior;
- change claim-enforcement validators;
- add CI or hook enforcement;
- create a release gate;
- backfill historical ledgers;
- define a final artifact schema version.

## Future implementation slice

A future implementation should be a separate reviewed slice with a narrow DONE
condition, for example:

```text
DONE = implement runtime ledger milestone export command with manifest-only
export, focused tests for missing/present/malformed ledgers, and no gate wiring.
```

Minimum focused tests should cover:

- both source ledgers absent;
- one source present and one absent;
- both source ledgers present;
- malformed `ndjson` line is reported without silent success;
- manifest hashes and counts are stable;
- live ignored ledger files remain untracked;
- no hook, CI, or closeout behavior changes.

## Decision boundary

Option B is already implemented for ignored runtime ledgers. This document only
records the missing durable-evidence path that Option B intentionally deferred.

Export design completion does not authorize implementation. Implementation
requires a separate user-approved slice and reviewer gate.
