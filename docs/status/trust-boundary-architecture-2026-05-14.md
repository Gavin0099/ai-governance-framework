# Trust Boundary Architecture

As-of: 2026-05-14  
Scope: runtime roles and authority isolation

## Role Authority Matrix

| role | allowed | forbidden | escalation path | veto/override |
|---|---|---|---|---|
| planner | task decomposition, risk classification, plan artifact edits | direct external side effects, destructive actions | reviewer | none |
| coder | code/doc changes inside scoped targets, test execution | policy authority edits without review, irreversible external actions | reviewer -> auditor | none |
| reviewer | accept/reject changes, require rework, approve bounded compensating actions | direct production mutations | auditor | veto yes, override no |
| auditor | observe, attest evidence lineage, trigger freeze recommendation | direct code mutations, execution side effects | human owner | veto yes for release gate |

## Hard Boundary Rules

- No role may self-escalate authority class.
- Any action outside role allowlist => block + incident record.
- Override requires explicit human token and audit trail.
- Planner/Coder cannot approve their own irreversible actions.

## Authority Tokens

Each privileged action must attach:
- role id
- approval source
- expiry timestamp
- scope hash
