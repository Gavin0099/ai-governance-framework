# Gate 3 common-harness non-counted rehearsal — 2026-07-29

Status: **PASS — SYNTHETIC, NON-COUNTED, NOT GATE 3 START AUTHORITY.**

## Result

The experiment-local common harness completed one fresh synthetic A/B
rehearsal from a shared planted-defect baseline. It produced two clean output
commits, two admissible outcome packets and the complete seven-event chain
through `mapping_released`.

The rehearsal evidence is:

- root:
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-rehearsal/gate3-common-harness-20260729-142526/`
- summary SHA-256:
  `30cb88b9475d075bcf25e704f965ae8a5957c764b4f7e4eba9cf4e88f4434405`
- chain head SHA-256:
  `47272ba7d3518cd375eb1896466bad6c1602270be5189da5021e403adc483a27`
- candidate manifest SHA-256:
  `51ac12190156eb0465d8e39a562eec0d31145bf41da5ddf8d5f1c6781a5a6801`
- outcome count: `2`
- event count: `7`

## What the harness exercised

- One structured-write function was used for both A and B.
- Each write receipt records requested/stored byte counts and SHA-256 values.
- The verifier reconstructs the stored `calc.py` bytes from each portable Git
  bundle and compares them with the structured-write receipt.
- Each outcome is bound to a clean live `HEAD`, empty `git status`, baseline
  and output commits, full-index binary diff, tracked path inventory, passing
  test receipt, raw event log and all retained input bytes.
- The planted baseline's actual non-zero test exit is retained and linked to
  the shared baseline commit; both blind packets bind its receipt SHA-256
  before synthetic scorer fields can say `regression_baseline_fail=true`.
- Randomization was committed before either outcome was produced.
- Blind-set closure, two structurally distinct synthetic scorer contexts and
  mapping release completed in the candidate's required order.
- The complete published artifact inventory is byte- and length-checked before
  semantic replay.
- The atomically published evidence directory inherits the repository ACL on
  Windows; a regression test rejects the private `tempfile` ACL that previously
  made the packet unreadable to a later Git process.

## Negative evidence

Focused tests reject:

- a structured-write path that escapes the synthetic repository;
- a retained input mutation even when the outer inventory is recomputed;
- a swapped mapping even when the outer inventory is recomputed;
- a missing test receipt;
- a write receipt coherently relabelled to bytes absent from the Git bundle;
- a capture receipt coherently relabelled to a different baseline commit;
- a failing baseline receipt coherently relabelled with exit code zero;
- reuse of an existing rehearsal output root.

These tests show that the implemented verifier fails on the named mutations.
They do not prove resistance to an actor that can coherently replace the
implementation, all evidence and every separately controlled digest.

## Reproduction

From the repository root:

```powershell
.\.venv\Scripts\python.exe `
  artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/gate3_common_harness.py `
  verify `
  --repo-root . `
  --rehearsal-root `
  artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-rehearsal/gate3-common-harness-20260729-142526
```

Expected result: `status=PASS`, `outcome_count=2`, `event_count=7`, with all seven
reported checks equal to `PASS`.

## Claim boundary

The two scorer submissions are synthetic fixtures used only to exercise the
ordering and identity checks. They are not independent judgments and provide no
quality or Skill-effectiveness evidence.

This rehearsal does not establish:

- independent approval of the candidate or harness implementation;
- owner signature;
- canonical promotion;
- natural-bug or resource admission;
- any counted Gate 3 run;
- Gate 3 start authority;
- Skill effectiveness;
- cryptographic writer authentication.
