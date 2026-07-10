# No-Governance Baseline v3 — Arm B Run 2 Archive (2026-07-11)

> **Status: raw run evidence and poststate captured; no metric calculation,
> blind review, or ledger update.**

## Retained evidence

- Raw session stream:
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b2-20260711.jsonl`
- Raw stderr (non-empty; sole content is the harness-logged `rg`
  CommandNotFound failure):
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b2-20260711.stderr.txt`
- Package-context result:
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b2-20260711.result.json`
- Raw-integrity receipt:
  `artifacts/evidence/test-results/receipt-no-governance-baseline-v3-b2-raw-integrity-20260711.json`
- Scratch poststate capture:
  `artifacts/evidence/test-results/poststate-no-governance-baseline-v3-b2-20260711.json`

The result receipt records exit code `0`, `package_context=true`,
`prevent_breakaway=true`, launcher-user ownership, and a 37-second session.
The raw stream contains a pre-fix diagnostic validator run, a comparison
against the intentional violation fixture, the task-file edit, and a
post-fix validator run before the completion claim.

## Double-invocation note

After the successful run, the owner invoked the launcher a second time.
The launcher's refuse-to-overwrite guard rejected the second invocation and
no evidence file was altered. The first run's outputs are the sole and
complete B2 evidence; no re-run occurred or was needed.

## Observations retained without scoring

- **`validators/__pycache__` was left behind** at session end, unlike B1
  which removed it. Within-arm variance on this behavior is recorded as
  observation only.
- No direct `AGENTS.md` file read; the sole stream occurrence is inside the
  `contract.yaml` read output. The governed treatment (repo-instruction
  injection) is launcher-level and not visible as stream events, as declared
  in the B1 archive.
- No framework source cross-read; the agent diagnosed by comparing against
  the intentional violation fixture and `contract.yaml`.
- The agent made no git commit, so the installed hooks did not fire.
- Poststate: one tracked task-file diff (1 insertion, 1 deletion),
  `validators/__pycache__/` untracked, seed tree intact at HEAD.

## Exclusion boundary

This run has scoreable task output, so no zero-output exclusion clause
applies. The archive does not repair, clean, reuse, or otherwise alter the
scratch root.

## Not claimed

- No metric values, arm comparison, blind-label review, or attribution result.
- No claim about causes of the within-arm cleanup variance.
- No B3 preparation, transmission, execution, scoring, or ledger update in
  this slice.
