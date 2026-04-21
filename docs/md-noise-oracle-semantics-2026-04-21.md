# MD Noise Oracle Semantics (2026-04-21)

Purpose: define the minimum pass/fail semantics before harness remediation.

Policy statement:

This remediation restores oracle satisfiability by removing structural
self-triggering; it does not lower the directional policy threshold.

## Minimal Semantics Table

| Case Type | Allowed To Match Directional Regex | Must Trigger Fail | Notes |
|---|---|---|---|
| Injected noise phrase in injected span | yes | no | noise phrase exists to test contamination pressure; self-match must not force fail |
| Quoted literal / backtick test string / explicit reference example | yes | no | reference context is not decision synthesis |
| Non-reference directional phrase with actionability context | yes | yes | this remains a true directional-synthesis signal |
| Non-reference directional phrase without actionability context | yes | no | directional token alone is insufficient without decision/action context |

## Guardrails

1. Exempt only injected-span phrase and reference-context literals.
2. Keep directional regex unchanged unless separately justified.
3. Require actionability context for directional-synthesis fail.
4. Validate with regression tests before rerun contract replay.
