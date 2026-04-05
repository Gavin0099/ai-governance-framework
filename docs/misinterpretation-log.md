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

---

## How to add an entry

```
### YYYY-MM-DD — <short description>

**Affected field:** repo_readiness_level | closeout_activation_state | activation_recency | reviewer mapping
**Misinterpretation type:** over-reading | under-reading | category confusion | decision leak
**What was observed:** <what the reviewer/adopter did or concluded>
**What the field actually means:** <the correct interpretation>
**Correction applied:** <doc update, code change, or no action>
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

---

## Log entries

*(empty — observation phase begins after commit 48c2d6b)*

---

## Pending watch items

These are predicted misinterpretation risks that have not yet been observed.
Move to log entries when/if they occur in practice.

| Field | Predicted misread | Status |
|-------|-------------------|--------|
| `observed/recent` | Interpreted as "healthy" or "actively maintained" | watch |
| `pending` | Interpreted as "almost activated" or "nearly ready" | watch |
| `observed/stale` | Root cause assumed to be adoption-stopped without checking wiring | watch |
| `activation_state` (any) | Used to influence verdict classification or memory promotion | watch |
| `repo_readiness_level=3` | Interpreted as "governance is working correctly" | watch |
| `activation_state` (any) | Ignored entirely because "can't be used for decisions" | watch |

---

## Model expansion trigger rule

A new dimension (e.g. `recent_closeout_quality`) is justified when:

1. A specific misinterpretation appears in the log **at least twice** from
   different contexts, AND
2. The existing three-dimension model cannot address it through documentation
   alone, AND
3. The cost of the misinterpretation is higher than the complexity cost of
   adding the new dimension.

Theory alone is not sufficient. First observed instance goes to "watch".
Second confirmed instance from a different context triggers a proposal.
