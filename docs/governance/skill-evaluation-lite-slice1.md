# Skill Evaluation Lite — synthetic slice 1

This additive entry verifies wiring with built-in fixtures. It does not evaluate
a real Skill and is not a substitute for the existing strict Solo R2 path.

From the repository root:

```powershell
& .\.venv\Scripts\python.exe -B -m governance_tools.skill_evaluation_lite --synthetic --output memory/evidence/my-new-lite-fixture --authorize-synthetic-unblinding
```

The output directory must not exist. The CLI creates only synthetic artifacts:
`scorer-input.json`, `scores-frozen.json`, and, when explicitly authorized,
`report.json`. Omitting `--authorize-synthetic-unblinding` stops after freezing.
There is no resume, replacement, live-model, task-selection or automatic retry
option. Choose a new fixture directory for a separately requested test.

## Implemented boundary

The entry consumes fixed synthetic A/B results and separate fixture oracle
evidence, uses `solo_r2_future_scoring_consumer.prepare_scoring_delivery` for
regression projection and anonymous input, then feeds a canned synthetic scorer.
That scorer demonstrates transport/order, not rubric interpretation or quality.
The fixture UUID/Pair strings are bundle metadata only; no actual evaluation,
Pair, ledger or Attempt is allocated. They are not forwarded to the scorer.

The coordinator keeps the arm mapping outside scorer input, validates the exact
two opaque score sets, and freezes immutable serialized bytes. It rejects
identity leakage in payloads and scorer evidence, unknown fields, missing scores,
out-of-rubric values and numeric ratings where required evidence is absent.
Oracle correctness is copied from input evidence, never accepted from the quality
scorer. The CLI persists and reads back frozen scores before revealing mapping.
Unblinding requires authorization referencing that exact freeze digest, and does
not change frozen bytes. Neither freezing nor unblinding can be replayed on the
same coordinator instance. This is not a durable cross-process authorization or
resume system, and it makes no OS isolation claim.

The default fixture has no regression execution evidence, so regression safety
and the quality total stay `NOT_ASSESSABLE`; comparison stays `NOT_DETERMINED`.
A numeric regression fixture test exercises only evidence propagation for an
observed current source/test version. It does not claim that a successful test
command alone establishes regression safety 2/2 for a real task. P3 must define
the actual task/rubric evidence requirements; missing evidence must remain unknown.

## Later integration, not implemented here

- A real Lite arm adapter would return two authorized `ScoringInput` values
  (payload, raw trace, externally expected digests) after separate fresh-context
  executions. The existing projection currently understands queue-range command
  shapes only. General task support is not claimed.
- A real fresh scorer adapter would receive only `scorer_input` bytes, never this
  coordinator, mapping, repo history or prior investigation. It would return the
  closed quality-score response accepted by `freeze`. The later host would own
  durable score storage and separately authorized unblinding. A fresh context
  cannot be replaced with the current, already-informed conversation.

No real adapters, credentials, model discovery, subprocesses, sandbox changes,
ChatGPT shutdown, quiescence, custody setup or strict lifecycle modifications are
included. The CLI does not execute a real oracle; fixture correctness is explicitly
synthetic. Passing this slice cannot establish that real Lite evaluation works.

## Claim and verification

Result token: `LITE_SYNTHETIC_END_TO_END_WIRING_VALIDATED` means only that synthetic
wiring reached a report. Ceiling: `NON_COUNTED / SOLO_CONTROLLED /
DECISION_SUPPORT_ONLY`. OS scorer isolation, strict equivalence, Formal/counted
evidence, real Skill effectiveness and production-ready real-model evaluation
remain explicitly unclaimed in every report.

Focused tests: `tests/test_skill_evaluation_lite.py`; regression dependencies:
`tests/test_solo_r2_future_scoring_consumer.py`,
`tests/test_solo_r2_regression_projection.py`,
`tests/test_solo_r2_blind_scoring_bundle.py`.

No requirement was removed from Strict. This slice removes those prerequisites
only from a built-in synthetic demonstration; it does not yet prove lower costs
for a real Skill evaluation or completion within one normal session.
