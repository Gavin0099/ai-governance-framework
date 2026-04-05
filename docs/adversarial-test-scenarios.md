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

**The honest answer, with a hidden assumption made explicit:**

The detection latency table above assumes observability — it shows detection
time *given that the failure produces an observable signal*. This is not
detection latency overall.

A failure that never produces recurrence, never produces a degradation
pattern, and never enters the observation structure is not "slow to detect."
It is structurally invisible: it does not exist within the observation model,
which means every mechanism in the framework will report clean results while
the failure continues.

Examples of structurally invisible failures:
- Decision is consistently over-conservative → no recurrence, no failure signal
- Exploration is suppressed → absence of signal is the failure
- Subtle bias toward familiar evidence types → observable only in aggregate over long periods

The corrected table:

| Mechanism | Detects | Earliest detection | Assumes observability? |
|-----------|---------|-------------------|----------------------|
| Signal 2 | Same failure recurs twice | Window 2 | Yes — failure must recur |
| Falsification condition fires | Decision was wrong | Window varies | Yes — falsification condition must be observable |
| Classification decay | Root cause classification stale | Window 2–3 | Yes — failure must recur to trigger decay |
| Signal 3 | Skepticism zone overdue | Window 4 | Yes — zone must have been opened |
| Silent degradation signals A–E | Quality metrics declining | Window 3 | Yes — degradation must produce observable pattern |
| Decision quality invariants | Consistency/robustness violation | Deferred | Yes — requires matched inputs to compare |
| Misaligned success | System optimizing wrong target | **Never** | No — this failure produces no observable signal |
| Governance overfitting | Framework correct internally, externally wrong | **Never** | No — internal consistency does not require external validity |

For misaligned success and governance overfitting, the framework has no
detection mechanism — and adding more mechanisms does not help, because
these failure modes are expressed in the absence of the signals the
framework monitors, not in their presence.

**The accurate framing:**

> Failures that remain silent within this model are not just undetected —
> they are structurally invisible to the system. The framework can only
> detect failures that manifest within its observation model.

This is not a defect of the mechanism. It is a risk of the system. The
correct response is not to add more mechanisms but to define what the system
does when it knows it is operating at its observation boundary.

See docs/boundary-crossing-protocol.md.

This boundary must be acknowledged by any adopter choosing to rely on this
framework for high-stakes decisions.

---

## Part D — Refusal correctness

The hardest governance correctness is not giving the right answer. It is
recognizing when giving any answer is itself incorrect.

The scenarios in Parts A–C test whether reviewers apply mechanisms correctly.
Part D tests whether reviewers stop when they should — when the mechanism
cannot produce a valid answer and proceeding would be more harmful than
deferring.

"Boundary articulation" (being able to describe where the system stops) is
not the same as "boundary-respecting behavior" (actually stopping when the
boundary is reached). A reviewer who can describe the limits of `cause_identified`
but still assigns it under pressure has passed the knowledge test and failed
the behavioral test.

---

### Scenario D.1: The pressure to conclude

A team is closing an observation window. They need to document the root cause
classification for an open failure. The lead reviewer says: "We've been looking
at this for two windows. We need to write something. What's our best guess?"

The available evidence: three log entries, all from a single reviewer, no
structural trace of a mechanism, no artifact linking cause to effect.

**Question:** What is the correct response to "we need to write something"?

<details>
<summary>Verdict</summary>

**The correct response is `cause_unknown`, documented with the reason why
the evidence is insufficient to advance beyond `cause_unknown`.**

"We need to write something" is pressure to produce a conclusion where no
conclusion is warranted. The available evidence supports `cause_unknown`:
single-source entries (not independent), no structural trace, no causal
chain. Writing `cause_suspected` with a named mechanism would be semantically
stronger than the evidence supports — it would manufacture a hypothesis from
a pressure to conclude.

The required output: a `cause_unknown` entry, with explicit documentation
of what evidence would be needed to advance to `cause_suspected`, and a
deadline by which that evidence will either be obtained or the failure
will be treated as structurally uninvestigable within the current model.

The failure mode: writing `cause_suspected` to satisfy the pressure. This
produces a `cause_suspected` entry that is indistinguishable from a genuine
`cause_suspected` entry in the log, but is actually a `cause_unknown`
labeled more confidently than the evidence supports. Future reviewers will
treat it as genuine `cause_suspected` and the error propagates.

**Why this is the hardest scenario:** "We need to write something" is
legitimate organizational pressure. The refusal to write something stronger
than `cause_unknown` requires explicitly naming that the pressure to conclude
is not a source of evidence. That is an uncomfortable thing to say, which
is why it rarely happens.

</details>

---

### Scenario D.2: The undecidable proposal

A reviewer is evaluating an expansion proposal. The proposal passes all five
gate questions. The counterfactual scaffold is genuinely completed. The
falsification condition is specific and observable.

But the reviewer realizes: the proposal is adding a dimension to address a
failure mode that the current observation model cannot distinguish from a
different failure mode. Both failure modes would produce the same log entries.
The proposed dimension would address one but not the other. There is no way
to determine which failure mode is actually occurring from within the
current observation structure.

**Question:** What should the reviewer do?

<details>
<summary>Verdict</summary>

**The reviewer should not accept or reject the proposal — they should name
the undecidability and defer with a specific resolution condition.**

This is a boundary condition B1 (evidence below observability threshold):
the evidence required to determine which failure mode is occurring is
structurally unavailable within the current observation model. The proposal
passes the gate, but the gate was not designed to handle proposals where
the motivating evidence is ambiguous between two failure modes.

Accepting: would add a dimension that may address the wrong failure mode,
with no way to detect the error until the wrong mode produces effects the
new dimension cannot prevent.

Rejecting: would block a potentially valid proposal based on an
observation model limitation rather than a problem with the proposal.

The correct response: `defer_with_condition`. Document the undecidability
explicitly: "the evidence base for this proposal is consistent with two
distinct failure modes; the proposed dimension addresses only one; the
observation model cannot currently distinguish them." Specify the resolution
condition: what additional evidence or observation structure change would
allow the decision to be made.

This is a governance finding about the observation model, not a finding
about the proposal. The proposal may be valid; the model cannot currently
confirm it.

**The failure modes:**
- Accepting under pressure to resolve: looks like decisiveness; is actually
  making a 50/50 guess while documenting it as a reviewed decision
- Rejecting on grounds the proposal is ambiguous: misdirects the problem
  from the observation model to the proposer
- Deferring indefinitely: `defer_with_condition` requires a resolution
  trigger; "defer until we know more" is not a valid deferral

</details>

---

### Scenario D.3: When not deciding is the wrong answer

A reviewer recognizes that a decision is outside the observation model
boundary. They defer, citing Scenario D.2's logic: "The evidence doesn't
support a decision. I'm marking this as undecidable."

But this decision has a deadline: if no action is taken within this window,
a deployment will proceed with an unreviewed change.

**Question:** Does observation model boundary justify deferral when deferral
itself has consequences?

<details>
<summary>Verdict</summary>

**No. Deferral is not consequence-free. It must be evaluated against the
consequences of the alternatives.**

The boundary crossing protocol produces four responses: `defer_with_condition`,
`low_confidence_proceed`, `escalate`, and `hard_stop`. `defer_with_condition`
is the default but is not always correct.

When deferral has a specific known consequence (deployment proceeds with
unreviewed change), the correct analysis is:

1. What are the expected costs of `defer_with_condition` (deployment proceeds
   unreviewed)?
2. What are the expected costs of `low_confidence_proceed` (decision made
   under uncertainty, tagged explicitly as such)?
3. Is `escalate` available and would it resolve the decision in time?

Deferring while a harmful action proceeds uncontested is not epistemically
cautious — it is a decision by omission. The framework does not endorse
non-decisions as inherently more valid than decisions. "I cannot determine
the answer" does not mean "therefore nothing should happen."

The correct response in time-constrained boundary conditions: use
`low_confidence_proceed` with an explicit uncertainty tag, document the
boundary condition that applies, and flag the decision for re-evaluation
as soon as resolution conditions can be met. A decision that acknowledges
its own limitations is more honest than a deferral that ignores its own
consequences.

**The failure modes:**
- "I can't decide" used as a general-purpose escape from difficult decisions
  (avoidance masquerading as epistemic caution)
- Treating all boundary conditions as equally blocking (ignoring the cost
  structure of each response type)
- Failing to distinguish "I cannot confirm this is correct" from "therefore
  I should not act"

</details>

### Scenario D.4: The confident wrong classification

A reviewer classifies a failure as `cause_identified`. The structural evidence
appears solid: two log entries, a traced reviewer behavior, a timing correlation
between the identified cause and the failure event.

The classification stands for three observation windows. No recurrence. No
decay triggered (the two-window threshold has not yet elapsed).

In window four, the same failure recurs — but the previously identified cause
was addressed in window one. The identified cause is definitively not present.

**Question:** What is the correct sequence of responses, and what does this
reveal about the prior `cause_identified` classification?

<details>
<summary>Verdict</summary>

**The recurrence directly contradicts the `cause_identified` classification.
The classification degrades immediately to `cause_unknown`.**

Per classification confidence decay: "a recurrence of the same failure after
the identified cause was addressed directly contradicts the classification
(decay to `cause_unknown`)." This is not a gradual decay — it is an
immediate reclassification.

The correct sequence:

1. Log the recurrence as a new entry with resolution status `open`
2. Update the prior `cause_identified` classification to `cause_unknown`:
   the identified cause cannot be the root cause since it was absent when
   the failure recurred
3. Re-examine what the structural evidence actually showed: if the prior
   evidence was real (log entries, traced behavior, timing), it may have
   shown a *correlated* factor rather than the *causal* factor
4. The prior `no_change_justified` outcome that relied on this classification
   must be re-opened: it was based on a classification that is now invalid
5. This is now a new failure requiring fresh root cause classification —
   starting at `cause_unknown` with the prior evidence treated as evidence
   about correlates, not causes

**What this reveals about the prior classification:**

The prior structural evidence was likely valid — the log entries, behavior
trace, and timing correlation were real. But structural evidence can show
correlation without causation. The prior `cause_identified` classification
committed the error of treating correlated evidence as causal evidence.

This is exactly the gap described in Scenario A.2: structural evidence
with a hidden gap. The evidence was present; the causal chain was assumed
rather than traced. The confidence felt justified by the evidence quality.
The recurrence reveals it was not.

**The critical failure mode this scenario tests:**

A `cause_identified` that is wrong will not look wrong until something
contradicts it. During the period when it is wrong but uncontradicted, it
will:
- Block model changes with the authority of `cause_identified`
- Support `no_change_justified` for future similar failures
- Propagate as precedent if future reviewers cite it

This is "the system incorrectly believes it can judge" in its most concrete
form. The correction mechanism is external to the reviewer's confidence:
it requires recurrence to fire. Until recurrence fires, the framework has
no mechanism to distinguish a correct `cause_identified` from a wrong one.

This is why adversarial external validation (external audits, forced
exploration) matters for high-confidence classifications specifically — not
just for low-confidence ones.

**Source:** learning-stability.md — Classification confidence decay (recurrence
path). boundary-crossing-protocol.md — Invisible zone response.

</details>

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
