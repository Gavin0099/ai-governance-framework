# DBL First-Slice Validation Plan

> Status: validation plan
> Created: 2026-03-31
> Depends on: `docs/decision-boundary-first-slice.md`

---

## Why this exists

The first executable slice of the Decision Boundary Layer now exists in
runtime, docs, and a minimal example.

That is enough to prove:

- the slice can run
- the slice can change verdicts
- the slice can be demonstrated in a small external example

It is **not** enough to prove:

- the slice can be reconstructed by external reviewers
- the slice resists misuse or gaming
- reviewer onboarding failures are onboarding problems rather than DBL problems

This plan exists to validate those questions before adding more DBL surface.

---

## Validation principle

The next step is not feature expansion.

The next step is to test whether the current first slice:

1. can be reconstructed by others
2. can be distinguished from documentation-only guidance
3. can resist obvious false-pass / false-compliance patterns

In short:

> do not ask only whether the slice can be used;
> ask whether it can be misused, misread, or wrongly passed.

---

## Step 0: Split the reviewer signal

Before using reviewer results as a gate, separate what is being tested.

Reviewer outcomes currently mix:

- onboarding UX
- document interpretation
- decision reconstruction
- escalation judgment

A simple fail is not enough.

The reviewer exercise should record which layer failed:

- discoverability failure
- interpretation failure
- decision reconstruction failure
- escalation failure

Without this split, reviewer onboarding is too coarse to evaluate DBL.

---

## Step 1: Add a second very small example

The second example should not repeat the first-slice absence case.

It should deliberately target an insufficiency-like case, for example:

- spec exists but is irrelevant to the actual task
- sample exists but covers only a happy path
- fixture exists but does not exercise the failing condition

Purpose:

- test the current boundary of the first slice
- expose what the current gate cannot distinguish
- prevent the team from confusing "works on absence" with "handles sufficiency"

This is still a **very small example**, not a new demo project.

---

## Step 2: Run reviewer reconstruction on both examples

Use the current minimal example plus the second insufficiency-like example.

Use `docs/dbl-first-slice-reviewer-reconstruction-kit.md` as the minimal
reviewer prompt pack for this step.

This is not yet the formal independent-reviewer gate.

Instead, observe:

- where the reviewer can reconstruct the decision cleanly
- where the reviewer starts filling gaps with human intuition
- where the reviewer assumes the system checks more than it actually checks

Purpose:

- validate DBL reconstruction quality
- find the first places where human interpretation exceeds runtime truth

---

## Step 2.5: Add an adversarial / gaming case

Before claiming the first slice is stable, test a case designed to pass form
without real grounding.

Examples:

- a spec that exists but is irrelevant
- a sample that exists but lacks failure-path coverage
- a fixture that exists but carries no meaningful assertion

Purpose:

- see whether the current gate can be trivially gamed
- distinguish "minimal" from "easily bypassed"

If the current gate passes such a case, that is not necessarily a failure of
slice 1 design, but it is evidence that:

- the slice is still explicit-missing-state only
- future validation must address insufficiency, not just absence

---

## Step 3: Return to independent reviewer onboarding

Only after Steps 0, 1, 2, and 2.5 should the formal reviewer onboarding gate be
used as the next maturity check.

At that point, failures become diagnosable:

- fails in discoverability -> onboarding problem
- fails in interpretation -> document/interface problem
- fails in reconstruction -> DBL problem
- fails in escalation -> decision model / authority problem

This makes the reviewer gate useful rather than noisy.

---

## Success criteria

The first slice is meaningfully validated only if all of the following become
true:

1. External reviewers can reconstruct first-slice decisions from artifact alone.
2. Reviewers do not need to silently upgrade the system with their own intuition.
3. The insufficiency-like example clearly exposes current limits instead of being misdescribed as supported.
4. The adversarial case reveals whether the slice is easy to game.
5. Reviewer failure can be attributed to a specific layer rather than a generic onboarding fail.

---

## Non-goals

This plan does not authorize:

- immediate expansion to identity enforcement
- immediate capability runtime integration
- full semantic sufficiency inference
- full precedence engine implementation

Those may come later, but only after the current slice is validated as a real
decision surface rather than a narrow runtime demo.

---

## Working conclusion

The current question is not:

> can the first slice be used?

The more important question is:

> can the first slice avoid being misused, misread, or wrongly passed?

That is the next validation boundary.
