# External Runtime Execution Evidence

## Purpose

This policy defines the narrow, report-only `external_runtime_execution`
capability for consumer repositories whose runtime hooks deliberately resolve to
an external AI Governance Framework checkout.

## Verified criteria

`external_runtime_execution=Verified` requires all of the following:

1. The adoption doctor observes an external framework dependency and external
   hook root.
2. External repository readiness and hook installation are verified.
3. The newest attributable JSON result under
   `artifacts/evidence/test-results/` or `.governance/evidence/` has the
   `external_repo_smoke_result.v0.1` schema, `ok=true`, and the same framework
   root and Git commit as the current hook configuration.

Run `external_repo_smoke.py` with `--output` to persist that JSON result. The
output path is explicit and is written atomically.

## Non-claims

This status proves only observed execution of the external runtime path. It
does not prove `runtime_capable=yes`, self-contained runtime governance, hook
enforcement, CI or fleet enforcement, domain correctness, or release
readiness.
