# C1 machine-policy observer AuthorizationManager correction freeze

This directory freezes a failure-driven correction to the reviewed long-path
setup executor at commit
`354ffd1a4f729fa7105cd12bf6c45275ecee5428`. It is a new immutable surface;
all earlier freezes and setup attempts remain unchanged.

Setup attempt 03 stopped before machine mutation. The exact observer was
readable and its digest matched, but the default child launch was rejected by
PowerShell AuthorizationManager. The executor parsed empty stdout before
classifying process failure and therefore retained `INVALID_ENVELOPE` rather
than the bounded authorization failure.

The corrected executor fixes the absolute PowerShell path and digest, verifies
the exact observer bytes before launch, and adds `-ExecutionPolicy Bypass` only
to that verified child process. It does not read or modify persistent execution
policy. Any observer non-zero exit or stderr maps to the existing
`MACHINE_POLICY_OBSERVER_LAUNCH_FAILED` terminal with bounded stage
`authorization` and error class `AUTHORIZATION_MANAGER_DENIED` before JSON
parsing or machine mutation.

All identity-first observation, Administrator admission, rollback, payload,
Git identity, and machine-state requirements remain in force. Setup attempt 04
has distinct create-once output and coordination roots; attempt 03's sole
terminal remains immutable and is not retried. This freeze
authorizes nothing and performs no machine mutation, qualification, hosted
request, randomization, or arm execution.
