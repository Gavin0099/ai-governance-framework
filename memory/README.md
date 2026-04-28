# memory/ README

This directory is the shared memory channel for this repository.

## Canonical Files
- `00_long_term.md`: curated long-term memory for main sessions
- `YYYY-MM-DD.md`: daily session logs and post-push entries

## Cross-Agent Rule
- Treat files in this `memory/` directory as the only cross-agent memory authority for this repo.
- Do not use external/private agent memory files (for example `C:\Users\reiko\.claude\projects\...\memory\MEMORY.md`) as governance truth for this repo.
- If useful context exists only outside the repo, copy a concise, auditable summary into this directory before relying on it.
