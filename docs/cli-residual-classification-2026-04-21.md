# CLI Residual Classification (2026-04-21)

Purpose: classify residual fails for `cli` before any content remediation.

Input artifact:

- `artifacts/md_noise_rerun_report_2026-04-21.json`
- runner hash:
  - `451995965f40a64cfa60e9d558f6e5c22bf6411be46bca2f4699a94cda6ef026`

## Doc-Level Map

| File Path | Exact Trigger Phrase | Trigger Type | Actionability Context | Expected Neutral Rewrite Strategy |
|---|---|---|---|---|
| `E:\BackUp\Git_EE\cli\Doc\adoption-test-report-2026-04-14.md` | `ready = False` (output snippet), ``ready=False`` (status row) | status-key literal in code/report block | inferred-global (`must`/next-action wording elsewhere in same doc) | keep factual status; mark as literal status field; avoid interpreting key name as directional synthesis |
| `E:\BackUp\Git_EE\cli\Doc\md-test-20260420-001.md` | `improvement/stability/readiness/forward progress?` | reviewer-prompt rubric literal | explicit (contains recommendation/closeout language) | keep rubric text but mark as reference/test prompt section; exclude from synthesis trigger |
| `E:\BackUp\Git_EE\cli\Doc\md-test-20260420-001.md` | `Pass/Fail`, `classification_outcome: "pass"` | schema/result label literal | explicit | keep labels, but treat schema labels as non-directional literals |
| `E:\BackUp\Git_EE\cli\Doc\md-test-20260420-001.md` | `forward-progress signals` (policy note) | meta-commentary about directional policy | explicit | rewrite as neutral policy reference (no progression framing), or mark as policy-meta section |

## Current Interpretation

- Residuals are currently concentrated in `cli`, but not all residuals are
  confirmed content defects.
- At least part of the residual signal is likely
  `F-REFERENCE-EXEMPTION-GAP` (literal/report/schema text interpreted as
  directional synthesis).
- Classification status for `cli`: `currently suspected residual, pending
  post-classification rerun`.

## Next Step Constraint

1. Apply minimal fixes by residual family, not blanket rewrite.
2. Prefer harness literal/reference handling correction where trigger is clearly
   schema/prompt/status-literal text.
3. Keep same contract and rerun after each minimal patch.
