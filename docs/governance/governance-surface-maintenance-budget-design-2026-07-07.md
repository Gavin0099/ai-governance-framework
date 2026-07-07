# Governance Surface Maintenance Budget Design - 2026-07-07

Status: design/reference note
Runtime behavior change: no
Enforcement change: no
Consumer repo change: no
Tooling change: no

## Purpose

This note defines a maintenance-budget model for AI Governance defenses. It
exists because a governance system can fail by growing faster than it can be
maintained: more rules, validators, memories, playbooks, and warnings can
increase apparent coverage while reducing actual decision quality.

This is a design artifact only. It does not delete, merge, retire, downgrade,
or enforce any defense.

## Problem

The next governance question should not only be:

> What defense is still missing?

It must also be:

> Which defenses are still worth their maintenance cost?

Observed risk pattern:

- documents can outgrow the agent load path;
- rules can become too detailed for humans or agents to maintain;
- validators can exist without checking the critical domain failure;
- new repo adoption can become painful;
- governance output can look complete while execution cost is too high.

The goal is to keep the system strong without letting it become heavy enough
that agents route around it or humans stop reading it.

## Existing Inputs

This design uses existing artifacts rather than creating a new gate:

- `docs/governance/decision-change-ledger.seed.json`
- `docs/governance/decision-change-ledger.inventory.v0.1.json`
- `docs/governance/decision-change-ledger.window-20260622-20260706.v0.2.json`
- `docs/governance/context-cost-budget-design-2026-07-06.md`
- `docs/governance/design-note-classification.json`

The decision-change ledger answers whether a defense output changed a later
decision. The context-cost design answers whether agent reads had a decision
purpose. This note uses both but does not merge their populations.

## Definitions

| Term | Meaning |
|---|---|
| Defense | A rule, validator, warning, advisory, managed block, protocol, hook, CI check, receipt, or report-only diagnostic. |
| Maintenance cost | The effort to keep a defense current, visible, tested, routed, documented, and understood across repos and agents. |
| Decision effect | Evidence that a defense changed scope, implementation, validation, claim ceiling, release note, review verdict, commit, push, routing, or next slice. |
| Duplicate defense | Two or more surfaces carry materially the same rule or warning. |
| Noisy defense | A defense fires often but current evidence does not show it changed a decision. |
| Zombie defense | A defense exists in inventory but has no recent load, call, output, or decision path. |
| Rare-critical defense | A low-frequency defense with high consequence, such as destructive-operation checks, authorization boundaries, safety escalation, or human-only gates. |

## Budget Principle

Every new defense must answer:

1. What observed failure requires this defense?
2. Why do existing defenses not cover that failure?
3. What surface does this defense replace, merge, or deliberately coexist with?
4. What evidence will show that this defense changes decisions?
5. What is the planned review or expiry point if no decision effect appears?

If these questions cannot be answered, the proposed defense should stay as a
proposal-only note, not become another active surface.

## Keep / Merge / Downgrade / Retire Criteria

### Keep

Keep a defense when at least one is true:

- it has confirmed decision-changing evidence in the ledger window;
- it is rare-critical and still reachable;
- it is the canonical source for a rule used by managed or runtime surfaces;
- it is needed to preserve traceability for a recent active decision.

Required evidence:

- ledger entry, receipt, review finding, memory entry, or wiring reference;
- no unresolved duplicate source that should become canonical instead.

### Merge

Merge defenses when:

- the same rule appears in multiple docs, managed blocks, or templates;
- one surface is clearly canonical and the others are propagation carriers;
- readers can be pointed to a summary or canonical surface without losing
  decision-relevant content.

Merge order:

1. identify the canonical target;
2. add pointers to covered source notes if they remain in place;
3. update classification metadata;
4. only then consider archive or retirement in a later slice.

### Downgrade

Downgrade a defense when:

- it fires often but rarely changes decisions;
- it is useful as reviewer context but too weak for high-salience reporting;
- it is lexical or heuristic and prone to Goodhart behavior;
- it should remain visible but aggregated, sampled, or moved to lower salience.

Downgrade examples:

- repeated historical warning counts that are better baseline-aggregated;
- lexical test-signal findings that are reviewer aids, not gates;
- broad summaries that should be linked from a canonical entrypoint instead of
  repeated in every closeout.

### Retire Candidate

Mark a defense as retire_candidate only when all are true:

- it is not rare-critical, or a focused safety review has approved retirement;
- inventory evidence shows no reachable load/call/output path or a superseding
  canonical defense exists;
- no recent decision-changing evidence exists;
- downstream surfaces will not silently lose an active rule;
- a rollback path or source note remains discoverable.

Retirement should be a two-step process:

1. classify and mark as retire_candidate;
2. retire/archive/delete only in a later reviewed slice.

## Rare-Critical Exception

Rare-critical defenses must not be retired solely because they do not appear in
a recent decision window.

Examples:

- destructive cleanup approval rules;
- push authorization discipline;
- human-only escalation boundaries;
- safety or privacy stop conditions;
- schema or evidence admissibility rules with high blast radius.

These defenses need a different proof path: reachability review, rehearsal,
mutation testing, or explicit human decision. Frequency is not enough.

## Maintenance Cost Classes

| Cost class | Typical signs | Preferred action |
|---|---|---|
| Low | single canonical surface, focused test, low drift | keep |
| Medium | several propagation surfaces, clear owner, known validation | keep or merge |
| High | many duplicated surfaces, unclear owner, stale docs, repeated warnings | merge or downgrade |
| Excessive | no decision effect, no owner, costly updates across repos | retire_candidate after review |

Cost class is advisory. It must not override rare-critical status.

## Decision-Effect Thresholds

Use the decision-change ledger vocabulary:

- `decision_changing`: strong keep signal;
- `decision_relevant_unacted`: keep_observe or investigate;
- `noisy`: downgrade candidate;
- `duplicate`: merge candidate;
- `zombie_candidate`: investigate or retire_candidate after focused review;
- `unknown`: do not change status without more evidence.

Do not promote a defense into enforcement just to make it feel useful. A noisy
defense should usually lose salience before it gains blocking power.

## Context-Cost Link

Maintenance budget and context budget are related but separate.

Maintenance budget asks:

> Is this defense worth keeping active?

Context-cost budget asks:

> Did reading this surface help this slice make a decision?

A defense can be worth keeping while rarely read, especially if it is
rare-critical. A frequently read surface can still be merged if it duplicates a
canonical rule. Do not collapse these records into one ledger.

## Recommended Review Cadence

Run a maintenance-budget review on a fixed cadence or after visible expansion:

- monthly for active framework development;
- after adding a new protocol, validator family, managed block, or hook;
- after a cluster of three or more related release-note entries;
- before promoting report-only diagnostics into advisory or blocking behavior.

The cadence should produce a queue, not direct edits:

1. keep;
2. merge;
3. downgrade;
4. retire_candidate;
5. investigate.

## Minimum Future Artifact Shape

A future data artifact may summarize budget status without changing behavior:

```json
{
  "schema": "governance_surface_maintenance_budget.v0.1",
  "source_ledgers": [
    "docs/governance/decision-change-ledger.window-20260622-20260706.v0.2.json",
    "docs/governance/decision-change-ledger.inventory.v0.1.json"
  ],
  "entries": [
    {
      "defense_id": "test_signal_quality_audit.lexical_signals",
      "decision_effect": "noisy",
      "frequency_class": "routine",
      "maintenance_cost_class": "medium",
      "recommended_action": "downgrade",
      "claim_ceiling": "reviewer aid only; no gate"
    }
  ]
}
```

This note does not create that artifact.

## Non-Claims

This note does not claim:

- any defense has been removed;
- any noisy surface has been downgraded;
- any duplicate surface has been merged;
- any validator is meaningful or industry-grade;
- any agent will comply;
- any token savings were measured;
- any hook, gate, CI, runtime behavior, or enforcement changed.

## Next Slice Candidate

The next narrow slice should be read-only:

> Apply this budget model to the current decision-change ledger and inventory,
> then produce a small keep / merge / downgrade / retire_candidate queue with
> evidence references.

That slice should not edit tools, hooks, gates, or consumer repos.
