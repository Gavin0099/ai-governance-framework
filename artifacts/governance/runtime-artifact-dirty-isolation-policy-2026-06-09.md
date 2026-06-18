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

2026-06-18 update:

The owner ratified Option B for the two recurring runtime ledgers:

- default state: ignored runtime artifacts;
- durable reviewer evidence: explicit audit / reviewer milestone export;
- implementation status: pending separate slice.

This update changes the selected policy direction only. It does not change
runtime behavior, hook behavior, `.gitignore`, tracking state, validator
behavior, or evidence export implementation in this artifact.

The selected policy is:

- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` is selected
  to become an ignored runtime artifact by default. Reviewer-facing durable
  evidence must be produced by explicit audit / reviewer milestone export, not
  by accidental runtime append commits.
- `artifacts/session-index.ndjson` is selected to become an ignored runtime
  artifact by default. Reviewer-facing session summaries must be exported
  deliberately when needed.
- Ordinary runtime runs that dirty either ledger should be reported as runtime
  side effects, then restored, staged, or explicitly included in scope before
  claiming a clean workspace until the implementation slice changes tracking.
- `artifacts/runtime/**` remains the ignored local-runtime destination for
  ordinary hook, smoke, verdict, trace, and closeout side effects.
- `artifacts/session/**` remains the ignored local-runtime destination for new
  raw claim-enforcement packets.

## Ledger Handling Rules

| Ledger | Current status | Selected handling | Why |
| --- | --- | --- | --- |
| `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` | tracked compact evidence index until implementation | ignore-by-default selected; explicit milestone export for durable review evidence | Auto-staging every append would turn the compact receipt into a runtime log and inflate evidence claims. |
| `artifacts/session-index.ndjson` | tracked session summary ledger until implementation | ignore-by-default selected; explicit milestone export for durable review evidence | Session-end can append to it during ordinary runs, so it should not be silently mixed into unrelated commits. |

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

The selected future implementation path is Option B:

- move ordinary runtime ledger tracking to ignored local runtime state;
- keep readers tolerant of absence;
- define an explicit audit / reviewer milestone export path before claiming
  durable reviewer evidence from these ledgers.

Rejected alternatives:

1. Keep both tracked ledgers with manual promotion as the long-term default.
   Rejected because it preserves recurring dirty-state friction and scope
   pollution risk for ordinary commits.
2. Treat the ledgers as always-commit evidence. Rejected because it turns
   runtime appends into accidental evidence claims.
3. Delete or ignore without an export story. Rejected because it would weaken
   reviewer-facing evidence durability.

## Warning-Only Detector

The first implementation slice adds:

```powershell
python -m governance_tools.dirty_runtime_ledger_detector --project-root . --format human
```

Default behavior is warning-only:

- dirty ledgers are reported;
- exit code remains `0`;
- no files are modified;
- no hook behavior changes;
- no staging, restore, migration, or routing occurs.

`--fail-on-dirty` exists only as an explicit diagnostic mode. It is not wired
into pre-commit, pre-push, runtime hooks, or validators by this policy.

## Claim Ceiling

CLAIMED:

- Runtime dirty-state policy direction selected for the two ambiguous tracked
  ledgers: ignored-by-default runtime artifacts plus explicit milestone export.
- A clean-workspace claim is invalid while these ledgers remain dirty and
  unhandled before implementation.
- A warning-only detector exists for identifying dirty manual-promotion ledgers.

NOT CLAIMED:

- artifact routing changed;
- ledger tracking changed;
- `.gitignore` implementation completed;
- milestone export implemented;
- hook behavior changed;
- validator behavior changed;
- schema changed;
- pre-commit or pre-push enforcement added;
- detector wired into hooks;
- tracked ledger migration completed;
- historical CE-1D cleanup completed;
- token usage reduced;
- #17 threshold readiness changed.
