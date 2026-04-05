# Learning Loop

> Version: 1.0
> Related: docs/falsifiability-layer.md, docs/misinterpretation-log.md

---

## Purpose

A system that can detect failure but does not change as a result of failure
is not learning — it is logging.

This document defines the minimal learning loop for this framework: what
must happen after a failure is observed, what form the minimum change takes,
and how repeated failures should shape future decisions.

The learning loop is not about punishment or blame. It is about ensuring that
observations produce updates, and that the system becomes different — not just
better-informed — as a result of experience.

---

## The three questions

### 1. Does every observed failure require a change?

**No.** But every observed failure requires an explicit decision about whether
to change.

The minimum response to an observed falsification event is a documented
decision with one of four outcomes:

| Outcome | Meaning | Required documentation |
|---------|---------|----------------------|
| `model_adjusted` | A dimension, threshold, or mechanism changed | What changed and why |
| `doc_updated` | Documentation was clarified but model unchanged | What was clarified and why that is sufficient |
| `no_change_justified` | Failure was examined and the current model is still correct | Why the observed failure does not invalidate the model |
| `investigation_pending` | Not enough information yet to decide | What information is needed and by when |

`investigation_pending` is time-limited. It must convert to one of the other
three within the next observation window. Open-ended investigation is
indistinguishable from inaction.

**Silent non-response is not allowed.** An observed falsification condition
with no documented outcome means the learning loop did not close.

---

### 2. What is the minimum form of change?

The minimum change that counts as a learning response is whichever of the
following applies:

**For `model_adjusted`:**
A specific, observable difference in how a dimension is defined, how a
threshold is set, or how a mechanism works — not a restatement of the
existing model with different wording.

**For `doc_updated`:**
A specific addition or revision to a document that changes what a reviewer
would do when encountering the same situation again. Rewording that does not
change behavior is not a learning response. If the same failure recurs after
a `doc_updated` response, the prior response must be re-evaluated — not
reused. Recurring failure after a response is evidence that the response
was at the wrong level, not just that the documentation needs more words.

**For `no_change_justified`:**
A written argument that addresses the specific failure mode observed, explains
why the existing model handles it correctly, and identifies what condition
would cause the model to be reconsidered. "The model is fine" is not
sufficient. "The model is fine because X, and if we observed Y it would not be"
is sufficient.

---

### 3. How should repeated failures change future decisions?

Repeated failures in the same category are evidence about the model's
structural weaknesses — not just individual incidents to be resolved.

**Trajectory shaping rule:** When two or more accepted proposals in the same
category have had their falsification conditions triggered:

1. The category becomes a **skepticism zone**: future proposals in the same
   area face a higher effective evidence bar. This is not a prohibition —
   it is a recognition that the model has been repeatedly wrong in this area
   and should be treated with corresponding caution.

2. Before establishing a skepticism zone, evaluate whether the failures share
   a root cause or only a surface category. Execution failures (bad implementation),
   environment failures (external conditions), and model failures (wrong assumption)
   all look like "category failures" but require different responses.
   A skepticism zone is only warranted when the shared root cause is in the model,
   not when two independent causes happened to affect the same area.

3. The pattern should be named explicitly: "We have had three proposals about
   activation state interpretation fail. Our model of how reviewers interpret
   activation may be systematically incorrect."

4. Before accepting the next proposal in a skepticism zone, the proposer
   must address the trajectory: why would this proposal succeed where
   previous ones failed?

**Skepticism zones do not persist indefinitely.** A zone can be retired when
two consecutive proposals in the same category succeed (falsification condition
not triggered after full observation window). Retirement requires explicit
documentation.

---

## What "learning" means in this system

Learning is not the same as knowing more. It is the system behaving
differently because of what it has observed.

A system that reads its log entries and then makes the same decisions as
before has not learned. A system that makes a different decision — even
if only about where to direct skepticism — has learned.

The minimum evidence of learning is any of the following:

- A decision was made differently than it would have been before the failure
- A category was treated with more skepticism than it would have been before
- A mechanism was adjusted based on observed failure, not theory
- An assumption was named as untested and placed under observation

If none of these apply after an observation window, the loop did not close.
Review the window checklist and confirm whether falsification signals were
checked and untested assumptions were named.

**Untested assumptions are signals, not obligations.** Naming an untested
assumption is useful; generating a backlog of assumptions that can never
be tested is not. When naming untested assumptions, prioritize: which
ones, if wrong, would most affect current decisions? The rest can be noted
without requiring immediate investigation.

**Direction check:** After any change, ask: did this reduce uncertainty,
or merely move it? A model adjustment that resolves one ambiguity by
introducing two others has not improved the system — it has rearranged it.
The direction check is not a gate; it is a question that should be
answerable after every accepted change.

---

## The learning loop in sequence

```
Proposal accepted with falsifiability condition
        ↓
Observation window runs
        ↓
Window close: check falsification conditions + untested assumptions
        ↓
   [No failure]                     [Failure observed]
       ↓                                    ↓
Name untested assumptions       Document: what changed?
Confirm model is still adequate  (model_adjusted / doc_updated /
Negative pressure applies        no_change_justified / investigation_pending)
                                            ↓
                                 If repeated failure in same category:
                                 Name as skepticism zone
                                 Require trajectory address for next proposal
```

---

## What the loop does not do

- It does not guarantee the model converges to correctness. Convergence
  requires that the falsifiability conditions are well-designed and that
  failure signals are genuine.
- It does not automate decisions. Every outcome in the loop requires a
  human decision with documentation.
- It does not eliminate the need for judgment. The loop structures where
  judgment is applied — it does not replace it.

---

## Relationship to other documents

| Document | Role in the loop |
|----------|-----------------|
| `misinterpretation-log.md` | Records observations and triggers falsification checks |
| `falsifiability-layer.md` | Defines what counts as a falsification condition |
| `anti-ritualization-patterns.md` | Identifies when the loop itself is being complied with ritually |
| `learning-loop.md` (this) | Defines what must happen after a falsification event |

The loop closes when an observation produces a documented outcome. It
remains open — and visible as open — until that happens.
