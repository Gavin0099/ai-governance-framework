# Reviewer Run Sheet

> Status: active
> Created: 2026-03-31
> Applies to: Beta Gate condition 2 reviewer runs

---

## Purpose

This file is the minimum author-side checklist for running and recording a
reviewer onboarding pass after `reviewer-signal-split.md` was introduced.

It does not replace the reviewer test pack.

It exists to ensure each run records:

- the raw reviewer experience
- the checkpoint score
- the override decision, if any
- the first meaningful failure layer

---

## Inputs

Before starting a run, confirm the author is using:

- `docs/beta-gate/reviewer-test-pack.md`
- `docs/beta-gate/onboarding-pass-criteria.md`
- `docs/beta-gate/reviewer-test-brief.md`

The reviewer should receive only what `reviewer-test-brief.md` permits:

- the repo URL
- one sentence of framing

Do not hand the reviewer `reviewer-test-pack.md`,
`onboarding-pass-criteria.md`, or `reviewer-signal-split.md` before the run.

After the run, classify failures using:

- `docs/beta-gate/reviewer-signal-split.md`

---

## Minimum recording sequence

1. Save the raw reviewer log at:
   - `docs/beta-gate/reviewer-run-<YYYY-MM-DD>.md`
2. Score CP1 through CP5 using `onboarding-pass-criteria.md`
3. Apply override rules if needed
4. Record the first meaningful failure layer using `reviewer-signal-split.md`
5. Only then propose the smallest fix

---

## Required summary block

Every reviewer run record should include this block near the end:

```text
Signal split:
- First meaningful failure layer: discoverability | interpretation | decision reconstruction | escalation judgment | none
- Why this layer was chosen:

Gate score:
- CP1:
- CP2:
- CP3:
- CP4:
- CP5:

Override:
- Applied: Y/N
- Reason:

Smallest next fix:
- ...
```

---

## Author rule

Do not propose a fix before recording the first meaningful failure layer.

If the run mixes multiple failures, record the earliest one first and keep the
later ones as secondary notes.
