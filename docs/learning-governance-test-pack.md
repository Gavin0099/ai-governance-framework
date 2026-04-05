# Learning Governance Test Pack

> Covers commits: d32444d → f4e7d33
> Scenario count: 16 (Parts 1–7)
> Passing score: 15–16
> Documents under test:
> - docs/anti-ritualization-patterns.md  (Part 7)
> - docs/falsifiability-layer.md         (Part 4)
> - docs/learning-loop.md                (Part 1)
> - docs/learning-stability.md           (Parts 2, 3)
> - docs/decision-quality-invariants.md  (Part 5)
> - docs/governance-mechanism-tiers.md   (Part 6)
>
> Maintenance note: if scenarios are added or removed, update scenario count,
> score bands, and the manifest above. These three must stay in sync.
>
> **Schema integrity check** (verify before publishing an updated version):
> - [ ] Scenario count in manifest == actual scenario count in document
> - [ ] Score band max == scenario count
> - [ ] Every enforceable mechanism in governance-mechanism-tiers.md has ≥1 scenario
> - [ ] No document listed in manifest is absent from the scenario sources
>
> This pack is a **conformance test**: it verifies internal consistency and
> correct application of mechanisms. It does not verify that the mechanisms
> produce correct decisions. See docs/adversarial-test-scenarios.md for
> external validity testing.

---

## How to use this pack

Each scenario gives you an input situation and asks you to make a judgment call.
After each scenario, a **verdict** section shows the correct outcome and which
rule produces it. Read the scenario first, write your answer, then check.

This pack is not a quiz about vocabulary. It is testing whether you can apply
the mechanisms under realistic conditions where the right answer is not obvious
from the surface.

If your answer matches the verdict: the mechanism is working as intended.
If your answer differs: read the verdict reasoning before concluding you were
wrong — the verdict may be wrong. Record genuine disagreements.

---

## Part 1 — Learning loop closure (docs/learning-loop.md)

### Scenario 1.1

An expansion proposal was accepted two months ago. Its falsification condition
was: "if the misinterpretation type recurs after the new documentation, this
proposal failed." Last week, a new log entry was added showing the same
misinterpretation type recurring.

The reviewer who added the log entry wrote: "This looks like the same issue
but in a slightly different context. I'll flag it for next window."

**Question:** Is the learning loop closed?

<details>
<summary>Verdict</summary>

**No. The loop is open.**

A falsification condition has been observed. The required response is not
"flag for next window" — it is a documented outcome now: one of
`model_adjusted`, `doc_updated`, `no_change_justified`, or
`investigation_pending`.

"Flag for next window" is silent non-response. It is indistinguishable from
not having noticed the falsification event.

If there is not enough information yet, the correct outcome is
`investigation_pending` with a deadline. That closes the loop
(provisionally) while making the open investigation visible.

**Source:** learning-loop.md — "Silent non-response is not allowed."

</details>

---

### Scenario 1.2

A `doc_updated` response was applied after a reviewer misread the
`activation_state` field as a decision input. The documentation was updated
with a clearer warning. Three weeks later, a different reviewer makes the same
error in a different repo.

The reviewing team says: "The doc was updated. This new reviewer probably just
didn't read the updated section. Let's point them to it."

**Question:** Is the prior `doc_updated` response still valid? What outcome
is required now?

<details>
<summary>Verdict</summary>

**The prior response must be re-evaluated — it cannot be reused.**

A `doc_updated` response is valid only if it changes what a reviewer would
do when encountering the same situation. If the same failure recurs, the
prior response was either at the wrong level or insufficient.

"They probably didn't read it" is a plausible explanation — but it requires
classification: is this `cause_identified` (specific evidence that the
reviewer had not read the update) or `cause_suspected`? If `cause_suspected`,
the outcome must be `investigation_pending`, not `no_change_justified`.

If this is the second recurrence from a different context, the same-failure
taxonomy applies: is this "exact symptom, different reviewer" (same class)?
If yes, the prior `doc_updated` may have been incomplete, not wrong. The
response required is an extension, not a repeat.

**Source:** learning-loop.md — "If the same failure recurs after a
`doc_updated` response, the prior response must be re-evaluated — not reused."

</details>

---

### Scenario 1.3

An observation window closed. The team reviewed the log and found no
falsification events. They wrote: "Window clean. Model is working. No
changes needed."

**Question:** Has the learning loop closed for this window?

<details>
<summary>Verdict</summary>

**Partially — but the window close is incomplete.**

No falsification events is a valid outcome. But the window close requires
two additional steps that the entry above omits:

1. **Name untested assumptions:** which assumptions underlying the current
   model have not been tested by any falsification signal during this window?
   These are not necessarily wrong — they should be named, not left implicit.

2. **Confirm observation activity:** were there actual reviewer interactions
   during this window? "Window clean" is only evidence of sufficiency if the
   window contained sufficient activity (≥3 distinct reviewer interactions
   per the negative pressure validity rule). If the window had no activity,
   the clean result means nothing was measured — not that the model is working.

**Source:** learning-loop.md (window close checklist) + misinterpretation-log.md
(negative pressure rule, anti-ritualization Pattern 4).

</details>

---

## Part 2 — Root cause classification and decay (docs/learning-stability.md)

### Scenario 2.1

A failure was observed and classified as `cause_identified`: a specific
environment variable was misconfigured, causing the hook to fire incorrectly.
The variable was fixed. Four observation windows have passed with no recurrence.
No new corroborating evidence has appeared for this classification.

**Question:** What is the current state of this classification?

<details>
<summary>Verdict</summary>

**The classification has decayed to `cause_suspected`.**

`cause_identified` degrades when the identified cause is not supported by
new corroborating evidence after two observation windows. Four windows have
passed — the classification decayed after window two. This does not mean
the classification was wrong. It means it can no longer block changes with
the authority of `cause_identified`.

If the no_change_justified outcome relied on this classification, it now
requires re-examination. `cause_suspected` supports `investigation_pending`,
not `no_change_justified`.

**Critical check:** Is the lack of recurrence itself corroborating evidence?
No. Absence of recurrence is consistent with both "the fix worked" and "the
failure was unrelated to the fix." Corroborating evidence requires structural
evidence of the same mechanism: a log entry, a traced artifact, a verified
configuration state. Absence of failure is not structural evidence.

**Source:** learning-stability.md — Classification confidence decay.

</details>

---

### Scenario 2.2

A reviewer argues that a failure should be classified `cause_identified`
because: "The pattern is consistent with reviewer attention bias during
high-load periods. This kind of thing always happens when the team is
under pressure."

**Question:** What classification state does this support?

<details>
<summary>Verdict</summary>

**`cause_suspected` at best.**

The reasoning is plausible but semantic. It names a mechanism ("attention
bias during high-load periods") but provides no structural evidence: no
log entries showing correlation between load and failure rate, no traced
reviewer behavior, no verified timeline. "Always happens" is a claim about
pattern, not a structural trace.

`cause_identified` requires structural evidence — log entries, verdict
artifacts, traced reviewer behavior. A cause supported only by plausible
reasoning is `cause_suspected`.

The practical consequence: this cause cannot support `no_change_justified`
for an execution/environment failure. The outcome must be
`investigation_pending` until structural evidence is obtained.

**Source:** learning-stability.md — "Evidence quality distinction."

</details>

---

### Scenario 2.3

A failure has been logged as `cause_unknown`. The team adds a note:
"Probably related to the migration last month, but we can't confirm."

**Question:** Should this update the classification?

<details>
<summary>Verdict</summary>

**No. The note describes a suspected mechanism — not a confirmed cause.**

"Probably related to the migration" with no supporting trace is
`cause_suspected`, not `cause_identified`. But `cause_unknown` requires
only that no reliable causal inference can be made yet. The note moves
the classification from "no hypothesis" to "unconfirmed hypothesis."

The appropriate documentation: update the entry to `cause_suspected` with
the migration as the suspected mechanism, and specify what structural
evidence would confirm or disconfirm it (e.g., failure timestamps vs
migration completion timestamp, affected repos vs migrated repos).

Leaving it as `cause_unknown` with a parenthetical "probably" is the
worst outcome: it appears complete while being neither.

**Source:** learning-stability.md — Three classification states.

</details>

---

## Part 3 — Over-correction signals and advisory containment

### Scenario 3.1

Over the last three observation windows, the following was observed:
- Window 1: 2 proposals accepted, 1 rejected
- Window 2: 1 proposal accepted, 3 rejected
- Window 3: 0 proposals accepted, 4 rejected

The high-severity failure rate has remained flat across all three windows.

**Question:** What signal is firing, what tier is it, and what is the
required action?

<details>
<summary>Verdict</summary>

**Signal 5 (advisory): rejection rate rising without high-severity failure
declining.**

Tier: **diagnostic** (advisory). Advisory signals inform review — they do
not directly trigger required actions.

The required response is: flag for gate calibration review. This is the only
permitted action based on Signal 5 alone. The following are NOT permitted
based on this signal alone:
- Raising the evidence bar for proposals
- Slowing or pausing proposal evaluation
- Opening a skepticism zone

An advisory signal may only influence a decision when combined with at least
one executable signal in the same window, or when the same advisory signal
has persisted across three consecutive windows (which converts it to an
executable requiring stability review).

In this case: Signal 5 has fired in windows 2 and 3 (rising rejection,
flat failure rate). If it fires again in window 4, it converts to executable
and a stability review is required before the next proposal is accepted.

**Source:** learning-stability.md — Signal 5 (advisory) + Advisory containment
rule + governance-mechanism-tiers.md (Signal 5: diagnostic tier).

</details>

---

### Scenario 3.2

A reviewer cites Signal 1 (change rate increasing without log entry rate
increasing) as justification for rejecting a new expansion proposal. The
justification reads: "Given the recent change rate, we should be more cautious
about accepting new proposals until the situation stabilizes."

**Question:** Is this a valid use of Signal 1?

<details>
<summary>Verdict</summary>

**No. This violates the advisory containment rule.**

Signal 1 is advisory. Advisory signals cannot directly trigger decision
changes. Specifically prohibited: raising the evidence bar for proposals,
slowing or pausing proposal evaluation, treating a category with increased
skepticism.

"We should be more cautious" is precisely raising the evidence bar — a
prohibited behavior based on advisory signals alone.

The correct use of Signal 1: prompt a direction check on the last three
accepted changes before the next one is evaluated. Signal 1 does not block
the proposal; it requires a direction check to be performed and documented
before evaluation proceeds.

Additionally, this advisory influence was used without being combined with
an executable signal, and without the three-consecutive-window conversion
condition being met. The use must be logged as an advisory containment
violation for the advisory/executable boundary review.

**Source:** learning-stability.md — Advisory containment rule, Signal 1
(advisory).

</details>

---

### Scenario 3.3

The same `doc_updated` response has been applied to the same misinterpretation
type twice. The failure has now recurred a third time.

**Question:** What is the required action before any further response is
applied?

<details>
<summary>Verdict</summary>

**Escalate to `model_adjusted` review. The next response cannot be
`doc_updated` without an explicit argument for why a third documentation
change would succeed where the previous two failed.**

Signal 2 is executable. It fires when the same failure recurs after two
responses at the same level (matched at same-class or stricter per the
taxonomy). When Signal 2 fires:

1. The next response is blocked from being `doc_updated` unless an explicit
   argument is made for why this attempt would differ from the prior two.
2. A `model_adjusted` review must be performed — not just considered.

This is not a judgment call. Signal 2 is enforceable. Applying a third
`doc_updated` without the explicit argument is a governance failure.

**Source:** learning-stability.md — Signal 2 (executable) +
governance-mechanism-tiers.md (Signal 2: enforceable).

</details>

---

## Part 4 — Falsifiability (docs/falsifiability-layer.md)

### Scenario 4.1

A proposal was accepted with the following falsification condition:
"If the problem continues to exist, we would know the dimension was
insufficient."

**Question:** Is this a valid falsification condition?

<details>
<summary>Verdict</summary>

**No. This is explicitly listed as an unacceptable (weak) falsification
condition in the framework.**

"Problem continues to exist" is undefined without a baseline and is
unfalsifiable because no specific observable outcome is named. A valid
condition requires:

- **Specific:** not "the problem continues" but "log entries of type X at
  rate Y"
- **Observable:** checkable by reviewing logs, artifacts, or behavior
- **Time-bounded:** when would we expect to see the failure signal?
- **Decision-reversing:** observing it must trigger re-evaluation

This proposal should not have been accepted with this condition. If it was
accepted, the falsifiability layer was not applied. This is an enforceable
gate failure.

**Source:** falsifiability-layer.md — Falsification condition examples
(weak, not acceptable).

</details>

---

### Scenario 4.2

A falsification condition fired: the misinterpretation it was meant to
prevent has recurred. The team reviews the original proposal and concludes:
"This was probably an edge case. The dimension is still correct for normal
usage."

**Question:** Is this a valid response? What must be documented?

<details>
<summary>Verdict</summary>

**Potentially valid — but only if the explanation is itself falsifiable.**

"Probably an edge case" is the first instinct when a falsification condition
fires. The framework permits keeping the decision — but requires:

1. Document the response with one of: `doc_updated`, `model_adjusted`,
   `threshold_changed`, or `no_change_with_justification`.
2. The explanation ("edge case") must be falsifiable: what would we expect
   to observe if this explanation is wrong? If "edge case" cannot be
   falsified — if there is no observable outcome that would show the failure
   was not an edge case — the explanation is a narrative covering a failure,
   not an analysis.
3. Trajectory awareness: this falsification event is now part of the
   falsification history for this category. Future proposals in the same
   category should treat this as evidence about where the model's reasoning
   tends to be weakest.

**Source:** falsifiability-layer.md — "Guard against explanation drift" +
"Falsification ≠ reversal condition."

</details>

---

## Part 5 — Decision quality invariants (docs/decision-quality-invariants.md)

### Scenario 5.1

An expansion proposal was reviewed by two different reviewers. Reviewer A
accepted it. Reviewer B, reviewing a materially identical proposal in a
different repo at the same time, rejected it. Both reviewers cited the
proposal gate criteria in their justifications.

**Question:** What invariant is at risk, and what is the required response?

<details>
<summary>Verdict</summary>

**The consistency invariant is at risk.**

Same evidence → same decision is the consistency requirement. Two reviewers
reaching different outcomes on materially identical inputs means at least one
decision is wrong, or the decision process is not actually governed by the
stated criteria.

The required response (per governance-mechanism-tiers.md): the consistency
invariant is currently **deferred**. This means there is no enforceable
mechanism to resolve the divergence automatically. The required response
is diagnostic: the divergence must be examined to determine whether
- the inputs were actually materially different (not a consistency violation)
- one reviewer applied the criteria incorrectly (reviewer correction)
- the criteria are ambiguous enough to support both outcomes (documentation
  update needed)

The divergence itself is the diagnostic signal. It must be logged and
examined, not averaged away.

**Source:** decision-quality-invariants.md — Consistency invariant.
governance-mechanism-tiers.md — Consistency: deferred.

</details>

---

### Scenario 5.2

The team reports: "We've gone three observation windows with no new failures.
The model is working. No changes needed."

**Question:** Does this constitute evidence that the decisions are correct?

<details>
<summary>Verdict</summary>

**No. It constitutes evidence that the decisions are uncontradicted.**

Absence of failure distinguishes three things indistinguishably: the decisions
were correct, they have not yet been tested, or the testing conditions did not
include the cases where they would fail.

Positive evidence of correctness requires at least one of:
- A decision has been replicated by a different reviewer on materially similar
  evidence (consistency evidence)
- A decision has been checked against variations that should not matter and
  did not change (robustness evidence)
- A decision's positive falsifiability condition has been observed (validation
  evidence)

If none apply, the decisions are uncontradicted — which is good — but they
have not been validated. Three clean windows of uncontradicted decisions does
not compound into validated governance. It compounds into a larger mass of
assumptions that have not yet been tested.

This is also the "It's working" silent degradation signal (E): if the most
common response to governance adequacy questions is "it seems to be working"
without specific evidence, the model has shifted from evidence-based to
inertia-based.

**Source:** decision-quality-invariants.md — "Relationship to the learning loop."
learning-stability.md — Silent degradation signal E.

</details>

---

## Part 6 — Governance mechanism tiers (docs/governance-mechanism-tiers.md)

### Scenario 6.1

A reviewer reads the silent degradation signals section of learning-stability.md
and decides to treat Signal D ("no one can articulate the model's known
weaknesses") as a gate for accepting new proposals: "We shouldn't accept any
new proposals until someone can name two or three current weaknesses."

**Question:** Is this a valid application of Signal D?

<details>
<summary>Verdict</summary>

**No. Signal D is diagnostic. It cannot be used as a gate.**

Per governance-mechanism-tiers.md, silent degradation signals A–E are in the
**diagnostic** tier. Diagnostic mechanisms produce required questions — not
required actions. Using Signal D as an acceptance gate treats a diagnostic
mechanism as enforceable, which is the over-reading failure mode the tier
map exists to prevent.

The correct application of Signal D: at the periodic silent degradation review
(once per three observation windows), ask whether anyone can articulate the
model's current weaknesses. If the answer is no, that is a diagnostic signal
requiring engagement — not a block on proposals.

Using Signal D as a gate also violates the advisory containment rule: advisory
signals cannot directly trigger "slowing or pausing proposal evaluation."

**Source:** governance-mechanism-tiers.md — Silent degradation signals A–E:
diagnostic. learning-stability.md — Advisory containment rule.

</details>

---

### Scenario 6.2

A reviewer is applying the calibration decay mechanism and needs to determine
whether an observation window "counts" toward classification confidence decay.
They conclude: "This window had 2 relevant observations, so I'll count it as
half a window."

**Question:** What is the problem with this approach, and what should the
reviewer do instead?

<details>
<summary>Verdict</summary>

**"Half a window" is an improvised calibration that has not been governed.**

The observation-density decay threshold (N relevant observations per window
to count toward decay) is a calibrated value per category. Per
governance-mechanism-tiers.md, the "per-category N" parameter is in the
**calibration governance gap** — it is currently set by reviewer judgment
without formal governance.

The reviewer is not wrong to consider observation density. But "count it as
half a window" is an invented interpolation that is not specified in the
framework. The correct approach under current (ungoverned) calibration:

1. Document the value being used explicitly in the window-close record:
   "Using N=3 for this category; this window had 2 relevant observations
   and does not count toward decay."
2. Make the N explicit — not implicit — so that drift from the value is
   visible in future records.

"Half a window" is an undocumented calibration judgment. Explicit
documentation of calibration values at window close is the minimum
governance required until formal calibration governance exists.

**Source:** governance-mechanism-tiers.md — Calibration governance:
"Per-category N: not formalized; explicit documentation at window close
required until formal governance exists."

</details>

---

## Part 7 — Anti-ritualization (docs/anti-ritualization-patterns.md)

### Scenario 7.1

An expansion proposal was submitted. The counterfactual scaffold was filled as:

```
Observation:
The misinterpretation has appeared three times.

Alternative mechanism:
Could be temporary reviewer behavior.

Why this mechanism fails:
Because it happened multiple times.

Which part of this reasoning are you least confident about?
The completeness of alternative mechanisms considered.
```

**Question:** Has the counterfactual scaffold been completed?

<details>
<summary>Verdict</summary>

**No. This is Pattern 1 (scaffold filling without reasoning) in its
canonical form.**

Three specific problems:

1. "Could be temporary reviewer behavior" names no mechanism. What specific
   behavior? Under what conditions? How would it produce this pattern?
   A mechanism must be nameable and refutable.

2. "Because it happened multiple times" is not a refutation of the
   proposed mechanism — it is a restatement of the observation. A refutation
   must explain why the mechanism cannot produce the observed pattern.

3. "The completeness of alternative mechanisms considered" is the explicit
   example of a safe non-answer in the framework. The uncertainty must be
   decision-relevant: resolving it differently would change whether the
   proposal should be accepted. "Completeness of alternatives" does not
   specify anything that could change the decision.

This proposal should be returned. It has not passed the counterfactual check.

**Source:** anti-ritualization-patterns.md — Pattern 1.
misinterpretation-log.md — Counterfactual scaffold requirements.

</details>

---

## Score interpretation

Count the number of scenarios where your answer matched the verdict before
reading the verdict. Total scenarios: **16** (Parts 1–7).

| Score | Interpretation |
|-------|---------------|
| 15–16 | Mechanisms are working as intended in this repo |
| 12–14 | Minor calibration gaps; review the missed scenarios with your team |
| 8–11  | Structural gaps in how the mechanisms are being applied; re-read source docs for missed areas |
| <8    | Framework adoption is incomplete; run the onboarding checklist before using these mechanisms |

Disagreements with verdicts are more informative than wrong answers. If your
reasoning differs from the verdict and you believe the verdict is wrong,
record it. The misinterpretation log exists precisely for this.
