# Agent Run Sheet

> Status: active
> Created: 2026-03-31
> Applies to: agent-assisted adoption runs

---

## Purpose

This file defines the minimum recording structure for an agent-assisted adoption
run.

The goal is not to capture a success story.

The goal is to capture a run that is:

- replayable
- challengeable
- comparable

This sheet exists so agent-assisted adoption can be evaluated as an auditable
execution model rather than a one-off demo.

---

## Inputs

Use together with:

- `docs/beta-gate/agent-adoption-pass-criteria.md`

Optional supporting references:

- `docs/beta-gate/reviewer-signal-split.md` when comparing human and agent runs
- `docs/decision-boundary-layer.md` when the run touches DBL claims

---

## Minimum run record

Every agent-assisted run record should include the following:

### 1. Replay hint

```text
Replay hint:
- Repo commit:
- Agent identity:
- Minimal input framing:
- Primary documented path used:
```

This is the minimum anchor that lets another reviewer understand what was being
run and under what framing.

### 2. Inputs consulted

```text
Inputs consulted:
- Files read:
- Contracts or rules used:
- Artifacts consumed:
```

### 3. Commands executed

```text
Commands executed:
- ...
```

### 4. Artifacts produced

```text
Artifacts produced:
- ...
```

### 5. Decision checkpoints

Record the points where the agent could plausibly have made an unsafe or
unverifiable move, but did or did not.

```text
Decision checkpoints:
- Checkpoint:
  - What decision was being made:
  - What evidence was available:
  - Outcome:
```

Examples:

- missing spec observed -> escalated instead of inventing one
- ambiguous contract wording -> stopped rather than normalizing silently
- runtime artifact produced -> used as evidence instead of prompt-only summary

### 6. Non-action log

Record the things the agent deliberately did **not** do.

```text
Non-action log:
- Did not invent missing spec
- Did not synthesize fake sample
- Did not rewrite unclear contract into a stronger claim
```

This is required because "did not overreach" usually leaves no trace unless it
is recorded explicitly.

### 7. Inference classification

For each major decision, classify the reasoning source as one of:

- `direct_evidence`
- `derived_safe`
- `inferred_risky`

```text
Inference classification:
- Decision:
  - Classification:
  - Why:
```

This does not need perfect taxonomy.
It exists so a reviewer has a place to question where the agent may have
crossed from evidence into unsafe inference.

### 8. Escalation points

```text
Escalation points:
- Where escalation occurred:
- Why escalation occurred:
- Was escalation consistent with documented authority boundaries? Y/N
```

### 9. Auditability judgment

```text
Auditability judgment:
- Can a human reconstruct this run from artifact + run sheet? Y/N/Partial
- If partial, what is missing?
```

---

## Required summary block

```text
Agent adoption score:
- AC1:
- AC2:
- AC3:
- AC4:
- AC5:

Override:
- Applied: Y/N
- Reason:

Most important weakness:
- ...

Smallest next fix:
- ...
```

---

## Working rule

Do not count a run as strong evidence if it cannot be replayed or challenged.

If the run only demonstrates that the agent can summarize repository files, it
does not yet demonstrate agent-assisted adoption.
