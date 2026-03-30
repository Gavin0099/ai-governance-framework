# Expansion Case: Entry Layer → session_start

> Status: **rejected**
> Date: 2026-03-30
> Gate document: `docs/expansion-admission-gate.md`
> Boundary document: `docs/entry-layer-boundary.md`

---

## What was proposed

Import `workflow_entry_observer` into `session_start.py` and call it during
session initialization. The result would be stored in the session_start return
dict under the key `workflow_entry_observation`.

This would make entry-layer observation states (`recognized`, `missing`,
`incomplete`, `stale`, `unverifiable`) available to anything that consumes
the session_start payload.

---

## Why it looked reasonable

The entry layer already existed. The observer already worked. The states it
produces describe whether a task had a tech_spec artifact before implementation
began — a legitimate governance concern.

The argument was: session_start is where governance context is assembled. If
the entry layer produces a governance signal, session_start is the natural
place to receive it.

The code change was small. No existing behavior changed. It felt like
connecting a wire, not adding a feature.

---

## Why it was rejected

### Q1: What failure mode does this solve?

No specific, observable failure was named. The candidate use case was:
"visibility into whether a tech-spec artifact existed before session_start ran."

Visibility is not a failure mode. A failure mode is a wrong decision —
a change to `ok`, `task_level`, `risk`, `oversight`, or a gate exit code.

> Q1 could not be answered. Gate says: stop here.

### Q2: Why can existing layers not solve it?

Not evaluated. Q1 was the blocking failure.

### Q3: What wrong decision occurs without it?

This was the key question. Under the proposed change:

- `session_start ok` does not change based on entry-layer state
- `task_level` does not change
- `risk` does not change
- `oversight` does not change
- gate exit codes do not change

The addition is visibility only. No decision in the runtime would be different.

> Q3 answer: "no decision changes, visibility only."
> Gate outcome: **Rejected — belongs outside the runtime.**

---

## How it almost drifted in

The implementation was written and committed. It passed a surface reading
because the observer call was isolated — it did not directly change any
output field.

The drift risk was subtler:

1. Once the key `workflow_entry_observation` exists in session_start's return
   dict, future code can read it
2. Future code reading it will be tempted to act on it
3. Acting on it means entry-layer states become decision inputs
4. At that point, boundary constraint 5 has been violated — silently

The wire itself is not the problem. The wire is the first step toward a circuit
that changes decisions based on unproven observation states.

---

## How it was caught and reverted

The user challenged the addition with the question: "does this need to exist
at all?" The expansion admission gate question was applied retroactively:

- Q1 could not be answered
- Q3 confirmed no decision would change

The change was reverted on 2026-03-30. The revert was recorded in:
- `PLAN.md` (E2 revert notice)
- `docs/entry-layer-boundary.md` (constraint 4, revert record)

---

## What the entry layer is allowed to be (today)

`workflow_entry_observer.py` continues to exist. It runs as a standalone tool.
Its output is readable by humans and by offline audit processes.

It is not a runtime input. It is not a session_start dependency. It produces
no gate verdicts.

If the entry layer later proves irreplaceable — if a specific failure mode is
named, and Q2 and Q3 can both be answered — the constraint in
`docs/entry-layer-boundary.md` can be lifted. Not before.

---

## Lesson

A useful-looking wire is not a justified runtime addition.

The test is not "does this break anything today." The test is "does this need
to exist in the runtime at all." Small, innocuous integrations that carry no
immediate risk are exactly how a governance runtime accumulates surface area
it cannot later remove without breaking things.

The right default is outside the runtime. The burden of proof runs in one
direction only: toward integration, not away from it.
