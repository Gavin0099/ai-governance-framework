# Falsifiability Layer

> Version: 1.0
> Related: docs/misinterpretation-log.md, docs/anti-ritualization-patterns.md

---

## Purpose

A governance decision that cannot be proven wrong cannot be evaluated.

This document defines the falsifiability requirement for expansion proposals
and governance decisions in this framework. It is the final check before a
proposal is accepted: not "is the reasoning sound?" but "if the reasoning is
wrong, how would we know?"

Without this layer, governance evolves by accumulation — each proposal adds
something, nothing is ever proven to have failed, and the system grows
without feedback.

---

## The core requirement

Every accepted expansion proposal must specify, at decision time:

**Falsification condition:** A concrete observable outcome that would indicate
the decision was wrong. This must be:

- **Specific** — not "the problem continues to exist" but "log entries of
  type X continue to appear at rate Y after Z observation periods"
- **Observable** — checkable by reviewing log entries, verdict artifacts,
  or reviewer behavior without running additional experiments
- **Time-bounded** — when would we expect to see the failure signal, if
  the decision was wrong?
- **Decision-reversing** — if the falsification condition is observed, it
  should trigger re-evaluation of the decision, not just be noted

---

## Why "process quality" is not sufficient

A proposal can be:

- Well-reasoned ✓
- Properly evidenced ✓
- Correctly structured ✓
- Wrong ✓

Process quality and decision correctness are independent. A framework that
only measures process quality will accumulate well-reasoned wrong decisions.

The falsifiability requirement is the bridge from process quality to
decision quality. It forces the proposer to think about what the world
looks like if they are wrong — before the decision is made.

---

## Falsification condition examples

**Weak (not acceptable):**
> If the problem persists, we would know the dimension was insufficient.

This is not falsifiable — "problem persists" is undefined and unfalsifiable
without a baseline.

**Acceptable:**
> If `activation_state` continues to appear in log entries as a decision
> input (type: decision_leak) at a rate of 2+ entries per observation window
> after the new dimension is introduced, the dimension failed to address
> the root cause.

**Acceptable:**
> If the total log entry rate does not decrease in the observation window
> following the change, the dimension added complexity without reducing
> misinterpretation frequency.

**Acceptable:**
> If reviewer proposals in the expansion proposal log still fail the
> counterfactual check at the same rate after introduction of the new
> scaffold, the scaffold is not improving reasoning quality.

---

## Falsification ≠ reversal condition

Observing a falsification condition is a trigger for re-evaluation, not
automatic reversal. The correct response is:

1. Note the condition in the misinterpretation log
2. Review the original proposal and its reasoning
3. Determine whether the failure is in the dimension design, the
   implementation, or whether the falsification condition itself was
   too strict
4. Make an explicit decision: reverse, adjust, or maintain with updated
   justification
5. Record what changed as a result: `doc_updated`, `model_adjusted`,
   `threshold_changed`, or `no_change_with_justification`. If nothing
   changed, say so explicitly — silent non-response to a falsification
   event is indistinguishable from not having noticed it.

"We observed the falsification condition but decided to keep the change"
is a valid outcome — if it is documented with reasoning.

**Guard against explanation drift:** When a falsification condition is
observed, the first instinct may be to explain it away: edge case,
temporary condition, unrelated factor. This is acceptable if the
explanation can itself be falsified. Ask: what would we expect to observe
if this explanation is also wrong? If no answer exists, the explanation
is not an analysis — it is a narrative covering a failure.

**Trajectory awareness:** Falsified proposals do not exist in isolation.
A pattern of similar proposals repeatedly failing falsification should
increase skepticism toward future proposals in the same category.
The falsification history is not just a record — it is evidence about
where the model's reasoning tends to be weakest.

---

## Relationship to the misinterpretation log

Falsification conditions should be checked at observation window close.
The end-of-window checklist (in misinterpretation-log.md) includes:

> Are any falsification conditions for previously accepted proposals now
> observable?

If yes, this triggers Step 1 above. The condition being observable does
not mean the decision was wrong — it means the decision needs to be
re-examined with current evidence.

---

## What happens without this layer

Without falsifiability requirements, governance decisions accumulate in one
direction: expansion. Because:

- A decision that adds something is visible (the thing exists)
- A decision that was wrong is invisible (unless someone checks)
- Checking requires having specified what to check for — in advance

The result is a system that grows by addition, shrinks only by accident,
and has no feedback loop between past decisions and future ones.

Falsifiability is not epistemological perfectionism. It is the minimum
requirement for learning.

---

## Scope

This layer applies to:

- Accepted expansion proposals (new model dimensions)
- Significant changes to trigger thresholds or severity definitions
- Changes to the proposal gate requirements themselves

It does not apply to:

- Documentation updates
- Wording clarifications
- `doc_updated` resolutions in the log

The falsifiability layer governs structural changes to the governance model,
not routine maintenance.
