# Reviewer Signal Split

> Status: active
> Created: 2026-03-31
> Applies to: Beta Gate condition 2 and later reviewer runs

---

## Why this exists

Reviewer onboarding failures are too coarse when recorded as a single pass/fail.

The same failed run can mean very different things:

- the reviewer could not find the entry point
- the reviewer found the right file but misread it
- the reviewer understood the files but reconstructed the runtime boundary incorrectly
- the reviewer understood the boundary but escalated or judged it incorrectly

Without splitting these signals, onboarding results are noisy and can lead to
the wrong fix.

---

## Four diagnostic layers

### 1. Discoverability failure

The reviewer cannot find where to start or where to look next.

Typical signs:

- stays at repo root with no direction
- misses `README.md`, `start_session.md`, or the relevant reviewer pack
- cannot locate the drift checker or adoption path

Interpretation:

- entry path problem
- navigation problem
- README / root-pointer problem

---

### 2. Interpretation failure

The reviewer finds the right file but misreads what it means.

Typical signs:

- treats the framework as static docs only
- conflates framework governance with consuming-repo governance
- confuses rule packs, runtime hooks, and domain contracts

Interpretation:

- naming problem
- framing problem
- heading / first-sentence problem

---

### 3. Decision reconstruction failure

The reviewer reads the DBL or runtime materials but reconstructs the wrong
system boundary.

Typical signs:

- treats limitation examples as capability examples
- assumes semantic sufficiency where only explicit presence is checked
- silently upgrades the runtime with reviewer-side intuition

Interpretation:

- DBL framing problem
- artifact contract problem
- example/reviewer-pack mismatch

---

### 4. Escalation judgment failure

The reviewer understands the surface but applies the wrong judgment to the
result.

Typical signs:

- treats a reconstruction failure as a runtime bug
- treats an onboarding blockage as a DBL limitation
- recommends runtime expansion where wording clarification would suffice

Interpretation:

- authority / decision-model communication problem
- reviewer guidance problem

---

## Recording rule

Every reviewer run should classify the first meaningful failure under one of
these four layers before proposing a fix.

If multiple layers are involved, record the earliest one first.

Do not jump directly from a failed run to a framework change without recording
which layer actually failed.

---

## Working rule for authors

When a reviewer run fails:

- fix the lowest-level failure first
- do not treat a discoverability failure as a DBL problem
- do not treat a wording problem as a runtime problem
- do not treat a runtime boundary limitation as an onboarding-only problem

This document exists to keep those distinctions explicit.
