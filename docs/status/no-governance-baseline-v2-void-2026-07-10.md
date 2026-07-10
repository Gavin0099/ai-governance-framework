# No-Governance Baseline v2 — Void Before Run 1 (2026-07-10)

## Disposition

The v2 experiment line is **void before Run 1**. No Codex session was launched,
no OpenAI API transmission was initiated, and no experimental output, score,
metric, or attribution conclusion exists.

## Observed Precondition Failure

The first new Arm A scratch root was created outside the sandbox by launcher
user `daish`, but its seed construction did not copy the contract files. Its
poststate therefore contained neither
`fixtures/architecture_drift_compliant.checks.json` nor a seed commit. It was
not eligible to start a run and is retained, unused, at:

`C:\Users\daish\.codex\visualizations\2026\07\10\019f4c83-2f1f-7b30-af00-324063641a72\v2-baseline-arm-a-run-1`

The immediate setup error alone did not create a scoreable run. It also exposed
a material v2 protocol gap: the frozen document inherited the v1 task but did
not bind a seed-construction procedure or seed-tree hash. Creating a fresh root
with an improvised repair would change an uncontrolled experimental input.

Under v2's zero-amendment rule, this line is void rather than repaired.

## Evidence

- `artifacts/evidence/test-results/receipt-no-governance-baseline-v2-arm-a-run1-precheck-void-20260710.json`
  retains the first poststate-validator failure caused by sandbox Git dubious
  ownership handling.
- `artifacts/evidence/test-results/receipt-no-governance-baseline-v2-arm-a-run1-precheck-void-retry-20260710.json`
  records the successful retry with a single-run `safe.directory` override:
  owner is `DESKTOP-EJOULKM\daish`, the task file is absent, and no seed commit
  exists.

## Claim Boundary

- CLAIMED: the v2 protocol was stopped before any experimental run because its
  first scratch precondition was not met and the seed input was not fully bound.
- NOT CLAIMED: an Arm A result, an infrastructure exclusion, a launcher
  failure, an API outcome, model behavior, qualification regression, or a
  governance-treatment effect.

## Next Candidate

Any successor must be a separately approved v3 pre-registration. Before any
external authorization or run, it must bind a reproducible seed-construction
method and seed-tree hash in addition to v2's launcher, package, ownership,
and version locks.
