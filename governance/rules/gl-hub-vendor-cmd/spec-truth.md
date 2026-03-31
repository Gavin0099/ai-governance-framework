# GL Hub Vendor Command Spec Truth

Tasks involving GL Hub vendor command issuance or implementation must be validated
against the spec truth layer before a decision is considered valid.

- Do not issue a GL Hub vendor command without first confirming all required preconditions
  are satisfied (chip, command issue mode, state, timing, data structure).
- Do not assume that a command is valid because it appears in the spec table —
  the spec also defines ordering constraints, timing requirements, and forbidden inferences
  that are not visible from the command table alone.
- Do not hard-code the I2C slave address (SlvAddr) without confirming the circuit design.
- Do not issue HW_RESET before ISP completion and without waiting 100ms.
- Do not issue Get VAL1=04 without a preceding Set VAL1=05.
- Do not mix up the 44-byte (Set VAL1=04) and 12-byte (Set VAL1=05) data structures.
- Every GL Hub vendor command decision must carry policy refs in the format
  `<rule_id>@<version>` traceable to the spec truth rule files.
