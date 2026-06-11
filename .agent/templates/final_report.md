# Final Report

## allowed_actions

- summarize completed approved scope
- list changed files
- report validation that was run or not run
- state risks and cannot-claim items

## forbidden_actions

- commit
- push
- run destructive commands
- claim selected tests passed means production ready
- claim unvalidated semantic correctness
- omit cannot-claim items

## required_output

- result
- capability_increased
- changed_files
- validation
- risk
- incidental_cleanup
- governance_surface_change
- remaining_blocker
- cannot_claim_this_session

## claim_ceiling

- may_claim:
  - completed scope and explicit validation evidence listed in the report
- must_not_claim:
  - production readiness from selected tests
  - semantic correctness without human review
  - full regression safety without full regression evidence

## human_approval_gate

- required_before:
  - commit
  - push
  - destructive action
  - scope expansion

1. Result:
2. Capability increased:
3. Changed files:
4. Validation:
   - structural:
   - build:
   - semantic:
   - behavioral:
   - ext evidence:
5. Risk:
   - scope drift:
   - claim inflation:
   - evidence maturity:
6. Incidental cleanup:
7. Governance surface change:
8. Remaining blocker:
9. Cannot claim this session:
   -

## required_scope_summary

- git diff --name-only:
- git diff --stat:
- implementation summary:
- tests not run:
- risks:

## token_discipline

- max_final_report_words: 500
- prefer_artifact_refs: true
- include_only:
  - result
  - changed_files
  - validation
  - risks
  - not_claimed
  - next_action
- do_not_restate_full_task_history: true
