# Task-Cost Event-Only Fixture (2026-06-25)

Status: fixture-only  
Scope: selected 2026-06-25 git log + memory evidence  
Token attribution: excluded  
ROI measurement: excluded  
CodeBurn integration: excluded  
Schema/tooling change: no  
Enforcement change: no

## Purpose

This fixture tests whether a minimal task-cost event vocabulary can label the
2026-06-25 session consistently before adding any parser, schema, CodeBurn
bridge, or token attribution surface.

It intentionally records event semantics only. It does not compute task ROI,
token cost, or a reliable rework rate.

## Minimal Event Vocabulary Tested

### `discrepancy_caught`

A review, audit, or verification event found a mismatch that would have produced
misleading state, stale authority, false delivery confidence, or avoidable
downstream rework if left uncorrected.

### `reviewer_induced_rework`

A reviewer finding against newly produced work forced a redo, replacement, or
material correction of that work before push or acceptance.

### `planned_debt_repair`

A deliberate repair of pre-existing governance debt found by audit/checker work.
This is valuable corrective work, but it is not reviewer-induced rework.

### `human_acceptance`

Human or delegated-review acceptance of a bounded scope. This event carries the
"correct enough for this scope" boundary. It may include validation evidence and
push readiness, but it is not a global correctness or ROI claim.

### `push_verified`

The accepted scope was pushed to required remotes and remote heads were verified.
This is delivery evidence, not proof of semantic correctness.

## Fixture Events

### E1 - Consumer hygiene delivery gap caught

```yaml
event_id: 2026-06-25-e1
event_type: discrepancy_caught
task_area: consumer-governance-hygiene
summary: Consumer .gitignore hygiene fix was implemented but not pushed, so it had zero cross-repo effect until delivery.
evidence:
  commits:
    - dca82b2
  memory:
    - memory/2026-06-25.md entry "Pushed the consumer .gitignore hygiene fix"
classification_notes:
  - delivery gap caught
  - not a source-code correctness failure
  - prevented false belief that consuming repos could already receive the fix
claim_ceiling:
  - discrepancy observation only
  - no ROI or token claim
```

### E2 - Consuming repo update reporting overclaim caught

```yaml
event_id: 2026-06-25-e2
event_type: discrepancy_caught
task_area: consuming-repo-update-reporting
summary: A consuming repo update report treated repo_native_verified/head_ok/ts_ok too strongly; the routed update protocol was corrected to state these are receipt/evidence-chain integrity signals only.
evidence:
  commits:
    - 58c53ea
    - 66767d6
  memory:
    - memory/2026-06-25.md entry "Amended governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md"
classification_notes:
  - external-agent overclaim detection
  - reporting correction
  - not proof that the consuming repo was governed or enforced
claim_ceiling:
  - reporting protocol correction only
  - no consuming repo runtime behavior change
```

### E3 - AUTHORITY live source misconception caught

```yaml
event_id: 2026-06-25-e3
event_type: discrepancy_caught
task_area: governance-authority-freshness
summary: Review traced session_start/authority_loader and found AUTHORITY tiers are live frontmatter-driven allowlist inputs, not inert prose.
evidence:
  commits:
    - 4a110cc
    - 7c767c8
  memory:
    - memory/2026-06-25.md entry "Added docs/governance/governance-document-freshness-classification"
classification_notes:
  - stale authority metadata risk found
  - full-text prompt injection was not proven
  - finding changed priority of AUTHORITY/PLAN repair
claim_ceiling:
  - allowlist/gate behavior observed
  - no prompt-injection proof
```

### E4 - governance/PLAN.md authority tier repaired

```yaml
event_id: 2026-06-25-e4
event_type: planned_debt_repair
task_area: governance-authority-freshness
summary: governance/PLAN.md was reclassified away from agent-runtime/canonical/default_load=always to agent-on-demand/reference/default_load=on-demand, with root PLAN.md kept as current planning authority.
evidence:
  commits:
    - 44a424b
    - 88a021c
    - ab7d559
    - 86ebb9c
  memory:
    - memory/2026-06-25.md entry "Implemented the P0 AUTHORITY freshness repair"
classification_notes:
  - pre-existing governance debt repair
  - not reviewer-induced rework
  - validation showed L0 allowed set excluded PLAN.md and L1 included PLAN.md on demand
claim_ceiling:
  - PLAN tier repair only
  - no SYSTEM_PROMPT/AGENT/HUMAN-OVERSIGHT rewrite
  - no full governance freshness repair
```

### E5 - AUTHORITY table/frontmatter drift found by checker

```yaml
event_id: 2026-06-25-e5
event_type: discrepancy_caught
task_area: authority-metadata-consistency
summary: The report-only authority metadata consistency checker found one missing AUTHORITY table row and three docs with table rows but missing parser-readable frontmatter.
evidence:
  commits:
    - 1c9b874
    - 6f8e1f0
  memory:
    - memory/2026-06-25.md entry "Added a read-only authority metadata consistency checker"
observed_findings:
  missing_table_rows:
    - governance/RULE_REGISTRY.md
  missing_frontmatter:
    - governance/MEMORY_PROTOCOL.md
    - governance/PHASE_D_CLOSE_AUTHORITY.md
    - governance/RESPONSE_ENVELOPE_CONTRACT.md
classification_notes:
  - checker-produced diagnostic
  - report-only, not enforcement
claim_ceiling:
  - diagnostic output only
  - no hook/CI/pre-push enforcement
```

### E6 - AUTHORITY table/frontmatter drift repaired

```yaml
event_id: 2026-06-25-e6
event_type: planned_debt_repair
task_area: authority-metadata-consistency
summary: Repaired the checker-reported authority metadata drift by adding the RULE_REGISTRY.md table row and frontmatter for three docs.
evidence:
  commits:
    - 459f369
    - 79016e3
  memory:
    - memory/2026-06-25.md entry "Repaired governance authority metadata consistency drift"
classification_notes:
  - pre-existing governance debt repair
  - not reviewer-induced rework
  - memory records corrective L1/L2 on-demand allowlist alignment
claim_ceiling:
  - metadata consistency repair only
  - L0 always-set unchanged
  - L1/L2 on-demand alignment acknowledged
```

### E7 - Memory claim ceiling under-described L1/L2 allowlist impact

```yaml
event_id: 2026-06-25-e7
event_type: reviewer_induced_rework
task_area: authority-metadata-consistency-memory
summary: Review found the first memory commit for the metadata repair under-described runtime impact; it was redone to state MEMORY_PROTOCOL.md and RESPONSE_ENVELOPE_CONTRACT.md entered L1/L2 on-demand allowlist while L0 stayed unchanged.
evidence:
  superseded_commit:
    - eeff1b4
  replacement_commit:
    - 79016e3
  source_commit:
    - 459f369
classification_notes:
  - clean reviewer-induced rework sample
  - caused by claim-ceiling precision finding on newly produced memory
  - separate from planned debt repair
claim_ceiling:
  - one reviewer-induced rework sample
  - no general rework-rate claim
```

### E8 - Task-cost extract-first diagnostic accepted and delivered

```yaml
event_id: 2026-06-25-e8
event_type:
  - human_acceptance
  - push_verified
task_area: task-cost-extract-first
summary: The extract-first diagnostic note was accepted after review, committed with canonical memory, pushed to origin/main and gitlab/main, and remote heads were verified at 6131405.
evidence:
  commits:
    - 659ae44
    - 6131405
  final_head:
    - 6131405
classification_notes:
  - human acceptance applies to the bounded diagnostic scope
  - push verification is delivery evidence only
  - this does not measure ROI or compute token-to-correct-result
claim_ceiling:
  - accepted docs+memory slice only
  - no task-level metric implementation
  - no token attribution
```

## Consistency Check

The minimal vocabulary can label this session's selected events without adding
token attribution or a schema:

```text
discrepancy_caught: E1, E2, E3, E5
planned_debt_repair: E4, E6
reviewer_induced_rework: E7
human_acceptance: E8
push_verified: E8
```

The vocabulary is usable for event-only analysis, but it is not yet sufficient
to compute task-level outcome cost.

## Ambiguities Observed

### Commit-to-event granularity

`79016e3` appears in both E6 and E7 because it is the memory record for the
metadata repair and also the replacement product after reviewer-induced rework.
This shows that commits are not guaranteed to map 1:1 to task-cost events.
Future records should either allow one commit to support multiple events or use
event IDs as the primary unit and treat commits as evidence anchors.

### Mixed-type discrepancies

`discrepancy_caught` is intentionally broad. It includes:

- self-caught delivery/reporting issues;
- external-agent overclaim detection;
- stale governance authority findings;
- checker-produced drift findings.

Future records may need a `discrepancy_subtype` field, but this fixture does not
add schema.

### Planned debt repair vs reviewer-induced rework

`ab7d559` and `459f369` are repair commits, but they should not be counted as
reviewer-induced rework because they repair pre-existing debt discovered by
audit/checker work.

`79016e3` is a clean reviewer-induced rework sample because it replaced a newly
produced memory record after review found a claim-ceiling precision gap.

### Human acceptance granularity

This fixture records one acceptance/push event for the task-cost diagnostic
slice. It does not attempt to reconstruct every acceptance event in the full
session. Many review ACCEPT events live in conversation rather than durable repo
artifacts.

## Claim Ceiling

Can claim:

- The minimal event vocabulary can label selected 2026-06-25 session events.
- Existing git log + memory evidence supports at least the fixture events above.
- The event-only layer is separable from CodeBurn execution/token observation.

Cannot claim:

- Governance ROI was measured.
- Task-level rework rate is reliable.
- Total tokens to correct result can be computed.
- Human acceptance events are completely captured across the session.
- CodeBurn is integrated with this event vocabulary.
- Any schema, parser, tooling, hook, validator, or enforcement behavior changed.

## Next Step

If this line continues, the next useful slice is to repeat event-only labeling on
one more session or turn this fixture into a minimal append-only record only for
events that cannot be recovered from git + memory.

Do not add token attribution until task lifecycle boundaries and human
acceptance events can be bound to token telemetry.
