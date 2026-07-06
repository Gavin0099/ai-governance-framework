# Host-Agent Memory Sync Signal Deprecation (2026-07-06)

As-of: 2026-07-06
Scope: deprecate-first record for the host-agent memory sync signal line,
authorizing removal of its evaluator and dedicated tests.

## Deprecated Surface

- `governance_tools/host_agent_memory_sync_signal.py`
- `tests/test_host_agent_memory_sync_signal.py`

Status: deprecated and removed. The module turned host-memory sync policy
inputs into reviewable signals (`memory_sync_missing`,
`host_memory_not_applicable`, `repo_memory_written_only`). It never talked to
a host memory API, was never wired into hooks, CI, scripts, or other tools,
and produced no memory-record output after 2026-04-01.

## Decision Basis

- Decision-change ledger inventory-line pass classified the module as a
  retire candidate (`docs/governance/decision-change-ledger.inventory.v0.1.json`).
- The 2026-07-06 retire-candidate focused review (memory/04_review_log.md)
  set disposition `deprecate-first`: mark deprecated before deletion if
  host-agent memory sync is no longer a current governance line.
- The repository owner confirmed in session on 2026-07-06 that the host-agent
  memory sync line is not a current governance line and authorized retirement.
  This document is the deprecation record required by that disposition.

## Claim Boundary

Allowed claim:

`The host-agent memory sync signal line is deprecated and its evaluator is
removed; the signal vocabulary remains documented here for lineage.`

Disallowed claims:

- "host-agent memory synchronization is handled elsewhere"
- "memory sync signals were migrated to another surface"
- "repo-memory governance (memory_workflow, memory_authority_guard) changed
  in any way"

## Reopening Criteria

If host-agent memory sync becomes a governance line again, open a new design
slice with an explicit operator entrypoint and wiring plan; do not restore the
removed module in place without one.
