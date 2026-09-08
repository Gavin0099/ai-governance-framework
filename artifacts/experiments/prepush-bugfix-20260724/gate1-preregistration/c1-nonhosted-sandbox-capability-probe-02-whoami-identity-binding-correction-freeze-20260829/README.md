# C1 Probe-02 whoami identity-binding correction freeze

This directory freezes the narrow Finding 59 correction identified by the
repo-external external-executable-resolution audit rev1. The active Probe-02
driver validated reviewed readiness by running
`C:/Windows/System32/whoami.exe`, but only the path was fixed; its bytes were
not part of the admission trust boundary.

The corrected driver pins `whoami.exe` by exact absolute path, byte count, and
SHA-256 before any repository binding, readiness validation, journal claim, or
capability execution. It supplies an explicit environment, validates the exact
argv, obtains the bounded identity projection through that runner, and passes
the projection to `validate_reviewed_readiness`. The validator's default
unverified runner is therefore unreachable in this execution path.

The existing exact-Git, sanitized-environment, detached-worktree identity,
start-before-child, create-once, and no-retry semantics remain unchanged. The
outer bootstrap obtains the corrected child and driver only from its
owner-authorized frozen inventory.

This freeze does not authorize or execute the journal, Probe-02, any hosted
request, Qualification-03, randomization, producer, scorer, or arm.
