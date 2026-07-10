# No-Governance Baseline v3 — Arm B Run 3 Archive (2026-07-11)

> **Status: raw run evidence and poststate captured; no metric calculation,
> blind review, or ledger update. v3 data collection is COMPLETE (6 of 6
> runs); the blind-scoring slice is the only remaining v3 work and requires
> separate owner authorization.**

## Retained evidence

- Raw session stream:
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b3-20260711.jsonl`
- Raw stderr (non-empty; sole content is the harness-logged `rg`
  CommandNotFound failure):
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b3-20260711.stderr.txt`
- Package-context result:
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b3-20260711.result.json`
- Raw-integrity receipt:
  `artifacts/evidence/test-results/receipt-no-governance-baseline-v3-b3-raw-integrity-20260711.json`
- Scratch poststate capture:
  `artifacts/evidence/test-results/poststate-no-governance-baseline-v3-b3-20260711.json`

The result receipt records exit code `0`, `package_context=true`,
`prevent_breakaway=true`, launcher-user ownership, and a 37-second session.
The raw stream contains a pre-fix diagnostic validator run, a comparison
against the intentional violation fixture, the task-file edit, and a
post-fix validator run before the completion claim.

## Observations retained without scoring

- Most compact arc of the six runs (seven stream events).
- Zero `AGENTS.md` occurrences in the raw stream. The governed treatment
  (repo-instruction injection) is launcher-level and not visible as stream
  events, as declared in the B1 archive.
- `validators/__pycache__` left behind (as in B2; B1 cleaned it).
- No framework source cross-read; no git commit, so installed hooks did not
  fire.
- Poststate: one tracked task-file diff (1 insertion, 1 deletion),
  `validators/__pycache__/` untracked, seed tree intact at HEAD.

## Data-collection closure

All six pre-registered runs (A1–A3, B1–B3) completed with exit code 0 under
the frozen launcher/package version `26.707.3748.0` on 2026-07-10/11 local
time, each with scoreable output; no exclusion clause was used for any
counted run. Raw evidence, integrity receipts, and poststates for all six
are committed. Scratch roots remain unaltered pending the blind-scoring
slice.

## Not claimed

- No metric values, arm comparison, blind-label review, or attribution
  result.
- No claim that any observed cross-run or cross-arm variance has a cause.
- The blind-scoring slice (label shuffle, four mechanical metrics, one
  decision-change ledger entry, backlog P0 #2 disposition, line freeze) has
  not started and requires separate owner authorization.
