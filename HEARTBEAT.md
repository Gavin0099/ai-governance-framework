# HEARTBEAT.md

## Fleet Freshness (Observe-Only)

Run this check during heartbeat cadence (e.g., 2-4 times/day):

`python -m governance_tools.required_freshness_probe --project-root . --format human`

Decision boundary:
- If all required repos are `ok`: reply `HEARTBEAT_OK` with short status.
- If any repo is `warning` / `critical` / `expired`: report repo names and remaining_days.

Hard rules:
- Do not run closeout automatically from heartbeat.
- Do not mutate repo state during heartbeat freshness checks.
- Freshness probe is observation only; remediation remains event-driven and manual.
