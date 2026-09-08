# C1 Stryker sidecar probe evidence

The single authorized probe ended as `SIDECAR_RESOLUTION_FAILED`.

The exact probe inputs were committed and pushed before execution. During
disposable snapshot materialization, the first failure was
`POWERSHELL_LITERAL_WILDCARD_NOT_EXPANDED`: the orchestration used a wildcard
with `Copy-Item -LiteralPath`, so the sidecar input contents were not copied.
The later mutation-range exclusion mismatch is a downstream consequence of
that missing input copy.

No Docker container was created. No consumer or tool `npm install`, Stryker
resolution probe, Vitest dry-run, mutation run, or active-Vitest resolution
check executed. The consumer dependency graph was therefore not measured.

The non-leakage scan found zero denied strings only across the raw surfaces
that this stopped attempt actually created; it is not a general non-leakage
claim. The failed attempt was not repaired in place and was not retried. A
corrected attempt would require fresh authority and a new attempt identity.
