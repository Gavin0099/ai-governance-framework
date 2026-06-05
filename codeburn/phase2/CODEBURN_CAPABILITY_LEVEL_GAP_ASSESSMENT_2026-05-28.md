# CodeBurn Capability Level Gap Assessment (2026-05-28)

Scope: assessment only. No authority upgrade.

Boundary (unchanged):
- analysis_safe_for_decision=false
- decision_usage_allowed=false

## Level-by-Level Status

| Level | Target definition (short) | Current status | Evidence | Remaining to reach target | Estimated effort |
|---|---|---|---|---|---|
| L0 Manual recording | accept manually reported usage facts and summarize by repo/agent/model/task | Achieved (minimum slice) | `codeburn_manual_usage_ingest.py` + `manual_usage_fixture.json` + Phase1 report fields `manual_reported_usage_count/manual_reported_usage_present` | Keep scope tight; do not expand into dedup/summary/cost surfaces in this phase | Very small (0.5-1 slice) |
| L1 Tool-output observation | ingest Codex/Copilot/CLI outputs with provenance/quarantine and analysis-only claims | Achieved (analysis-only) | Phase2 codex/copilot smokes pass; provenance+quarantine observed; codex gap fixtures calibrated | Tighten known gaps: document rate_limits validation deferred; keep admitted_with_warning classification surfaced in outputs | Very small (0.5-1 slice) |
| L2 Provider-response observation | ingest provider/API/billing-authoritative outputs as separate authority class | Not started (by design) | No provider API ingestion path enabled in current calibration scope | Define provider authority contract, admissibility rules, source trust boundaries, replay model, and fail-closed validator before any API ingest claim | Large (4-6 slices) |
| L3 Governance integration advisory | stable ledger + anomaly/warning outputs integrated with governance workflow (advisory only) | Not started | Current outputs are component-level smoke/report evidence, not integrated governance surface | Need L2-ready evidence layering, anomaly spec, budget-warning semantics, false-positive handling, override trail; keep enforcement disabled | Large (5-8 slices) |

## What Is Already True Now

- CodeBurn can already support L1 claim safely:
  - collect and summarize AI usage evidence from existing tool outputs
  - keep provenance/quarantine records
  - remain analysis-only (no decision authority)
- L0 manual batch ingest is now hardened and deterministic under tested fixtures.
- Phase 2 Codex/Copilot calibration status is unchanged by L0 work.

## L0 Capability Matrix Row (Explicit)

| Capability | Evidence command | Result | Tested coverage | Coverage gap | Allowed analysis-only claim | Forbidden decision claim | Decision authority | Blocker / gap |
| ---------- | ---------------- | ------ | --------------- | ------------ | --------------------------- | ------------------------ | ------------------ | ------------- |
| L0 manual batch ingest | `codeburn_manual_usage_ingest.py --input-json manual_usage_batch_valid.json` + invalid fixtures | Pass | single JSON object, JSON array, required string non-empty, integer token >= 0, fail-whole-batch no-write | partial success policy, dedup, summary, cost estimate, schema versioning not tested and out-of-scope | L0 manual usage events can be batch-ingested for analysis-only evidence under tested validation rules | billing truth, budget gate, cost enforcement, agent efficiency ranking | none | L0 only; does not affect Phase 2 Codex/Copilot coverage |

## Key Known Gaps (Current)

1. `rate_limits` field-level validation is deferred (known gap).
2. Missing token stats are admitted as evidence but marked `admitted_with_warning` in Codex smoke summary.

## "How much more" Summary

- Reach solid L0: minimum slice completed; ~0.5-1 slice to harden.
- Stabilize L1 (from achieved to operationally robust): about 1 small slice.
- Reach L2: about 4-6 slices plus contract/validator work (largest governance risk jump).
- Reach L3 advisory integration: about 5-8 slices after L2 foundations.

## Recommended Order (No Expansion Jump)

1. Freeze current L1 calibration artifacts and known gaps (done).
2. Complete explicit L0 manual-ingest contract (small).
3. Harden L1 output semantics (`admitted_with_warning` surfaced in matrix/report views).
4. Decide whether L2 is needed; if yes, start with authority contract before any provider ingestion code.

## Non-Claims Reminder

- L1 smoke pass does not permit budget gating or ranking decisions.
- Local artifact observation is not billing truth.
- Composite metrics inherit the lowest authority input.
