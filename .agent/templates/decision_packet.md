# Decision Packet

## identity

- task_id:

## allowed_actions

- read implementation packet
- read review packet
- choose one decision value
- state allowed next action
- state safe claim and unsafe claims

## forbidden_actions

- commit
- push
- run destructive commands
- treat Reviewer ACCEPT as DONE
- treat Reviewer ACCEPT as push allowed
- claim selected tests passed means production ready

## inputs

- implementer_status: DONE | PARTIAL | BLOCKED
- reviewer_verdict: ACCEPT | CHANGES_REQUESTED | BLOCKED

## decision

- decision: ACCEPT_FOR_COMMIT | CHANGES_REQUESTED | BLOCKED | DISCARD
- reason:
- allowed_next_action:
- commit_allowed: false
- push_allowed: false

## required_output

- task_id
- implementer_status
- reviewer_verdict
- decision
- reason
- allowed_next_action
- commit_allowed
- push_allowed
- safe_claim
- unsafe_claims_to_avoid

## safe_claim

-

## unsafe_claims_to_avoid

- Reviewer ACCEPT means DONE.
- Reviewer ACCEPT means push allowed.
- Selected tests passed means production ready.
- Commit candidate means production ready.
- Review packet presence proves semantic correctness.

## claim_ceiling

- may_claim:
  - decision status for the reviewed packet set
  - candidate_for_commit when decision is `ACCEPT_FOR_COMMIT`
- must_not_claim:
  - DONE from Reviewer ACCEPT
  - push allowed from Reviewer ACCEPT
  - production readiness from selected tests

## reviewer_accept_rule

Reviewer ACCEPT only means candidate_for_commit when the decision is `ACCEPT_FOR_COMMIT`. It does not mean DONE, does not mean push allowed, and does not bypass human approval for commit or push.

## human_approval_gate

Commit and push remain disallowed unless explicit human approval changes `commit_allowed` or `push_allowed` in a later authorized step.

## token_discipline

- max_decision_packet_words: 300
- include_only:
  - task_id
  - implementer_status
  - reviewer_verdict
  - decision
  - allowed_next_action
  - blockers
  - safe_claim
  - unsafe_claims_to_avoid
- do_not_restate_full_task_history: true
- do_not_paste_full_diff: true
