# Machine-policy setup identity/diagnostic correction

## Authority and scope

This failure-driven correction is bound to the reviewed setup freeze
`1807be5228475405883c384a3537f266b8ed6f7d`, its merge commit
`68bd0f6a0c1a62e010dcbc70d1fbeebf6405e750`, and the immutable attempt-01
terminal digest recorded in the manifest. It changes only pre-mutation identity
admission and bounded observer diagnostics.

## Required ordering

1. Validate frozen files, source bindings, owner authority, payload, path, and
   independent rollback precheck.
2. Confirm the rollback heartbeat.
3. Run the frozen observer in `Identity` mode. It performs no account,
   firewall, or target-state query.
4. Require Administrator role, reject the sandbox-account class, and require
   the SID digest to equal the elevated owner SID digest in the precheck.
5. Run the same frozen observer in `Full` mode and require identical identity.
6. Validate bounded machine state.
7. Only then may atomic publication begin.

## Bounded diagnostics

The observer envelope has exact fields: schema, mode, status, stage,
error_class, identity, and machine_state. Identity contains only sid_sha256,
account_class, and administrator_role_enabled. Failure terminals may retain
only that identity projection plus stage/error_class.

`INSUFFICIENT_PRIVILEGE` maps to
`MACHINE_POLICY_INSUFFICIENT_PRIVILEGE`. Missing, malformed, timed-out, or
stderr-bearing process output maps to `MACHINE_POLICY_OBSERVER_LAUNCH_FAILED`.
A valid bounded `CMDLET_FAILURE`, `IDENTITY_QUERY_FAILED`, or `STATE_MISMATCH`
envelope maps to `MACHINE_POLICY_PRECONDITION_FAILED`. Parsed state drift keeps
the existing `MACHINE_POLICY_DRIFT_REVIEW_REQUIRED` terminal.

## Claim ceiling

Passing tests proves only that the corrected frozen bytes enforce the stated
pre-mutation classifications under synthetic inputs. It does not prove the
machine policy is installed, reveal attempt-01's exact root cause, qualify the
sandbox, authorize retry, or authorize randomization or arms.
