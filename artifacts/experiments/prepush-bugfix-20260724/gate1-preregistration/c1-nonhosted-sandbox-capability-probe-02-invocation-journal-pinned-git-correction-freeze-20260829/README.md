# C1 Probe-02 invocation-journal pinned-Git correction freeze

This directory freezes the Finding 58 correction for the outer Probe-02
invocation journal.  The predecessor journal used the ambient `PATH` to resolve
`git`; this revision pins Git by absolute path, byte count, and SHA-256 before
any repository identity or blob is trusted.

The new bootstrap supersedes the predecessor bootstrap only for a future
Probe-02 entry.  It preserves the reviewed start-before-child journal semantics,
attempt identity, create-once paths, no-retry rule, and bounded outcomes.

No readiness probe, capability probe, hosted request, authorization packet, or
downstream execution was performed by this freeze.  All execution-authority and
authoring-boundary flags remain false.
