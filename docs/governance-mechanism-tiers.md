# Governance Mechanism Tiers

> Version: 1.0
> Related: docs/learning-loop.md, docs/learning-stability.md, docs/falsifiability-layer.md,
>           docs/misinterpretation-log.md, docs/decision-quality-invariants.md,
>           docs/anti-ritualization-patterns.md

---

## Purpose

As a governance framework matures, descriptive language and enforceable policy
begin to look identical on the page. Both are written carefully; both are
presented with reasoning; both use similar vocabulary. The difference is
operational: one can be checked at decision time and produces a required
action when violated; the other informs judgment and produces a better question.

Conflating them produces two failure modes in opposite directions:

**Over-reading:** Reviewers treat diagnostic principles as runtime rules,
applying them as gates when they were meant as prompts. This produces
over-constraint and ritual compliance with criteria that were never designed
to be enforced mechanically.

**Under-reading:** Reviewers treat enforceable rules as advisory guidelines,
giving them weight proportional to how persuasive they seem rather than
applying them consistently. This produces governance drift invisible to any
single reviewer.

This document maps every significant mechanism in the framework to one of
three tiers: **enforceable**, **diagnostic**, or **deferred**. The tiers
are not judgments of importance — a diagnostic mechanism may matter more than
an enforceable one. They are descriptions of current operational status.

**A mechanism's tier can change.** Tier upgrades require specifying what
additional instrumentation or evidence makes enforcement possible. Tier
downgrades require explaining why a previously enforceable mechanism can no
longer be reliably checked. Both are recorded in the promotion log at the
end of this document.

---

## Tier definitions

### Enforceable

A mechanism is **enforceable** when:

1. The check can be completed by reviewing log entries, verdict artifacts,
   or documented reviewer behavior — without requiring additional experiments
   or subjective assessment
2. A specific required action follows from a positive check result
3. The check is repeatable: two different reviewers given the same inputs
   would reach the same result

Enforceable mechanisms produce gates. An enforceable condition that is not
checked is a governance failure, not a judgment call.

### Diagnostic

A mechanism is **diagnostic** when:

1. It identifies a signal that should inform the next decision or review
2. The signal does not, by itself, determine what the next decision must be
3. Two reviewers may reasonably interpret the same signal differently

Diagnostic mechanisms produce questions. A diagnostic signal that is ignored
is a governance failure, but the required response is engagement with the
question — not a specific action.

**Advisory vs diagnostic distinction:** Some mechanisms in this framework are
explicitly labeled advisory (learning-stability.md, Signals 1, 4, 5). Advisory
and diagnostic are overlapping categories: advisory signals are always
diagnostic, but diagnostic mechanisms are not always advisory. A diagnostic
mechanism that an advisory signal is based on may have its own enforcement
rules (e.g., advisory influence must be traced even though the advisory signal
itself does not trigger required actions).

### Deferred

A mechanism is **deferred** when:

1. The problem the mechanism addresses has been named and understood
2. The mechanism cannot currently be made enforceable or reliably diagnostic
   due to missing instrumentation, insufficient baseline data, or
   calibration dependencies that are not yet governed
3. The deferred status is explicit, not implicit

Deferred mechanisms are not aspirational wishes. They are documented
acknowledged gaps with a promotion condition — what would need to be true
for the mechanism to move to diagnostic or enforceable status.

**Deferred mechanisms accumulate governance debt.** Each deferred item is
a gap that the framework's runtime authority does not cover. Deferred items
that have no plausible promotion path should be explicitly closed (with
reasoning) rather than left open indefinitely.

---

## Mechanism map

### Learning loop (docs/learning-loop.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Every observed failure requires a documented outcome (model_adjusted / doc_updated / no_change_justified / investigation_pending) | **Enforceable** | Silent non-response is a governance failure; checked at window close |
| `investigation_pending` must convert within next observation window | **Enforceable** | Open-ended investigation is indistinguishable from inaction |
| `doc_updated` that does not change reviewer behavior does not count as learning response | **Enforceable** | Checked by asking: would a reviewer encountering the same situation do something different? |
| Recurring failure after `doc_updated` requires re-evaluation of prior response, not reuse | **Enforceable** | Same-failure taxonomy determines match level; same location, different cause is NOT recurrence |
| Skepticism zone required when two proposals in same category fail with shared model-level root cause | **Enforceable** | Root cause must be in model layer, not execution or environment |
| Skepticism zone retirement after two consecutive successes | **Enforceable** | Requires explicit documentation |
| Direction check after any change (did this reduce uncertainty or move it?) | **Diagnostic** | Not a gate; a required question that should be answerable |
| Untested assumptions should be named and prioritized by impact on current decisions | **Diagnostic** | Naming is required; full investigation is not |

### Falsifiability layer (docs/falsifiability-layer.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Every accepted expansion proposal must specify a falsification condition | **Enforceable** | Condition must be specific, observable, time-bounded, decision-reversing |
| Observed falsification condition triggers documented re-evaluation | **Enforceable** | "We noticed but decided to continue" is valid if documented; silence is not |
| Guard against explanation drift: an explanation that explains away falsification must itself be falsifiable | **Diagnostic** | Required question; no specific action required unless the explanation cannot be falsified |
| Trajectory awareness: repeated falsifications in same category increase skepticism | **Diagnostic** | Informs proposal evaluation; does not block proposals automatically |

### Misinterpretation log (docs/misinterpretation-log.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Expansion proposal gate: all five questions must be answered | **Enforceable** | Proposals that cannot answer all five are returned without review |
| Counterfactual scaffold: all four fields required, including "least confident" | **Enforceable** | Scaffold with empty or non-decision-relevant "least confident" field has not been completed |
| Rejection reason required when status = rejected | **Enforceable** | Rejection without reason is indistinguishable from oversight |
| `framework` owner requires one-line justification explaining why reviewer/team cannot resolve it | **Enforceable** | Framework ownership must remain scarce |
| New evidence required to re-raise a previously rejected proposal | **Enforceable** | Repetition of same pattern without new context is a duplicate, not a re-raise |
| Observation vs conclusion separation: entries record what happened, not verdicts | **Enforceable** | Interpretive language test: could a reviewer with a different prior read this differently? |
| Semantic grouping: group by shared underlying misconception, not surface phrasing | **Diagnostic** | Over-grouping and fragmentation are both errors; exact boundary requires judgment |
| Sampling bias check: spike in one area → "what are we not looking at?" | **Diagnostic** | Required question at window close; no specific action required |
| Negative pressure validity: clean log is evidence of sufficiency only if actual interactions occurred | **Enforceable** | Fewer than 3 distinct reviewer interactions: window result may not be meaningful |
| Medium severity guard: 3+ recurrences in window → re-evaluate severity | **Enforceable** | Not re-classification; re-evaluation required |
| High-severity exception: single decision-boundary impact may trigger immediate review | **Enforceable** | High is reserved for decision boundary violations; when in doubt, mark medium |

### Learning stability (docs/learning-stability.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Signal 2 (executable): same failure after two responses at same level → escalate to model_adjusted review | **Enforceable** | Third `doc_updated` requires explicit argument for why it would succeed where two failed |
| Signal 3 (executable): skepticism zone >3 windows without retirement review → blocks new zone | **Enforceable** | New zone cannot be opened until overdue review is completed |
| Root cause for no_change_justified must be cause_identified (not cause_suspected) | **Enforceable** | cause_suspected → investigation_pending; cause_unknown → documented without causal claim |
| Classification confidence decay: trigger by N relevant observations without corroboration | **Diagnostic** | N is per-category; what counts as "relevant" requires per-category definition. Decay decision cannot be automated without calibrated thresholds (see Calibration governance below) |
| Signal 1 (advisory): change rate up without log rate down | **Diagnostic** | Advisory: informs direction check on last three accepted changes before next is evaluated |
| Signal 4 (advisory): functional reversal of previous change | **Diagnostic** | Advisory: change note must acknowledge and justify reversal axis |
| Signal 5 (advisory): rejection rate rising without high-severity failure declining | **Diagnostic** | Advisory: flag for gate calibration review |
| Advisory containment rule: listed behaviors not permitted based on advisory signals alone | **Enforceable** | Decision path compliance: advisory not cited in justification for restricted behaviors |
| Advisory influence tracing: reviewer cites advisory signal → must be logged | **Enforceable** | Tracing requirement covers explicit acknowledgment |
| Behavioral drift detection: decision distribution shifts in response to advisory-only periods | **Diagnostic** | Detection requires baseline + sample size; currently a detection hypothesis, not a control mechanism |
| Pre-decision bias detection | **Deferred** | Cannot be detected by tracing alone; requires distribution monitoring over time with sufficient baseline. Promotion condition: defined baseline and minimum sample threshold per category |
| Stability review when 2+ signals present: produces converging / oscillating / stable_noise | **Enforceable** | Must be supported by log data, not reviewer impression |
| Silent degradation signals A–E | **Diagnostic** | Require periodic direct review outside standard window cadence; not answerable by reviewing log alone. Cannot be made enforceable without defining what constitutes degradation per signal |

### Anti-ritualization patterns (docs/anti-ritualization-patterns.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Pattern detection signals (entries getting shorter, same phrases recurring, etc.) | **Diagnostic** | Signals that ritualization may be happening; require review, not automatic action |
| When ritualization confirmed: note in log as under-reading, identify mechanism adjustment | **Enforceable** | Confirmed ritualization requires a mechanism response, not behavioral correction of reviewer |
| Do not add new mechanisms to compensate for a ritualized one | **Enforceable** | A ritualized mechanism that gets a companion mechanism will produce two ritualized mechanisms |

### Decision quality invariants (docs/decision-quality-invariants.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Consistency invariant: same evidence → same decision | **Deferred** | Checking requires comparing decisions across reviewers on matched inputs; no current infrastructure. Promotion condition: reviewer agreement rate tracking on a sample of decisions per observation window |
| Robustness invariant: irrelevant variation → no decision change | **Deferred** | Requires counterfactual; not directly observable. Promotion condition: deliberate probing protocol defined and run at least once per N windows |
| Positive falsifiability: every accepted decision must have a condition under which it would be validated | **Diagnostic** | Can be checked at decision time by asking: "what specific outcome would constitute validation?" Currently a required question, not a gate, because positive falsifiability conditions have not been mandated in the proposal format |
| Misaligned success detection: decision space narrowing, evidence type convergence, exploration reduction | **Diagnostic** | Partially overlaps silent degradation signals A and B; requires periodic review outside standard cadence |

### Boundary crossing protocol (docs/boundary-crossing-protocol.md)

| Mechanism | Tier | Notes |
|-----------|------|-------|
| Boundary condition detection: recognizing when a decision is outside the observation model (B1–B5) | **Diagnostic** | Requires reviewer to recognize the condition; cannot be automated. Protocol applies after recognition |
| `defer_with_condition` response: boundary condition named, resolution condition specified, deadline set | **Enforceable** | Open-ended deferral without resolution condition is treated as avoidance; must satisfy all four genuineness conditions |
| `low_confidence_proceed` response: decision made with explicit boundary tag and re-evaluation trigger | **Enforceable** | Tag must be visible to future reviewers using this decision as precedent; used only when deferral cost is non-trivial |
| `escalate` response: specific question, specific deadline, external input sought | **Enforceable** | Escalation must name the boundary condition and ask a specific answerable question; offloading without a specific question is not escalation |
| `hard_stop` response: decision blocked until boundary condition resolves | **Enforceable** | Reserved for irreversible decisions under B1 or B2; not a general-purpose block for uncertain decisions |
| Deferral genuineness check: boundary condition named, resolution condition specific, deadline set, deferral itself falsifiable | **Enforceable** | A deferral that cannot satisfy condition 4 (falsifiability of the deferral) is avoidance |
| Boundary recognition calibration: reviewer can identify which of B1–B5 applies | **Deferred** | Cannot be verified without probing; Part D of adversarial test pack tests this. Promotion condition: probing protocol run at least once per N windows |

---

## Calibration governance

Several enforceable and diagnostic mechanisms depend on calibrated values
whose definition is not yet governed. These are distinct from deferred
mechanisms: the mechanism itself is operative, but a key parameter is
currently set by judgment rather than governed policy.

| Parameter | Used by | Current state | Governance gap |
|-----------|---------|---------------|----------------|
| Per-category N (relevant observations for decay trigger) | Classification confidence decay | Defined per reviewer at window close | Who approves N for a category? What triggers N revision? |
| "Relevant observation" definition per category | Classification confidence decay | Implicitly defined by reviewer | Not formalized; different reviewers may use different criteria |
| Minimum interaction threshold for negative pressure validity | Negative pressure rule | Currently "fewer than 3" | Based on initial calibration; no revision process defined |
| Evidence completeness relevance criteria | Evidence integrity caveat | Assessed at review time | No formal scope boundary; susceptible to post-hoc rationalization |
| Distribution baseline for behavioral drift | Behavioral drift detection | Not yet established | No baseline defined; mechanism cannot currently fire |
| Observation window size and end conditions | All window-close mechanisms | 10 interactions OR 30 days | Fixed at framework version; revision process not defined |

**Calibration governance gap:** The values above are currently set by
whoever performs the review at window close. This is appropriate for an
early framework, but as the framework matures, ungoverned calibration
values become a vector for gradual drift: reviewers adjust values
implicitly to reach preferred outcomes, without any mechanism to detect
or prevent it.

**Minimum governance for calibration values:** For each parameter above,
the framework should eventually specify:
1. Who has authority to set and revise the value
2. What evidence is required to revise it
3. What would falsify the current calibration

Until formal calibration governance exists, calibration values should be
documented explicitly in each window-close record — not left implicit.
Explicit documentation makes silent drift visible.

---

## Deferred item summary

Deferred items are not failures. They are named gaps. Each must specify a
promotion condition — what would need to be true for the mechanism to move
to diagnostic or enforceable status.

| Mechanism | Deferred because | Promotion condition |
|-----------|-----------------|---------------------|
| Pre-decision bias detection | Requires distribution baseline + sample size; tracing alone insufficient | Define baseline per category; specify minimum observation count required to detect drift signal |
| Consistency invariant | Requires reviewer agreement tracking on matched inputs | Define matched-input sampling protocol; run for one full observation window |
| Robustness invariant | Counterfactual not directly observable | Define deliberate probing protocol; specify cadence |
| Positive falsifiability (as gate) | Positive conditions not yet required in proposal format | Add positive falsifiability condition to expansion proposal gate; run for one window to assess burden |

---

## Promotion log

Record when mechanisms change tiers, with reasoning.

*(empty — mechanism tiers established at framework version 1.0)*

---

## Reading this document

This document is not a specification of what the framework should eventually
become. It is a snapshot of what each mechanism currently is.

A reader evaluating whether the framework is adequate for a given use case
should:

1. Check whether the enforceable mechanisms cover the failure modes they
   care about
2. Check whether the deferred gaps include anything they consider essential
3. Check whether the calibration governance gaps affect mechanisms they
   would rely on

A reader adopting the framework should understand: enforceable mechanisms
will be checked; diagnostic mechanisms will be engaged with; deferred
mechanisms are named gaps that adopters are absorbing by choosing to proceed.
