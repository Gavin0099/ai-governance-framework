# Expansion Admission Gate

> Status: **active**
> Created: 2026-03-30
> Applies to: any proposed addition to the governance runtime

---

## Purpose

This gate exists because the most common way a governance framework fails is not
from bad implementations — it is from good-sounding additions that were never
necessary.

Every new runtime surface (import, hook, signal source, dict key, decision input)
must pass this gate before it enters the codebase.

The gate is not a bureaucratic checkpoint. It is a forcing function that surfaces
the question that is easy to skip: **does this need to exist at all?**

---

## What Triggers This Gate

A change triggers this gate if it introduces any of the following:

- a new import in `session_start.py`, `pre_task_check.py`, or `post_task_check.py`
- a new key in the dict returned by any of those three functions
- a new source that influences `ok`, `task_level`, `risk`, or `oversight`
- a new escalation path (anything that can raise task_level)
- a new schema (a new JSON/YAML structure that other code will parse)
- a new runtime hook (anything that runs automatically during session lifecycle)
- a new `governance_tools/` module that the runtime is expected to call

A change does **not** trigger this gate if it:
- fixes a bug in existing behavior
- adds tests for existing behavior
- improves error messages or output formatting
- adds a standalone CLI tool with no runtime integration

---

## Required Questions

Every proposed addition must answer all five. If any cannot be answered, the
addition is rejected.

### Q1: What failure mode does this solve?

Name a specific, observable failure that happens today without this addition.
Not a hypothetical. Not a "would be nice to know." A thing that actually goes
wrong.

> If you cannot name a failure mode, stop here.

### Q2: Why can existing layers not solve it?

Show that the following were considered and found insufficient:
- `pre_task_check`
- `session_start` state loading
- `governance_drift_checker`
- `post_task_check` validators
- offline CLI tools (no runtime integration)

If any of those can solve it, use that instead.

### Q3: What wrong decision occurs without it?

Describe the specific decision that would be wrong without this addition.
A decision means: a change to `ok`, `task_level`, `risk`, `oversight`, or
a gate exit code.

If the answer is "no decision changes, only visibility" — the addition belongs
outside the runtime, not inside it.

### Q4: Does this add a new decision input?

Answer yes or no.

If yes: this is a high-risk addition. It must justify why an additional decision
input is worth the complexity and determinism cost. The burden of proof is higher.

If no: confirm that the new surface cannot influence any of the five outputs named
in Q3, under any code path including future changes.

### Q5: What is the token and complexity cost?

Estimate:
- added tokens to the session_start / pre_task payload
- added imports and call paths
- added schema surface that will need to be maintained

If the cost is non-trivial and Q1–Q3 are weak, reject.

---

## Decision Outcomes

| Q1 | Q2 | Q3 | Q4 | Outcome |
|----|----|----|----|----|
| answered | answered | answered | no | Proceed with review |
| answered | answered | answered | yes | Proceed with elevated scrutiny |
| not answered | — | — | — | Rejected: no failure mode |
| answered | not answered | — | — | Rejected: existing layer sufficient |
| answered | answered | "visibility only" | — | Rejected: belongs outside runtime |

---

## How to Submit

Create a file at `docs/expansion-cases/<slug>-proposed.md` using the structure:

```
# Expansion Proposal: <name>

## Proposed addition
<describe the import / hook / key / schema>

## Q1: Failure mode
## Q2: Why existing layers are insufficient
## Q3: Wrong decision without this
## Q4: New decision input? (yes/no + justification)
## Q5: Token and complexity cost

## Recommendation
```

Submit the file for review before writing any code.

---

## Rejected Cases

| Case | Date | Rejection reason |
|------|------|-----------------|
| [Entry layer → session_start](expansion-cases/entry-layer-rejected.md) | 2026-03-30 | Q3 unanswerable: no decision changes, visibility only |
