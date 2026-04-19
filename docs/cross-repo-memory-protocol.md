# Cross-Repo Memory Protocol

Use this protocol in any repository to keep execution continuity consistent.

## Trigger

- Main session and a push just completed.

## Required Write

- Append one compact line/block to `memory/YYYY-MM-DD.md`.
- Include exactly four fields:
  - `what_changed`
  - `commit`
  - `test_evidence`
  - `next_step`

## Long-Term Promotion Rule

- If the change establishes a stable workflow preference, also update `memory/00_long_term.md`.
- Keep long-term memory curated; do not duplicate every daily detail.

## Portable Template

```md
- what_changed: ...
  commit: ...
  test_evidence: ...
  next_step: ...
```
