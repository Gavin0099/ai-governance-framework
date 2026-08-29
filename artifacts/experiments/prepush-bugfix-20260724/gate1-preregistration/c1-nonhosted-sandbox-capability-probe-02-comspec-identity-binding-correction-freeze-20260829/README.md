# C1 Probe-02 COMSPEC identity-binding correction freeze

This directory freezes the narrow Finding 60 correction identified by the
repo-external external-executable-resolution audit rev2. The active Probe-02
chain allowed ambient `COMSPEC` to reach the capability execution plane even
though command-shell identity participates in Windows task-command resolution.

The correction pins `C:/Windows/System32/cmd.exe` by exact path, byte count,
and SHA-256. The outer journal verifies those bytes before Git binding and
journal claim. The child bootstrap and driver reverify the same identity, and
the driver wraps the capability engine's minimal environment so every active
environment receives only the frozen COMSPEC value. Ambient COMSPEC and PATH
cannot select another command processor.

The existing exact-Git, sanitized-environment, detached-worktree identity,
start-before-child, create-once, exact-whoami, and no-retry semantics remain in
force.

This freeze does not authorize or execute Probe-02, any hosted request,
Qualification-03, randomization, producer, scorer, or arm.
