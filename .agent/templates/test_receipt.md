# Test Receipt

## identity

- task_id:

## allowed_actions

- read task packet, implementation packet, and in-scope changed files
- run approved validation commands
- report exact command results
- identify skipped and not-run validation

## forbidden_actions

- edit files
- commit
- push
- run destructive commands
- run external publication steps
- claim selected tests passed means production ready

## scope_under_test

- files:
- behavior:

## commands

| Command | Result | Notes |
| --- | --- | --- |
|  | NOT RUN |  |

## required_output

- task_id
- scope_under_test
- commands
- results
- risks
- not_claimed
- recommended_next_step

## results

- passed:
- failed:
- skipped:
- not run:

## selected_test_limitation

Selected tests passed does not mean production ready.

## claim_ceiling

This receipt claims only the observed outcome of the commands listed above. It does not claim full regression safety, semantic correctness, production readiness, or behavior outside the tested scope.

## human_approval_gate

- required_before:
  - editing files
  - running broad regression beyond the approved scope
  - running destructive tests
  - mutating external systems
  - committing
  - pushing

## risks

-

## not_claimed

- production readiness
- semantic correctness
- full regression safety

## recommended_next_step

-

## token_discipline

- max_test_receipt_words: 500
- prefer_log_artifact_path: true
- paste_full_logs: false
- paste_full_logs_exception: explicit_user_request_or_blocker_context
