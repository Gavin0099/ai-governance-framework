# C1 machine-policy setup long-path correction freeze

This directory freezes a failure-driven correction to the reviewed identity
and diagnostic setup executor at commit
`b6a73ba39e4abba5a9d6cb4ddf7c03b346b0ac39`. It is a new immutable surface;
the PR #125 freeze and failed setup attempt remain unchanged.

Setup attempt 02 stopped before machine mutation. The frozen executor invoked
`git -C` against its deeply nested freeze directory, and Git for Windows
returned `Filename too long`. The exception escaped before the executor could
publish its create-once terminal. The target and its parent remained absent;
the attempt produced only the separately elevated rollback precheck and stale
heartbeat in its coordination root.

The corrected executor resolves Git identity from the bounded repository root,
never from the deep freeze directory. Git launch, timeout, non-zero exit,
stderr, or malformed commit output maps to the bounded terminal
`MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE`. That terminal records
`executing_commit_verified=false`, uses a zero commit sentinel, retains no Git
stderr or exception text, and is published before any observer or mutation.

All identity-first observation, Administrator admission, rollback, payload,
and machine-state requirements from the PR #125 freeze remain in force. Setup
attempt 03 has distinct create-once output and coordination roots. This freeze
authorizes nothing and performs no machine mutation, qualification, hosted
request, randomization, or arm execution.
