# P1 Observation Phase Test Plan (Gate C / FGCR)

Date: 2026-05-11
Phase: P1 Observation (post P0 operationally stabilized)
Scope: ChatGPT / Claude / Copilot
Mode: Observation-only (no new governance semantics)

## 1. Objective

Collect runtime distribution evidence under a fixed legality pipeline, without introducing new contracts/hooks/metrics.

## 2. Preconditions

1. P0 pipeline is active and replayable:
   - decision-set builder
   - dual-report pipeline
   - derivation manifest
   - FGCR detector-only summary
2. Hostile regression suite is green.
3. Same task pack / same repo ecology / same Gate C pipeline across lanes.

## 3. Fixed Inputs

- Window ID format: `gate-c-window-YYYY-MM-DD`
- Lanes: `copilot`, `claude`, `chatgpt`
- Task packs (fixed):
  - Comparable pack
  - Ambiguity pack
  - Ablation pack

## 4. Required Outputs Per Window

Must produce all of the following artifacts:

1. Canonical report
2. Decision-set report
3. Decision-derivation manifest
4. FGCR summary (detector-only)
5. Hostile regression test result

## 5. Execution Checklist

1. Run lane windows under identical task-pack mapping.
2. Generate dual-report outputs.
3. Generate FGCR summary from event log.
4. Run hostile fixtures/tests.
5. Publish only observation notes (no uplift claims).

## 6. Observation Questions (Only 3)

For each completed window, answer only:

1. What lane-level differences appear in `filtered_reason_counts`?
2. Is FGCR `by_failure_type` concentrated in specific lanes or repo ecologies?
3. Is `governance_narration / engineering_delta` increasing?

## 7. Forbidden Actions During P1

Do NOT:

- add new metrics
- add new contracts
- add new governance hooks
- change decision legality rules
- claim quality uplift or reasoning uplift

## 8. Pass/Fail for P1 Window Execution

A window execution is valid when:

1. All required outputs exist
2. Re-run produces same decision-set rows under same builder/policy versions
3. Hostile regression remains green

If any condition fails: mark `window_status=invalid_observation`.

## 9. Interpretation Boundary (Mandatory Text)

Use this exact boundary in each window summary:

> This window is observational evidence only. It does not prove quality uplift, reasoning uplift, or deterministic governance effect.

## 10. Suggested File Naming

- `docs/status/<window-id>-canonical-report.md`
- `docs/status/<window-id>-decision-set-report.md`
- `docs/status/<window-id>-decision-derivation-manifest.json`
- `docs/status/<window-id>-fgcr-summary.json`
- `docs/status/<window-id>-observation-note.md`

## 11. Completion Condition for P1

Move beyond P1 only when:

1. At least 2 valid windows per lane are collected
2. FGCR taxonomy distribution is stable enough for comparison
3. No regression in hostile fixture boundaries
