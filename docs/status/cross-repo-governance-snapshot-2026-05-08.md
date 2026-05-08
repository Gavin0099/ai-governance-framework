# Cross-Repo Governance Snapshot (2026-05-08)

Scope: fast observability scan across 9 repos for runtime verdict presence, session closeout coverage, and payload-audit availability.

## Summary Table

| Repo | Verdicts | Session Index | Closeout Valid | Closeout Missing | Payload JSONL | Notes |
|---|---:|---|---:|---:|---:|---|
| `hp-firmware-stresstest-tool` | 0 | no | 0 | 0 | 0 | governance runtime not yet producing verdict/session surfaces |
| `cli` | 42 | yes | 1 | 41 | 0 | runtime active; closeout completion is bottleneck |
| `CFU` | 0 | no | 0 | 0 | 2 | payload-audit exists; runtime closeout surfaces absent |
| `Bookstore-Scraper` | 43 | no | 0 | 0 | 0 | verdict artifacts exist without session index exposure |
| `AITradeExecutor` | 0 | no | 0 | 0 | 0 | no observable runtime governance artifacts |
| `meiandraybook` | 31 | yes | 0 | 31 | 3 | runtime active; all observed closeouts missing |
| `IsptoolRefine2018_EndUser_Tool` | 4 | yes | 0 | 4 | 0 | early adoption footprint; closeout completion gap |
| `Hearth` | 3 | yes | 0 | 3 | 0 | early adoption footprint; closeout completion gap |
| `gl_electron_tool` | 37 | yes | 1 | 36 | 2 | runtime active; closeout completion is primary gap |

## Key Findings

1. Two distinct adoption states exist:
   - Runtime-active repos with strong verdict volume but weak closeout completion (`cli`, `meiandraybook`, `gl_electron_tool`).
   - Repos with minimal or no runtime governance surface (`hp-firmware-stresstest-tool`, `AITradeExecutor`, partial in `CFU`).
2. `closeout_missing` dominates where session index exists (notably `cli`, `meiandraybook`, `gl_electron_tool`), indicating operational/manual closeout discipline gap rather than runtime hook outage.
3. Payload observability is uneven (`CFU`, `meiandraybook`, `gl_electron_tool`) and not yet aligned with verdict/session surfaces repo-wide.

## Priority Actions (No Spec Expansion)

1. Priority P0 (operational): raise closeout completion in runtime-active repos.
   - `cli`: 1/42 valid
   - `gl_electron_tool`: 1/37 valid
   - `meiandraybook`: 0/31 valid
2. Priority P1 (surface parity): ensure `session-index.ndjson` is present wherever verdicts are being produced.
3. Priority P2 (observability parity): align payload-audit lane with runtime closeout lane for cross-repo comparability.

## Decision

This snapshot supports staying in an observation-first mode:
- keep v1.2 frozen,
- improve closeout completion discipline before adding metrics/features,
- then evaluate trend deltas over the next 10-run windows per active repo.
