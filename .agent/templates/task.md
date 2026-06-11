# Governed Task

## identity

- task_id:
- authority: human_request | followup | hook_trigger | autonomous
- source:

## done_definition

- DONE =

## allowed_actions

- read approved task inputs
- modify files listed in `allowed_files`
- run commands listed in `required_commands`
- produce outputs listed in `required_output`

## forbidden_actions

- modify files outside `allowed_files`
- modify files listed in `forbidden_files`
- commit
- push
- run destructive commands
- claim selected tests passed means production ready

## write_scope

- allowed_files:
- forbidden_files:
- required_commands:
- loop_mode: lite_loop | full_loop

## required_output

- implementation_packet:
- test_receipt:
- review_packet:
- decision_packet:

## required_agents

- planner:
- implementer:
- tester:
- reviewer:

## claim_ceiling

- may_claim:
  - approved task scope and done definition
  - observed command results only
- must_not_claim:
  - production readiness from selected tests
  - semantic correctness unless explicitly reviewed
  - full regression safety unless full regression was run

## human_approval_gate

- required_before:
  - modifying files outside the allowlist
  - changing enforcement semantics, schemas, runtime behavior, or governance authority
  - running destructive commands
  - committing
  - pushing
  - publishing data outside the machine

## validation_expectation

- selected_tests:
- not_run:
- selected_tests_limitation: selected tests passed does not mean production ready.

## token_discipline

- loop_mode: lite_loop | full_loop
- max_task_words: 300
- prefer_artifact_paths: true
- paste_full_diff: false
- lite_loop_use_when:
  - low-risk documentation or template changes
  - tightly scoped main-thread implementation followed by independent reviewer review
- full_loop_use_when:
  - governance tools, hooks, validators, schemas, cross-repo rollout, or authority-changing work
  - likely modification of more than 3 existing files
  - tests or runtime behavior are in scope
  - cross-repo, submodule, or worktree rollout is in scope
  - long-running validation or many commands are required
  - A/B implementation comparison is needed
  - failure rollback cost is high
  - dirty worktree isolation is needed
