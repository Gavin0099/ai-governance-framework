# C1 Probe-02 parent-readiness trusted-bootstrap correction freeze

This freeze closes the parent-readiness circular-trust gap without executing
readiness or changing the reviewed readiness and invocation-journal bytes.

The only future entrypoint is the bootstrap blob streamed from the exact
owner-authorized commit into the exact Python interpreter with `-I -`. Before
any staging directory, sentinel, receipt path, or readiness evidence is
accessed, the bootstrap verifies its own frozen inventory, both predecessor
manifests, the parent-readiness wrapper, the readiness implementation, the
exact Git executable, and the exact Python interpreter.

Verified source bytes are materialized outside the `gate1-execution`
exact-child boundary, imported by absolute path with module-cache replacement,
and removed before the readiness implementation can run. The imported wrapper
uses the bootstrap's pinned `git --no-replace-objects` adapter, so ambient
`PATH`, `sys.path`, working-tree files, and Git replace objects are not trust
sources. The adapter is injected into `verify_anchor_git_binding()` through its
`git_runner` parameter; assigning an unrelated module attribute is forbidden.

This freeze authorizes no execution, creates no staging or evidence root, and
does not authorize Probe-02, hosted requests, Qualification-03, randomization,
producer, scorer, or arms.
