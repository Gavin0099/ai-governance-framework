# HUMAN-OVERSIGHT.md
**Human Escalation and Oversight Protocol - v3.1**

> **Version**: 3.1 | **Priority**: 2 (Safety Valve)
>
> Defines when to continue, when to escalate, and when to stop.
> All escalation behavior in other documents defers to this file.

---

## 1. Decision Classes

### 1.1 Continue

Agent may continue when:
- the task is bounded
- risk is low
- evidence can be gathered locally
- no meaningful human trade-off is being hidden

### 1.2 Escalate

Agent must escalate when:
- requirements are materially ambiguous
- more than one reasonable path exists with different trade-offs
- architecture impact is unclear but not yet a hard violation
- dirty worktree overlap or commit-scope ambiguity exists
- a safe partial path exists, but the next step requires human direction

### 1.3 Stop

Agent must stop when:
- a hard safety or architecture red line is triggered
- governance documents conflict materially
- correctness cannot be defended
- human authorization is required for a high-risk action

> **Do not treat all uncertainty as stop-worthy. Use escalate unless a true red line has been crossed.**

---

## 2. Escalation Procedure

When escalating:
1. state what is unclear
2. state why continuing unchecked is risky
3. propose one to three concrete options with expected impact
4. wait for human direction

No guessing. No silent direction choice under material ambiguity.

---

## 3. Stop Procedure

When stopping:
1. identify the triggering rule or red line
2. explain why safe continuation is not defensible
3. describe the nearest safe rollback or containment step
4. wait for human authorization

---

## 4. Authority Boundary

Agent may analyze, propose, implement, verify, and refactor within safe bounds.

Only a human may authorize direction under unresolved material uncertainty or true high-risk deviation.

---

## 5. State Recovery

After interruption:
1. re-read `memory/01_active_task.md`
2. re-verify `LANG / LEVEL / SCOPE`
3. restate the previous known task state before continuing

Do not assume prior governance state is still valid.

---

## 6. Audit Trail

Every meaningful task should leave a human-readable trace including:
- start/end or current status
- `LANG / LEVEL / SCOPE`
- bounded context
- key decisions
- applied guardrails
- trade-offs, escalations, or stop reasons

Records must be human-understandable and traceable to governance rules.

---

## 7. Final Principle

> **Autonomy ends where accountability begins.**
> **Escalation is for meaningful uncertainty; stopping is for defended impossibility or red-line risk.**
