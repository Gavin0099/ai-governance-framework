# Run State

## identity

- task_id:
- run_id:
- repo:
- worktree:
- branch:
- base_commit:
- loop_mode: lite_loop | full_loop

## current_stage

- stage: task_created | implementation_in_progress | implementation_received | review_in_progress | review_received | decision_ready | closed | blocked
- stage_owner: main_thread | implementer | reviewer | human
- last_updated_at:

## allowed_actions

- record pending implementer or reviewer state
- record artifact paths and packet paths
- record polling target thread ids
- record current stage and next required action
- record commit and push authorization flags

## forbidden_actions

- modify implementation files
- perform automatic polling
- start a daemon
- commit
- push
- claim runtime enforcement exists
- claim reviewer acceptance means DONE

## participants

- main_thread_id:
- implementer_thread_id:
- reviewer_thread_id:
- human_owner:

## packet_paths

- task_packet:
- implementation_packet:
- review_packet:
- decision_packet:
- patch_path:
- artifact_path:

## pending_state

- implementer_status: not_started | pending | done | partial | blocked | not_applicable
- reviewer_status: not_started | pending | accept | changes_requested | blocked | not_applicable
- next_required_action: implement | send_to_reviewer | poll_reviewer | produce_decision | request_human_commit_approval | request_human_push_approval | close | blocked_by_tool_access | none
- blocker:

## auto_advance_policy

- read_only_gates_allowed: true
- mutation_gates_allowed_without_human_approval: false
- implementation_received_requires: send_to_reviewer
- review_in_progress_requires: poll_reviewer
- reviewer_accept_requires: produce_decision
- blocked_tool_access_status: BLOCKED_BY_TOOL_ACCESS

## poll_policy

- strategy: exponential_backoff
- first_poll_after_seconds: 30
- backoff_seconds:
  - 30
  - 60
  - 120
- max_polls_per_read_only_gate: 3
- max_polls_per_orchestrator_turn: 1
- busy_polling_allowed: false
- stop_after_max_polls: true

## poll_state

- poll_count: 0
- last_poll_at:
- next_poll_after:
- next_poll_reason:

## authorization

- commit_allowed: false
- push_allowed: false
- destructive_action_allowed: false
- external_publication_allowed: false

## required_output

- task_id
- run_id
- loop_mode
- current_stage
- participants
- packet_paths
- pending_state
- poll_policy
- poll_state
- authorization
- claim_ceiling
- not_claimed

## claim_ceiling

- may_claim:
  - recorded orchestration state
  - pending implementer or reviewer status
  - artifact paths known to the main thread
  - commit and push authorization flags as recorded
- must_not_claim:
  - automatic polling is implemented
  - daemon behavior exists
  - checker enforcement exists
  - reviewer acceptance means DONE
  - commit or push is allowed when authorization flags are false

## human_approval_gate

- required_before:
  - changing loop mode after implementation starts
  - expanding scope
  - committing
  - pushing
  - starting background automation
  - treating `candidate_for_commit` as DONE

## token_discipline

- max_run_state_words: 400
- prefer_packet_paths: true
- prefer_artifact_paths: true
- do_not_paste_full_diff: true
- do_not_restate_full_task_history: true

## not_claimed

- runtime enforcement
- daemon
- automatic polling
- checker enforcement
- commit allowed
- push allowed
