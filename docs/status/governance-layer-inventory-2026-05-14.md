# Control-Layer Inventory (R1)

As-of: 2026-05-14

| layer_id | layer_name | type | runtime_cost | expected_reliability_impact | status_hypothesis |
|---|---|---|---|---|---|
| L01 | pre-task checks | assurance | low | medium | keep |
| L02 | post-task checks | assurance | low | medium | keep |
| L03 | session closeout audit | assurance | low | low | uncertain |
| L04 | daily memory guard | control | low | medium | keep |
| L05 | pre-push memory gate | control | low | high | keep |
| L06 | runtime-governance smoke | assurance | medium | medium | keep |
| L07 | full enforce runtime suite | control | high | high | uncertain |
| L08 | claim boundary linting | assurance | low | medium | keep |
| L09 | version bump advisory | assurance | low | low | candidate_remove |
| L10 | side-effect boundary model | control | medium | high | keep |

## Notes

- This table is a starting hypothesis and must be validated by R3 compression runs.
- `runtime_cost` should later be quantified with token/latency/operator-minutes.
