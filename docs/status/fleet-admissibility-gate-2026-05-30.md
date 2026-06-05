# Fleet Admissibility Gate Snapshot (2026-05-30)

Scope: `usb-if-hub-spec-reference`, `Bookstore-Scraper`, `financial-pdf-reader`, `meiandraybook`
Purpose: determine whether current cross-repo evidence is sufficient to let `ai-governance-framework` advance claim ceiling.

## Gate Criteria

Pass conditions (minimum):
- `baseline_present = true`
- `framework_lock_present = true`
- `head_match = true`
- `latest_closeout_status = valid` (or equivalent non-missing admissible closeout state)

If closeout status is `missing`, claim ceiling is capped to procedural adoption only.

## Evidence Table (as checked on 2026-05-30)

| Repo | baseline_present | framework_lock_present | head_match | dirty_count | closeout_count | latest_closeout_status | Gate |
|---|---:|---:|---:|---:|---:|---|---|
| usb-if-hub-spec-reference | true | true | true | 14 | 0 | missing | FAIL |
| Bookstore-Scraper | true | true | true | 22 | 5 | missing | FAIL |
| financial-pdf-reader | true | true | true | 0 | 0 | missing | FAIL |
| meiandraybook | true | true | true | 27 | 50 | missing | FAIL |

## Decision

`ai-governance-framework` should **not** advance to a higher claim ceiling based on this snapshot.

Current admissible fleet-level claim:
- `procedural adoption observed`

Current inadmissible fleet-level claims:
- `operational verification established`
- `closeout discipline established`
- `authority-ready governance evidence established`

## Blocking Pattern

Common blocker across all four repos:
- `latest_closeout_status = missing` (or no closeout artifact present)

This is a consumption/admissibility blocker, not an installation blocker.

## Next Step (Convergence Only)

1. Bring each repo to one admissible latest closeout (non-missing closeout state).
2. Re-run this same gate table with identical criteria.
3. Keep claim ceiling capped until all required repos clear closeout admissibility.
