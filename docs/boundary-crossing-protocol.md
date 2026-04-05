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

## Protocol self-stability

The pattern-to-policy binding generates policy changes: constraint zones,
`structurally_inaccessible` markings, calibration updates. These are changes
to governance parameters produced by governance mechanisms. They are subject
to the same stability and correction requirements as any other governance
decision.

The learning-stability.md principles apply to this protocol's outputs:

**Policy surface compaction:**

Constraint zones, `structurally_inaccessible` markings, and calibration
updates in the same category accumulate over time. Accumulation is normal;
unreviewed accumulation is not. At each periodic review (same cadence as
silent degradation review), apply this check to the protocol's own outputs:

- Are multiple constraint zones in the same category expressing the same
  root cause? If yes, consolidate: one precise change is more useful than
  layered restrictions that obscure each other.
- Are `structurally_inaccessible` markings still accurate? A path that was
  inaccessible due to cost may become accessible if costs change. Markings
  that are stale should be retired, not accumulated.
- Are calibration updates building toward a coherent revised baseline, or
  are they patchwork corrections? When patches accumulate, a baseline reset
  may be more accurate than continued incremental updates.

Compaction is not rollback — it is precision. A compacted governance record
is easier to apply correctly than a layered one. The goal is not fewer
constraints but fewer constraints that are redundant or stale.

**Policy rollback trigger:**

A policy change produced by pattern-to-policy binding may itself be wrong —
if the triggering pattern was misattributed (all three triggering outcomes
were `calibration_error` retroactively). When a policy change is found to be
based on a misattributed pattern, it must be rolled back:

- For behavioral constraint zones: the zone is retired with documentation
  of why the triggering pattern was wrong; the category count resets
- For `structurally_inaccessible` markings: the marking is removed and the
  path is re-evaluated under corrected dimension assessments
- For calibration updates: the stale update is identified, and the baseline
  is corrected to the pre-update state if the update was net wrong

Rollback trigger condition: when the falsifiability question for the
triggering outcome classification (see Outcome falsifiability requirement)
is answered in the negative — the evidence that was cited does not support
the classification. Rollback is not optional when the trigger condition is met.

**Misattribution detection signal:**

Rollback requires first detecting misattribution. The detection signal is:
the same deviation pattern continues after the mandatory policy change that
was supposed to address it. A policy change that does not reduce the pattern
it was triggered by is either wrong (misattributed triggering pattern) or
insufficient (root cause not addressed by the selected change type).

The same-failure taxonomy from learning-loop.md applies: if the pattern
persists at exact symptom level, the policy change failed directly. If it
persists at same-class level, the change may have been incomplete. If it
appears in a different category with the same underlying root cause, the
change targeted the wrong layer.

When persistence is detected after a policy change: the triggering pattern
classification must be re-examined. This is not automatic rollback — it is
automatic re-examination. Rollback occurs only if re-examination confirms
misattribution. If re-examination confirms the pattern is genuine but the
policy change was insufficient, a different policy change is required
(escalation, not rollback).

The absence of misattribution detection is itself a signal. If no policy
changes have ever triggered re-examination, either the changes are all correct
(unlikely at scale) or the post-change pattern check is not being performed.
At periodic review, confirm that at least one policy change per N windows
has been followed up with a post-change pattern check.

**Domain entropy baseline comparison:**

Not all persistent patterns after a policy change indicate misattribution.
Some categories are structurally high-entropy: the underlying domain has
genuine variability that makes it difficult to eliminate pattern recurrence
regardless of how correct the policy change is. In high-entropy categories,
"pattern persists" is normal — and treating persistence as a misattribution
signal will produce rollback of correct changes.

The baseline comparison rule: before treating pattern persistence as a
misattribution signal, compare the persistence rate against the expected
baseline for that category type. The relevant comparison is not "did the
pattern persist?" but "did the pattern persist at a higher rate than the
expected baseline for this category?"

Two category types have distinct expectations:

| Category type | Persistence after correct change | Implication of persistence |
|--------------|----------------------------------|---------------------------|
| Low-entropy (deterministic failure modes) | Declining to near-zero within 2 windows | Persistence strongly suggests misattribution |
| High-entropy (domain-variable failure modes) | Declining but not to zero; oscillating | Persistence may be correct-change baseline |

When a category has no established baseline (fewer than 3 prior policy
change cycles), treat it as unknown entropy. Unknown-entropy persistence
is not automatically misattribution — it is insufficient data. The required
response is: extend the observation window before triggering re-examination,
rather than treating absence of baseline as evidence of misattribution.

The entropy classification itself must be documented when a category is first
designated high-entropy. A category marked high-entropy without documented
justification is using the classification as an avoidance route.

**Baseline validity check:**

An entropy baseline is not a neutral constant. It was formed under specific
governance conditions: a particular constraint density, a particular detection
capability, a particular exploration rate. If those conditions were themselves
distorted — too many constraints suppressing deviation, insufficient detection
missing failures, narrow exploration producing a homogenous sample — then the
baseline encodes past governance distortions, not domain truth.

A baseline that was formed under distorted governance is a historical artifact,
not a calibration reference. Using it to normalize current persistence rates
means calibrating toward the old distortion, not toward the actual domain.

Baseline validity check: when a baseline is first established or used, the
review record must answer: under what governance conditions was this baseline
formed? Specifically, was the window in which baseline data was collected
subject to over-constraint, under-detection, or reduced exploration that would
make the sample unrepresentative?

If the baseline was formed under conditions now classified as governance
failure (confirmed `drift_confirmed` or over-learning finding in that window):
the baseline is suspect. A suspect baseline may still be used, but must be
tagged as provisional, not treated as ground truth. A suspect baseline that
has not been re-calibrated within two subsequent windows is expired.

**Consequence strength normalization:**

The three outcome types currently produce changes of unequal governance
weight. Left unchecked, this creates outcome selection bias: reviewers will
route toward outcomes whose consequences feel more manageable, producing a
systematic preference that does not reflect the actual distribution of failure
types.

Normalization rule: at periodic review, examine whether the distribution of
outcome types over the past N windows reflects the actual distribution of
failure modes, or whether one type is systematically over-represented. An
over-representation of `cost_legitimate` relative to `calibration_error` or
`drift_confirmed` is a signal that either (a) the constraints on the system
are genuinely external and the paths genuinely inaccessible — in which case
the `structurally_inaccessible` markings are accumulating correctly — or (b)
outcome selection bias is present and reviewers are routing to the lower-cost
outcome type.

The distinction: if `cost_legitimate` is predominant and
`structurally_inaccessible` markings are accumulating, the system is producing
a governance finding. If `cost_legitimate` is predominant and no
`structurally_inaccessible` markings have been produced, the outcome is being
used as a terminal classification — a sign that the outcome falsifiability
requirement is not being applied.

**Over-learning guard:**

Accumulated constraints reduce the decision space. This is intended: each
constraint zone, calibration update, and `structurally_inaccessible` marking
reflects a pattern of genuine governance failure. But accumulated constraints
that are not periodically audited will eventually make the system more
conservative than the evidence warrants.

**Early rigidity signals** (leading indicators — detected before constraint
accumulation rate diverges from deviation rate):

| Signal | What it measures | Why it precedes constraint accumulation |
|--------|-----------------|----------------------------------------|
| Decision justification length increasing | Reviewers are reasoning around more constraints | Documents get longer before deviation rate changes |
| Constraint cross-reference count increasing | Decisions cite multiple overlapping constraint zones | Layered constraints begin interacting before net impact shows in rates |
| Decision latency increasing | More constraints → more reasoning required per decision | Latency rises before quality metrics change |
| Reviewer disagreement rate increasing | Constraint interpretation becomes ambiguous | Disagreement about constraints precedes wrong decisions from constraints |

When two or more early rigidity signals fire in the same window, initiate
a constraint inventory before the next mandatory policy change is accepted.
This is a leading check: it fires while there is still time to intervene
before the lagging indicator (constraint accumulation without deviation
improvement) becomes visible.

**Over-learning accumulation rule (parallel to deviation accumulation):**

| Pattern | Tier | Required action |
|---------|------|----------------|
| Over-learning signal (lagging) in 1 window | Diagnostic | Direction check on last three changes in affected category |
| Over-learning signal in 2+ windows | Operationalized | Constraint inventory required; new mandatory changes in affected category paused pending inventory |
| Over-learning signal in 3 consecutive windows | Enforced | Constraint accumulation paused across all categories until stability review produces `converging`, `oscillating`, or `stable_noise` outcome |

This brings over-learning detection to parity with the deviation accumulation
rule. A system that can detect over-learning but not enforce a correction is
asymmetric: it enforces against drift, not against rigidity. Both are
governance failures; both must have enforcement paths.

The governance system must be able to make this assessment about itself. A
system that cannot audit its own constraint accumulation will eventually reach
the same state it was designed to prevent: high activity, no improvement,
increasingly rigid, increasingly wrong — with the additional problem that the
rigidity is now dressed in the language of governance rather than in the
language of the original failures.

---

## Governance fitness function

The mechanisms above define what to avoid: drift, rigidity, misattribution,
over-learning, strategic compliance. A system defined only by avoidance has
no positive direction — it can detect failure but cannot confirm improvement.

A governance system is improving when all four of the following hold:

**1. Mandatory change rate is declining in established categories.**
A category that has undergone several rounds of pattern-to-policy binding
should require fewer mandatory changes over time, not more. Increasing change
rate in a stable category indicates the changes are not addressing root causes.
Declining change rate indicates genuine learning.

**2. Exploration cost is stable or declining.**
Exploration cost is the effort required to make a decision in a new or
unfamiliar category — one without accumulated constraint zones or calibration
history. If exploration cost is rising, constraints are blocking new territory.
If stable or declining, constraints are clarifying existing territory without
blocking new.

**3. Post-change deviation recurrence is declining.**
When a mandatory policy change is made, the pattern that triggered it should
not recur. A declining recurrence rate after policy changes means changes are
addressing root causes. A stable or rising recurrence rate after changes means
the changes are targeting symptoms.

Recurrence is measured in two forms, and both must be tracked:

- **Count recurrence:** raw frequency of the pattern reappearing
- **Severity-weighted recurrence:** each recurrence weighted by consequence
  tier (reversible / partially reversible / irreversible / boundary-crossing)

Count recurrence alone optimizes toward eliminating high-frequency low-severity
patterns while leaving low-frequency high-severity patterns unaddressed. A
system improving on count recurrence while severity-weighted recurrence is
rising is optimizing for visibility, not for consequence reduction.

Priority 1 (recurrence declining) is satisfied only when severity-weighted
recurrence is declining, not just count recurrence. Count recurrence is a
leading indicator; severity-weighted recurrence is the authoritative metric.
When they diverge, severity-weighted recurrence takes precedence.

**4. False positive rate is detectable and bounded.**
A false positive is a constraint zone or policy change that was triggered by
a misattributed pattern and subsequently rolled back. Some false positives
are expected and acceptable — they indicate the system is sensitive enough to
detect genuine patterns. Zero false positives means the system is not reaching
the detection threshold. High false positive rate means the classification
mechanisms are overclaiming.

These four metrics do not require instrumentation to assess — they require
periodic structured review. The periodic review (once per three observation
windows) should answer all four questions explicitly. A system that cannot
answer at least one of them has insufficient observability of its own fitness.

**Priority ordering when metrics conflict:**

The four metrics can produce conflicting signals. Reducing recurrence may
require adding constraints that raise exploration cost. Bounding false
positives may require accepting a higher mandatory change rate. When two or
more metrics conflict, the following default priority ordering applies:

1. **Post-change recurrence declining** — if changes are not addressing root
   causes, all other metrics are unreliable. A system making changes that do
   not reduce recurrence is not learning; it is generating activity that
   looks like governance.

2. **False positive rate detectable and bounded** — if the classification
   mechanism cannot be evaluated for accuracy, the system cannot distinguish
   genuine learning from systematic error. Priority 1 is meaningless without
   reliable classification.

3. **Exploration cost stable or declining** — if the system can make correct
   changes (1) and detect wrong ones (2), then rising exploration cost indicates
   the constraint architecture is impeding new territory without genuine benefit.

4. **Mandatory change rate declining in established categories** — this is
   the long-term health signal. It becomes meaningful only when priorities
   1–3 are satisfied: a declining change rate in a system with unbound false
   positives or rising exploration cost is not improvement; it is stagnation.

When priority 1 is not satisfied, the other three metrics should not be used
to assess fitness. A system with declining change rate, low exploration cost,
and bounded false positives but rising recurrence is getting worse, not better
— the other signals are masking a root cause failure.

This ordering is a default, not a rule. A specific category may have
documented reasons to deviate. Deviations must be recorded with explicit
justification and are subject to the same falsifiability requirement as any
other documented decision.

**Fitness function self-revision trigger:**

The fitness function defines what improvement looks like. But the fitness
function itself is a governance artifact — its metric definitions, priority
ordering, and interpretation rules were set at a point in time, under
particular governance conditions. Like any governance artifact, they can
become miscalibrated without producing any failure within the observation model.

The specific failure mode: two metrics that should move together (per the
priority ordering) diverge persistently. The clearest case is priority 1
declining alongside priority 3 rising — recurrence is falling, but exploration
cost is rising with it. Per the priority ordering, this is acceptable: priority
3 yields to priority 1. But if the divergence persists across three or more
periodic reviews without stabilizing, the ordering may be resolving the wrong
way: the system is achieving recurrence reduction by sacrificing exploration,
and calling that improvement.

This is not a conflict the priority ordering can resolve, because the priority
ordering is what produces it. The fitness function itself requires re-examination.

**Fitness function self-revision condition:** When any two adjacent-priority
metrics diverge persistently across three or more consecutive periodic reviews
— moving in opposite directions without either stabilizing — the periodic
review must include a meta-question: is this divergence evidence that the
governance system is improving in the right direction, or evidence that the
fitness function's priority ordering is producing a systematic tradeoff that
was not intended?

The meta-question cannot be answered by applying the fitness function. It
requires stepping outside the fitness function and asking whether the metrics
themselves are measuring what was intended. This is not automated. It requires
a reviewer who can assess whether the current priority ordering still reflects
the system's actual needs, or whether the ordering has become a source of
systematic mismeasurement.

If the meta-question concludes that the fitness function requires revision: the
revision must be documented with the same falsifiability requirement as any
other governance change — what would the revised fitness function predict, how
would that prediction be checked, and what would show the revision was wrong.
A fitness function revision that cannot be falsified is a preference change
dressed as a governance improvement.

---

## Historical inertia and the right to forget

A constraint zone that has not been tested — no decisions in that category
during N observation windows — is not validated by absence of activity. It is
untested. An untested constraint is not evidence of ongoing protection; it is
a rule that may have outlived the conditions that justified it.

**Untested constraint rule:**

A constraint zone, `structurally_inaccessible` marking, or calibration update
that has seen no decisions or activity in the relevant category for three
consecutive observation windows must be actively re-evaluated, not assumed still
valid. This is the negative pressure principle applied to the governance record
itself: absence of testing is not evidence of correctness.

Re-evaluation options:
- **Renew with evidence:** active decision activity has since occurred and
  confirmed the constraint is still needed; document the specific evidence
- **Retire as obsolete:** the conditions that triggered the constraint have
  changed and the original pattern is no longer expected; document why
- **Retire as untestable:** the category has no decision activity and no
  prospect of generating it; the constraint cannot be validated or invalidated;
  it should be archived as historical context rather than active governance

**What to discard:**

Not all historical constraints should be retained. Specific conditions for
discarding:

1. The triggering pattern has been confirmed misattributed (rollback already
   handled this)
2. The category has been redesigned and the old constraint no longer maps to
   any current decision type
3. The constraint was a first-generation response that has been superseded by
   a more precise version covering the same risk (compaction handles this)
4. The constraint has been untested for more than five consecutive windows
   with no prospect of becoming testable

Discarding a constraint is not the same as forgetting the problem it addressed.
The history of why the constraint existed should be preserved in an archive,
not active governance. Active governance records contain constraints that are
currently applicable; history records contain the reasoning behind expired ones.
The distinction matters because an active record that includes too many expired
constraints becomes unreadable — which has the same effect as no record at all.

**When forgetting is wrong:**

Not all old constraints should be retired on a schedule. A constraint in a
high-consequence category should be retained even if untested, as long as the
conditions that could trigger the original failure mode still exist. The
relevant question is not "has this been tested recently?" but "if this
constraint were absent, would the original failure mode be possible?" If yes,
the constraint should be renewed, not retired, even with no recent testing.

**Condition observability requirement:**

The question "do the conditions that could trigger the original failure mode
still exist?" must be answerable by observation, not by reasoning alone. If
the only way to assess whether the condition persists is to reason through
a chain of assumptions — rather than to observe an indicator directly — then
the retention decision is operating under B1 or B5 boundary conditions (evidence
below observability threshold; scope outside observation model).

When a "when forgetting is wrong" assessment cannot be made observably, the
default is: retain the constraint and treat the retention as a
`low_confidence_proceed` with an explicit re-evaluation trigger. Do not use
unverifiable reasoning chains to conclude the condition has passed — that
conclusion cannot be falsified.

The practical test: before renewing a constraint on the grounds that its
triggering conditions persist, identify the specific observable indicator
that would confirm those conditions. If no such indicator can be named, the
renewal is based on assumption, not evidence. The renewal may still be correct,
but it should be tagged with lower confidence, not stated as confirmed.

**`low_confidence_proceed` renewal and expiry discipline:**

`low_confidence_proceed` is a legitimate response to unverifiable retention
conditions — but it is not a free carry-forward. Without explicit expiry
discipline, it becomes a softer form of silent indefinite retention: the
constraint persists, the uncertainty is acknowledged, and neither is ever
resolved.

Required conditions for a `low_confidence_proceed` retention tag to remain
valid:

1. **Explicit re-evaluation trigger:** a named condition that, when observed,
   requires re-assessment. "At next periodic review" is not a trigger — it is
   a schedule. The trigger must be an observable condition, not a calendar date.

2. **Maximum carry duration:** a `low_confidence_proceed` retention that has
   not reached its re-evaluation trigger within two consecutive observation
   windows automatically converts to a required re-evaluation. The carry does
   not silently extend.

3. **Re-evaluation must produce a different state:** the re-evaluation cannot
   produce another `low_confidence_proceed` on the same basis. If the
   observability gap that triggered the original low-confidence tag has not
   been resolved, the constraint must be either retired to archive (with
   documented reasoning) or escalated as a B1 boundary condition requiring
   explicit `hard_stop` or `escalate` response.

A second `low_confidence_proceed` on the same constraint, issued on the same
unresolvable basis as the first, is silent carry-forward with extra steps.
The second tag is not permitted unless the re-evaluation produced new
information that partially resolved the original observability gap.

---

## System value function: when learning and forgetting conflict

The preceding sections define learning mechanisms (add constraints when
patterns confirm failure modes) and forgetting mechanisms (remove constraints
when conditions no longer hold). These can be triggered simultaneously on
the same category. When they are, the system must choose. That choice
reveals the system's implicit value function — what it considers more costly
to get wrong.

**The conflict case:**

Learning is triggered when a deviation pattern has accumulated to the
Enforced tier. Forgetting is triggered when a constraint in the same category
has been untested for three or more windows and its retention condition cannot
be confirmed observably.

Both triggers are valid. One says: "this category needs a new constraint."
The other says: "an existing constraint in this category may no longer apply."
Applied simultaneously without a priority rule, they produce incoherent
governance: adding a constraint to a category while simultaneously removing
an unvalidated one, with no guarantee the removed constraint and the new
constraint are actually independent.

**The explicit priority rule:**

When learning (add constraint) and forgetting (remove constraint) are
simultaneously triggered on the same or overlapping category:

**Forgetting evaluates first. Learning evaluates second, on the post-evaluation
baseline.**

The reason is asymmetric error cost:

- Adding a constraint on top of an invalid existing constraint produces
  compounded over-constraint. Two wrong constraints in the same category
  are harder to diagnose and unwind than one.
- Removing a constraint that should have been retained, when a new constraint
  is about to be added, produces a clean baseline — and the new constraint is
  evaluated against that baseline, not against accumulated historical noise.

The priority rule does not mean forgetting wins. It means forgetting is
evaluated first to establish whether the baseline is clean. After evaluation:

- If the existing constraint is confirmed valid: learning proceeds against a
  validated baseline. Both constraints coexist only if confirmed independent.
- If the existing constraint is retired: learning proceeds against a clean
  baseline. The new constraint is not contaminated by the removed one.
- If the existing constraint is tagged `low_confidence_proceed`: the new
  constraint proceeds but is flagged as operating in a contested zone.
  Future recurrence in this category must distinguish between "new constraint
  is wrong" and "old constraint removal was wrong" before re-examination
  concludes anything.

**What the priority rule makes explicit:**

This system considers over-constraint a more persistent governance failure
than under-constraint. The reasoning: under-constraint in a single window
produces a detectable deviation. Over-constraint accumulates silently —
each constraint that references another, each decision justified by multiple
overlapping zones, each reviewer who reasons around more rules than necessary.
Silent accumulation is harder to detect and harder to reverse than a single
missed deviation.

This is not a claim that under-constraint is acceptable. It is a claim about
which error the detection mechanisms are better positioned to catch. The
deviation accumulation rule catches under-constraint within three windows.
Over-constraint requires periodic direct review and explicit measurement of
exploration cost. Given asymmetric detectability, the default should protect
against the harder-to-detect error — which is over-constraint.

**When the priority rule should not apply:**

In high-consequence, low-entropy categories where the cost of under-constraint
is irreversible: learning takes priority and forgetting is deferred until after
the new constraint is established. The threshold for this override must be
documented at the time of the decision, not applied post-hoc. Undocumented
overrides are not overrides — they are unrecorded priority violations.

**System personality as an observability artifact:**

The priority rule — forgetting first, learning second; protect against
over-constraint because it is harder to detect — is not an arbitrary preference.
It is derived from the asymmetry in the detection infrastructure: the deviation
accumulation rule catches under-constraint within three windows; over-constraint
requires periodic direct review and explicit exploration cost measurement.

But this derivation has a consequence that adopters should understand: the
system's behavioral lean is not fully external. The system will, over time,
tend toward:

- Earlier retirement of untested constraints
- Later addition of new constraints
- Preference for preserving decision mobility over decisional stability

This is not a design error. It is the system's personality emerging from what
it can and cannot see reliably. A system that defaults to protecting against
the error it cannot detect will, by that default, exhibit a consistent lean
in its decisions — even when no single decision reflects explicit preference.

This means: the system's observability architecture is also its character
architecture. The two cannot be fully separated. What the system finds hard
to detect, it will systematically underweight. What it finds easy to detect,
it will systematically overweight. The value function makes this explicit so
that adopters can assess whether the lean is appropriate for their domain —
rather than discovering it post-hoc as a pattern of seemingly neutral decisions.

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

---

## Terminal condition: the honest limit

This system can enforce the following:

- **No silent failure:** non-response, drift, pattern, and accumulation all
  produce detectable and required downstream effects
- **No silent bias:** baselines, priorities, and the system's own personality
  are required to be explicit and subject to re-examination
- **No cost-free escape:** deferral, legitimization, and override all leave
  traces; traces have expiry and consequence

What this system cannot do — and what no observation-bounded system can do:

**A failure that has not yet produced an observable signal cannot be governed.**

A latent design flaw, a long-tail interaction, an edge case that has never
appeared, a failure mode that only manifests under conditions the system has
not encountered — these exist outside the observation model. They are not
deferred or low-confidence; they are, at this moment, unnamed.

The system's response to this limit is honest and specific:

1. **Naming is the threshold.** Once a failure mode is named — by any mechanism,
   including external audit, near-miss, or deliberate exploration — it enters
   the observation model. From that point, silence is no longer permitted.
   The threshold is recognition, not occurrence.

2. **Forced exploration expands the boundary.** The invisible zone response
   (exploration with falsifiability requirement, external audit, risk acceptance)
   exists precisely to reduce the surface area of the unnamed. Exploration does
   not eliminate unknowns; it converts some unknowns into named risks with
   observable indicators.

3. **The system is designed to shrink the unnamed zone, not to claim it is
   empty.** A claim that the system has no unnamed failure modes is not a
   governance achievement — it is a signal that the exploration function has
   stopped working, or that reviewers have stopped looking beyond the existing
   observation model.

The final statement of this protocol's scope:

**Everything that has been named and observed: governed. Everything that remains
unnamed: a boundary condition of type B5 (scope outside observation model),
requiring the invisible zone response at the moment of recognition. Until
recognition: genuinely outside the protocol's authority.**

This is not a failure of design. It is the honest terminal condition of any
system that governs by observation. The aim is not to extend governance to the
unobservable. The aim is to ensure that the moment something becomes observable,
it cannot remain ungoverned.
