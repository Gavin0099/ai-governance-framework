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
   `external_repo_smoke_result.v0.2` schema, `ok=true`, a clean framework
   worktree, and the same framework root and Git commit as the current hook
   configuration.
4. The currently configured hook framework worktree is still clean when the
   maturity summary evaluates the retained result.

Run `external_repo_smoke.py` with `--output` to persist that JSON result. The
output path is explicit and is written atomically.

The producer fails closed when tracked, staged, or untracked files make the
framework checkout dirty. A dirty checkout cannot produce attributable passing
evidence, even when `HEAD` still matches the recorded commit.
The v0.2 fields are semantically bound: `ok=true` requires
`framework_worktree_clean=true`; a clean worktree requires an empty
`framework_worktree_changes` list.

## Non-claims

This status proves only observed execution of the external runtime path. It
does not prove `runtime_capable=yes`, self-contained runtime governance, hook
enforcement, CI or fleet enforcement, domain correctness, or release
readiness.
