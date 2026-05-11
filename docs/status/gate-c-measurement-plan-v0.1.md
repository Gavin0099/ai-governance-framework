# Gate C Measurement Plan v0.1

Date: 2026-05-11  
Scope: Copilot / Claude / ChatGPT lanes  
Goal: convert Gate C from provisional-pass to evidence-backed decision input.

## 1) Why Gate C Exists

Gate A/B can prove closure quality and consistency, but cannot prove engineering value.
Gate C is the outcome layer that answers:
- Is reviewer burden improving?
- Are reopen/revert events decreasing?
- Is integration behavior stable?

Without Gate C, expansion decisions risk becoming governance-theater decisions.

## 2) Metrics to Capture

## 2.1 Reviewer Minutes

Definition:
- `review_minutes_per_run = review_end - review_start`
- unit: minutes (integer or one decimal)

Capture rule:
- Start: reviewer opens run evidence package
- End: reviewer finishes decision for that run (`accept` / `accept_with_note` / `reject`)

Output fields:
- `review_start_utc`
- `review_end_utc`
- `review_minutes`
- `review_decision`

## 2.2 Reopen/Revert Rate

Definition:
- `reopen_revert_rate = (reopen_count + revert_count) / total_changes`

Where:
- `reopen_count`: number of runs reopened after initial reviewer decision
- `revert_count`: number of accepted runs later reverted due to quality/safety concerns
- `total_changes`: total accepted run changes in the same observation window

Output fields:
- `reopen_count`
- `revert_count`
- `total_changes`
- `reopen_revert_rate`

## 2.3 Integration Stability

Definition:
Operational stability after merge/landing, not just test pass.

Minimum indicators:
- `post_merge_incident_count` (within observation window)
- `integration_block_count` (dependency/compatibility blocks)
- `stability_note` (short reviewer/system note)

Output fields:
- `post_merge_incident_count`
- `integration_block_count`
- `integration_stability_status` (`stable|minor_fluctuation|unstable`)
- `stability_note`

## 3) Data Collection Workflow (Per Run)

1. Run completes Gate A/B evidence package.
2. Reviewer logs review start/end timestamps.
3. Reviewer decision is recorded.
4. If reopened/reverted later, append event to window log.
5. At window close, compute lane-level Gate C metrics.

## 4) Window-Level Rollup

For each lane and each window:
- `avg_review_minutes`
- `median_review_minutes`
- `p90_review_minutes`
- `reopen_revert_rate`
- `integration_stability_status`

Recommended output file:
- `docs/status/gate-c-window-report-YYYY-MM-DD.md`

## 5) Decision Threshold Guidance (Initial)

Use as review triggers, not hard policy:

1. Reviewer burden drift:
- if `avg_review_minutes` increases >20% window-over-window without quality gain -> investigate

2. Reopen/revert drift:
- if `reopen_revert_rate` increases for 2 consecutive windows -> pause expansion

3. Stability drift:
- if `integration_stability_status=unstable` in any lane -> freeze lane expansion and run root-cause review

## 6) Minimal Reporting Template

```yaml
window_id: ""
lane: "copilot|claude|chatgpt"

review_effort:
  avg_review_minutes: 0
  median_review_minutes: 0
  p90_review_minutes: 0

quality_rework:
  reopen_count: 0
  revert_count: 0
  total_changes: 0
  reopen_revert_rate: 0.0

integration_stability:
  post_merge_incident_count: 0
  integration_block_count: 0
  integration_stability_status: "stable|minor_fluctuation|unstable"
  stability_note: ""

gate_c_result: "pass|provisional-pass|pause"
```

## 7) Practical Start (this week)

Phase 1 (lightweight):
- Start manual timestamp capture for next 10 runs per lane
- Start reopen/revert event log immediately
- Add one stability note per lane per window

Phase 2 (after one window):
- Normalize to one parser/report script
- Compare lane deltas and feed expansion decision

## 8) Boundary

Gate C does not replace Gate A/B.
Gate C is decision augmentation for outcome value, not correctness certification.

