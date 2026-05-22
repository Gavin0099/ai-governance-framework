# Interception Ledger Schema v0.1

> Authority: observation contract — not a policy document
> Purpose: governance effectiveness falsification surface
> Scope: two append-only NDJSON files tracking what governance actually changed

---

## Design Principle

`guard firing ≠ meaningful prevention`

The ledger captures **counterfactual materiality**, not hit counts.
A blocked event is only worth recording if the counterfactual answer to
"what would have happened without this guard?" is non-trivial.

The ledger must record both **interceptions** (guard fired, path changed)
and **bypasses** (guard circumvented, ignored, or ineffective).
A system that only records its successes is producing vanity telemetry.

---

## Files

| File | Contents |
|------|----------|
| `artifacts/governance/intercepted-events.ndjson` | Events where a guard altered execution or prevented a semantic escalation |
| `artifacts/governance/bypass-events.ndjson` | Events where a guard was circumvented, ignored, proved ineffective, or was a false positive |

Both files are append-only. Do not delete entries; add a `superseded_by` field if an entry needs correction.

---

## intercepted-events.ndjson Schema

Required fields:

| Field | Type | Values / Notes |
|-------|------|----------------|
| `event_id` | string | `IE-YYYYMMDD-NNN` — stable cross-reference key |
| `recorded_at` | ISO-8601 UTC | when this entry was written |
| `event_class` | enum | `blocked` \| `semantic_ceiling_enforced` \| `state_transition_rejected` |
| `event_type` | string | semantic label, snake_case |
| `guard` | string | which guard/rule fired |
| `surface` | string | where it fired: `closeout` / `authority_state_machine` / `session_boundary` / `output_mode` / `admissibility_gate` |
| `counterfactual_effect` | string | what would have happened without this guard — be specific, not vague |
| `execution_path_changed` | bool | true if agent/reviewer behavior would have differed |
| `materiality` | enum | `high` / `medium` / `low` / `noise` |
| `evidence_basis` | enum | `observed` / `test_derived` / `retroactive_analysis` — **must not be inflated** |

Optional fields:

| Field | Notes |
|-------|-------|
| `prevented_claim` | the semantic claim that was blocked (for semantic ceiling events) |
| `prevented_action` | the execution action that was blocked |
| `session_id` | if tied to a specific session |
| `repo` | repo context |
| `notes` | free text, max 200 chars |

**Materiality scale:**

| Level | Meaning |
|-------|---------|
| `high` | Without this guard, an unsafe action would have executed or an authority boundary would have been crossed |
| `medium` | Without this guard, a semantic claim would have inflated or a reviewer would likely have been misled |
| `low` | Without this guard, a process gap would have gone undetected but no immediate action consequence |
| `noise` | Guard fired correctly but the event was not materially distinct from ambient behavior |

**evidence_basis rules (hard constraints):**

- `observed`: guard was witnessed firing in a real session with real execution data
- `test_derived`: confirmed by a test that exercises the guard path under real conditions
- `retroactive_analysis`: inferred from code reading + design analysis; no direct execution observation
- `retroactive_analysis` entries **must not** be cited as proof of operational effectiveness
- Upgrading from `retroactive_analysis` → `observed` requires an actual session event, not repeated analysis

---

## bypass-events.ndjson Schema

Required fields:

| Field | Type | Values / Notes |
|-------|------|----------------|
| `event_id` | string | `BE-YYYYMMDD-NNN` |
| `recorded_at` | ISO-8601 UTC | |
| `event_class` | enum | `bypassed` \| `ineffective` \| `false_positive` \| `noise` \| `overridden` |
| `event_type` | string | semantic label |
| `guard` | string | which guard failed to fire or was bypassed |
| `surface` | string | where the bypass occurred |
| `bypass_mode` | string | how it was bypassed: `stale_content` / `manual_no_receipt` / `skip_declared` / `config_absent` / `not_wired` / etc. |
| `counterfactual_effect` | string | what actually happened as a result of the bypass |
| `execution_path_changed` | bool | did the bypass result in a different outcome vs. guarded path? |
| `materiality` | enum | `high` / `medium` / `low` / `noise` |
| `detected_after` | bool | was the bypass detected after the fact (not in real time)? |
| `evidence_basis` | enum | same as intercepted-events |

Optional fields:

| Field | Notes |
|-------|-------|
| `resolution` | commit or action that fixed or accepted the bypass |
| `detection_mechanism` | how the bypass was found |
| `accepted_risk` | bool — if true, bypass is a known accepted structural limit |
| `session_id` | |
| `repo` | |

---

## What NOT to record

- Advisory signals that were displayed but had no gate effect — those belong in canonical-audit-log
- Routine OK sessions with no guard firing — no signal, no record
- Theoretical attack vectors not yet observed or derived from tests
- Events without a non-trivial counterfactual (do not record guards that fire constantly on low-value checks)

---

## honest_state_report (P1 — not yet built)

When built, `honest_state_report.py` will consume both files and answer:

1. How many interceptions have `observed` vs `retroactive_analysis` evidence? (measures operational grounding)
2. What is the bypass-to-interception ratio per guard? (measures guard effectiveness)
3. Are any guards producing only `noise` materiality? (candidates for removal)
4. Have any bypasses recurred after a resolution was recorded? (measures fix durability)

This report is the **bridge between topology vulnerability (E1-B Phase 2) and operational evidence**.
