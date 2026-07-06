# R49.x-4 Metric Ranking Artifact Freeze (2026-07-06)

As-of: 2026-07-06
Scope: artifact-provenance freeze for the R49.x-4 metric usefulness ranking
evidence, authorizing retirement of its one-off producer script.

## Frozen Artifact

- `docs/status/ab-causal-r49x4-metric-ranking-2026-05-16.json`

Status: frozen historical evidence. The artifact is preserved in place and
must not be regenerated, edited, or deleted. Lineage references from R49.x
and R50 documents remain valid as historical citations:

- `docs/status/ab-causal-r492-reviewer-substitution-status-2026-05-15.md`
- `docs/status/ab-causal-r49x-consolidation-tracker-2026-05-15.json`
- `docs/status/ab-causal-r50-non-upgrade-audit-2026-05-16.md`

## Retired Producer

- `governance_tools/r49x4_metric_ranking.py`

The script was a one-off analysis over the fixed 18-run R49.2 checkpoint
(`docs/status/ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json`).
Its output was written once on 2026-05-16 and has not been regenerated since.
There is no regeneration path after retirement; the frozen artifact is the
canonical record of the R49.x-4 result.

Provenance basis:

- Decision-change ledger inventory-line pass classified the script as a
  retire candidate (`docs/governance/decision-change-ledger.inventory.v0.1.json`).
- The 2026-07-06 retire-candidate focused review (memory/04_review_log.md)
  set disposition `deprecate-first`: preserve the generated artifact as
  historical evidence and retire the script only after documenting the
  artifact as frozen and no longer regenerated. This document is that record.

## Claim Boundary

Allowed claim:

`The R49.x-4 metric ranking evidence is frozen as-is; its producer script is
retired without loss of the recorded result.`

Disallowed claims:

- "R49.x metric conclusions were re-validated at freeze time"
- "the metric ranking generalizes beyond the original 18-run checkpoint"
- "any other retire candidate is authorized by this freeze"

## Exit Criteria

Reopening R49.x metric analysis requires new lineage (a new task id and a new
producer), not regeneration of the frozen artifact in place.
