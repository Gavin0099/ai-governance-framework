# Surface maintenance queue: re-validation against current state

**Date:** 2026-08-13
**Queue:** `governance-surface-maintenance-queue.v0.1.json` — generated 2026-07-07,
amended 2026-07-09, 101 entries
**Validated against:** `0a639e3a`
**Status:** read-only. No queue entry was edited, no disposition changed, no
surface removed.

## Why this was run

The queue carries its own warning that it was stale at birth: entries were
generated while parallel sessions were removing the surfaces being catalogued.
Five weeks have passed. Any use of it — including as the starting point for a
capability-boundary exercise — needs to know which entries still describe
something real.

## Result

| | count |
|---|---|
| present | 82 |
| absent, and intended to be | 5 |
| **determined** | **87** |
| undetermined — no locator a script can resolve | 14 |
| **total** | **101** |

**Among the 87 determined entries, none was silently lost.** The 14 undetermined
entries are not covered by that statement, and nothing here should be read as
clearing them.

An earlier draft of this note put "silently lost load-bearing surfaces = 0" at
the top of the table without that qualifier, while listing the 14 unjudged
entries further down. Those two things cannot both be said. A count of zero
across 101 requires having looked at 101.

Per-entry results — `defense`, resolution type, resolved locator, method,
status, evidence — are in
[`surface-maintenance-queue-revalidation-2026-08-13.ledger.json`](surface-maintenance-queue-revalidation-2026-08-13.ledger.json),
so the sweep can be rechecked without rerunning it.

### The five absences are the executed retirements

All five `retire_candidate` entries resolve to files that no longer exist:

```
governance_tools/ab_cost_backfill_apply.py
governance_tools/clean_pilot_admissibility.py
governance_tools/host_agent_memory_sync_signal.py
governance_tools/promotion_gate_receipt_smoke.py
governance_tools/r49x4_metric_ranking.py
```

That is the disposition being carried out, not decay. These entries are closed
and need no further decision.

### The mechanical pass produced four false absences

Worth recording, because the first pass of this audit reported three `keep` and
one `keep_rare_critical` entry as missing, which would have read as load-bearing
defenses silently disappearing. Per-entry checking showed all four present:

| entry | disposition | actually |
|---|---|---|
| `F-7` | keep | `governance_tools/f7_full_update.py` |
| `pre-push` | keep | `scripts/hooks/pre-push` |
| `red-team` | keep | a documented process, three docs under `docs/governance/` |
| `escalation_authority_writer / escalation_authority_path_guard` | keep_rare_critical | **both** files present; the compound name defeated path lookup |

The lesson is about the queue's schema rather than its content: `defense` mixes
file paths, bare tool names, compound names and prose descriptions in one field.
Nothing keyed on it can be trusted without a second pass, and a mechanical
sweep over it will manufacture alarming false negatives.

## What still needs a human

Fourteen entries name surfaces no script can resolve — processes, vocabularies,
document clusters, and cross-tool duplication judgements. These are the actual
remaining work in the queue:

- `decision-change ledger`, `design-note classification`, `pre-commit hook`,
  `closeout receipt` — keep / keep_observe, conceptual
- `phase_d_closeout_writer (human-only close gate)`,
  `memory_freshness_guard (fail-closed)`,
  `push / destructive-operation authorization discipline` — keep_rare_critical,
  where the question is whether the discipline holds, not whether a file exists
- `cache-aware design-note cluster (11 docs)`,
  `human_readable_adoption_summary carriers`,
  `manual_update / destructive_manual_update vocabulary surfaces` — merge
  candidates, requiring a judgement about which carrier is canonical
- `memory_workflow doc surfaces`,
  `release/reviewer/trust reader+snapshot+summary tool triplets (14 tools)` —
  investigate
- `memory historical warning counts`,
  `test_signal_quality_audit lexical signals` — downgrade candidates

## Claim boundary

This is an existence check against one revision. It does **not** establish that
a present surface still works, is still reached at runtime, still earns its
maintenance cost, or that its recorded disposition is still the right one. The
frequency and cost classes in the queue were not re-derived; `maintenance_cost_class`
is still `unassessed` on the entries that shipped that way. Nothing here
authorises retiring, merging or downgrading anything.

The "none silently lost" finding covers the 87 determined entries only. The 14
undetermined entries have not been checked by any means — not mechanically, not
by hand — and could contain a lost surface without this audit knowing.
