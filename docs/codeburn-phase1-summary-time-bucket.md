# CodeBurn Phase1 Summary Time Bucket Rule

Version: `v1.0.0`  
Applies to: `Script/codeburn_phase1_7day_summary.py`

## Rule

- Day bucket is derived from `sessions.created_at` using UTC date extraction.
- Implementation uses `substr(created_at, 1, 10)` where `created_at` is ISO-8601 with UTC offset.
- Therefore `--start-day` and `--end-day` are interpreted against UTC day buckets.

## Practical Impact

- A session created at local `2026-05-05 00:30 +08:00` is stored as
  `2026-05-04T16:30:00+00:00` and belongs to UTC day `2026-05-04`.
- If the summary window uses local-day assumptions without UTC conversion,
  `session_count=0` can appear unexpectedly.

## Operational Guidance

- Always pass explicit DB path and schema path in session/run commands.
- When validating a known session, query the session's `created_at` first, then
  choose `--start-day/--end-day` by UTC date.
- Do not classify UTC/local bucket mismatch as ingestion failure.
