# Misinterpretation Log

> Purpose: collect real misuse and misreading evidence from reviewer and
> adopter behavior. Used to determine when model expansion is justified.
>
> **Not a bug tracker.** This log records cases where the system's output
> was correctly produced but incorrectly interpreted.
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

A proposal that passes the gate is a candidate for evaluation. Passing the
gate does not mean the dimension will be added — it means the proposal has
sufficient substance to be worth reviewing.

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
