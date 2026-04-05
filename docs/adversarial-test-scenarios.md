# Adversarial Test Scenarios

> Version: 1.0
> Related: docs/learning-governance-test-pack.md, docs/decision-quality-invariants.md,
>           docs/governance-mechanism-tiers.md

---

## Purpose

The conformance test pack (learning-governance-test-pack.md) tests whether
mechanisms can be correctly applied under clear conditions. It does not test
whether the mechanisms hold up when conditions are adversarial.

This document tests three failure conditions the conformance pack cannot reach:

1. **Misleading evidence** — evidence that appears to support a conclusion
   it does not actually support
2. **Partial observability** — the system has incomplete information and
   must decide whether to acknowledge that or proceed
3. **Conflicting signals** — two mechanisms produce incompatible guidance
   simultaneously

A system that passes the conformance pack but fails here has achieved
internal consistency without external robustness. These scenarios are designed
to find that gap.

---

## How this differs from the conformance pack

The conformance pack has correct answers that can be derived by reading the
framework documents carefully. These scenarios are designed so that:

- The surface reading suggests one answer
- The correct answer requires recognizing what the surface is hiding
- Several scenarios have no single correct answer — only a correct *process*

Where no single answer exists, the verdict describes the required process
and the failure modes to avoid.

---

## Part A — Misleading evidence

### Scenario A.1: Corroboration that is not corroboration

Three log entries exist for the same failure type across three observation
windows. The reviewing team concludes: "This is three independent
corroborations of the same root cause. `cause_identified` is justified."

The three entries are:
- Entry 1: reviewer in Repo A misread activation_state as a quality signal
- Entry 2: reviewer in Repo B misread activation_state as a quality signal
- Entry 3: reviewer in Repo C misread activation_state as a quality signal

**Question:** Is `cause_identified` justified? If not, what is missing?

<details>
<summary>Verdict</summary>

**`cause_identified` is not yet justified by these three entries alone.**

Three entries showing the same surface behavior (activation_state misread as
quality signal) are evidence of a pattern — but the root cause is still
unclassified. Three recurrences confirm the pattern exists; they do not
identify its mechanism.

Possible root causes:
- Documentation is insufficient (model failure → `doc_updated` candidate)
- Onboarding does not cover this distinction (team failure)
- The field name itself invites the misreading regardless of documentation

The three entries are corroboration of the *pattern*, not corroboration of
a specific *cause*. `cause_identified` requires structural evidence of the
mechanism: what specifically causes reviewers to make this error? Counting
recurrences is not the same as identifying cause.

The correct state: `cause_suspected` if a mechanism has been proposed with
partial evidence; `cause_unknown` if no specific mechanism has been identified
despite the pattern. The recurrence count moves the entry toward `requires_model_change` in the expansion trigger logic — it does not move `cause_unknown` to `cause_identified`.

**The misleading element:** Three entries feel like strong evidence. They are
strong evidence of frequency, not of mechanism. The framework distinguishes
these; informal review often conflates them.

</details>

---

### Scenario A.2: Structural evidence with a hidden gap

A reviewer classifies a failure as `cause_identified` and cites as structural
evidence: a log entry timestamped 14 minutes after the failure, showing the
misconfigured field in a verdict artifact.

**Question:** Is this valid structural evidence for `cause_identified`?

<details>
<summary>Verdict</summary>

**Potentially valid, but the gap must be explicitly addressed.**

The framework requires structural evidence for `cause_identified`: log
entries, verdict artifacts, traced reviewer behavior. A verdict artifact
14 minutes post-failure qualifies as structural evidence of the state at
that point. It does not, by itself, establish causation.

What is missing:
1. **Causal chain:** does the log entry show the misconfigured field *causing*
   the failure, or merely *present* during the failure? A field that appears
   in a log is correlated with the failure; it is not confirmed as causal
   unless the chain from field state to failure is traced.
2. **Timing gap:** 14 minutes is enough time for the state to have changed
   after the failure. Was the log entry capturing pre-failure state or
   post-failure state?

This does not disqualify the evidence. It means the classification requires
an explicit acknowledgment of these gaps. A `cause_identified` that does not
address the causal chain is a classification supported by correlation, not
causation — which is `cause_suspected` by the evidence quality standard.

**The misleading element:** "We have a log entry" sounds like structural
evidence. Whether that log entry establishes causation rather than correlation
requires a further step that reviewers often skip.

</details>

---

### Scenario A.3: A successful fix that proves nothing

A failure was classified `cause_identified`. The identified cause was addressed
directly. The failure has not recurred in three observation windows.

The team says: "The fix worked. Classification confirmed."

**Question:** Does non-recurrence after a targeted fix confirm `cause_identified`?

<details>
<summary>Verdict</summary>

**No. Non-recurrence after a fix is consistent with three distinct situations,
only one of which confirms the classification.**

Situation 1: The fix addressed the actual cause. Classification confirmed.
Situation 2: The fix addressed a proximate cause; the underlying mechanism
  remains. The failure will recur in a different form.
Situation 3: The failure was transient and would not have recurred regardless
  of the fix.

Non-recurrence cannot distinguish these three. It is consistent with all of
them.

The framework is explicit: absence of recurrence is not corroborating
structural evidence for `cause_identified`. Corroborating evidence requires
a trace of the same mechanism in a new context — not just the absence of
the old failure.

Per classification confidence decay: a `cause_identified` classification
that has no new corroborating evidence after two observation windows degrades
to `cause_suspected`. Three windows of non-recurrence with no additional
structural evidence means the classification has already decayed.

**The misleading element:** "We fixed it and it stopped happening" is the
strongest possible informal argument that the fix was right. It does not
satisfy the structural evidence standard, and the framework requires
acknowledging this explicitly rather than treating it as confirmation.

</details>

---

## Part B — Partial observability

### Scenario B.1: The quiet window

An observation window closes. The team has had two reviewer interactions — both
brief, neither producing log entries. They write: "No issues observed."

A junior reviewer asks: "Should we flag that we only had two interactions?"
The lead reviewer says: "We observed, nothing came up. The rule only requires
three interactions if we're trying to claim negative pressure. We're not
claiming anything."

**Question:** Is the lead reviewer correct?

<details>
<summary>Verdict</summary>

**Partially correct — but the response is still incomplete.**

The lead reviewer is right that the negative pressure validity rule applies
specifically to claims of negative pressure ("the model is sufficient because
no issues appeared"). If the team is not making that claim, the three-interaction
threshold is not strictly triggered.

But the window close is still incomplete in two ways:

1. **Untested assumptions must be named** regardless of whether negative
   pressure is being claimed. The window close checklist requires naming
   which assumptions were not tested during the window. Two brief interactions
   almost certainly left major assumptions untested. These must be named, not
   silently passed over.

2. **The conclusion "no issues observed" with two interactions is not neutral.**
   It is a statement with an implicit claim: that the window produced no signal.
   With two brief interactions, what the window produced is *insufficient
   observation* — which is different from *no issues*. Writing "no issues
   observed" when the correct statement is "insufficient observation to detect
   issues" is a completeness failure.

The frame "we're not claiming negative pressure" is technically accurate and
also a way of avoiding the responsibility to acknowledge what the window
actually couldn't observe.

**The misleading element:** "We're not claiming anything" sounds epistemically
modest. It is actually a way to make incomplete observation invisible.

</details>

---

### Scenario B.2: Evidence that covers its own gaps

A reviewer evaluates an expansion proposal. The supporting log has four entries,
all from the same observation window, all logged by the same reviewer. The
reviewer assesses: "Four entries. Pattern is clear."

**Question:** What is the problem with this evidence base?

<details>
<summary>Verdict</summary>

**Single-source evidence has a coverage gap the count obscures.**

Four entries from the same reviewer in the same window are not four independent
observations. They are one observer's attention over one period. This matters for:

1. **Semantic grouping validity:** the four entries may reflect one underlying
   misconception framed four ways by the same reviewer — not four independent
   observations of the same pattern. The semantic grouping rule requires
   grouping by shared underlying misconception, not surface phrasing — but
   it also prohibits over-grouping entries that have different root causes.
   When all entries come from one reviewer, it is impossible to determine from
   the log alone whether the grouping is valid or whether it reflects one
   reviewer's interpretive framework being applied four times.

2. **Two-instance rule context:** the standard expansion trigger requires two
   instances from different contexts (different repos, reviewers, or sessions).
   Four entries from one reviewer in one window does not satisfy the "different
   contexts" requirement regardless of count.

3. **Observer attention bias:** the misinterpretation-log explicitly notes that
   spikes in one area should prompt "what are we not looking at?" — not just
   "what does this spike tell us?" A single reviewer generating four entries
   is exactly this pattern.

The correct response: acknowledge the coverage gap, treat this as one data
point from one context, and require a second instance from a different context
before treating this as a pattern.

**The misleading element:** "Four entries" sounds thorough. Source diversity
matters more than count for establishing independence.

</details>

---

### Scenario B.3: The invisible boundary

A reviewer applies Signal 3 (executable): a skepticism zone has been open for
more than three observation windows without a retirement evaluation, blocking
a new zone from being opened.

The team realizes: the skepticism zone was established under a different
definition of "observation window" than is currently used. Under the old
definition (30-day windows), the zone is 4 windows old. Under the current
definition (10-interaction windows), it may be only 2 windows old.

**Question:** How should the team proceed?

<details>
<summary>Verdict</summary>

**This is a calibration governance gap in the real world, not a scenario with
a clean verdict.**

The framework defines observation windows in misinterpretation-log.md
(ends after 10 reviewer interactions OR 30 days, whichever comes first).
If the skepticism zone predates this definition, or if the definition changed,
the window count is ambiguous.

The correct process:

1. **Do not resolve the ambiguity by choosing the interpretation that produces
   the preferred outcome** (opening the new zone vs. blocking it). This is
   exactly how calibration drift becomes self-serving.

2. **Document the ambiguity explicitly** in the current window-close record:
   what definition was used when the zone was established, what definition
   is current, and what the count is under each.

3. **Apply the current definition prospectively.** If the zone is 2 windows
   old under the current definition, it cannot be retired yet and the block
   stands. The question of how many windows the old definition represented
   does not retroactively change the enforcement.

4. **Treat the definition change as a calibration event** that should be
   documented in the calibration governance section. If window definitions
   can change without updating in-flight skepticism zone counts, the
   framework has a consistency gap.

**The misleading element:** "Under which definition?" sounds like a
clarifying question. It is often a framing that allows the preferred
outcome to be reached while appearing principled.

</details>

---

## Part C — Conflicting signals

### Scenario C.1: Executable and advisory pointing opposite directions

The team is evaluating a new expansion proposal in a category where:
- Signal 2 has fired (same failure recurred after two `doc_updated` responses) — this is **executable**, requiring escalation to `model_adjusted` review
- Signal 1 has fired (change rate increasing without log entry rate decreasing) — this is **advisory**, suggesting the system may be over-correcting

Signal 2 says: escalate to model change.
Signal 1 says: the system may be changing too much already.

**Question:** How should the team proceed?

<details>
<summary>Verdict</summary>

**Signal 2 (executable) takes precedence. Signal 1 (advisory) informs the
review but cannot block or modify the required escalation.**

Signal 2 is enforceable. It fires and requires a `model_adjusted` review —
not consideration, but review. This is not overridable by Signal 1 alone.

However, Signal 1 is still operative and must be engaged with:

1. The `model_adjusted` review proceeds as required.
2. Within that review, Signal 1 is a legitimate input: the reviewer should
   ask whether the proposed model change reduces uncertainty or merely moves
   it (direction check), and whether the proposed change would destabilize
   mechanisms that are otherwise working.
3. Signal 1 cannot be used to defer the review or lower the required response
   level. It can be used to raise the quality bar within the review.

The conflict is not actually between the signals — it is a framing error.
Signal 2 determines that a review must happen. Signal 1 provides context
for what that review should examine. They operate at different layers.

**Failure mode to avoid:** treating Signal 1 as a reason to downgrade Signal
2's required action. This is advisory containment violation under the guise
of "weighing multiple signals."

</details>

---

### Scenario C.2: The consistent wrong answer

Three reviewers independently review the same expansion proposal and reach
the same conclusion: reject. Their justifications differ in wording but
converge on the same reasoning: the proposal's counterfactual scaffold
names a plausible alternative mechanism but refutes it with reasoning rather
than structural evidence.

A fourth reviewer challenges the rejection: "Three people looked at this and
agreed. The consensus is strong."

**Question:** Is three-way agreement a valid basis for confidence in the
rejection?

<details>
<summary>Verdict</summary>

**Agreement is evidence of consistency, not evidence of correctness.**

Three reviewers independently reaching the same conclusion using the same
reasoning demonstrates that:
- The rejection criterion is being applied consistently
- The reasoning pattern is shared across reviewers

It does not demonstrate that:
- The criterion itself is correct
- The shared reasoning pattern is not a shared blind spot

The decision quality invariants are relevant here: consistency (same evidence
→ same decision) is satisfied. Robustness is not tested by same-reviewer
agreement. And positive falsifiability is still required: what would show
that the rejection was correct?

More concretely: if the criterion being applied (structural evidence required
to refute an alternative mechanism) is too strict for this type of proposal,
three reviewers applying it consistently will produce three consistent wrong
rejections. High agreement under a wrong criterion is a governance failure,
not a governance success.

The fourth reviewer's challenge ("consensus is strong") is the "It's working"
silent degradation signal in a different form: treating consistency as
validation.

**The correct response to the fourth reviewer:** "Three people reached the
same conclusion. That confirms the criterion is being applied consistently.
It does not confirm the criterion is correct. What would show the rejection
was wrong?"

</details>

---

### Scenario C.3: Governance failure detection time

This scenario has no verdict. It is a question the framework cannot currently
answer, and its purpose is to name that gap explicitly.

The team has been operating the governance framework correctly for six
observation windows. All mechanisms are being applied as specified. No
falsification events have fired. No over-correction signals are active. The
conformance test passes 16/16.

**Question:** If the governance framework is systematically wrong — if the
mechanisms are consistently producing incorrect decisions — how many
observation windows would pass before the framework's own mechanisms detected
the problem?

**Why this has no verdict:**

The framework's detection mechanisms operate at the following speeds:

| Mechanism | Detects | Earliest detection |
|-----------|---------|-------------------|
| Signal 2 (executable) | Same failure recurs twice | Window 2 |
| Falsification condition fires | Decision was wrong | Window varies (requires specified condition) |
| Classification confidence decay | Root cause classification stale | Window 2–3 |
| Signal 3 (executable) | Skepticism zone overdue | Window 4 |
| Silent degradation signals A–E | Quality metrics declining | Window 3 (periodic review) |
| Decision quality invariants | Consistency/robustness violation | Not currently instrumented (deferred) |
| Misaligned success | System optimizing wrong target | Not currently detectable |

**The honest answer:** For misaligned success and governance overfitting —
where the system is producing consistent, well-reasoned, internally coherent
wrong decisions — the framework has no detection mechanism.

The earliest possible detection assumes a failure produces an observable
signal that a falsification condition was specified for. If the failure mode
is one that doesn't produce observable signals within the specified conditions,
the framework will not detect it at all.

This is not a failure of the framework design — it is a property of all
closed-world governance systems. The correct response is not to add more
mechanisms (which would produce more governance overfitting) but to name the
boundary explicitly:

**The framework can detect failures that produce observable signals within
the defined observation structure. It cannot detect failures that are
expressed only in the quality of decisions whose correctness is not
independently verifiable.**

This boundary must be acknowledged by any adopter choosing to rely on this
framework for high-stakes decisions.

---

## Using this pack alongside the conformance pack

| | Conformance pack | Adversarial pack |
|---|---|---|
| Tests | Internal consistency, correct application | Robustness under misleading/incomplete/conflicting conditions |
| Correct answers | Derivable from docs | Some have no single correct answer |
| Passing means | Mechanisms applied correctly | System recognizes its own limits |
| Failure indicates | Application gaps | Over-confidence or boundary blindness |

Run the conformance pack first. A system that has not passed conformance
should not be evaluated against adversarial scenarios — the adversarial cases
require understanding the mechanisms well enough to recognize when they are
being misapplied under pressure.

Run the adversarial pack when the conformance pack passes consistently. The
purpose is not to find new failure modes to add rules for — it is to locate
the boundary where the current rules stop being sufficient.

**Score interpretation for this pack:**

There is no numerical score. The adversarial pack is evaluated by whether the
team can articulate, for each scenario, what the mechanism they applied is
actually testing — and where it stops. A team that answers every scenario
correctly but cannot name the boundary of each mechanism has not passed.
