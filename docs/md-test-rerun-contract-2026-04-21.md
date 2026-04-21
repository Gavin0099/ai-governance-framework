# MD Test Rerun Contract (2026-04-21)

Purpose: define a closure-grade rerun contract before executing any new md-test
wave, so interpretation and evidence stay in the same version boundary.

Status before rerun:

- scope filter compliance: `unverified`
- closure state: `open remediation`

## Input Contract

- Repos:
  - `SpecAuthority`
  - `Kernel-Driver-Contract`
  - `Bookstore-Scraper`
  - `Enumd`
  - `cli`
- Scope: filtered target set only (no whole-repo broad scan).
- Target list source:
  - `artifacts/contracts/md-test-rerun-contract-2026-04-21.json`
- Scope policy references:
  - `docs/md-test-scope-filter-2026-04-20.md`
  - `docs/md-test-target-pack-2026-04-20.md`

## Tooling Contract

- Runner: `scripts/run_md_noise_test.py`
- Summary: `scripts/summarize_md_report.py`
- Output schema:
  - `artifacts/schemas/md-noise-rerun-report.schema.json`
- Tooling commit lock: `pending`

## Output Invariants

Each closure target must satisfy:

- `clean_status = pass`
- `noise_status = pass`
- `directional_synthesis = no`
- `actionability_source = fact_fields`

Repo closure gate fails when any target violates invariants or target files are
missing.

## Output Artifact

- `artifacts/md_noise_rerun_report_2026-04-21.json`

## Decision Rule

- Rerun result can confirm or overturn the current report narrative.
- Report interpretation must be updated from rerun outputs, not the reverse.
