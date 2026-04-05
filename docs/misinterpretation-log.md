# Misinterpretation Log

> Purpose: collect real misuse and misreading evidence from reviewer and
> adopter behavior. Used to determine when model expansion is justified.
>
> **Not a bug tracker.** This log records cases where the system's output
> was correctly produced but incorrectly interpreted.
>
> **Entries record observations, not conclusions.** What was observed and
> what the field actually means are factual records. Severity, grouping, and
> expansion justification must be derived from entries during review — not
> embedded in the entry at write time. An entry that already contains its
> own expansion argument is a conclusion dressed as evidence.
>
> **Interpretive language test:** Before submitting an entry, ask: if a
> statement leaves no room for alternative interpretation, it likely encodes
> a conclusion. The test is not whether specific words appear ("misused",
> "incorrectly", "clearly" are signals but not the only ones) — it is
> whether the statement could be read differently by a reviewer with a
> different prior. Describe what was done and what outcome occurred;
> leave the verdict — whether that constitutes misuse — to review.
>
> **Expansion trigger:** patterns in this log are the primary evidence base
> for adding new dimensions (e.g. activation quality). Do not expand the
> model on theory alone.
>
> **Observation period:** begins at commit 608be20 (2026-04-05).
> Ends after 10 reviewer interactions OR 30 days, whichever comes first.
> After the window closes, review log entries and pending watch items
> to determine whether model expansion, documentation changes, or no action
> is warranted.

---

## How to add an entry

```
### YYYY-MM-DD — <short description>

**Affected field:** repo_readiness_level | closeout_activation_state | activation_recency | reviewer mapping
**Misinterpretation type:** over-reading | under-reading | category confusion | decision leak
**Severity:** low | medium | high
**What was observed:** <what the reviewer/adopter did or concluded>
**What the field actually means:** <the correct interpretation>
**Correction applied:** <doc update, code change, or no action>
**Resolution status:** doc_updated | training | ignored | requires_model_change | open
**Owner:** reviewer | team | framework
**Signal for model expansion:** yes | no | watch
```

---

## Entry types

| Type | Description |
|------|-------------|
| `over-reading` | Treating a weaker signal as a stronger guarantee (e.g. `observed` → "currently reliable") |
| `under-reading` | Ignoring a field because "it can't be used for decisions" |
| `category confusion` | Mixing structural level with activation state, or activation with quality |
| `decision leak` | Using activation state or readiness level to influence verdict or memory promotion |

## Severity levels

| Severity | Definition |
|----------|------------|
| `low` | Misread causes incorrect mental model but no incorrect action taken |
| `medium` | Misread leads to incorrect reviewer action (e.g. wrong triage path) |
| `high` | Misread directly impacts decision boundaries — e.g. activation state used to influence allow/deny or memory promotion |

**High-severity exception:** A single `high` severity event may justify earlier
intervention — doc hardening, code-level guard, or model expansion proposal —
without waiting for the standard two-instance threshold.

**Severity judgment rule:** `high` is reserved for misinterpretations that
directly affect decision boundaries: allow/deny behavior, memory promotion,
or policy precedence. All other misinterpretations default to `medium` or
`low`. Confusion, wrong mental model, or incorrect triage does not qualify
as high unless it produced or nearly produced a decision boundary violation.
When in doubt, mark `medium` — not `high`. The exception path must not become
the normal path.

**Medium severity guard:** `medium` indicates misinterpretations that require
observation and evidence accumulation — not a terminal classification. If the
same `medium` misinterpretation recurs in a short window (e.g., 3+ times within
the observation period), re-evaluate whether the severity should be escalated or
whether the owner assignment should change. Medium must not become a category
that entries enter and never leave.

**Semantic grouping rule:** When counting recurrences, group by semantic
category, not surface phrasing. Misinterpretations that differ in wording but
share the same root (e.g., "activation used as quality proxy", "activation used
as usage signal", "activation used as decision input" are all activation
boundary violations) count toward the same recurrence threshold. Surface
fragmentation must not be used — deliberately or accidentally — to avoid
reaching the trigger threshold. Grouping must be based on a shared underlying
misconception, not merely because entries involve the same field. Over-grouping
— merging entries that have different root causes to reach the threshold faster
— is the opposite error from fragmentation and equally invalid.

## Resolution status

| Status | Meaning |
|--------|---------|
| `doc_updated` | Misinterpretation addressed by updating documentation |
| `training` | Addressed by reviewer guidance or onboarding update |
| `ignored` | Determined to be acceptable ambiguity; no action taken |
| `requires_model_change` | Documentation cannot resolve it; model dimension needed |
| `open` | Not yet resolved |

Tracking resolution status prevents false positives in the expansion trigger:
the same misinterpretation appearing multiple times may reflect adoption lag
(doc was already updated) rather than a structural model gap.

## Owner

| Owner | Meaning | Responsible action |
|-------|---------|--------------------|
| `reviewer` | Individual behavior correction needed | The reviewer who logged the entry reviews the correct interpretation |
| `team` | Adoption or training gap | Team updates onboarding, training, or shared conventions |
| `framework` | Model or documentation change needed | Framework maintainer evaluates doc update or model expansion |

`owner` is assigned at log time, not after resolution. If resolution later reveals
a different owner was appropriate, update the entry. Unowned entries default to
`framework` since they require model-level attention to close.

**Framework owner guard:** When `owner = framework`, include a one-line
justification explaining why the issue is not resolvable at the `reviewer` or
`team` layer. Assigning `framework` without justification is a sign that the
entry was not triaged — not that the framework is responsible. Framework
ownership must remain scarce or it becomes a responsibility sink.

---

## Log entries

*(empty — observation phase begins after commit 608be20, 2026-04-05)*

---

## Pending watch items

These are predicted misinterpretation risks that have not yet been observed.
Move to log entries when/if they occur in practice.

| Field | Predicted misread | Severity if occurs | Status |
|-------|-------------------|--------------------|--------|
| `observed/recent` | Interpreted as "healthy" or "actively maintained" | medium | watch |
| `pending` | Interpreted as "almost activated" or "nearly ready" | low | watch |
| `observed/stale` | Root cause assumed to be adoption-stopped without checking wiring | medium | watch |
| `activation_state` (any) | Used to influence verdict classification or memory promotion | **high** | watch |
| `repo_readiness_level=3` | Interpreted as "governance is working correctly" | medium | watch |
| `activation_state` (any) | Ignored entirely because "can't be used for decisions" | low | watch |

---

## Expansion proposal quality gate

Before a triggered expansion proposal is evaluated, it must answer three
questions. Proposals that cannot answer all three are returned without review.

1. **What specific misinterpretation does this dimension address?**
   Name the log entry (or entries) that motivated the proposal. Theory
   alone is not a valid answer.

2. **Why is documentation insufficient to resolve it?**
   Describe what was tried (doc update, wording change, guard clause) and
   why it did not stop the misinterpretation from recurring.

3. **What is the risk of not adding this dimension?**
   Describe the expected harm — reviewer error rate, decision boundary
   violations, or specific failure modes — if the status quo continues.

4. **Name at least one unobserved but potentially relevant area.**
   Identify a part of the system that may have similar problems but has
   not appeared in the log — even speculatively. The area must be specific
   enough to be investigable by another reviewer: "other modules" does not
   qualify; "session_end vs pre_task_check mismatch under the same
   misinterpretation pattern" does. This is not a requirement to fix that
   area; it is a requirement to demonstrate that your observations do not
   exhaust the search space. If you cannot name anything specific, that is
   itself a signal worth examining.

A proposal that passes the gate is a candidate for evaluation. Passing the
gate does not mean the dimension will be added — it means the proposal has
sufficient substance to be worth reviewing.

**Counterfactual check (required before accepting):** The reviewer must
complete the following scaffold. A proposal that does not fill all three
fields has not passed the counterfactual check, regardless of how strong
the supporting evidence looks.

```
Observation:
<What the log entries show — factual, no verdict language>

Alternative mechanism:
<A concrete mechanism that could produce the same observations without
a structural model gap — e.g. "reviewer attention was focused on activation
issues this week", "a CI change caused a spike in verdict artifacts">

Why this mechanism fails to explain the data:
<Specific reason the alternative is implausible — not 'seems unlikely'
but 'the pattern appeared across 3 different reviewers over 4 weeks,
which attention bias cannot explain'>

Which part of this reasoning are you least confident about?
<Required. If you cannot answer this, the reasoning is likely shallow.
If the answer comes easily, it identifies where the proposal is most
vulnerable and should be examined first.>
```

Stating "this could be transient but given repeated occurrences it is
unlikely" does not satisfy the scaffold. A mechanism must be named and
then refuted. Possibility without mechanism is not a counterfactual.
If an alternative mechanism can be dismissed without referencing concrete
system behavior (specific files, runs, reviewer identities, time ranges),
it is likely too weak.

## Expansion proposal log

Record all proposals here, including rejections. Without this record,
the same proposal will be re-raised repeatedly, consuming review cycles
and obscuring whether the underlying problem has actually changed.

```
### YYYY-MM-DD — <proposal title>

**Triggered by:** <log entry or watch item reference>
**Proposed dimension:** <name>
**Status:** accepted | rejected | deferred
**Decision date:** YYYY-MM-DD
**Rejection reason / deferral condition:** <required if rejected or deferred>
```

**Rejection reason is required** when `status = rejected`. A rejection
without a reason cannot be distinguished from "we forgot to look at it".

**Deferred proposals** must specify the condition that would reopen them
(e.g., "reopen if `observed/recent` appears in log twice with
`requires_model_change`"). Open-ended deferrals are treated as rejections.

**History weight guard:** Past proposal decisions provide context but must not
prevent re-evaluation when new evidence emerges. A previously rejected proposal
may be re-raised if the log contains new entries that were not present at the
time of rejection. A rejection without new evidence is not a re-raise — it is
a duplicate. New evidence must introduce a previously unobserved context,
impact, or failure mode; repetition of the same pattern does not qualify.
Adding a weak log entry specifically to satisfy the "new evidence" requirement
is gaming the system — the entry must reflect a genuinely new observation, not
be constructed to justify a re-raise.

*(empty — no proposals yet)*

---

## Model expansion trigger rule

A new dimension (e.g. `recent_closeout_quality`) is justified when **any one** of:

**Standard path (two-instance rule):**
1. A specific misinterpretation appears in the log **at least twice** from
   different contexts (different repos, reviewers, or sessions), AND
2. The existing three-dimension model cannot address it through documentation
   alone (`resolution != doc_updated` for both instances), AND
3. The cost of the misinterpretation is higher than the complexity cost of
   adding the new dimension.

**High-severity exception:**
A single `high` severity entry (decision boundary impact) may trigger an
expansion proposal immediately, without waiting for a second instance.

**Not sufficient to trigger expansion:**
- Theory or predicted risk alone
- Two instances where `resolution = doc_updated` (adoption lag, not model gap)
- Reviewer confusion that was resolved by explanation without doc change

**Negative pressure rule:** The absence of repeated misinterpretations is
evidence that the current model is sufficient — expansion is not required.
"No new entries" is a valid and positive outcome of an observation window.
The default state is stability, not expansion. This rule is only valid when
actual reviewer interactions occurred during the observation window; absence
of observation is not evidence of sufficiency. A clean log with no reviewer
activity means nothing was measured, not that the model is working.
Observations may reflect reviewer attention bias: increased entries in one
category do not imply coverage of the overall system. A spike in one area
should prompt the question "what are we not looking at?" — not just
"what does this spike tell us?"

First observed instance → "watch". Second confirmed instance from different
context → proposal. High severity single instance → immediate review.

---

## Observation window end checklist

When the observation window closes, review these before deciding next steps:

- [ ] How many log entries exist?
- [ ] Are any entries `high` severity?
- [ ] Are any entries `requires_model_change`?
- [ ] Are any watch items still unobserved? (may indicate the risk was overstated)
- [ ] Did any `doc_updated` resolutions stop recurrence, or did the same
      misread appear again? (distinguishes adoption lag from model gap)
- [ ] Is the three-dimension model still adequate, or is a fourth dimension
      now justified by evidence?
