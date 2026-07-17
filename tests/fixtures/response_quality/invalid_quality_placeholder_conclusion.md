mode: VALIDATION
mode_source: validation_command
task_authority: user_request
conclusion: TBD
recommended_action: none
next_action: none
claim_ceiling:
  - structural validation only
not_claimed:
  - semantic correctness
evidence_refs:
  - command: python -m pytest tests/test_response_envelope_validator.py
    result: PASS
