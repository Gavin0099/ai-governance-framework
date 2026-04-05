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

## Action selection determinism

The four response types exist to prevent "same uncertainty → different actions"
depending on which reviewer handles the decision. To achieve consistency,
response selection must follow the same criteria regardless of reviewer.

The selection criteria are two dimensions:

**Dimension 1: Reversibility**
Can the decision be corrected after the fact if it turns out to be wrong?

Reversibility is not binary. Use the most specific tier the situation supports:

| Tier | Definition | Example |
|------|-----------|---------|
| `fully_reversible` | Decision can be corrected within the current observation window with no residual harm | A doc update that can be revised |
| `reversible_with_cost` | Decision can be corrected but requires significant re-work, re-evaluation, or affects downstream decisions that cited it | A skepticism zone classification that must be unwound |
| `reversible_eventually` | Decision can be corrected but not before causing compounding effects | A `cause_identified` that was wrong and was cited as precedent |
| `irreversible` | Wrong decision causes harm that cannot be undone within observation period at acceptable cost | A permanent deletion, a public disclosure |

Classify at the **worst plausible tier**, not the best case. "We could probably fix it" is `reversible_with_cost` at minimum — not `fully_reversible` unless the path to reversal is clear and costless.

**Dimension 2: Cost of not deciding**
What happens if no decision is made now? Assess at the **system level**, not the local decision level.

- **Low:** Deferral has minimal system-level consequence; situation can wait without enabling harm or closing an irreversible window
- **High:** Deferral allows a harmful action to proceed uncontested, or closes a window that cannot be reopened, or prevents dependent decisions from being made

Common miscalibration: rating cost as "local low" when the system-level cost is high. Example: "the decision only affects one log entry" — but if that log entry is the only opportunity to classify a failure before the next review cycle, the window is closing. Always ask: what system-level state changes if this decision does not get made in this window?

Selection matrix:

| Reversibility | Cost of not deciding | External validation available? | → Required response |
|--------------|---------------------|-------------------------------|---------------------|
| fully_reversible | Low | — | `defer_with_condition` |
| fully_reversible | High | Yes | `escalate` |
| fully_reversible | High | No | `low_confidence_proceed` |
| reversible_with_cost or worse | Low | — | `defer_with_condition` |
| reversible_with_cost or worse | High | Yes | `escalate` → if unavailable in time: `hard_stop` |
| reversible_with_cost or worse | High | No | `hard_stop` |

**How to use this matrix:** Both dimensions must be classified explicitly before
selecting a response. A reviewer who selects `low_confidence_proceed` for a
`reversible_with_cost` or worse decision without documenting that external
validation was unavailable has not applied the protocol.

**Consistency check:** Two reviewers facing the same boundary condition, the
same reversibility tier, and the same cost classification should reach the same
response type. Divergence is a consistency violation requiring examination —
either the situation was assessed differently (which must be reconciled) or the
criteria were applied differently (which is a calibration gap).

**Dimension drift guard:** Dimension classifications are themselves subject to
the same consistency pressure as response types. If reviewers consistently
classify the same categories of decisions as `fully_reversible` when a more
conservative tier is warranted, the matrix produces correct-looking outputs
from incorrect inputs. Monitor dimension classifications across reviewers at
periodic review, not just response types.

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

## Deferral pressure

A deferral that is formally falsifiable but practically never checked is
indistinguishable from avoidance in its effects. "Formally falsifiable,
practically untested" is a distinct failure mode — more dangerous than
obvious avoidance because it passes all surface tests while accumulating
unresolved decisions.

**Deferral decay rule:** A `defer_with_condition` entry that has not been
checked against its resolution condition within two observation windows
automatically upgrades its required action:

- After two windows without resolution check: the deferral must be explicitly
  reviewed and either renewed with updated resolution condition and deadline,
  or converted to `low_confidence_proceed`, `escalate`, or `hard_stop`
- A deferral that is renewed without evidence that the resolution condition
  was actually checked is avoidance with an additional step

**Deferral registry requirement:** Open deferrals must be tracked. At each
window close, the review must include: how many deferrals are currently open,
when each was created, and whether each resolution condition has been checked.
An open deferral that does not appear in the window-close record has not been
governed.

**Maximum deferral age:** A deferral that has been renewed more than twice
without resolution is structurally stuck. At that point it must be escalated
or converted to `hard_stop` — not renewed again. Repeated renewal of the
same deferral is a signal that the resolution condition itself is unachievable
within the current observation model, which is a B1 condition requiring a
different response than `defer_with_condition`.

**Evidence-gain condition for renewal:** Deferral renewal is not valid if the
observation window that elapsed produced no new evidence types relevant to the
resolution condition. Time passing is not progress. A renewal must document:
- What new evidence arrived during the window (if any)
- Why this evidence did not yet satisfy the resolution condition
- What specifically is expected in the next window that was not present in this one

A renewal that cannot answer these three questions is a time-based renewal,
not an evidence-based one. It must be treated as maximum deferral age reached
(escalate or hard_stop), not as a legitimate renewal.

This distinction — time passing vs evidence accumulating — is the same error
as time-based classification decay (treating "two windows elapsed" as equivalent
to "corroboration failed to arrive"). The deferral system makes the same error
if it allows time to substitute for evidence in renewal justification.

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

## Invisible zone response

Some failures are structurally invisible: they do not produce observable
signals within the observation model, so no mechanism in the framework
will fire to detect them. These are documented in adversarial-test-scenarios.md
(Scenario C.3) as the unreachable category of the detection latency table.

Naming a failure as structurally invisible is not sufficient. If the system
identifies a region of its decision space as invisible and then does nothing,
it has acknowledged a risk and declined to respond. That is not an acceptable
governance outcome for decisions with significant consequences.

**Required response to structurally invisible failure identification:**

When a decision is identified as involving a structurally invisible failure
mode — meaning the failure would not produce an observable signal if it
occurred — the system must select one of the following responses, in order
of preference:

**Response 1: Forced exploration**
Deliberately create conditions that would make the invisible failure visible
if it exists. This requires designing a test or intervention that could
produce an observable signal. If the failure is "decision is systematically
over-conservative," a forced exploration injects some decisions that test
the conservative boundary. If the failure is "coverage narrowing to familiar
evidence types," a forced exploration introduces unfamiliar evidence types
to see how they are handled.

Forced exploration is the preferred response because it converts an invisible
failure to potentially observable failure. It does not guarantee detection
but it changes the detection probability from zero.

**Forced exploration must be capable of falsification.** An exploration that
cannot produce a result that would change the current assumption is activity
without information gain. Before executing forced exploration, specify:

1. What specific hypothesis is being tested? (e.g., "decisions in this
   category are systematically over-conservative")
2. What result would confirm the hypothesis? (e.g., "injected decisions that
   should be accepted are rejected at rate > X%")
3. What result would disconfirm it? (e.g., "injected decisions are accepted
   at the expected rate, and the conservative pattern was specific to
   observed cases")

An exploration that is designed to produce only confirmatory evidence is
not forced exploration — it is confirmation of a prior belief dressed as
investigation. The disconfirmatory result must be genuinely possible given
the exploration design; if the design makes disconfirmation impossible, the
exploration is not falsifiable.

**Cheap exploration failure mode:** Exploration that tests only low-stakes
or familiar cases does not reach the invisible failure zone. If the invisible
failure is expressed in a specific region of the decision space, the
exploration must be designed to reach that region. Generic "do something
different" exploration is activity without targeted information gain.

**Response 2: External audit injection**
An observer outside the current observation model reviews a sample of
decisions in the invisible zone. The external observer is not bound by
the same observation model and may detect patterns the framework cannot.

This requires: (a) identifying who the external observer is, (b) specifying
what sample they review, (c) specifying what criteria they apply. "Get
someone else to look at it" is not external audit injection — it is offload.

**Response 3: Explicit risk acceptance**
If neither forced exploration nor external audit is feasible, the risk must
be explicitly accepted and documented: which failure mode is invisible, what
the estimated consequences would be if it occurs, and what would change in
the observation model to make it detectable.

Explicit risk acceptance is the weakest response. It acknowledges the gap
without reducing it. It is acceptable when the cost of forced exploration
or external audit exceeds the expected cost of the invisible failure. It
is not acceptable as a default response to all invisible failures — that
would make the concept of invisible zone response meaningless.

**What is not acceptable:**
Labeling a failure as structurally invisible and taking no further action.
The invisible zone is not a governance-free zone. It is a zone where
different governance mechanisms are required.

---

## Three-tier observation model

Before addressing incentive alignment, a clarification about what this
protocol has already built — and where it sits.

Observations in this framework exist at three levels:

| Tier | Definition | Example in this protocol |
|------|-----------|------------------------|
| **Observable** | Recorded in the log; can be retrieved | Deviation logged with reason |
| **Operationalized** | Feeding into a review, signal, or metric that someone must engage with | Deviation pattern triggers periodic review item |
| **Enforced** | Directly alters behavior: blocks an action, requires escalation, creates unavoidable cost | Deferral decay forces escalation after 3 renewals |

Most governance systems stop at Observable. Visibility is treated as
sufficient. It is not — a system with perfect observability and zero
consequence for what it observes has not governed anything.

**Current state of this protocol:**

- Deferral decay → **Enforced**: maximum renewal forces escalation or hard_stop
- Invisible zone response → **Enforced**: taking no action after naming an
  invisible failure is not permitted; a required response must be selected
- Forced exploration falsifiability → **Operationalized**: required before
  execution, but the check is reviewer-assessed
- Deviation logging → **Observable** only

The goal of the incentive alignment section is to lift deviation logging
from Observable to Operationalized, and — for persistent patterns — to Enforced.

---

## Incentive alignment

The action selection matrix and response types are defined in terms of
epistemic state (reversibility, cost of not deciding). But response selection
happens in an environment where actions have different costs. If the cost of
the correct response is systematically higher than the cost of an incorrect
but lower-effort response, the system will produce cost-motivated decisions
while documenting them as epistemically-motivated ones.

This is the economic consistency problem: the cost of correct behavior must
not systematically bias the system toward incorrect decisions.

**What this protocol already does to incentives:**

This protocol is not neutral with respect to incentives. Three existing
mechanisms already shape behavior by making inaction costly:

- **Deferral decay:** inaction (deferring indefinitely) is penalized by
  forced escalation. Deferral has a cost now; it did not before.
- **Invisible zone response:** inaction after naming a structurally invisible
  failure is explicitly prohibited. The cost of naming-and-ignoring is now
  higher than the cost of responding.
- **Forced escalation and hard_stop:** both require the reviewer to absorb
  the cost of stopping a process. These exist precisely because the natural
  incentive is to keep processes moving.

These are incentive interventions, not observation mechanisms. Calling them
"just documentation" would be inaccurate. They are deliberate costs imposed
on paths that were previously costless.

The protocol therefore already occupies the incentive space partially. The
remaining gap is: these interventions address specific behaviors (defer too
long, ignore invisible failures, fail to stop). They do not address the
broader pattern of cost-motivated response downgrade across the full matrix.

**Cost-motivated downgrade detection:**

Any deviation from the matrix-indicated response must be logged explicitly
with its reason. A reviewer who selects `low_confidence_proceed` when the
matrix indicates `hard_stop` must document:
- Which matrix cell applied (reversibility tier + cost classification)
- Why the matrix-indicated response was not used
- Whether cost was a factor in the deviation

A deviation without documented reason is a protocol violation. A deviation
where cost is acknowledged as the reason is permitted — but it enters the
deviation record.

**Deviation accumulation rule:**

A single deviation is logged and reviewed. It does not trigger required
action. Patterns are different.

| Pattern | Tier | Required action |
|---------|------|----------------|
| Same deviation type in 1 window | Observable | Logged; included in periodic review |
| Same deviation type in 2+ windows | Operationalized | Must appear on the next periodic review agenda; reviewer must engage with it |
| Same deviation type in 3 consecutive windows | Enforced | Required review before the next decision in the affected category; review must produce one of three outcomes |

**Required outcomes for enforced deviation review:**

| Outcome | Meaning | Required downstream effect |
|---------|---------|--------------------------|
| `cost_legitimate` | The cost of the correct response was genuinely prohibitive under current constraints | Named adoption blocker: document why, specify what change would make the correct response feasible, assign ownership. The blocker is open until resolved or explicitly accepted as permanent risk |
| `calibration_error` | The dimension assessment (reversibility, cost of not deciding) was wrong; the matrix actually indicated the chosen response | Correct the dimension classification in the reference record; re-evaluate the original decision under corrected assessment; if the re-evaluation changes the indicated response, the decision must be revisited |
| `drift_confirmed` | Cost-motivated drift is occurring; the correct response was available but not chosen for non-epistemic reasons | A specific named change is required: to the process that makes the correct response too costly, to the escalation path, or to the threshold calibration. The outcome is not closed until the change is made or explicitly declined with documented reasoning |

A review that does not produce one of these three outcomes has not completed
the enforced review. The pattern continues to accumulate.

**Outcome falsifiability requirement:**

Each outcome classification must specify what would show it was incorrectly
applied. This prevents outcomes from functioning as justification vocabulary
rather than learning mechanisms.

- `cost_legitimate` must answer: "What change would make this cost no longer
  prohibitive?" If no answer exists, the constraint has not been named — it
  has been labeled. A constraint with no path to resolution is a permanent
  invisible failure zone, not a legitimate cost.

- `calibration_error` must answer: "What reference example or criterion
  change would prevent this miscalibration in future?" If no answer exists,
  the error was not identified — it was acknowledged. An error with no
  correction path is not calibration_error; it is an observation waiting
  to be classified.

- `drift_confirmed` must answer: "What specific observable behavior change
  would indicate the drift has been corrected?" If no answer exists, the
  confirmation is unfalsifiable — it names a pattern but specifies no
  outcome that would close it.

An outcome that cannot answer its falsifiability question is incomplete.
The enforced review is not closed until all three fields are answerable.

**Outcome downstream closure:**

An examined deviation is not governance-complete when an outcome is produced.
It is governance-complete when the downstream effect is either implemented
or explicitly declined with documented reasoning.

The distinction:
- `outcome produced, effect pending` = investigation_pending (time-limited)
- `outcome produced, effect implemented` = closed
- `outcome produced, effect declined with reasoning` = closed with
  documented risk acceptance
- `outcome produced, effect never addressed` = silent non-response;
  indistinguishable from not having examined the deviation

This is the same closure logic as the learning loop: an observed failure with
`investigation_pending` must convert within one window. An outcome with
`effect pending` must either implement or explicitly decline within the next
observation window.

The consequence of repeated non-closure: a deviation that produces an outcome
but no downstream effect in two consecutive windows upgrades: the deviation
category is now subject to the same accumulation rule as the original
deviations — it counts as a new pattern of non-response, triggering its own
enforced review. Non-closure cannot accumulate silently.

**The key diagnostic question:** Is the distribution of response types
consistent with the distribution of epistemic states in the decisions being
made? If high-cost responses (`hard_stop`, `escalate`) appear systematically
less often than the observed uncertainty levels would predict, cost is likely
influencing response selection beyond the documented deviations.

**What this protocol does and does not do regarding incentives:**

The protocol converts cost-motivated drift from a silent, untraceable bias
into an explicit, attributable decision pattern. Single deviations are
recorded. Patterns are surfaced. Persistent patterns are enforced into review.
Enforced reviews produce attributed outcomes.

This is not the same as eliminating the incentives that cause drift.
`cost_legitimate` is a valid outcome — it names a real constraint. The
protocol's claim is not that organizations will always choose the epistemically
correct response. It is that when they do not, the pattern cannot remain
invisible, and eventually cannot remain unattributed.

The progression is: single deviation → observable → pattern → operationalized
→ persistent pattern → enforced → attributed outcome → mandatory system change
(see Pattern-to-policy binding below). Whether change occurs is no longer
solely dependent on organizational will — the pattern-to-policy rule forces
specific system parameter updates when outcome patterns cross the threshold.

---

## Pattern-to-policy binding

The accumulation and outcome mechanisms above produce attributed patterns.
Attribution is necessary but not sufficient for the system to be genuinely
self-correcting. A pattern that is attributed but produces no mandatory
change to system behavior is a terminal record — informative historically,
inert going forward.

The missing step: specific outcome patterns must produce specific mandatory
changes to system parameters. Not reviews. Not recommendations. Parameter changes.

**Binding rule:**

When the same outcome type appears in the same category three consecutive
windows, the following changes are mandatory:

| Repeated outcome | Mandatory system change |
|-----------------|------------------------|
| `calibration_error` × 3 in same dimension | The dimension calibration for that category must be updated in the reference record; reference examples for that dimension are stale and must be revised; existing decisions that relied on the stale calibration are flagged for re-evaluation |
| `cost_legitimate` × 3 in same response category | The response path is marked `structurally_inaccessible` for that category in governance-mechanism-tiers.md; this is a mandatory disclosure to adopters: "response type X is theoretically required but practically unavailable in category Y" |
| `drift_confirmed` × 3 in same category | The category enters a **behavioral constraint zone**: any future decision in this category requires an additional documentation field explaining why the matrix-indicated response was used (or why it was not, with attributed reason); the zone remains until two consecutive decisions in the category use the matrix-indicated response |

These changes are not conditional on reviewer agreement. They are automatic
consequences of the pattern count reaching the threshold. The decision to
apply them does not require a new review — the threshold crossing is the
trigger.

**Why parameter changes, not additional reviews:**

The accumulation rule already produces reviews at the enforced tier. Adding
another review at the outcome accumulation tier would create closure inflation:
every unresolved pattern generates a new review structure, review agenda items
accumulate faster than they are resolved, and the system becomes operationally
active while decision quality remains unchanged.

The binding rule breaks this by making the downstream effect automatic and
specific. The change happens to a documented artifact (reference record,
governance-mechanism-tiers.md, constraint zone declaration) — not to a review
agenda. Artifacts are versioned; reviewers can see what changed and when.
Reviews can be skipped or de-prioritized. Versioned artifact changes cannot.

**Strategic compliance guard:**

A reviewer who repeatedly uses `cost_legitimate` to avoid change eventually
produces the mandatory system change: the path is marked `structurally_inaccessible`.
This is the opposite of avoidance — marking a path as structurally inaccessible
is a stronger governance finding than any individual drift confirmation. It must
be disclosed to adopters. Strategic compliance that routes through `cost_legitimate`
eventually forces the constraint into the public governance record.

Similarly, `drift_confirmed` repeated three times creates a behavioral constraint
zone that makes future non-standard responses require explicit justification.
The cost of repeated non-standard behavior increases over time, not stays flat.

---

## Closure inflation guard

The recursive closure structure (deviation → loop → non-closure → new loop)
creates a risk that the system becomes structurally active but behaviorally
stagnant: many loops, many reviews, no change.

**Signal materiality filter:**

Not every deviation enters the accumulation count. A deviation is material
for accumulation purposes only if it meets at least one of:
- The decision involved a `reversible_with_cost` or worse reversibility tier
- The cost-of-not-deciding was assessed as high
- The same deviation type has appeared in a previous window (any recurrence
  is automatically material regardless of tier)

Single, well-documented deviations on `fully_reversible`, low-cost situations
are logged but do not enter the accumulation count. This prevents trivial
edge cases from generating enforcement loops.

**Loop retirement:**

An accumulation loop is retired when:
- The pattern-to-policy binding produces its mandatory change (the change
  resets the count for that category)
- Two consecutive windows in the same category produce no deviation (the
  constraint zone is retired by the same mechanism as skepticism zones)

A loop that has been in enforced tier for three windows without producing
its mandatory change must be explicitly escalated outside the protocol — it
represents a governance failure of the protocol itself, not a governance
failure within it.

**The limit of self-correction:**

The pattern-to-policy binding produces mandatory changes to system parameters.
It does not produce mandatory changes to organizational behavior. An organization
that has `structurally_inaccessible` marked for a response type, and `drift_confirmed`
zones active, and behavioral constraint zones accumulating — but still does not
change how it actually makes decisions — has exhausted the self-correction capacity
of this protocol.

At that point, the protocol has done what it can. The governance record is
complete, attributable, and visible. The remaining gap is between governance
record and governance effect — which is the organizational design problem that
sits outside any mechanism this protocol can provide.

What the protocol guarantees: that gap cannot be hidden. The governance record
will show exactly where the system stopped responding to its own signals.

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
