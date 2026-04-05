# Learning Stability

> Version: 1.0
> Related: docs/learning-loop.md, docs/falsifiability-layer.md

---

## Purpose

A system that changes too readily in response to every observed signal is not
learning — it is oscillating. Oscillation looks like learning because changes
keep happening, but the system does not converge; it drifts in response to
noise.

This document defines when the system should resist changing, how to detect
whether changes are accumulating into drift rather than improvement, and what
to do when the learning system itself appears to be over-correcting.

The goal is not to prevent learning. It is to ensure that changes are
driven by genuine signal, not by the availability of explanations.

---

## When NOT to change

The following conditions are each independently sufficient to justify
`no_change_justified` as the outcome of a falsification review:

**1. The failure is isolated and non-repeating.**
A single falsification event with no prior pattern in the same category
is weak evidence for a structural problem. Document it, watch for recurrence,
do not change the model on a single data point.

**2. The failure is explained by execution rather than model.**
If the falsification condition was triggered by a specific implementation
mistake, environment issue, or process error — rather than a wrong assumption
in the model — the model does not need to change. Fix the execution; note the
distinction explicitly.

**Root cause classification reliability:** Root cause classification is itself
an inference, not an observation. Before treating "this was an execution
failure" as settled, ask: what evidence supports this classification, and what
would we expect to see if the classification is wrong? When root cause
confidence is low, the appropriate response is `investigation_pending`, not
`no_change_justified`. Premature root cause closure moves over-correction one
layer upstream — from wrong response to wrong attribution — and is harder to
detect because the reasoning appears complete.

Three classification states:
- `cause_identified`: specific mechanism named, evidence cited, falsifiable
- `cause_suspected`: plausible mechanism, insufficient evidence to confirm
- `cause_unknown`: failure observed, no reliable causal inference yet

Only `cause_identified` supports `no_change_justified` for execution or
environment failures. `cause_suspected` should be treated as `investigation_pending`.
`cause_unknown` should be documented without a causal claim.

**3. The proposed change shifts uncertainty without reducing it.**
If the direction check (did this reduce uncertainty or move it?) cannot be
answered affirmatively, the change does not improve the system. Defer the
change and identify what would need to be true for it to represent a genuine
improvement.

**4. Two observation windows have passed without recurrence.**
If a falsification condition was observed once and has not recurred in the
following two observation windows, the original condition may have been
transient. Document it as resolved-by-time, not as a persistent problem.

**5. The change would destabilize a mechanism that is otherwise working.**
If a proposed change to address one failure type would increase the error rate
for other failure types (as evidenced by prior log data), the change is not
net-positive. Stability of working mechanisms is a legitimate reason to
preserve them.

---

## How to detect over-correction

Over-correction is harder to detect than under-correction because it looks
like responsiveness. These are the signals to watch for:

Signals are classified as **advisory** (informs review; does not block
proposals) or **executable** (triggers a required action). A signal that
is treated as executable when it should be advisory produces over-reaction;
one treated as advisory when it should be executable allows drift to continue
undetected.

**Signal 1 (advisory): Change rate increasing without log entry rate increasing.**
If the model is changing more frequently but the number of observed
misinterpretations is staying the same or increasing, the changes are not
addressing the actual failure source. Advisory: does not block proposals, but
should prompt a direction check on the last three accepted changes before the
next one is evaluated.

**Signal 2 (executable): The same failure recurs after two responses at the same level.**
If `doc_updated` has been applied to the same failure type twice (matched at
same-class or stricter, per the taxonomy in learning-loop.md) and the failure
still recurs, escalate to `model_adjusted` review before applying a third
`doc_updated`. Executable: the next response cannot be `doc_updated` without
an explicit argument for why a third documentation change would succeed where
the previous two failed.

**Signal 3 (executable): Skepticism zones accumulating without retirement.**
If multiple skepticism zones have been established and none have been retired,
the system is becoming increasingly restrictive without evidence that
restriction is improving outcomes. Executable: any skepticism zone older than
three observation windows without a retirement evaluation must be reviewed
before a new zone is opened.

**Signal 4 (advisory): The most recent change functionally reversed a previous change.**
Oscillation manifests as alternating adjustments. A functional undo is broader
than an explicit reversal: if the new change makes the prior change's decision
logic inapplicable, it is a functional undo even if it does not explicitly
remove prior text. Advisory: document the reversal axis; does not block the
change, but requires the change note to acknowledge and justify the reversal.

**Signal 5 (advisory): Proposals are being rejected at a higher rate than accepted,
but high-cost failure rate is not declining.**
A rising rejection rate is only an over-correction signal if it is not
correlated with declining severe failures. If rejection rate rises and
high-severity misinterpretations decrease, the gate is working. If both rise
together, or if rejection rises while failure severity is flat, the gate may
be miscalibrated. Advisory: flag for gate calibration review; does not block
proposals.

---

## The stability check

At each observation window close, in addition to the learning loop checklist:

- [ ] Has the change rate increased without a corresponding decrease in
      misinterpretation frequency? (Signal 1)
- [ ] Is any failure type still recurring after two `doc_updated` responses?
      (Signal 2 — escalate to `model_adjusted` review)
- [ ] Are any skepticism zones overdue for retirement review? (Signal 3)
- [ ] Did the last change in any category reverse a previous change? (Signal 4)
- [ ] Is the proposal rejection rate trending upward over consecutive windows?
      (Signal 5 — review gate calibration)

If two or more signals are present, run a stability review before the next
proposal is accepted. A stability review is not a freeze — it is a deliberate
pause to assess whether the current pattern of changes is converging or
oscillating.

---

## What a stability review produces

A stability review must produce one of three outcomes:

| Outcome | Meaning |
|---------|---------|
| `converging` | The pattern of changes is reducing misinterpretation frequency; continue |
| `oscillating` | Changes are reversing each other or not reducing frequency; identify the oscillation axis and resolve it before continuing |
| `stable_noise` | The system is responding to noise rather than signal; raise the evidence bar for the next observation window |

A stability review is itself subject to the observation / conclusion separation
rule: the outcome must be supported by log data, not by the reviewer's
impression of how things are going.

---

## The relationship between stability and learning

Stability is not the opposite of learning. A stable system is one where
changes are driven by genuine signal and accumulate into consistent direction.
An unstable system changes frequently but without convergence.

The goal is:

**Fewer changes, each of which is more likely to be correct.**

Not:

**Maximum responsiveness to every observed signal.**

A system that reacts to every signal is not highly adaptive — it is poorly
calibrated. Treating responsiveness as intelligence, correction volume as
learning quality, or gate strength as governance quality are each forms of
the same error: confusing activity for progress.

A system that changes less because it has strong confidence in its current
model is healthy. A system that changes less because it has stopped observing
is not. The distinction is in whether untested assumptions are being named and
monitored, not in the change rate itself.

---

## Calibration over time

The evidence thresholds in this framework (two instances for standard trigger,
one for high severity, three recurrences for medium severity re-evaluation)
are starting calibrations — not permanent values.

If the system consistently produces too many false positives (skepticism zones
established for noise), raise the instance threshold.

If the system consistently misses genuine structural problems (failures recur
without skepticism zones forming), lower it.

Threshold calibration is itself a learning loop outcome and requires the same
falsifiability standards: what would we observe if the current threshold is
wrong, and what would we change if we observed it?
