---
name: reviewer-handoff
description: Build reviewer-facing governance summaries for this repository. Use when Codex needs to summarize trust signals, release state, reviewer handoff packets, publication artifacts, or the shortest reviewer entrypoint across release, trust, and adoption surfaces.
---

# Reviewer Handoff

Use the highest-level reviewer surface that answers the request.

## Workflow

1. Start from `reviewer_handoff_summary.py` when the user wants one reviewer packet.
2. Use `reviewer_handoff_snapshot.py` when the result should be preserved as latest/history/index artifacts.
3. Use the reader tools when the user already has a manifest or publication path.
4. Pull in trust-signal or release-surface detail only when the top-level packet is insufficient.

## Commands

Read `references/commands.md` for the normal command paths.

## Gotchas

Read `references/gotchas.md` before adding new reviewer-facing flows or interpreting missing publication artifacts.

## Output Expectations

- Start summary-first.
- Keep reviewer language concrete and operational.
- Distinguish current status from historical limitations.
- Prefer one reviewer entrypoint over a file-by-file dump.
