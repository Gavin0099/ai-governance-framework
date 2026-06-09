# Runtime Artifact Dirty Isolation Policy - 2026-06-09

Status: policy boundary selected; implementation deferred

## Purpose

This policy defines how ordinary runtime hook output should be treated when it
modifies tracked runtime ledgers.

It follows the write-path inventory recorded in
`artifacts/governance/artifact-write-path-inventory-2026-06-09.md`.

## Selected Boundary

Ordinary hook, smoke, query, and session-end runs must not automatically promote
tracked runtime ledger changes into repo-facing evidence.

The selected policy is:

- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` remains a
  compact repo-facing evidence ledger, but staged commits to it require explicit
  manual promotion or an approved evidence-capture slice.
- `artifacts/session-index.ndjson` is treated as a tracked runtime summary
  ledger with the same manual-promotion boundary until a separate routing
  decision changes it.
- Ordinary runtime runs that dirty either ledger should be reported as runtime
  side effects, then restored, staged, or explicitly included in scope before
  claiming a clean workspace.
- `artifacts/runtime/**` remains the ignored local-runtime destination for
  ordinary hook, smoke, verdict, trace, and closeout side effects.
- `artifacts/session/**` remains the ignored local-runtime destination for new
  raw claim-enforcement packets.

## Ledger Handling Rules

| Ledger | Current status | Selected handling | Why |
| --- | --- | --- | --- |
| `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` | tracked compact evidence index | manual-promotion-only | Auto-staging every append would turn the compact receipt into a runtime log and inflate evidence claims. |
| `artifacts/session-index.ndjson` | tracked session summary ledger | manual-promotion-only until replaced by a separate routing decision | Session-end can append to it during ordinary runs, so it should not be silently mixed into unrelated commits. |

## Required Reporting When These Ledgers Are Dirty

If either tracked ledger is dirty after ordinary runtime activity, the agent
must not report the workspace as clean.

Allowed reporting:

```text
Committed scope: DONE
Workspace state: NOT CLEAN
Runtime ledger side effects:
- artifacts/claim-enforcement/claim-enforcement-receipts.ndjson
- artifacts/session-index.ndjson
Required next action: restore, stage under explicit evidence-capture scope, or
exclude with reviewer approval.
```

## What This Policy Does Not Do

This policy does not:

- move `artifacts/session-index.ndjson`;
- move or rewrite `claim-enforcement-receipts.ndjson`;
- add `.gitignore` rules;
- change hook behavior;
- change session-end behavior;
- change validator behavior;
- change claim-enforcement receipt schema;
- delete or migrate historical CE-1D packet directories;
- make compact receipts an audit source of truth;
- prove token reduction;
- make #17 blocking-ready.

## Future Implementation Options

Future scoped work may choose one of these implementation paths:

1. Keep both tracked ledgers and add explicit pre-commit guidance that refuses
   accidental staging outside evidence-capture scope.
2. Move ordinary runtime appends to ignored local paths and generate compact
   reviewer-facing snapshots only when evidence capture is requested.
3. Keep current write paths but add a warning-only dirty-ledger detector for
   commit preflight.

No implementation option is selected by this policy artifact.

## Claim Ceiling

CLAIMED:

- Runtime dirty-state policy selected for the two ambiguous tracked ledgers.
- Both ledgers are manual-promotion-only for ordinary runtime side effects.
- A clean-workspace claim is invalid while these ledgers remain dirty and
  unhandled.

NOT CLAIMED:

- artifact routing changed;
- hook behavior changed;
- validator behavior changed;
- schema changed;
- pre-commit or pre-push enforcement added;
- tracked ledger migration completed;
- historical CE-1D cleanup completed;
- token usage reduced;
- #17 threshold readiness changed.
