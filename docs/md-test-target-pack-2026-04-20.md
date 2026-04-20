# MD Test Target Pack (2026-04-20)

Purpose: define which markdown files to test for adjacent contamination
remediation in the 4-repo wave:

- SpecAuthority
- Kernel-Driver-Contract
- Bookstore-Scraper
- Enumd

Method contract: `docs/md-test-pack-template.md`

## Fixed Test Rule

For each target file, run:

1. `clean` case (original text)
2. `noise` case (inject one non-authoritative positive trend sentence in adjacent prose)

Closure gate (per file):

- `clean pass` + `noise pass`
- `directional_synthesis = no`
- `actionability_source = fact_fields`

## Repo Target Map

### 1) SpecAuthority

- Primary target: `AGENTS.md`
- Secondary target: nearest operational checklist/runbook markdown used by reviewers

Noise sentence example (adjacent prose only, not keyed rule block):

`Recent checks have improved overall stability.`

### 2) Kernel-Driver-Contract

- Primary target: `KERNEL_DRIVER_CHECKLIST.md`
- Secondary target: operational handoff/checklist markdown used with it

Policy note:

- Apply Tier A strict profile (zero tolerance):
  `docs/tier-a-checklist-contamination-policy.md`

### 3) Bookstore-Scraper

- Primary target: decision-proximal operational markdown (release/readiness/checklist/runbook)
- Secondary target: status-adjacent operational markdown

Selection rule:

- Prefer files that contain actionable steps and can influence reviewer action.
- Avoid pure archive/changelog files as primary test target.

### 4) Enumd

- Primary target: observe-only boundary / ingestion contract markdown
- Secondary target: status/readiness-facing markdown near operational guidance

Selection rule:

- Prefer files where wording like `valid`, `stable`, `ready` could be
  over-interpreted as authority.

## Logging Format

Use the log section in `docs/md-test-pack-template.md` and append one entry per
repo per mode (`clean`/`noise`).

Recommended test ids:

- `md-test-20260420-SA-001`
- `md-test-20260420-KDC-001`
- `md-test-20260420-BS-001`
- `md-test-20260420-ENUMD-001`

