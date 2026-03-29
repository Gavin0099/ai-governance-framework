# Entry Layer Justification

> Status: **incomplete — entry layer not yet justified**
> Created: 2026-03-30
> Constraint document: `docs/entry-layer-boundary.md`

---

## Purpose of This Document

This is a **counter-argument document**, not a feature proposal.

Its job is to establish whether the entry layer has an irreplaceable role in
the framework — or whether it is a nice-to-have visibility layer that belongs
outside the runtime.

If this document cannot be completed, the conclusion is:
**entry layer does not meet the bar for runtime integration. Do not proceed.**

---

## A. What the existing system already handles

### session_start already provides

- task level detection (L0 / L1 / L2) from task text and risk signals
- domain contract loading and domain gate (L0 short-circuit)
- rule pack loading with context-aware suggestions
- authority table validation
- risk signal override from prior drift check results
- change proposal with oversight requirement and expected validators
- domain validator preflight

### pre_task_check already provides

- PLAN.md freshness gate
- runtime contract (rules, risk, oversight, memory mode)
- architecture impact preview
- suggested skills and agent

### existing artifacts already provide

- `change_control_summary` — proposal-time change record
- `reviewer_handoff_summary` — review-facing evidence and trust signal
- `session_end` artifacts — post-session knowledge record
- `governance_drift_checker` — governance file health

---

## B. What gap the entry layer claims to fill

> **This section is incomplete. The gap has not been defined.**

Known candidate gaps (not yet evaluated):

- Visibility into whether a `tech-spec` artifact existed before session_start ran
- Traceability from a PR back to the original task spec
- Pre-session evidence that the change was scoped before implementation began

None of the above have been tested against the question:
**Does the absence of this visibility cause a wrong decision anywhere in the runtime?**

---

## C. Smaller alternatives not yet evaluated

Before accepting runtime integration, these must be ruled out:

| Alternative | Why it might be sufficient |
|-------------|---------------------------|
| Document-only convention | Teams write tech-spec, no machine checks needed |
| Offline observer (CLI only) | `workflow_entry_observer.py` runs as standalone audit tool, not part of runtime |
| Post-run reporting | Included in `reviewer_handoff_summary` after the fact |
| Pre-task evidence reuse | `pre_task_check` extended to accept an optional `--spec-file` flag |

---

## D. Why smaller alternatives are insufficient

> **This section is incomplete. No argument has been made.**

---

## E. Irreplaceability test

> **Neither question has been answered.**

**Q1: If entry layer never existed, what capability would the framework irreversibly lose?**

Answer: *unknown*

**Q2: Why can that capability not be addressed in `pre_task_check`?**

Answer: *unknown*

---

## Current conclusion

Entry layer has not met the bar for runtime integration.

`docs/entry-layer-boundary.md` constraints remain fully active.

This document should be completed before any of the following:
- re-adding `workflow_entry_observer` to `session_start`
- treating entry-layer observation states as policy inputs
- implementing E1–E4 from the suspended sprint items
