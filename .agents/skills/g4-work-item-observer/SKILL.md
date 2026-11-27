---
name: g4-work-item-observer
description: Read-only pilot observer that summarizes delivery, Owner interventions, complete AI token cost (main + Guardian + sub-agents), and Observer self-cost for a single natural consumer Work Item without adding gates, hooks, or runtime changes.
---

# G4 Work Item Observer (Read-Only Pilot)

## Purpose

Observe a completed natural Consumer Work Item from raw evidence and emit:
1. A concise 1-page decision report (`report.md`)
2. A redacted machine-readable evidence index (`evidence_index.json`)

This skill is an **experiment** for Gate 4 operational visibility. It does **not** add a governance gate, hook, dashboard, database, or merge blocker.

## Hard Rules (Non-Negotiable)

1. **Strictly Read-Only**: Never modify consumer files, receipts, memory, PRs, CI, or governance runtime.
2. **Independent Observation**: The executing AI must not grade itself or declare final PASS; run this skill in an independent read-only pass after the Work Item completes.
3. **One Work Item Unit**: Group all sessions, PRs, and fix rounds belonging to one natural Work Item into a single observation.
4. **Honest Unknowns & Completeness Separation**:
   - Separate `parsed_files_valid` (found JSONL files parsed cleanly) from `work_item_cost_complete` (all expected participating sessions, including Guardian/sub-agents, are proven present). Without an explicit verified session inventory (`--expected-session-id`), report `known_totals` with `cost_completeness=incomplete` and `comparability_token=0`.
   - Missing intervention logs → `UNKNOWN` (never `0`).
   - Missing Owner-confirmed minutes → `UNKNOWN` (never substitute wall-clock duration).
5. **Four-Tier Delivery Separation**: Report `Code Completed`, `Merged + CI`, `Product Verified`, and `Deployed / Enabled` separately. An `OPEN` PR alone is `NOT_VERIFIED`; `Product Verified` requires a verifiable non-empty `--product-evidence-file` (never trust an unbacked status flag).
6. **Privacy, Redaction & Long-Term Archive**: Never commit or upload raw Codex rollout JSONL files, raw user photos, raw conversation logs, or local absolute paths to GitHub. Output only redacted basename+SHA-256 references and aggregated counts. To archive a completed Work Item for long-term comparison, pass `--archive-root docs/status/g4-observer` so `report.md`, `evidence_index.json`, and `INDEX.md` are persisted cleanly even when some fields are honestly `UNKNOWN`.
7. **Observer Self-Cost**: Always record Observer execution duration; script-only runs report `0` script LLM tokens while noting that any separate Observer AI analysis must be accounted for (`--observer-mode llm_assisted --observer-ai-tokens <N>` or `UNKNOWN`).

## Procedure

Run the read-only script against the Work Item's authorized evidence paths:

```bash
python scripts/g4_work_item_observer.py \
  --work-item-id <WORK_ITEM_ID> \
  --title "<Short Title>" \
  --repo <owner/repo> \
  --rollout-dir <path/to/codex/sessions> \
  --archive-root docs/status/g4-observer
```

Optional flags:
- `--output-dir <path/to/local/output>` (optional when `--archive-root` is provided)
- `--archive-root <path/to/docs/status/g4-observer>` (writes redacted `<WORK_ITEM_ID>/report.md` & `evidence_index.json` and updates `INDEX.md`)
- `--pr <number>` (repeatable; if omitted, attempts read-only `gh pr list --search <WORK_ITEM_ID>`)
- `--exclude-session-id <id>` (e.g., to separate pre-run probe sessions with explicit disclosure)
- `--events-file <path/to/interventions.json>` (if structured intervention log exists)
- `--owner-minutes-confirmed <float>` (only when explicitly confirmed by Owner)
- `--product-verified <status>` / `--deployed-status <status>` (only backed by real evidence)

## S0 v0.2 Provider and Rescue Boundaries

- `--claude-dir <path>` accepts Claude JSONL files or recursive directories. `--gemini-dir <path>` accepts Gemini JSONL and session JSON files or recursive directories. Both flags are repeatable. For split transcripts, pass files in update order. Use `--claude-expected-session-id <id>` and `--gemini-expected-session-id <id>` (repeatable) to select and verify the respective provider's expected sessions. A file stem can match an inventory when the log has no embedded session ID.
- Claude and Gemini report `measured` when token usage is observed, `confirmed_unused` with an explicit `--claude-confirmed-unused` or `--gemini-confirmed-unused`, or `unknown` when usable evidence is missing. Missing token counts stay unknown. Completeness covers only the provider's expected sessions.
- `--copilot-csv <path>` (repeatable) reads daily billing exports. Valid rows are `billing_reference_only` and show AI credits by model and billing window. The figures exclude completions and monetary columns and have no work-item attribution. Use `--copilot-confirmed-unused` with explicit confirmation. Evidence takes precedence over contradictory unused confirmations.
- `--outer-orchestrator <name>` records an explicitly named orchestrator with unknown usage. Codex usage stays in the existing top-level `ai_cost` fields. Provider summaries use redacted source references and retain their own units. Cross-provider summation is disabled.
- `--rescue-evidence-ref <ref>` (repeatable) accepts short references such as `PR#123` and hashes paths and free-form references. A reference or a logged `unplanned_rescue` sets `human_interventions.unexpected_rescue_observed` to `yes`. Use `--rescue-confirmed-none` only with Owner confirmation or a complete intervention log. It records `no` when there is no rescue evidence. Contradictory confirmation is recorded and evidence takes precedence. Without evidence or explicit confirmation the status is `unknown`, even if an event list has zero rescue entries.

## Non-Claims

Observer output does **not** prove ROI, does **not** rank agents across tasks of differing complexity, and has **no** authority to approve or block merges.
