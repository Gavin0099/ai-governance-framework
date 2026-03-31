# Onboarding Pass/Fail Criteria

> Status: **active**
> Created: 2026-03-30
> Applies to: Beta Gate condition 2

---

## Why this document exists

"Can the reviewer figure it out?" is not a measurable criterion.
This document converts it into observable, recordable checkpoints.

---

## Five observable checkpoints

### CP1: Entry point found
**Observable**: Reviewer navigates to `README.md`, `docs/start_session.md`,
or `governance_tools/adopt_governance.py` without being told these exist.

Pass: reached within 15 minutes of starting.
Fail: reviewer is still at repo root with no direction after 15 minutes.

---

### CP2: Minimum adoption path described
**Observable**: Reviewer can describe (not necessarily run) this flow:

> adopt → drift check → session_start → pre_task → post_task

in any words. Does not need to name the exact commands. Conceptual understanding counts.

Pass: reviewer articulates the sequence unprompted.
Fail: reviewer believes the framework is a static documentation set with no runtime.

---

### CP3: Core concepts distinguished
**Observable**: Reviewer can distinguish between:

- framework governance (this repo) vs. project governance (consuming repo)
- `governance_tools/` (tools you run) vs. `runtime_hooks/` (hooks that run per session)
- domain contract (what rules apply to a specific project) vs. rule packs (generic rule sets)

Pass: reviewer correctly identifies at least 2 of 3 distinctions without prompting.
Fail: reviewer treats everything as one flat documentation system.

---

### CP4: Drift detection understood
**Observable**: Given the scenario "you come back to a project after two weeks," reviewer
knows that `governance_drift_checker` exists and can explain what it checks for.

Pass: reviewer finds or describes the drift checker independently.
Fail: reviewer does not know how to verify governance health on a returning session.

---

### CP5: Produces one governance artifact
**Observable**: Reviewer runs or meaningfully attempts one of:

- `python -m governance_tools.adopt_governance` on a temp directory
- `python -m governance_tools.governance_drift_checker` on a repo
- A manual `session_start` on an example contract

Pass: artifact is produced or attempt is substantive (ran the command, understood the output).
Fail: reviewer does not reach the point of attempting any tool execution.

---

## Scoring

| CPs passed | Result |
|-----------|--------|
| 5 of 5 | Strong pass — Beta Gate condition 2 met |
| 3–4 of 5 | Pass — Gate met, record which CPs failed for onboarding improvement |
| 2 of 5 | Fail — Gate not met, blocker must be diagnosed and fixed |
| 0–1 of 5 | Fail — entry path needs significant rework |

---

## Gate override rules

Score-based results can be overridden by the following conditions.
An override takes precedence over the scoring table above.

| Condition | Override | Reason |
|-----------|----------|--------|
| CP5 (artifact production) fails | Automatic FAIL regardless of total score | Framework's core claim is that governance produces verifiable evidence. If onboarding cannot produce any artifact under realistic constraints, the claim cannot be verified. A 3/5 score that masks a CP5 failure misrepresents Gate status. |

**How to apply an override:**

Record the override explicitly in the reviewer run file:

```
Gate Verdict: FAIL
Override applied: CP5 automatic FAIL rule
Score-based result: X/5 (would have been: Pass / Fail)
```

Do not silently use the score-based result when an override applies.

---

## Blocker classification

When a reviewer fails a checkpoint, classify the blocker:

Use `docs/beta-gate/reviewer-signal-split.md` first to decide whether the run
failed at discoverability, interpretation, decision reconstruction, or
escalation judgment.

| Type | Description | Implication |
|------|-------------|-------------|
| **Conceptual** | Reviewer doesn't understand what the thing is for | Needs explanation or example, not restructuring |
| **Structural** | Reviewer cannot find the relevant file or tool | Entry path or README needs a clearer pointer |
| **Naming** | Reviewer finds the right thing but misreads its purpose | Name or heading needs clarification |
| **Friction** | Reviewer understands but cannot execute (missing dep, unclear command) | Tooling or quickstart needs a fix |

One blocker type = one targeted fix.
Do not refactor the whole framework to fix a naming issue.

---

## What does NOT count as a failure

- Reviewer reads files in a different order than expected
- Reviewer uses the wrong tool first, then corrects
- Reviewer asks clarifying questions about AI/governance theory (not framework mechanics)
- Reviewer takes longer than 60 minutes but still reaches pass criteria

The test is about whether they can get there, not how fast or how linearly.
