# Technical specification: qualification-02 failure evidence

## Scope

Create a new create-once qualification attempt without executing it. Preserve
the qualification-01 terminal exactly and retain the previous Git-blob trust
chain.

## Failure stage machine

The bounded stages are:

1. `bindings`
2. `pre_request_setup`
3. `hosted_launch`
4. `transport_result`
5. `probe_read`
6. `probe_json`
7. `probe_schema`
8. `probe_validator`
9. `cleanup`
10. `unclassified`

The stage is assigned immediately before the corresponding operation. A failure
terminal retains that stage. No exception message participates in terminal
classification.

## Transport evidence

Immediately after the launcher returns, before any probe access, the executor
records:

- `returncode`
- `timed_out`
- `stdout_bytes`
- `stderr_bytes`
- `stdout_sha256`
- `stderr_sha256`

`hosted_transport_completed` is true only when the launcher returned,
`timed_out` is false, and `returncode` is zero. It therefore remains true for a
later probe-read or probe-validation failure.

Raw output and raw exception messages are forbidden. `exception_class` is
restricted to the allowlist in `terminal-policy.json`; every other class becomes
`OTHER`.

## Terminal mapping

- binding stage -> `SANDBOXED_RUNNER_BINDING_MISMATCH`
- launch/transport stage -> transport unavailable or timeout
- probe read -> `SANDBOXED_RUNNER_PROBE_UNAVAILABLE`
- probe JSON/schema/validator -> `SANDBOXED_RUNNER_PROBE_INVALID`
- cleanup -> `SANDBOXED_RUNNER_CLEANUP_FAILED`
- every unmatched stage -> `SANDBOXED_RUNNER_UNCLASSIFIED_FAILURE`

## Create-once paths

Qualification-02 uses distinct `qualification-02` output, CLI staging, and
bootstrap staging roots. Qualification-01 paths and terminal are immutable.

## Non-goals

No hosted request, qualification execution, consumer amendment, randomization,
producer, scorer, arm, mapping release, Rekor POST, machine-policy mutation, or
qualification-01 retry belongs to this freeze.
