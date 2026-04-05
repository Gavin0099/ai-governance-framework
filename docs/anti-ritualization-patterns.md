# Anti-Ritualization Patterns

> Version: 1.0
> Related: docs/misinterpretation-log.md

---

## Purpose

Any governance mechanism that requires human thought can be complied with
formally without the thought occurring. This is ritualization: the form of
the mechanism is preserved while the substance is absent.

This document catalogs patterns where specific governance mechanisms in this
framework are most likely to ritualize, describes what ritualized compliance
looks like, and provides detection signals.

It does not add new rules. It describes how to tell when existing rules have
stopped working.

---

## What ritualization looks like

Ritualization is not malicious. It is the natural result of humans taking the
path of least cognitive resistance. A scaffold that was designed to make correct
thinking easier will, over time, also become a template for producing output
that looks like correct thinking without the thinking having occurred.

Signals that ritualization may be happening:

- Entries in the misinterpretation log are getting shorter over time
- The same phrases recur across entries from different reviewers
- The time between observation and log entry is consistently very short
- Counterfactual fields are filled with the same structure in every proposal
- Nobody has questioned a grouping decision in the current observation window

---

## Pattern catalog

### Pattern 1 — Scaffold filling without reasoning

**Mechanism:** Counterfactual scaffold in expansion proposal gate.

**Ritualized form:**
```
Alternative mechanism: Could be temporary behavior
Why this mechanism fails: Because it happened multiple times
```

**What makes this ritualized:** "Could be temporary" names no mechanism.
"Happened multiple times" is not a refutation of a mechanism — it is a
restatement of the observation.

**Detection signal:** The "Why this mechanism fails" field does not reference
any concrete system property (file, person, time range, count, or process).
If the refutation could be copy-pasted into any proposal without modification,
it is likely ritualized.

**Self-detection probe:** Which part of this reasoning are you least confident
about? If you cannot answer, or if the answer is "none of it", the reasoning
may not have been genuinely constructed.

---

### Pattern 2 — Ritual blind spot

**Mechanism:** Blind spot requirement in expansion proposal gate (question 4).

**Ritualized form:**
```
Unobserved area: Other parts of the system
```
or
```
Unobserved area: Modules not yet covered
```

**What makes this ritualized:** These statements are always true and require
no knowledge of the system to write. They identify nothing investigable.

**Detection signal:** Could another reviewer use this blind spot description
to actually investigate something? If the answer is no, it is ritualized.

**Self-detection probe:** Can you name a specific file, hook, or workflow
where this misinterpretation pattern might appear but has not been checked?
If not, the blind spot requirement has not been met substantively.

---

### Pattern 3 — Keyword-sanitized conclusions

**Mechanism:** Interpretive language test (observation vs conclusion).

**Ritualized form:**
```
Activation state was applied in a context where it influenced the outcome
of the review.
```

**What makes this ritualized:** No flagged words ("misused", "incorrectly")
appear, but "influenced the outcome" still encodes an interpretive judgment.
The entry has been keyword-sanitized without removing the embedded conclusion.

**Detection signal:** Can a reviewer with a different prior read this
statement and reach a different verdict about whether something went wrong?
If no, the statement is still encoding a conclusion.

**Self-detection probe:** What did the reviewer actually do, described
without any implication of wrongness? If that description is identical to
the submitted entry, the entry may be clean. If a "clean" version would
require removing important information, the entry may be conclusion-laden.

---

### Pattern 4 — Negative pressure without activity

**Mechanism:** Negative pressure rule ("no new entries = model is sufficient").

**Ritualized form:**
A reviewer closes an observation window noting "no new misinterpretations
observed" without having had any meaningful reviewer interactions during
the window.

**What makes this ritualized:** The negative pressure rule is only valid
when actual interactions occurred. Observing nothing because you did not
observe is not evidence of sufficiency — it is an absence of measurement.

**Detection signal:** How many distinct reviewer interactions occurred
during this observation window? If fewer than 3, the window result may
not be meaningful regardless of the entry count.

**Self-detection probe:** Name one reviewer interaction that occurred during
this window where a potential misinterpretation did not happen. If you cannot,
the window may not have had sufficient activity to support any conclusion.

---

### Pattern 5 — Severity inflation over time

**Mechanism:** Severity classification (low / medium / high).

**Ritualized form:**
Over successive observation windows, the proportion of `medium` entries
increases while no entries are ever reclassified or resolved. Every new
observation defaults to `medium` regardless of actual behavior observed.

**What makes this ritualized:** `medium` has become the default filing
category rather than a meaningful classification. The severity gradient
has compressed.

**Detection signal:** In the current log, is the distribution of
low/medium/high entries roughly what you would expect given the types of
misinterpretations observed? If almost all entries are medium, either the
system has unusually uniform misinterpretation severity (unlikely) or the
classification has ritualized.

**Self-detection probe:** For the last three entries you classified as
`medium`, could any of them have been `low`? If you cannot articulate why
they were not `low`, the `medium` classification may have been reflexive.

---

## What to do when ritualization is detected

Ritualization is not a violation to be punished — it is a signal that a
mechanism has become too easy to comply with formally. The correct response
is to adjust the mechanism, not blame the reviewer.

When a pattern is confirmed ritualized:

1. Note it in the misinterpretation log as an entry with
   `type = under-reading`, `owner = framework`.
2. Identify whether the mechanism needs a higher friction point, a
   sharper example, or a different probe question.
3. Update the mechanism. Do not just add more rules to the existing one —
   that increases burden without increasing signal.

**Do not add new mechanisms to compensate for a ritualized one.** A ritualized
mechanism that gets a new companion mechanism will produce two ritualized
mechanisms. Fix the original.

---

## The hardest ritualization to detect

The most dangerous ritualization is one where the reviewer genuinely believes
they are thinking, but the thinking is shallow.

This cannot be fully prevented by mechanism design. The only reliable signal
is external: another reviewer who reads the output and finds it unconvincing,
or a later observation that contradicts what the shallow reasoning predicted.

This is why the observation window and reviewer diversity matter more than
any single mechanism: shallow thinking tends to produce consistent-looking
outputs that only diverge from reality under stress or over time.
