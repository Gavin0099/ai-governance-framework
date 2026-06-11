# Plan Receipt

## identity

- task_id:
- authority:
- source:

## done_definition

- DONE =

## allowed_actions

- read task inputs and in-scope files
- propose implementation plan
- define validation plan
- hand off to implementer

## forbidden_actions

- edit implementation files
- commit
- push
- run destructive commands
- claim implementation complete
- claim selected tests passed means production ready

## scope

- allowed_files:
- forbidden_files:
- non_goals:
- required_commands:

## required_output

- plan_summary:
- implementation_steps:
- validation_plan:
- handoff_target:

## implementation_plan

1.
2.
3.

## validation_plan

- targeted validation:
- not planned:
- selected-tests limitation: selected tests passed does not mean production ready.

## claim_ceiling

- plan readiness only
- no implementation claim
- no production readiness claim

## human_approval_gate

- approval_status: approved | required | blocked
- required_before:
  - scope expansion
  - enforcement/schema/runtime behavior change
  - destructive action
  - commit
  - push

## handoff

- next agent:
- handoff notes:

## token_discipline

- max_plan_receipt_words: 300
- prefer_artifact_refs: true
- include_only:
  - task_id
  - done_condition
  - allowed_files
  - forbidden_files
  - validation_plan
  - approval_gates
