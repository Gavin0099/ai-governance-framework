mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion: CHANGES_REQUESTED
claim_ceiling:
  - guard_summary=completion_claim_allowed=True current_diff_b0_blocker_count=0
not_claimed:
  - safe to push
evidence_refs:
  - command: python -m governance_tools.memory_workflow --check --run-guard --fail-on-blocker
    result: PASS
  - command: python -m pytest tests/test_response_envelope_validator.py
    result: PASS
next_action: active_non_canonical_writer=0 test_evidence_linked_commit_mismatch=33 re-review f85d5560 2b7d81d1
