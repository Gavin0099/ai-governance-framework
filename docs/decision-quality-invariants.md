# Decision Quality Invariants

> Version: 1.0
> Related: docs/falsifiability-layer.md, docs/learning-loop.md, docs/learning-stability.md,
>           docs/governance-mechanism-tiers.md

---

## Purpose

A decision that produces no failures has not been validated — it has been
uncontradicted. Absence of failure is evidence of three things
indistinguishably: the decision was correct, it has not yet been tested, or
the testing conditions did not include the cases where it would fail.

The learning loop handles failure. The falsifiability layer handles whether
decisions can be proven wrong. This document handles the remaining gap:

**What would it mean for a decision to be genuinely correct, not just
unchallenged?**

Without an answer to this question, the system can enter a state called
misaligned success: observable metrics look healthy (low failure rate, stable
verdicts, clean logs) while actual decision quality is declining. The system
optimizes toward whatever avoids measured failure — which is not the same as
optimizing toward correct decisions. Over-conservatism, blame-avoidance,
reduced exploration, and narrowing to well-covered cases are all consistent
with low measured failure rates while being forms of quality degradation.

Misaligned success is the ceiling above which the standard learning mechanisms
cannot see.

---

## The three decision quality invariants

These invariants are not rules — they are diagnostic properties that any
decision system making genuine claims about quality must satisfy. Failure to
satisfy them does not mean a specific decision was wrong; it means the system
cannot currently distinguish correct decisions from unchallenged ones.

### Invariant 1: Consistency

**Same evidence → same decision.**

If two reviewers, or the same reviewer at different times, reach different
decisions on materially identical inputs, at least one decision is wrong — or
the decision process is not actually governed by the stated criteria.

Consistency is not uniformity. It is the property that decisions are determined
by the evidence and the stated criteria, not by factors that should not affect
the decision (reviewer identity, recent context, unrelated prior decisions).

**How to check:** Take a sample of past decisions. Would materially similar
inputs in a different context have produced the same decision? If the answer
is "it depends on who reviewed it" or "it depends on the timing," consistency
is not satisfied.

**Common failure mode:** Consistency is violated locally before it is violated
globally. Individual reviewers develop local conventions that diverge from
each other and from the stated criteria, while summary statistics still look
uniform. The divergence is only visible when decisions from different reviewers
on similar inputs are compared directly.

### Invariant 2: Robustness

**Irrelevant variation → no decision change.**

A decision that changes in response to factors that do not bear on the
stated criteria has incorporated noise into its basis. The decision is not
governed by the criteria — it is influenced by something else.

Robustness is not rigidity. It is the property that decisions are stable
under variations that should not matter: different phrasing of the same
evidence, different order of presentation, reviewer fatigue, ambient context.

**How to check:** Identify recent decisions. What factors were present that
should not have affected the outcome? Is there evidence that these factors
changed the decision? If yes, robustness is not satisfied.

**Common failure mode:** Robustness failures are systematically
under-detected because they require comparing the actual decision to a
counterfactual. The counterfactual — "what decision would have been reached
without this irrelevant factor?" — is never recorded. Robustness can only be
estimated by deliberate probing, not by reviewing decision logs.

### Invariant 3: Positive falsifiability

**Every accepted decision must have a condition under which we would conclude
it was correct.**

The falsifiability layer (docs/falsifiability-layer.md) requires specifying
what would show a decision was wrong. Positive falsifiability is the
complementary requirement: specifying what would show the decision was right.

If a decision has no positive falsifiability condition — no observable outcome
that would constitute genuine validation — then the decision is unfalsifiable
in the success direction. Absence of failure is then the only available
evidence of correctness. And absence of failure does not distinguish correct
decisions from decisions that have not yet been tested.

**How to specify a positive falsifiability condition:**

> "This decision will have been validated if [specific observable outcome]
> occurs within [time period], without evidence that [confound that would
> make the outcome misleading]."

Example:
> "This documentation change will have been validated if the affected
> misinterpretation type does not recur across three or more observation
> windows from different reviewers, provided those windows contained at
> least [N] relevant observations each."

**What does not count as a positive falsifiability condition:**
- "No new failures appeared" (absence of failure; tested above)
- "The process was followed correctly" (process quality ≠ decision quality)
- "The next review will evaluate it" (deferred to future state, not current)

---

## Misaligned success

Misaligned success occurs when the system's optimization target has quietly
shifted from "decision quality" to "absence of measured failure." The two
targets overlap most of the time — which is why the shift is hard to detect.
Where they diverge, the system produces decisions that minimize detectable
failure while degrading in ways that are not measured.

Common forms:

**Over-conservatism:** Decisions narrow to well-covered territory. Proposals
outside the established pattern are rejected at higher rates not because they
are worse but because they are less familiar. Failure rate stays low because
the system stops taking decisions where failures are more likely.

**Blame-avoidance routing:** Decisions route toward outcomes that distribute
responsibility more broadly, making individual decisions harder to evaluate.
Failure rate stays low because accountability is diffuse.

**Coverage narrowing:** The range of evidence types that influence decisions
shrinks over time. Decisions become reliable for the kinds of evidence the
system has processed before, while becoming less sensitive to new evidence
types. Failure rate stays low for familiar cases; unfamiliar cases are not
recognized as such.

**Exploration reduction:** Decisions that would test the model's assumptions
are avoided in favor of decisions that apply known patterns. The model stops
learning its own boundaries.

**Detection:** Misaligned success is not detectable by failure rate monitoring
alone. It requires checking whether the decision space is narrowing (Coverage
narrowing), whether evidence types are diversifying or converging (Exploration
reduction), and whether decisions would hold up against positive falsifiability
conditions (not just absence of failure).

The silent degradation signals in docs/learning-stability.md cover some of
these: declining decision diversity (Signal A), proposals becoming simpler
(Signal B). Misaligned success extends this by asking whether the decisions
themselves — not just the proposals — are becoming narrower or less testable.

---

## Relationship to the learning loop

The learning loop closes when a failure produces a documented outcome. The
decision quality invariants close the loop in the other direction: when
there is no failure, the system must still ask whether the absence of failure
constitutes evidence that the decisions were correct.

The minimum evidence of positive quality is any of the following:

- A decision has been replicated by a different reviewer on materially similar
  evidence (consistency evidence)
- A decision has been checked against variations that should not matter and
  did not change (robustness evidence)
- A decision's positive falsifiability condition has been observed
  (validation evidence)

If none of these apply, the decision has not been validated. It has been
uncontradicted. The distinction matters when building confidence across
accumulated decisions: uncontradicted decisions do not compound into
validated governance. They compound into a larger mass of assumptions
that have not yet been tested.

---

## What this document does not provide

This document names three invariants and one failure mode. It does not provide
a measurement system. The invariants are diagnostic properties: they tell you
what questions to ask, not what the answers should be.

Building automated measurement for consistency, robustness, or positive
falsifiability requires instrumentation that does not currently exist in this
framework. The purpose of naming the invariants now is to prevent the system
from treating their absence as acceptable indefinitely.

When the framework is mature enough to instrument these invariants, the
threshold at which instrumentation is required should be specified here.
Until then, the invariants function as periodic review prompts — the same
cadence as the silent degradation review (once per three observation windows).
