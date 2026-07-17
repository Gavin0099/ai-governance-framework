mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion: The fix is complete and the workspace is clean.
reason: needs review — the validator behavior changed, so a human must confirm before merge.
next_action: Re-run the focused test module, then hand the diff to the reviewer.
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: python -m pytest tests/test_response_envelope_validator.py
    result: PASS
