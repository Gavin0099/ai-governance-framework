# C1 Stryker sidecar attempt-02 evidence

The single authorized attempt ended as `SIDECAR_RESOLUTION_FAILED` before the
materialization self-test or any Docker container execution.

Remote pre-run binding and the pinned Docker client/server version passed. The
first failure was `SIDECAR_RESOLUTION_FAILED:HARNESS_INPUT_BINDING:.gitattributes`.
The committed `.gitattributes` blob is 92 bytes with SHA-256
`1349094487e290e8fe99ce71ac927db6cce1b5202f2e1ee5ed8c2f4b56193fac`,
while the already-created `git archive` entry is 96 bytes with SHA-256
`d81cb4d5b70f252e073a8ed6c49e8ee54528980f4cf4a5757ab75d5b0591e552`.
The extracted file exactly matches the archive entry. Static inspection of the
same archive shows that all three frozen PowerShell harness files match their
committed bindings.

The original terminal and its five bound artifacts are unchanged. The separate
archive-fidelity analysis is static inspection of artifacts created by this
attempt; it is not a new execution, repair, or retry.

No disposable Docker container, `npm ci`, materialization self-test, resolution
probe, Vitest, Stryker dry run, mutation run, consumer graph comparison, mount
audit, or functional cost probe ran. A corrected attempt requires fresh
authority and a new attempt identity.
