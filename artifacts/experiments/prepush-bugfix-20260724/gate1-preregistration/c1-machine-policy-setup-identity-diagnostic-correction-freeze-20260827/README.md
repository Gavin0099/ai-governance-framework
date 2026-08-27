# C1 machine-policy setup identity/diagnostic correction freeze

This directory freezes a corrected, separately owner-authorized executor for
the one machine-wide managed-requirements file. It supersedes the execution
surface at commit `1807be5228475405883c384a3537f266b8ed6f7d`; it does not
rewrite that commit or setup attempt 01.

Attempt 01 stopped before mutation with terminal SHA-256
`19d6e01b85978eee6a3d5f3a4b9fcd4d02a41c4b56e09281390f6695be3e0b5e`.
Its generic `machine observation failed` diagnostic did not distinguish
identity, privilege, process launch, command failure, or state drift.

The corrected path performs an identity-only observer call before any bounded
machine-state query. The retained identity is limited to a SID digest, an
account class, and an Administrator-role boolean. The executor must be the
same elevated owner identity recorded by the independent rollback precheck;
the sandbox account is never an admissible setup identity.

The observer emits only a bounded envelope. Failures retain a stage and error
class, never exception text, raw SID, account name, firewall inventory, or
security descriptor. A valid insufficient-privilege envelope maps to
`MACHINE_POLICY_INSUFFICIENT_PRIVILEGE`; a missing or malformed process
envelope maps to `MACHINE_POLICY_OBSERVER_LAUNCH_FAILED`; other bounded query
failures remain fail-closed as `MACHINE_POLICY_PRECONDITION_FAILED`.

The only admissible payload remains the exact committed 58-byte
`requirements.toml`. Setup attempt 02 has distinct create-once output and
coordination roots. This freeze authorizes nothing and performs no machine
mutation, hosted request, sandbox qualification, randomization, or arm.
