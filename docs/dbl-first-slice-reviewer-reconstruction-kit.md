# DBL First-Slice Reviewer Reconstruction Kit

> Status: review aid
> Created: 2026-03-31
> Depends on: `docs/dbl-first-slice-validation-plan.md`

---

## Why this exists

Step 2 is not a feature test.

It is a reconstruction test for the current first-slice DBL surface.

The goal is to find out whether an independent reviewer can correctly infer:

- what the current slice actually checks
- what it explicitly does not check
- whether the insufficiency-like example is read as a limitation proof rather
  than a capability claim

This kit should be used without author-side verbal explanation.

---

## Inputs

Give the reviewer only these materials:

- `examples/README.md`
- `examples/decision-boundary/minimal-preconditions/README.md`
- `examples/decision-boundary/insufficiency-like-preconditions/README.md`

For a ready-to-send reviewer handoff, use
`docs/dbl-first-slice-reviewer-test-pack.md`.

Do not add oral clarification during the first pass.

---

## Reviewer Task Sheet

Ask the reviewer to answer these four questions in writing:

1. What does the current first-slice DBL gate appear able to judge?
2. What does the current first-slice DBL gate appear unable to judge?
3. In what kind of situation would the current gate still pass even though the
   evidence may be semantically weak or incomplete?
4. Is the insufficiency-like example a capability proof or a limitation proof?
   Explain why.

---

## Expected Reconstruction Rubric

Treat the reconstruction as correct only if the reviewer clearly captures most
or all of these points:

- explicit signal presence is not the same thing as semantic sufficiency
- the current first slice is precondition-level only
- the insufficiency-like example is intentionally non-claiming
- a passing result in that example does not imply adequacy judgment
- the semantic insufficiency gap remains open by design

---

## Failure Signals

Treat the exercise as failed if the reviewer:

- claims the current slice already performs semantic sufficiency judgment
- treats the green test result as evidence-quality proof
- reads the insufficiency-like example as a new capability demo
- cannot clearly distinguish presence from sufficiency

---

## Output Format

Record the result as one of:

- `reconstructed correctly`
- `reconstructed partially`
- `reconstructed incorrectly`

Also note:

- which sentence, file, or example caused the misread
- whether the fix appears to be framing-only or runtime-related

---

## Working rule

Step 2 is not asking whether the reviewer is strong enough.

It is asking whether the current examples and framing are strong enough to
prevent reviewer-side over-inference.
