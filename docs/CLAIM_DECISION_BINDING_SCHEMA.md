# CLAIM_DECISION_BINDING_SCHEMA

## Purpose
Bind checker output to reviewer decision so semantic-drift signals cannot be silently ignored.

## Canonical Shape
```json
{
  "checker_status": "pass|fail",
  "semantic_drift_risk": true,
  "claim_level": "bounded|parity|strong|unbounded",
  "enforcement_action": "allow|downgrade|block",
  "reviewer_override_required": true,
  "reviewer_response": {
    "action_taken": "accept|downgraded|blocked|override",
    "override_reason": "string|null"
  },
  "publication_scope": "public|local_only"
}
```

## Decision Coupling Rules
- Reviewer must provide `reviewer_response.action_taken`.
- If `enforcement_action` is `downgrade` or `block`, reviewer response is mandatory.
- If reviewer chooses `override`, `override_reason` must be non-empty and contain at least one of:
  - `evidence_ref:`
  - `risk_ack:`

## Local-Only Guard
- If `publication_scope=local_only`, then `claim_level` must not exceed `bounded`.
- Violation must be mapped to `enforcement_action=block`.

## Validity
A closeout is invalid if:
- schema fields are missing,
- reviewer response is missing,
- override exists without reason,
- override reason is weak (no `evidence_ref:` and no `risk_ack:` marker).

## Rationale
The objective is not only drift detection.
The objective is to prevent drifted claims from being adopted into reviewer decisions.
