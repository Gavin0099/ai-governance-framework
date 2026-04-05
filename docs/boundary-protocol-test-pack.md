# Boundary Protocol Test Pack

> Covers commits: f0a9935 → e6f73d3
> Scenario count: 18 (Parts A–F)
> Passing score: 16–18 (strong pass); 13–15 (marginal pass — review Part D and E); <13 (fail)
> Documents under test:
> - docs/boundary-crossing-protocol.md    (Parts A–F)
>
> Prerequisite: familiarity with docs/learning-governance-test-pack.md recommended.
> This pack tests mechanisms that build on the learning loop and adversarial
> test scenarios. Some scenarios reference learning-loop.md concepts without
> re-explaining them.
>
> Maintenance note: if scenarios are added or removed, update scenario count,
> score bands, and the manifest above. These three must stay in sync.
>
> **Schema integrity check** (verify before publishing an updated version):
> - [ ] Scenario count in manifest == actual scenario count in document
> - [ ] Score band max == scenario count
> - [ ] Every enforceable mechanism in boundary-crossing-protocol.md has ≥1 scenario
> - [ ] No verdict cites a mechanism that was removed from the protocol
>
> This pack is a **conformance test** for boundary protocol mechanisms.
> It does not test adversarial conditions. Adversarial testing of boundary
> recognition is in docs/adversarial-test-scenarios.md Part D.

---

## How to use this pack

Each scenario gives you an input situation and asks you to make a judgment call.
After each scenario, a **verdict** section shows the correct outcome and which
rule produces it. Read the scenario first, write your answer, then check.

Where a scenario has no single correct answer, the verdict describes the
required process and the disqualifying failure modes.

If your answer matches the verdict: the mechanism is working as intended.
If your answer differs: read the verdict reasoning before concluding you were
wrong — the verdict may be wrong. Record genuine disagreements.

---

## Part A — Boundary condition recognition and response types

### Scenario A.1

A reviewer is asked to evaluate a proposal to expand the framework's scope
to cover a new decision category. The proposal cites one prior incident as
evidence that the category needs governance. The reviewer cannot find any
other record of decisions being made in this category — no log entries, no
prior proposals, no observable activity.

The reviewer writes: "There's only one data point here. I can't tell if
this is a genuine pattern or a one-off. I'll approve it cautiously."

**Question:** Has the reviewer correctly identified the boundary condition?
If not, what is wrong, and what response type should they use?

<details>
<summary>Verdict</summary>

**The reviewer has not correctly identified the boundary condition.**

One data point with no corroborating log activity is a B1 condition: evidence
below the observability threshold. The reviewer identified that evidence is
thin, but responded with `low_confidence_proceed` without naming the condition
or attaching a re-evaluation trigger.

A correct `low_confidence_proceed` requires:
1. Naming the boundary condition (B1)
2. Specifying a re-evaluation trigger (e.g., "if two more decisions occur in
   this category and are logged, re-evaluate whether the pattern is genuine")
3. Making the tag visible to future reviewers who use this decision as precedent

"I'll approve it cautiously" does none of these. The low-confidence decision
will be used as precedent without any future reviewer knowing it was made
under B1 conditions.

**Correct action:** Name the B1 boundary condition explicitly. Proceed with
`low_confidence_proceed` only if the cost of deferral is non-trivial and is
documented. Attach an observable re-evaluation trigger, not a calendar date.

</details>

---

### Scenario A.2

A reviewer receives a proposal that asks the framework to classify a failure
mode the framework has never encountered. The proposal argues by analogy to
a similar failure mode that is already classified.

The reviewer writes: "This is analogous to X, which we've classified as
medium-severity. I'll classify this as medium-severity too."

The proposal is accepted and published.

**Question:** Has a boundary condition been triggered? If so, which one, and
what is missing from the reviewer's response?

<details>
<summary>Verdict</summary>

**Yes — B3 has been triggered (classification with no resolution path).**

The failure mode has never appeared in the observation model before. Classifying
it by analogy to a known case substitutes structural argument for observation.
This is a B3 boundary condition: a classification is being applied to something
the system has not observed, with no path to confirming the classification until
the failure mode actually occurs.

Analogy-based classification is not forbidden. But it requires:
1. Acknowledging the classification is analogical, not observationally derived
2. Specifying what observation would confirm or disconfirm the analogy
3. Tagging the classification as provisional until observation is available

The reviewer has done none of this. The medium-severity classification will
be used as established precedent despite being unvalidated.

**Correct action:** Accept the proposal as a provisional classification under
B3. Specify the falsification condition for the analogy. Tag the classification
as "derived by analogy from X; requires corroboration before treating as
established."

</details>

---

## Part B — Deferral genuineness

### Scenario B.1

A reviewer defers a proposal with the following note:

> "This proposal raises complex questions about how we handle cross-domain
> failures. I'm deferring pending further review by the framework team."

**Question:** Is this a genuine deferral? Check it against all four genuineness
conditions and identify which fail.

<details>
<summary>Verdict</summary>

**This fails conditions 2, 3, and 4. It is avoidance, not deferral.**

Condition 1 — Boundary condition named: **Fail.** "Complex questions about
cross-domain failures" does not name a specific boundary condition (B1–B5).
Which condition applies? Why is this decision outside the current observation
model?

Condition 2 — Resolution condition specific: **Fail.** "Further review by
the framework team" is not a resolution condition. What specific question
must the framework team answer? What output from that review would allow
the proposal to be re-evaluated?

Condition 3 — Deadline set: **Fail.** No deadline is specified. Open-ended
deferral is indistinguishable from rejection without reasoning.

Condition 4 — Deferral itself falsifiable: **Fail.** There is no condition
under which this deferral would be shown to be avoidance rather than genuine
deferral. A genuinely falsifiable deferral can be checked: either the
resolution condition was met and the proposal was re-evaluated, or it wasn't.

**Correct action:** If the proposal genuinely cannot be evaluated now, name
the specific boundary condition, specify what the framework team must produce,
set a deadline, and confirm that the deferral will be auditable at that
deadline.

</details>

---

### Scenario B.2

A reviewer defers a proposal with this note:

> "Deferring under B2 (outcome not verifiable with current instrumentation).
> Resolution condition: after the next framework instrumentation update, if
> outcome tracking for this decision type becomes available, re-evaluate.
> Deadline: end of observation window 5. If instrumentation is not available
> by then, we will issue a `low_confidence_proceed` rather than continuing
> to defer."

Three windows pass. Instrumentation is still not available. The reviewer
issues another deferral with the same note, except the deadline is now
"end of observation window 8."

**Question:** Is the second deferral valid?

<details>
<summary>Verdict</summary>

**No — this exceeds the maximum deferral age and violates the renewal condition.**

The first deferral was well-formed. But deferral has a maximum of two renewals,
and each renewal requires evidence of evidence gain — that progress toward
resolving the boundary condition has occurred. The second deferral:

1. Provides no evidence that instrumentation progress has been made
2. Simply extends the deadline by three windows
3. Does not satisfy the evidence-gain condition for renewal

Renewing a deferral on the same basis as the original deferral is not renewal
— it is extension. Extension is not permitted.

The reviewer's own first note specified the correct fallback: "if
instrumentation is not available by then, we will issue a `low_confidence_proceed`."
That commitment is now due. The correct response is to proceed with
`low_confidence_proceed` as stated, not to issue a second deferral.

**Correct action:** Issue `low_confidence_proceed` per the stated fallback.
Tag the decision with the B2 boundary condition and attach an observable
re-evaluation trigger for when instrumentation becomes available.

</details>

---

### Scenario B.3

A proposal is deferred for the third time. The reviewer writes:

> "Still unable to resolve the original observability gap. Issuing a third
> deferral — this is important enough that proceeding without resolution
> feels wrong."

**Question:** Is the third deferral permitted?

<details>
<summary>Verdict</summary>

**No — the third deferral is not permitted under any circumstances.**

The maximum deferral age is two renewals (three deferrals total would be
the second renewal). But more importantly: if the boundary condition has
been unresolvable across two renewal cycles, continuing to defer is
structurally equivalent to blocking the proposal indefinitely. That is
only permitted under specific conditions: `hard_stop` is reserved for
irreversible decisions under B1 or B2, not for all cases where resolution
feels premature.

The reviewer's reasoning ("this is important enough that proceeding without
resolution feels wrong") is the canonical avoidance pattern: using importance
as justification for blocking without meeting the hard_stop conditions.

**Correct action:** The reviewer must choose between:
- `low_confidence_proceed` with explicit boundary tag and re-evaluation trigger
- `escalate` if a specific external party can resolve the boundary condition
  within a defined timeline
- `hard_stop` only if the decision meets the irreversibility threshold under
  B1 or B2

Continued deferral is not available.

</details>

---

## Part C — Deviation accumulation and outcome downstream closure

### Scenario C.1

A boundary protocol deviation is observed: a reviewer issued a `defer_with_condition`
that failed condition 3 (no deadline). This is logged.

The next window, the same reviewer issues another `defer_with_condition` without
a deadline in the same category.

The reviewer responsible for periodic review notes it but does not escalate:
"Two instances, but they might be the same underlying confusion. I'll watch
for a third."

**Question:** Has the periodic reviewer applied the deviation accumulation rule
correctly?

<details>
<summary>Verdict</summary>

**No — the periodic reviewer has applied the wrong tier.**

The deviation accumulation rule:
- 1 window: Diagnostic — direction check on last three changes in affected category
- 2+ windows: Operationalized — constraint inventory required; new mandatory
  changes paused pending inventory
- 3 consecutive windows: Enforced — constraint accumulation paused until
  stability review completes

Two observations of the same class of deviation (missing deadline in
`defer_with_condition`) in the same category has crossed the Operationalized
threshold. The periodic reviewer is treating it as Diagnostic ("I'll watch
for a third"), which is incorrect.

The reasoning "they might be the same underlying confusion" is not relevant
to the tier determination. The same-failure taxonomy applies to escalation
decisions, not to whether the tier has been crossed.

**Correct action:** At two deviations in the same category, the operationalized
response is required: document the pattern, initiate a constraint inventory
for `defer_with_condition` in this category, and pause new mandatory changes
pending the inventory result.

</details>

---

### Scenario C.2

A `drift_confirmed` outcome is issued after a pattern-to-policy binding. The
mandatory policy change is recorded. Six weeks later, a periodic review
confirms the triggering pattern has not recurred.

The periodic reviewer writes: "Pattern resolved. Loop closed."

**Question:** Has the loop been closed? What is missing?

<details>
<summary>Verdict</summary>

**No — the loop has not been closed.**

Outcome downstream closure requires not just that the mandatory policy change
is recorded, but that its downstream effect has been implemented or explicitly
declined. The periodic reviewer has confirmed that the pattern resolved, but
has not confirmed that the policy change produced a specific behavioral or
structural change that explains the resolution.

The test is: would a reviewer encountering the same situation do something
different now that the policy change exists? If the answer is "yes, because
the policy changed X" — the loop may be closed. If the answer is "the pattern
just stopped recurring and we marked it resolved" — the downstream effect has
not been confirmed.

Additionally, the governance-complete condition requires that the closure
record answers: was the downstream effect implemented, or explicitly declined
with reasoning? Neither is present.

**Correct action:** Document specifically what the policy change altered. If
a behavioral or structural change was made, record it. If the pattern resolved
without an identifiable downstream change, that is a `calibration_error` signal
— the triggering classification may have been wrong — not a `drift_confirmed`
closure.

</details>

---

### Scenario C.3

Three consecutive `cost_legitimate` outcomes are produced for the same category.
No `structurally_inaccessible` markings have been generated.

The periodic reviewer writes: "The constraints here are genuinely external.
Three cost_legitimate outcomes is consistent with that."

**Question:** Is the reviewer's interpretation correct? What does the framework
require at this point?

<details>
<summary>Verdict</summary>

**The interpretation may be correct, but the framework requires more than
an assertion.**

Three `cost_legitimate` outcomes without `structurally_inaccessible` markings
triggers the strategic compliance guard. The guard exists because this pattern
is consistent with two very different situations:
- Genuine external constraints that make the deviation path structurally
  inaccessible
- Outcome selection bias: reviewers routing to the lower-cost outcome type
  without applying the falsifiability requirement

The periodic reviewer's response ("consistent with external constraints") is
the verbal form of the first interpretation, but it is not a governance
finding. It is an assertion.

What is required: examine whether `structurally_inaccessible` markings should
have accumulated. If the constraints are genuinely external and the paths are
genuinely inaccessible, those markings should exist. Their absence is a signal
that either (a) the outcome is being used as a terminal classification rather
than triggering the `structurally_inaccessible` step, or (b) the falsifiability
requirement for `cost_legitimate` is not being applied.

**Correct action:** The periodic reviewer must produce one of: (a) documented
`structurally_inaccessible` markings for the confirmed-inaccessible paths, or
(b) a governance finding that `cost_legitimate` is being used as a terminal
classification, triggering re-examination of the outcome classification
mechanism in this category.

</details>

---

## Part D — Baseline validity and domain entropy

### Scenario D.1

A category is designated high-entropy based on the following note in the
governance record:

> "This category has always been noisy. We've never gotten clean signal here."

The designation was made in observation window 3. The current window is 9.

**Question:** Is the high-entropy designation still valid? What does the
framework require before it can be used to normalize persistence rates?

<details>
<summary>Verdict</summary>

**The designation requires a validity check before it can be used.**

The high-entropy designation was made in window 3 with informal justification
("has always been noisy"). The baseline validity check requires asking: under
what governance conditions was this baseline formed, and were those conditions
themselves distorted?

Window 3 is early in the observation model. If the framework in window 3 had
higher constraint density, lower detection capability, or narrower exploration
than the current window, the "always noisy" observation may reflect historical
governance conditions, not the domain itself. A category that appears noisy
under over-constraint may be deterministic under correct calibration.

Additionally, "has always been noisy" is not the required justification format.
The high-entropy designation requires documented justification explaining the
structural reason for high entropy — why the domain produces genuine variability
regardless of governance state.

**Correct action:** Before using the designation to normalize current
persistence rates, verify: (1) was window 3 subject to governance conditions
now classified as failure? If yes, the baseline is suspect and must be tagged
provisional. (2) Does the justification identify structural domain entropy, or
historical measurement noise? If the latter, the designation may not reflect
domain truth.

</details>

---

### Scenario D.2

A policy change was made in window 5 to address a deviation pattern in a
category with no established entropy baseline. Window 6 and 7 show the
pattern persisting at roughly the same rate as before the change.

The reviewer in window 8 writes: "The policy change didn't work. The pattern
is still present. Triggering misattribution re-examination."

**Question:** Is triggering re-examination correct here?

<details>
<summary>Verdict</summary>

**No — the category has no established baseline, so persistence is insufficient
evidence to trigger re-examination.**

The baseline comparison rule requires comparing persistence rate against the
expected baseline for that category type. This category has fewer than three
prior policy change cycles, which means it has unknown entropy. Unknown-entropy
persistence is not evidence of misattribution — it is insufficient data.

The required response for unknown-entropy persistence is: extend the observation
window before triggering re-examination. Two windows of persistence in an
unknown-entropy category does not meet the evidentiary standard for misattribution.

The reviewer's reasoning ("the policy change didn't work") is the intuitive
response to persistent patterns, but it conflates "the change didn't eliminate
the pattern" with "the change was wrong." In an unknown-entropy category, the
change may have been correct and the remaining persistence may reflect baseline
variability that has not yet been characterized.

**Correct action:** Extend observation to at least one more window before
triggering re-examination. Use the extended window to begin establishing an
entropy baseline for this category.

</details>

---

## Part E — Fitness function and self-revision

### Scenario E.1

A periodic fitness review produces the following measurements:

- Post-change recurrence: declining (priority 1 satisfied)
- False positive rate: bounded and stable (priority 2 satisfied)
- Exploration cost: rising steadily across last 4 windows (priority 3 failing)
- Mandatory change rate in established categories: declining (priority 4 satisfied)

The reviewer concludes: "Three of four metrics are healthy. Exploration cost
is rising but priorities 1 and 2 are satisfied, so this is acceptable per
the priority ordering."

**Question:** Is the reviewer's conclusion correct?

<details>
<summary>Verdict</summary>

**The reviewer has applied the priority ordering correctly, but has not asked
the required meta-question.**

Per the priority ordering, priority 3 (exploration cost) yields to priorities
1 and 2. A system with declining recurrence and bounded false positives that
has rising exploration cost is not in immediate governance failure. The
reviewer's application of the ordering is technically correct.

However: exploration cost has been rising for four consecutive windows. This
constitutes persistent divergence between priority 1 (satisfied, declining)
and priority 3 (failing, rising). Four windows is above the three-window
threshold that triggers the fitness function self-revision condition.

When adjacent-priority metrics diverge persistently across three or more
periodic reviews, the fitness function self-revision condition requires a
meta-question: is this divergence an acceptable tradeoff, or evidence that
the priority ordering is producing a systematic tradeoff that was not intended?

The reviewer has confirmed the ordering is being applied correctly. They have
not asked whether the ordering itself is producing the right outcome.

**Correct action:** Document the persistent divergence and include a meta-question
in the review: is recurrence declining because root causes are being addressed,
or because the system is tightening constraints in ways that reduce exploration
while suppressing familiar failure modes? The answer determines whether the
fitness function requires revision.

</details>

---

### Scenario E.2

Recurrence is declining on count measures. A closer analysis shows that
severity-weighted recurrence is rising: the remaining recurrences are
concentrated in the highest-consequence tier.

The periodic reviewer reports: "Recurrence is declining. Priority 1 satisfied."

**Question:** Is priority 1 satisfied?

<details>
<summary>Verdict</summary>

**No — priority 1 is not satisfied.**

Priority 1 requires that severity-weighted recurrence is declining, not just
count recurrence. Count recurrence is a leading indicator; severity-weighted
recurrence is the authoritative metric. When they diverge, severity-weighted
recurrence takes precedence.

The current situation — count declining, severity-weighted rising — is the
canonical case where count-only measurement produces a false positive for
improvement. The system is eliminating high-frequency low-severity recurrences
while high-consequence recurrences remain or increase. This is optimization
for visibility, not for consequence reduction.

Reporting "priority 1 satisfied" on count recurrence alone while severity-weighted
recurrence is rising is a fitness function misreading.

**Correct action:** Report priority 1 as not satisfied. Document both metrics.
Prioritize addressing the high-consequence recurrences — these are the cases
where the system's changes are not reaching root causes.

</details>

---

## Part F — `low_confidence_proceed` expiry and system value function

### Scenario F.1

A constraint in a low-activity category was tagged `low_confidence_proceed`
in window 4 because the reviewer could not name an observable indicator that
the triggering conditions still existed. The re-evaluation trigger was:
"if three decisions occur in this category."

No decisions have occurred. The current window is 7.

**Question:** Is the `low_confidence_proceed` tag still valid? What is required?

<details>
<summary>Verdict</summary>

**The tag has expired and requires mandatory re-evaluation.**

A `low_confidence_proceed` retention tag that has not reached its re-evaluation
trigger within two consecutive observation windows automatically converts to
a required re-evaluation. The tag was issued in window 4. By window 7, three
windows have passed without the trigger being reached.

The trigger ("if three decisions occur") has not fired because no decisions
have occurred. This does not extend the carry — the carry expired after two
windows regardless of whether the trigger fired.

The required re-evaluation must produce a different state. Options:
- **Retire as untestable:** no decision activity and no prospect of generating
  it; archive the constraint as historical context rather than active governance
- **Escalate as B1:** the boundary condition (cannot observe whether conditions
  persist) has not resolved; treat as active boundary condition requiring
  `hard_stop` or `escalate` response
- **Renew with different basis:** if new information has emerged that allows
  an observable indicator to be named, issue a new (first-generation)
  `low_confidence_proceed` with that indicator

A second `low_confidence_proceed` on the same unresolved basis — "still cannot
name an observable indicator" — is not permitted.

</details>

---

### Scenario F.2

A constraint and a new learning pattern are simultaneously triggered in the
same category. The constraint is due for re-evaluation (three untested
windows). The new pattern has accumulated to the Enforced tier.

The reviewer writes: "The new pattern is at the Enforced tier, which means
a mandatory constraint change is required immediately. I'll address the
existing constraint re-evaluation after I implement the new one."

**Question:** Has the reviewer correctly applied the system value function?

<details>
<summary>Verdict</summary>

**No — the reviewer has inverted the priority rule.**

When learning (add constraint) and forgetting (remove constraint) are
simultaneously triggered on the same category, forgetting evaluates first.
Learning evaluates second, on the post-evaluation baseline. The reviewer has
applied the opposite order.

The reason for the priority rule is asymmetric error cost: adding a new
constraint on top of an invalid existing constraint produces compounded
over-constraint. Two wrong constraints in the same category are harder to
diagnose and unwind than one. The Enforced tier trigger creates urgency for
the new constraint, but urgency does not override the priority rule — it is
precisely the kind of pressure that the priority rule is designed to resist.

The category type matters here: if this is a high-consequence, low-entropy
category where under-constraint cost is irreversible, the priority rule may
be overridden — but only with documented justification at decision time. The
reviewer has not invoked this override.

**Correct action:** Evaluate the existing constraint first. Determine whether
it should be renewed, retired, or tagged `low_confidence_proceed`. Then proceed
with the new mandatory constraint change against the resulting clean or
confirmed baseline. Document the sequence explicitly.

</details>

---

### Scenario F.3

Two categories are simultaneously in scope for the system value function
priority rule. Category A is high-consequence, low-entropy (documented). Both
learning and forgetting have been triggered in Category A.

The reviewer invokes the override: "Category A is high-consequence and
low-entropy. Learning takes priority. I'm proceeding with the new constraint
before evaluating the existing one."

**Question:** Is the override valid?

<details>
<summary>Verdict</summary>

**Yes — but only if the override is documented at decision time.**

The high-consequence, low-entropy override exists for exactly this case. The
conditions are met: Category A has documented designation as high-consequence
and low-entropy. The override allows learning to take priority and forgetting
to be deferred until after the new constraint is established.

The critical requirement: the override must be documented at the time of the
decision. The reviewer has stated the reasoning in the decision record, which
satisfies this requirement.

What must be confirmed in the record:
1. The high-consequence, low-entropy designation is documented (not just asserted
   in this decision)
2. The override is explicitly invoked with reasoning
3. Forgetting is deferred — not abandoned. The existing constraint re-evaluation
   must be scheduled as a required follow-up after the new constraint is established

If the existing constraint re-evaluation is not completed within two windows
of the new constraint being established, it converts to a required re-evaluation
under the `low_confidence_proceed` expiry rules.

An undocumented override — invoking this rule without a record — is an
unrecorded priority violation, not an override.

</details>

---

### Scenario F.4

A reviewer is evaluating whether to retain a constraint whose triggering
conditions "probably still exist" based on reasoning from adjacent categories.
No direct observable indicator is available.

The reviewer writes: "Given what we know about the adjacent categories,
it's reasonable to conclude the conditions persist. Renewing the constraint."

**Question:** Has the condition observability requirement been satisfied?

<details>
<summary>Verdict</summary>

**No — the condition observability requirement has not been satisfied.**

The retention decision cannot be based on reasoning from adjacent categories
if that reasoning produces a conclusion that cannot be directly observed. A
chain of inferences from adjacent evidence is exactly the pattern the
observability requirement is designed to prevent: the conclusion "conditions
probably still exist" cannot be falsified through observation, only through
more reasoning.

The practical test: what specific observable indicator would confirm that the
triggering conditions persist? If no such indicator can be named — only a
chain of analogical reasoning — the renewal is based on assumption, not evidence.

The renewal may still be correct. But it cannot be stated as confirmed. It
must be tagged `low_confidence_proceed` with an explicit re-evaluation trigger
that names an observable condition (not a reasoning conclusion).

**Correct action:** Convert the renewal to `low_confidence_proceed`. Name the
specific observable indicator that would confirm the conditions persist, or
acknowledge that no such indicator exists (in which case, this is a B1 or B5
boundary condition requiring the appropriate response). Do not present
inference-based conclusions as confirmed observations.

</details>

---

## Score interpretation

| Score | Interpretation |
|-------|---------------|
| 16–18 | Strong pass — mechanisms are operational |
| 13–15 | Marginal pass — review Part D (baseline) and Part F (value function); these are the scenarios most commonly misread |
| 10–12 | Partial pass — the accumulation rules (Part C) and expiry discipline (Part F) are likely being applied at the wrong tier |
| <10 | Fail — re-read docs/boundary-crossing-protocol.md before re-running; particularly the four response types, deferral genuineness conditions, and the system value function section |

## Common error patterns

**Applying the deviation accumulation rule at the wrong tier:** The most
frequent error is treating two deviations as Diagnostic when it is
Operationalized. The rule is count-based, not judgment-based. Two observations
in the same category cross the Operationalized threshold regardless of whether
they "feel" like the same underlying cause.

**Treating `low_confidence_proceed` as indefinite:** This tag has a two-window
maximum carry. Many reviewers treat it as "acknowledged uncertainty" with no
expiry. It is not. After two windows without reaching its re-evaluation trigger,
it converts to required re-evaluation.

**Inverting the learning/forgetting priority:** The counterintuitive direction
— forgetting first — is the most commonly inverted rule. The Enforced-tier
learning trigger creates urgency that makes proceeding with the new constraint
feel correct. The priority rule is designed to resist exactly this urgency.

**Using count recurrence as the Priority 1 metric:** Severity-weighted
recurrence is the authoritative metric. Count recurrence is a leading indicator.
Reporting Priority 1 as satisfied when only count is declining, while
severity-weighted is rising, is the most consequential fitness function
misreading.
