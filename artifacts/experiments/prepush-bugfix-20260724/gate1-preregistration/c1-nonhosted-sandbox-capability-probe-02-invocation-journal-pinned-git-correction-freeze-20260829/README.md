# C1 Probe-02 invocation-journal pinned-Git correction freeze

This directory freezes the Finding 58 correction for the outer Probe-02
invocation journal.  The predecessor journal used the ambient `PATH` to resolve
`git`; this revision pins Git by absolute path, byte count, and SHA-256 before
any repository identity or blob is trusted.

The new bootstrap supersedes the predecessor bootstrap only for a future
Probe-02 entry.  It preserves the reviewed start-before-child journal semantics,
attempt identity, create-once paths, no-retry rule, and bounded outcomes.

The corrected outer journal now selects a corrected child bootstrap from its
owner-authorized frozen inventory.  That child and its corrected driver pin the
same Git executable and sanitize Git and child-process environments; neither
the superseded bare-Git child nor ambient `PATH`/`GIT_*` reaches the execution
chain.

The same three layers also freeze the detached-worktree identity before any
HEAD/blob binding or journal claim. The checkout must contain a non-reparse
regular `.git` gitfile pointing to the exact worktree-admin directory under
`D:/ai-governance-framework/.git/worktrees/<checkout-name>`. The reverse
gitfile, exact `commondir` bytes, non-reparse directories, and pinned Git's
`--show-toplevel`, `--absolute-git-dir`, and `--git-common-dir` results must all
agree. Redirected or decoy Git directories therefore fail before formal roots.
The checkout root itself is also byte-for-byte frozen as
`C:/Users/daish/.codex/visualizations/2026/08/20/01a01f9a-76de-7b00-8170-409653fa352d/c1-nonhosted-capability-probe-02-execution`;
another otherwise valid worktree cannot consume the same authorization.

No readiness probe, capability probe, hosted request, authorization packet, or
downstream execution was performed by this freeze.  All execution-authority and
authoring-boundary flags remain false.
