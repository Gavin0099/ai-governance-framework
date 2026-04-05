# Boundary Crossing Protocol

> Version: 1.0
> Related: docs/decision-quality-invariants.md, docs/learning-stability.md,
>           docs/adversarial-test-scenarios.md, docs/governance-mechanism-tiers.md

---

## Purpose

A governance system that operates within its observation model can produce
reliable decisions. The same system, operating outside its observation model,
can produce confident-looking decisions that are structurally unsupported.

The gap between these two states is often invisible from the inside: the
mechanisms run, the signals are checked, the process is followed. Nothing
fires to indicate the decision is unsupported because the mechanisms that
would fire are designed for problems within the observation model — not for
the condition of being outside it.

This document defines:

1. What constitutes a boundary condition — when the system is operating at
   or beyond the edge of what its observation model can support
2. Required behavior at the boundary — the four response types and when
   each applies
3. How to distinguish genuine deferral from avoidance
4. Re-entry conditions — when normal operation resumes

---

## Boundary conditions

A boundary condition is not just "we don't have enough information yet."
It is a structural state: the evidence or mechanism required to make a
supportable decision is unavailable *within the current observation model*,
not just currently absent.

**B1: Evidence below observability threshold**

The evidence required to advance a classification or make a decision is
structurally unavailable. Not "we haven't collected it yet" but "the current
observation structure cannot produce this evidence." Examples: failure mode
that produces no log entries; root cause that would only be visible through
instrumentation that doesn't exist; decision outcome that can only be assessed
after a time horizon the observation window doesn't cover.

**B2: Decision outcome unverifiable within the observation model**

No positive falsifiability condition can be specified for the proposed
decision. The decision would compound into "uncontradicted" rather than
validated. If the only evidence of correctness is absence of failure, and
the failure mode being addressed produces no observable signal when it
recurs in a different form, the decision cannot be verified.

**B3: Classification with no path to resolution**

A failure has been observed and cannot be classified beyond `cause_unknown`.
The mechanisms that would produce structural evidence for `cause_suspected`
or `cause_identified` are not available within the current observation
structure. This is distinct from "we haven't looked enough" — it means the
observation model does not currently cover the causal chain.

**B4: Conflicting signals with no framework adjudication**

Two or more mechanisms produce incompatible required actions, and no
mechanism within the framework establishes precedence between them. Note:
most conflicts between advisory and executable signals are not boundary
conditions — the advisory containment rule resolves them. A true B4 condition
requires that both conflicting signals be executable with no resolution path.

**B5: Decision scope outside observation model coverage**

The decision concerns a failure mode, evidence type, or domain that the
observation model was not designed to cover. The decision requires evidence
or reasoning that the framework cannot produce or evaluate.

---

## Required behavior at the boundary

When a boundary condition is detected, normal operation is suspended. The
required behavior is one of four responses:

### `defer_with_condition`

**When:** The boundary condition is temporary or resolvable. A specific piece
of evidence or a specific change to the observation structure would allow the
decision to be made.

**What it produces:** A documented deferral specifying:
- Which boundary condition applies (B1–B5)
- What specific evidence or structural change would resolve it
- A deadline or trigger: what event causes this deferral to convert to a
  decision or escalate

**What makes it genuine:** The resolution condition must be specific enough
that a different reviewer reading the deferral record could determine whether
the condition has been met. "More evidence" is not a resolution condition.
"A log entry from a second independent reviewer showing the same failure
in a different context" is.

**Default response** when time permits and resolution is possible.

---

### `low_confidence_proceed`

**When:** A decision must be made despite the boundary condition. Deferral
has known consequences (an action proceeds unreviewed; a window closes without
documentation). The cost of proceeding under uncertainty is lower than the
cost of not deciding.

**What it produces:** A decision made and explicitly tagged:
- Which boundary condition applies
- What assumptions the decision relies on that cannot be verified
- A re-evaluation trigger: when or how the decision will be revisited as
  the observation model matures

**What it is not:** A way to make unverifiable decisions without
acknowledging their limitation. `low_confidence_proceed` is not a bypass
of the boundary — it is a boundary-aware decision. The tag must be visible
to future reviewers considering this decision as precedent.

**Failure mode:** using `low_confidence_proceed` to avoid deferral when
deferral is actually feasible. If deferral has no meaningful consequence,
it is the correct response. `low_confidence_proceed` is for cases where
the cost of not deciding is real and acknowledged.

---

### `escalate`

**When:** External validation is available, the decision is important enough
to warrant it, and the escalation can produce a decision within the required
timeframe.

**What it produces:** Decision paused; external input sought with a specific
question and a specific deadline.

**The question must be specific.** "We're not sure what to do" is not an
escalation — it is an offload. A valid escalation names the boundary condition,
describes the decision that needs to be made, and asks a specific question
whose answer would allow the decision to proceed.

---

### `hard_stop`

**When:** The decision must not proceed without crossing back into observable
range. The cost of a wrong decision under the boundary condition exceeds the
cost of blocking the decision entirely.

**What it produces:** A documented hard stop with the condition that must be
met before the decision is re-evaluated.

**When not to use:** `hard_stop` is not a general-purpose block for uncertain
decisions. If the cost of not deciding is non-trivial, `low_confidence_proceed`
is usually more appropriate. Reserve `hard_stop` for decisions where a wrong
answer would be difficult to reverse and the boundary condition is B1 or B2
(not just insufficient evidence, but structurally unavailable evidence).

---

## Distinguishing genuine deferral from avoidance

Both produce the same output: no decision. The distinction matters because
avoidance masquerading as epistemic caution is a governance failure that
does not trigger any standard signal.

A genuine deferral satisfies all four conditions:

1. **The boundary condition is named specifically** — which of B1–B5 applies,
   and why this situation meets that definition
2. **The resolution condition is specified** — what specific evidence or
   structural change would allow the decision to proceed
3. **The deadline or trigger is set** — when this converts to a decision
   or escalates; open-ended deferrals are treated as avoidance
4. **The deferral is itself falsifiable** — what would we observe if this
   deferral was actually avoidance rather than a genuine boundary condition?

Condition 4 is the hardest. A deferral that cannot be distinguished from
avoidance by any observable criterion is not epistemically defensible — it
is an unfalsifiable claim of epistemic caution.

Common avoidance patterns that pass the surface test:

**Pattern: "We need more evidence."**
Looks like: acknowledging insufficient evidence
Is actually: deferring without a resolution condition or deadline
Test: ask "what specific evidence would resolve this?" If the answer is
vague, this is avoidance.

**Pattern: "The situation is complex."**
Looks like: acknowledging that a boundary condition exists
Is actually: naming complexity as a substitute for naming the specific
boundary condition
Test: ask "which of B1–B5 applies and why?" If this cannot be answered,
complexity is not a boundary condition.

**Pattern: "We'll revisit when we have more data."**
Looks like: `defer_with_condition`
Is actually: an open-ended deferral with no trigger
Test: ask "what data, by when, and who is responsible for obtaining it?"
If the answer is "we'll see," this is avoidance.

---

## Re-entry conditions

A boundary condition resolves when:

- For B1: the required evidence is obtained or the observation structure is
  extended to produce it
- For B2: a specific positive falsifiability condition can be stated for the
  decision
- For B3: the failure is reclassified from `cause_unknown` to
  `cause_suspected` with a named mechanism and structural trace requirement
- For B4: one of the conflicting signals is resolved or adjudication
  precedence is established
- For B5: the decision scope is brought within observation model coverage,
  or a specific scope boundary is drawn

When a boundary condition resolves, the deferred decision must be explicitly
reopened and re-evaluated. It does not automatically proceed — the boundary
condition may have changed what the decision should be.

---

## Relationship to the observation model

The boundary crossing protocol is the operational layer for a structural
fact that the framework does not otherwise address: the governance system
has an observation model, and some failures are outside that model.

This is documented in adversarial-test-scenarios.md (Scenario C.3) as the
"structurally invisible" failure class. The protocol does not make these
failures visible — it makes the system's behavior when it encounters them
consistent and documented.

Without this protocol, boundary conditions are handled by individual
reviewer judgment with no requirement for documentation or escalation. The
result is a class of decisions that are neither validated nor flagged as
unvalidated — they exist in the record as decided while actually being
decided under structurally unsupported conditions.

---

## What this protocol does not do

This protocol governs behavior at the boundary. It does not:

- Extend the observation model (that requires instrumentation changes)
- Make structurally invisible failures visible (that requires external
  validation or outcome tracking outside the current system)
- Eliminate the need for judgment about which boundary condition applies

The protocol assumes reviewers can recognize boundary conditions when they
encounter them. That assumption may itself require testing — a reviewer who
applies `cause_identified` under pressure without recognizing it as a B1
condition is not failing to follow the protocol; they are failing to recognize
that the protocol applies. This is a reviewer calibration issue, not a
protocol gap.

The adversarial test pack (Part D) tests boundary recognition. The protocol
governs what happens after recognition occurs.
