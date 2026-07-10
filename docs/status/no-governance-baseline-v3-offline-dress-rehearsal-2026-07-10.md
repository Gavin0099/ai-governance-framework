# No-Governance Baseline v3 — Offline Dress Rehearsal (2026-07-10)

## Result

The requested zero-API dress rehearsal completed after two retained setup
failures. It demonstrated a reproducible Arm A seed procedure without starting
Codex, invoking `Invoke-CommandInDesktopPackage`, or transmitting to OpenAI.

## Demonstrated Procedure and Frozen Candidate Inputs

1. Create a fresh scratch root outside the sandbox as launcher user `daish`.
2. Copy the `examples/multi-validator-contract` file tree while excluding
   generated `__pycache__` files; initialise and commit the baseline tree.
3. Apply the sole frozen mutation by inserting the literal JSON text
   `\n#include \"../database_service/Global.h\"` into
   `fixtures/architecture_drift_compliant.checks.json`; commit the seed.
4. Run `consumer_fixture_runner` with the scratch `contract.yaml`, while
   suppressing bytecode output; require 8 fixtures, 7 matched expectations,
   and one mismatch at the named architecture fixture.
5. Require a clean post-probe Git status and capture the tree/manifest/task
   hashes and the assembled package-context launcher arguments without calling
   that launcher.

Successful result artifact:
`artifacts/evidence/test-results/raw-no-governance-baseline-v3-dress-rehearsal-20260710.result.json`

| Input | Captured value |
| --- | --- |
| baseline tree hash | `769ab03b59e4c8ee50905a8dd6433492099daa34` |
| seed tree hash | `27b7d8f9e7c7b7bccce5d47ce991c92a6e3fea71` |
| seeded task SHA-256 | `16642a46a363b10ccb53f74bd0efdf027b47d08c39726259c5c86c08b5659065` |
| package/PFN | `26.707.3748.0` / `OpenAI.Codex_2p2nqsd0c76g0` |
| API call | `false` |

## Rehearsal Failures Retained

- Initial script parse failed before scratch creation because the injected
  PowerShell string was malformed.
- First and second scratch attempts exposed invalid JSON construction: the
  literal newline and then the JSON-escaped include quotes were not preserved.

Those failures are retained in the first three receipts. The successful third
attempt uses a new scratch root; no failed root is reused.

## Claim Boundary and Next Slice

- CLAIMED: the offline setup procedure, seed inputs, mutation-probe behavior,
  and pre-API launcher assembly were demonstrated once under the qualified
  package version.
- NOT CLAIMED: v3 preregistration is frozen; a Codex session or OpenAI API call
  occurred; the launcher is qualified for a task run; the setup will transfer
  to a later package version; or governance has any behavioral effect.

The next slice, if separately approved, is to write and freeze a v3
pre-registration from this demonstrated procedure. It must carry the listed
hashes and the retained failure history. It does not inherit the v2
transmission authorization.
