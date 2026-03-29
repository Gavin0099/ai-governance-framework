# Entry Layer Boundary

> Status: **enforced**
> Created: 2026-03-30
> Reason: entry layer exists in codebase but has not been proven necessary

---

## What This Document Is

This document defines what the entry layer is currently **not allowed to be**,
before any justification has been completed.

It is not a feature list. It is a constraint document.

If `docs/entry-layer-justification.md` later proves the entry layer necessary,
specific constraints here may be relaxed. Until then, all constraints below
are active.

---

## Active Constraints

### 1. Entry layer is not an authority source

The entry layer does not determine what rules apply to a task.
That is the responsibility of `pre_task_check` and the contract loader.

### 2. Entry layer is not an escalation source

The entry layer does not raise task level, risk tier, or oversight requirement.
Observation of a missing `tech_spec` artifact does not trigger L2 escalation.

### 3. Entry layer does not affect stop / continue / escalate verdicts

The presence or absence of any entry-layer artifact (tech_spec,
validation_evidence, pr_handoff) must not change the outcome of:
- `session_start ok`
- `pre_task_check ok`
- `post_task_check ok`
- any governance gate exit code

### 4. Entry layer is not connected to session_start

`workflow_entry_observer` must not be imported or called from
`session_start.py` until the justification is complete and this
constraint is explicitly removed.

**Record**: A connection was added and reverted on 2026-03-30.
Reason for revert: runtime surface area increased without proven necessity.

### 5. Entry layer observation states are not policy inputs

The states `recognized`, `missing`, `incomplete`, `stale`, `unverifiable`
are diagnostic labels only. They must not be used as:
- inputs to risk signal computation
- inputs to task level detection
- inputs to domain gate decisions
- inputs to authority validation

---

## Drift Detection

If any of the following appears in a code review, it should be treated as
a boundary violation:

- `workflow_entry_observer` imported in `session_start.py`, `pre_task_check.py`, or `post_task_check.py`
- any entry-layer state used in an `if` branch that affects `ok`, `task_level`, or `risk`
- entry-layer observations included in authority validation payload
- entry-layer artifact absence treated as a gate failure

---

## How to Lift a Constraint

Complete `docs/entry-layer-justification.md` and answer:

1. If entry layer never existed, what capability would the framework irreversibly lose?
2. Why can that capability not be addressed in `pre_task_check`?
3. What is the smallest implementation that provides only that capability?

If those questions cannot be answered, the constraint stays.
