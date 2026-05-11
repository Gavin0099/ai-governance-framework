# Gate C Three-Lane Ingest Checklist (2026-05-11)

Window ID (canonical): `gate-c-window-2026-05-11`

Purpose:
- make Copilot / Claude / ChatGPT Gate C inputs auditable under one schema
- remove provisional-pass data gaps

---

## 1) Required Files (must exist)

- [ ] `docs/status/gate-c-review-log.ndjson`
- [ ] `docs/status/gate-c-rework-log.ndjson`
- [ ] `docs/status/gate-c-stability-log.ndjson`

---

## 2) Schema Checklist

## 2.1 Review log (per row)

Required keys:
- [ ] `window_id`
- [ ] `lane` (`copilot|claude|chatgpt`)
- [ ] `run_id`
- [ ] `review_start_utc`
- [ ] `review_end_utc`
- [ ] `review_minutes`

Validation rules:
- [ ] `window_id == gate-c-window-2026-05-11`
- [ ] `review_end_utc >= review_start_utc`
- [ ] `review_minutes >= 0`

Minimum volume:
- [ ] Copilot valid rows >= 10
- [ ] Claude valid rows >= 10
- [ ] ChatGPT valid rows >= 10

## 2.2 Rework log (per row)

Required keys:
- [ ] `window_id`
- [ ] `lane`
- [ ] `run_id`
- [ ] `reopen_count`
- [ ] `revert_count`
- [ ] `total_changes`
- [ ] `reopen_revert_rate`

Validation rules:
- [ ] `window_id == gate-c-window-2026-05-11`
- [ ] `total_changes > 0`
- [ ] `reopen_revert_rate == (reopen_count + revert_count) / total_changes`

## 2.3 Stability log (per row)

Required keys:
- [ ] `window_id`
- [ ] `lane`
- [ ] `run_id`
- [ ] `integration_stability` (`stable|degraded`)
- [ ] `stability_note`

Validation rules:
- [ ] `window_id == gate-c-window-2026-05-11`
- [ ] `integration_stability != unknown`

---

## 3) Lane-by-Lane Ingest Checklist

## 3.1 Copilot lane

- [ ] review log rows ingested (>=10)
- [ ] rework log row(s) ingested with valid denominator
- [ ] stability log row(s) ingested
- [ ] lane-level Gate C recomputed

## 3.2 Claude lane

- [ ] review log rows ingested (>=10)
- [ ] rework log row(s) ingested with valid denominator
- [ ] stability log row(s) ingested
- [ ] lane-level Gate C recomputed

## 3.3 ChatGPT lane

- [ ] review log rows ingested (>=10)
- [ ] rework log row(s) ingested with valid denominator
- [ ] stability log row(s) ingested
- [ ] lane-level Gate C recomputed

---

## 4) Upgrade Gate (provisional-pass -> pass)

Upgrade only when all are true:
- [ ] All three lanes have >=10 valid review timing rows
- [ ] All three lanes have valid reopen/revert denominator (`total_changes > 0`)
- [ ] All three lanes have non-unknown stability entries
- [ ] `avg_review_minutes` is computed from valid rows per lane

If any unchecked:
- keep `provisional-pass`
- do not publish cross-agent pass decision

---

## 5) Final Sign-off

- Reviewer:
- Date:
- Result: `pass | provisional-pass | pause`
- Notes:

