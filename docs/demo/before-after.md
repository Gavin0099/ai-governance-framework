# Before / After Demo: AI Coding With Governance

## Scenario
AI agent modifies a request handler and calls database API directly from handler code.

Project rule:
- `no_direct_db_access_from_handler`

## Before (No Governance Layer)
- AI output looks reasonable.
- Code compiles.
- Reviewer must manually discover architectural rule violation.
- High risk of incorrect merge under time pressure.

## After (With Governance Layer)
- `post_task_check` detects contract violation.
- Session verdict becomes `blocked`.
- Output includes exact violated rule and file location.
- Reviewer receives actionable remediation path.

### Example blocked output
```json
{
  "ok": false,
  "verdict": "blocked",
  "failure_code": "contract_violation",
  "violations": [
    {
      "rule": "no_direct_db_access_from_handler",
      "location": "src/handlers/user.py:42",
      "detail": "AI agent attempted to call db.execute() directly; project contract requires repository layer"
    }
  ],
  "remediation": "refactor to use UserRepository.find_by_id() per governance/RULE_REGISTRY.md"
}
```

## Why This Matters
- Governance output is reviewer-facing evidence, not an opaque pass/fail.
- Teams can enforce architecture constraints consistently across AI-generated changes.
- Decision remains human-owned; evidence quality is system-owned.
