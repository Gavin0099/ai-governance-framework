# Capture Quality Fixed-Window Cadence (v0.1)

- date: 2026-05-13
- scope: cadence only
- repo focus: `writing-contract` (current live capture surface)

## Purpose

Keep capture-quality observation stable without governance-surface expansion.

## Boundary

- capture quality only
- no KPI fill
- no agent capability ranking
- no new gate/checklist/validator

## Fixed Checks (End-of-work)

Run the same three checks:

1. schema/field diff
2. lanes/providers set
3. drift metrics (`schema_complete_rate`, `missing_capture_rate`, `hard_rule_violations`)

## Trigger Rules (Open New +10 Window Only If)

Open a new +10 observation window only when at least one condition is true:

1. schema/field diff is non-empty
2. a new lane or provider appears
3. drift is not `100 / 0 / 0`

If none of the conditions are true, do not open a new window.

## Routine

1. execute normal engineering work
2. observe the three fixed checks
3. update the same summary surface only when needed
4. append memory entry and push after accepted change

## Current Baseline Snapshot

- source: `writing-contract/docs/status/capture-quality-summary-2026-05-12.md`
- last known window: `88-run`
- lane distribution: `single-lane=28`, `copilot=30`, `claude=30`
- drift: `100.0 / 0.0 / 0`
