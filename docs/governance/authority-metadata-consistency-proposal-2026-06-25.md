# Governance Authority Metadata Consistency Proposal - 2026-06-25

Status: proposal-only
Scope: docs-only planning artifact
Runtime impact: none in this slice

## Problem

The AUTHORITY repair slice exposed a structural drift risk: the human-facing
`governance/AUTHORITY.md` table can diverge from the live authority metadata in
each `governance/*.md` file's frontmatter.

The live `session_start` authority filter is driven by
`governance_tools.authority_loader.load_authority_table(governance_dir)`, which
parses each governance markdown file's frontmatter. The `AUTHORITY.md` table is
therefore a registry mirror, not the runtime source of truth for
`allowed_governance_files`.

If the table and frontmatter disagree, a reviewer can believe the authority tier
has been repaired while runtime behavior still follows stale frontmatter. The
recent `governance/PLAN.md` repair fixed one P0 instance. This proposal scopes
the next step: detect and prevent the class of table-vs-frontmatter drift without
changing enforcement yet.

## Current repository truth

Current verified facts from the AUTHORITY freshness work:

- `authority_loader.load_authority_table(governance_dir)` scans
  `governance/*.md` and parses frontmatter.
- `filter_for_session(...)` builds the live allowed governance file set from
  frontmatter-derived rows.
- `runtime_hooks/core/session_start.py` consumes that authority table and
  validates `allowed_governance_files`.
- `governance/AUTHORITY.md` contains a manually maintained table that mirrors
  intended metadata.
- `governance/PLAN.md` was repaired by changing both frontmatter and the
  `AUTHORITY.md` table row. The focused tests now check the live frontmatter
  behavior.

Important boundary:

- Editing only `governance/AUTHORITY.md` can change reviewer-facing prose while
  leaving runtime filtering unchanged.
- Editing only frontmatter can change runtime filtering while leaving the human
  registry stale.

## Target outcome

Define a narrow consistency check that can compare the `AUTHORITY.md` table
against governance document frontmatter and report mismatches before they become
claim drift.

The first useful outcome is a reviewer-facing diagnostic, not an enforcement
gate.

## Scope

Covered by this proposal:

- `governance/AUTHORITY.md` authority table rows for repo-local governance docs;
- frontmatter fields in tracked `governance/*.md` documents;
- fields that directly affect authority semantics:
  - `audience`
  - `authority`
  - `can_override`
  - `overridden_by`
  - `default_load`
- detection/reporting strategy;
- validation scope for a future checker;
- failure modes and claim ceiling.

Not covered:

- runtime behavior changes;
- hook or validator enforcement changes;
- rewriting governance doctrine;
- broad freshness cleanup;
- external repo adoption.

## Non-goals

This proposal does not authorize:

- editing `governance/AUTHORITY.md`;
- editing any `governance/*.md` frontmatter;
- changing `governance_tools/**`;
- changing `runtime_hooks/**`;
- changing hook, validator, CI, or enforcement behavior;
- declaring all authority metadata consistent;
- declaring all governance documents fresh.

## Affected surfaces for a future implementation

Likely implementation surfaces:

- a read-only checker under `governance_tools/` or `tools/`;
- focused tests for table parsing and mismatch reporting;
- optional documentation update explaining that frontmatter is live input and
  the AUTHORITY table is a mirror.

Surfaces that should not be touched in the first implementation tranche:

- `runtime_hooks/core/session_start.py`;
- `governance_tools.authority_loader` filtering semantics;
- hook installation or pre-push enforcement;
- prompt docs such as `SYSTEM_PROMPT.md` and `AGENT.md`.

## Detection strategy

Recommended future checker behavior:

1. Parse live authority metadata from `governance/*.md` frontmatter.
2. Parse the `governance/AUTHORITY.md` table.
3. Normalize paths so `governance/PLAN.md` in the table maps to
   `governance/PLAN.md` on disk.
4. Compare only fields with direct authority semantics:
   `audience`, `authority`, `can_override`, `overridden_by`, `default_load`.
5. Report:
   - table row missing for a frontmatter-bearing governance doc;
   - frontmatter missing for a table-listed governance doc;
   - field mismatch;
   - non-repo-local rows skipped with reason;
   - glob / abstract rows skipped with reason.
6. Exit zero in the first implementation tranche unless explicitly invoked in a
   failure mode.

The initial checker should be diagnostic-only. It should not block commits or
pushes until the mismatch model is reviewed against existing historical drift.

## Validation scope

Focused validation for a future implementation:

- unit tests for parsing `AUTHORITY.md` table rows;
- unit tests for normalizing repo-local governance paths;
- unit tests for mismatches in each semantic field;
- unit tests for skipped abstract rows such as external domain contracts or
  glob-like entries;
- integration check against the current repo showing either:
  - no mismatches after known repairs; or
  - explicit reviewed mismatches with documented disposition.

The validation must distinguish:

- "runtime frontmatter changed" from "registry table changed";
- "diagnostic mismatch found" from "enforcement failure";
- "repo-local governance doc" from "abstract registry row."

## Failure modes or risk points

1. Table-only false repair

A future change edits `AUTHORITY.md` and claims authority tier repair, but the
frontmatter remains unchanged. Runtime behavior does not change.

2. Frontmatter-only hidden behavior change

A future change edits frontmatter and changes `session_start` filtering, but
`AUTHORITY.md` still advertises the old authority tier.

3. False positives from abstract rows

The AUTHORITY table contains rows that are not direct repo-local files, such as
domain contract summaries or glob-like references. A checker must skip or label
these rather than treating them as missing files.

4. Enforcement too early

Turning the checker into a pre-push or CI blocker before reviewing historical
drift could block unrelated work on legacy inconsistency.

5. Freshness overreach

Metadata consistency is not the same as document freshness. A file can have
matching metadata and still contain stale content.

6. Injection overclaim

Consistency of authority metadata does not prove full document text injection
into the model prompt. It only supports claims about frontmatter-driven
authority filtering and registry consistency.

## Claim ceiling

This proposal may claim:

- a proposed table-vs-frontmatter consistency strategy;
- fields to compare;
- likely future implementation surfaces;
- validation expectations;
- diagnostic-only first-tranche posture.

This proposal must not claim:

- a checker exists;
- metadata consistency has been verified;
- any mismatch has been fixed;
- `AUTHORITY.md` has been edited;
- frontmatter has been edited;
- session_start behavior has changed;
- hooks, validators, CI, or enforcement have changed;
- full governance document freshness is repaired;
- prompt text injection behavior has been proven.

## Implementation tranche recommendation

Recommended next tranche after this proposal is reviewed:

1. Add a read-only authority metadata consistency checker.
2. Add focused tests for table parsing, frontmatter parsing, normalization, and
   mismatch reporting.
3. Run the checker against the current repo in report-only mode.
4. Record canonical memory bound to the checker source commit.

Do not add hook, CI, pre-push, or enforcement wiring in the first implementation
tranche.

