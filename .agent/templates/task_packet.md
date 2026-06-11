# Task Packet

## identity

- task_id:
- repo:
- worktree:
- branch:
- base_commit:

## done_definition

DONE =

## allowed_actions

- read approved task context
- write files listed in `allowed_files`
- run commands listed in `required_commands`
- produce packets listed in `required_output`

## forbidden_actions

- write files outside `allowed_files`
- modify `forbidden_files`
- commit
- push
- run destructive commands
- claim selected tests passed means production ready

## write_scope

- write_scope:
- allowed_files:
- forbidden_files:
- loop_mode: lite_loop | full_loop

## non_goals

-

## required_commands

| Command | Required | Purpose |
| --- | --- | --- |
|  | yes |  |

## required_output

- implementation_packet:
- test_receipt:
- review_packet:
- decision_packet:

## hard_rules

- Do not edit files outside `allowed_files`.
- Do not modify `forbidden_files`.
- Do not commit.
- Do not push.
- Do not run destructive commands.
- Do not claim selected tests passed means production ready.
- Stop when DONE is reached.

## claim_ceiling

- may_claim:
  - approved task packet scope
  - observed results from required commands
- must_not_claim:
  - production readiness from selected tests
  - semantic correctness without review
  - commit allowed
  - push allowed

## human_approval_gate

Approval is required before scope expansion, enforcement/schema/runtime behavior changes, destructive actions, commit, push, or external publication.

## token_discipline

- loop_mode: lite_loop | full_loop
- default_loop_mode: lite_loop
- lite_loop_use_when:
  - low-risk documentation or template changes
  - no governance tool, hook, validator, schema, or cross-repo rollout change
- full_loop_use_when:
  - governance tools, hooks, validators, schemas, cross-repo rollout, or authority-changing work
  - likely modification of more than 3 existing files
  - tests or runtime behavior are in scope
  - cross-repo, submodule, or worktree rollout is in scope
  - long-running validation or many commands are required
  - A/B implementation comparison is needed
  - failure rollback cost is high
  - dirty worktree isolation is needed
- max_task_packet_words: 300
- prefer_artifact_paths: true
- full_diff_inline_allowed: false
- full_diff_inline_exception: explicit_user_request_only
