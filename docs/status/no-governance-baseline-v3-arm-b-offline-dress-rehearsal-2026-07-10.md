# No-Governance Baseline v3 Arm B — Offline Dress Rehearsal (2026-07-10)

## Result

The Arm B offline rehearsal completed with no Codex session and no OpenAI API
call. It used a fresh host-owned clone of the demonstrated Arm A seed, installed
the consumer-style hooks, validated installation, and made a local probe commit
whose Git trace shows `.git/hooks/pre-commit` was invoked.

Successful artifact:
`artifacts/evidence/test-results/raw-no-governance-baseline-v3-arm-b-dress-rehearsal-20260710.result.json`

| Check | Result |
| --- | --- |
| source and fresh-copy seed tree | both `27b7d8f9e7c7b7bccce5d47ce991c92a6e3fea71` |
| hook installer | `exit_code=0`, `ok=true` |
| hook validator | `exit_code=0`, `valid=true` |
| manual commit | `exit_code=0`, trace shows `.git/hooks/pre-commit` |
| framework-root hook config | `D:\ai-governance-framework` |
| poststate | clean |
| API call | `false` |

## Failure Retained

The first attempt reached the manual commit but the PowerShell wrapper treated
`GIT_TRACE` stderr as a terminating error. A new scratch root was used for the
successful retry; the first receipt is retained. This was a trace-capture
failure, not evidence of a hook failure.

## Boundary

- CLAIMED: Arm B hook installation, validation, and a host-side manual
  pre-commit invocation are reproducible on a fresh copy of the verified seed.
- NOT CLAIMED: hooks execute successfully inside a package-context sandbox;
  a real Arm B agent run is qualified; v3 is preregistered; any API call
  occurred; or governance changes agent behavior.

## Next Slice

If separately approved, the next slice may freeze v3 from both Arm A and Arm B
rehearsals. The initial v3 protocol must include a pre-declared exclusion/re-run
rule for a package-context Arm B hook-environment failure with zero scoreable
output. This is not a transmission authorization or a run authorization.
