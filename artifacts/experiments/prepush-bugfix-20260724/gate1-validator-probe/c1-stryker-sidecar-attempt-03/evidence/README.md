# C1 Stryker sidecar attempt-03 evidence

Attempt-03 terminated `SIDECAR_RESOLUTION_FAILED` after the bootstrap raw-object
projection succeeded and before the materialized runner could load its manifest.
The Stryker sidecar, consumer projection, Docker, npm, Vitest, mutation, graph,
mount, and cost phases were not reached.

The three original run-root evidence files are preserved byte-for-byte:

- `attempt03-bootstrap-raw-object-inventory.json`
- `non-leakage-scan.json`
- `probe-terminal.json`

`static-path-causal-analysis.json` is an appended static analysis. It does not
alter the terminal, perform a repair, run a retry, or claim dynamic confirmation.
The analysis identifies a frozen path-contract mismatch: the raw materializer
correctly retained full repository-relative paths, while the runner searched for
the manifest directly under the projection root.

Any corrected harness requires fresh authority, a fresh attempt identity, a new
pre-run commit and push, and a separately authorized execution. Nothing in this
directory authorizes that continuation.
