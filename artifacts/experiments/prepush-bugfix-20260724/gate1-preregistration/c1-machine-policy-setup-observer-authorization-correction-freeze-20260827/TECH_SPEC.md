# Machine-policy observer AuthorizationManager correction

## Problem

The setup-03 executor launched a digest-matched observer with the default
PowerShell execution-policy path. AuthorizationManager rejected that script,
returning non-zero with stderr and no stdout. The executor attempted JSON
parsing first and classified the result as `INVALID_ENVELOPE`.

## Current repository truth

The reviewed long-path correction is commit
`354ffd1a4f729fa7105cd12bf6c45275ecee5428`. Attempt 03 produced exactly one
616-byte terminal with SHA-256
`82111edb99d88f2b8f8999026ee1eb440a849019ddb01a582ff9efb010e70a14`.
It produced no setup evidence, policy receipt, target file, or policy parent.

## Target outcome

Launch only the exact frozen observer with the exact frozen PowerShell child,
using child-scoped `-ExecutionPolicy Bypass`. Classify AuthorizationManager
denial before envelope parsing and retain no raw process output.

## Scope

1. Fix the absolute PowerShell path and executable digest.
2. Re-read and verify observer bytes and digest immediately before each launch.
3. Add `-ExecutionPolicy Bypass` only to that exact observer child.
4. Preserve persistent execution policy without mutation.
5. Map non-zero exit or any stderr to the existing observer-launch terminal,
   stage `authorization`, class `AUTHORIZATION_MANAGER_DENIED`.
6. Create distinct attempt-04 output and coordination roots while binding the
   immutable attempt-03 terminal.
7. Add default-policy, Bypass, digest, process-contract, and zero-mutation tests.

## Non-goals

No setup execution or retry, machine mutation, rollback, qualification, hosted request,
randomization, arm execution, push, or PR belongs to this tranche.

## Affected surfaces

The executor, terminal policy, setup/terminal attempt identity, manifest,
tests, README, and this specification are affected. Observer script bytes,
rollback, requirements payload, top-level terminal vocabulary, output policy,
and downstream receipt semantics remain unchanged.

## Boundary and failure paths

Git identity and observer byte verification remain pre-mutation prerequisites.
Bypass is an argv-only child setting; `Set-ExecutionPolicy`, registry changes,
or any persistent policy mutation are forbidden. Raw stderr, exception text,
environment data, and paths are forbidden.

## Evidence plan

Run focused tests for default-policy rejection, exact child Bypass success,
wrong observer digest, non-zero/stderr mapping, and zero mutation, plus
fresh-checkout tests under `core.autocrlf=true`, inventory, leakage scan, diff
check, and the canonical precommit entrypoint.

## Claim ceiling

Passing evidence proves only that these frozen bytes verify the child bindings,
apply child-scoped Bypass, and terminalize synthetic observer authorization
failures without mutation. It does not prove setup succeeds, authorize retry,
install policy, qualify containment, or authorize randomization or arms.

## Implementation tranche

Create one local correction-freeze commit and stop for independent review.
