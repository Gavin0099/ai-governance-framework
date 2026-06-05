mode: VALIDATION
mode_source: validation_command
task: response envelope fixture validation
task_authority: user_request
scope:
  - tests/fixtures/response_envelopes/valid_minimal.md
done:
  - fixture validates the minimal structural envelope
claim_ceiling:
  - static structural validation only
not_claimed:
  - semantic correctness
  - runtime enforcement
evidence_refs:
  - command: python -m pytest tests/test_response_envelope_validator.py
    result: PASS
risk:
  - evidence relevance is not validated
next_action: none
