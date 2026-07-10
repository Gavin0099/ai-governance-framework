# No-Governance Baseline v3 — Arm B Run 1 Archive (2026-07-11)

> **Status: raw run evidence and poststate captured; no metric calculation,
> blind review, or ledger update.**

## Retained evidence

- Raw session stream:
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b1-20260711.jsonl`
- Raw stderr (non-empty; sole content is the harness-logged `rg`
  CommandNotFound failure, as in Arm A Runs 2–3):
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b1-20260711.stderr.txt`
- Package-context result:
  `artifacts/evidence/test-results/raw-no-governance-baseline-v3-b1-20260711.result.json`
- Raw-integrity receipt:
  `artifacts/evidence/test-results/receipt-no-governance-baseline-v3-b1-raw-integrity-20260711.json`
- Scratch poststate capture:
  `artifacts/evidence/test-results/poststate-no-governance-baseline-v3-b1-20260711.json`

The result receipt records exit code `0`, `package_context=true`,
`prevent_breakaway=true`, and launcher-user ownership. The raw stream contains
a pre-fix diagnostic `consumer_fixture_runner` execution, the task-file edit,
and a post-fix execution reporting all expectations matched before the
completion claim.

## Treatment delivery note (declared honestly)

Arm B's governed treatment is delivered by launcher flags (no
`project_doc_max_bytes=0`, so repo instructions including `AGENTS.md` are
injected at prompt assembly) plus pre-session hook installation
(`ok=true` / `valid=true`, receipt retained). Prompt-assembly injection is
not visible as a file-read event in the raw stream; the committed launcher
diff and the launcher-ready receipt are the treatment evidence. The agent
made no git commit during the session, so the installed hooks did not fire.

## Observations retained without scoring

- **Bytecode-cache cleanup**: the agent noticed the runner-generated
  `validators/__pycache__` and removed it before reporting; the poststate
  has no untracked files. All three Arm A runs left `__pycache__` behind.
  Recorded as observation only; no causal or metric claim.
- No direct `AGENTS.md` file read; the sole occurrence in the stream is
  inside the `contract.yaml` read output.
- Framework source cross-read occurred (full-path read of
  `architecture_drift_checker.py` after a failed `python -c inspect`
  attempt, which exited 1 and is part of the retained stream).
- Poststate: one tracked task-file diff (1 insertion, 1 deletion), zero
  untracked files, seed tree intact at HEAD.

## Exclusion boundary

This run has scoreable task output, so no zero-output exclusion clause
applies. The pre-declared Arm B hook-environment failure clause was not
needed. The archive does not repair, clean, reuse, or otherwise alter the
scratch root.

## Not claimed

- No metric values, arm comparison, blind-label review, or attribution result.
- No claim that the injected instructions caused the cleanup behavior.
- No B2/B3 preparation, transmission, execution, scoring, or ledger update
  in this slice.
