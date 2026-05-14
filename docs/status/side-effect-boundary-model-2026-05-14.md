# Side-Effect Boundary Model

As-of: 2026-05-14  
Purpose: make rollback realistic by classifying execution side effects.

## Action Classes

| class | definition | examples | auto-allowed | rollback strategy |
|---|---|---|---|---|
| reversible | can be fully reverted by deterministic command | temp file write, local draft artifact | yes | direct rollback |
| compensating | cannot be fully reversed, but can be compensated | PR comment, issue label change | yes (bounded) | compensating action |
| irreversible | external state change without reliable rollback | email sent, third-party API mutation | no (needs approval) | incident log + manual remediation |
| forbidden-autonomous | high-risk actions requiring explicit human gate | production DB write, destructive delete, credential rotation | no | block before execution |

## Checkpoint Boundary

Before any non-reversible action:
1. write state checkpoint
2. persist action intent
3. verify authority token
4. execute action
5. append outcome and compensation route

## Execution Record Template

```yaml
action_id: ""
timestamp_utc: ""
actor_role: "planner|coder|reviewer|auditor"
action_class: "reversible|compensating|irreversible|forbidden-autonomous"
action_summary: ""
checkpoint_id: ""
approved_by_human: false
result: "success|blocked|failed"
compensation_required: false
compensation_plan: ""
```

## Gate Rules

- `forbidden-autonomous` without human approval => hard block.
- `irreversible` in autonomous path => degrade/freeze required.
- repeated compensation failures => escalate to `S2+` incident.
