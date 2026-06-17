# Governance Mutation Memory-Gap Advisory Spec

Status: design-only
Runtime behavior change: no
Enforcement change: no
Commit/push status: not committed
Phase posture: Phase E / failure-driven advisory candidate

## Problem

Consuming repositories can perform governance-surface mutations without a
corresponding canonical memory record in the consuming repository.

This is not the same as daily memory freshness. `memory/YYYY-MM-DD.md` files are
append-only evidence records, not status surfaces that must refresh every day.
The observed risk is narrower:

```text
governance mutation happened
but no repo-local canonical memory evidence records that mutation
```

The triggering example is the CFU audit supplied in-session. Evidence source:
user-supplied read-only CFU audit transcript; not reverified in this spec slice.

- `CFU/memory/` latest canonical daily file: `2026-06-04.md`
- `91a387b` on 2026-06-08 updated `ai-governance-framework` submodule without
  matching CFU memory evidence
- `7706802` on 2026-06-16 updated `ai-governance-framework` submodule without
  matching CFU memory evidence
- CFU had framework lock and managed hooks, but lacked an `AGENTS.md`
  `governance:key=memory_workflow` router section
- CFU closeout wiring targeted the CFU project root, but pure git-level
  submodule updates did not necessarily pass through an instrumented session
  closeout path

This spec treats that as a memory-evidence gap for consuming repositories, not
as a mandate that every repository must produce daily memory records.

## Target Outcome

Design an advisory-only diagnostic that can identify likely consuming-repo
memory capture gaps when governance surfaces change without matching
repo-local memory evidence.

The intended output is a warning such as:

```text
governance_memory_gap_advisory:
  governance surface changed in this repository
  but no matching repo-local canonical memory entry was found
  this is advisory evidence only, not a blocking failure
```

The advisory should help reviewers and agents distinguish:

- acceptable memory silence: no governance-relevant activity occurred
- evidence gap: governance mutation occurred but no canonical memory note exists

## Scope

In scope for a future implementation tranche:

- detect governance-surface commits or current diffs in consuming repositories
- check for matching repo-local canonical memory evidence
- report warning-only diagnostics in read-only verification paths
- keep the warning separate from daily freshness checks
- preserve repo-local memory authority by requiring the target repo's
  `memory/` directory, not the framework repo's `memory/` directory

Candidate governance-surface signals:

- submodule pointer update to `ai-governance-framework`
- `governance/framework.lock.json`
- `.governance/baseline.yaml`
- `.governance-payload-config.yaml`
- `AGENTS.md`
- `AGENTS.base.md`
- `PLAN.md`
- `.github/copilot-instructions.md`
- managed hook root pointer or hook installation state, where inspectable
- `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`
- `governance/F7_FULL_UPDATE.md`
- `governance/MEMORY_PROTOCOL.md`

Candidate matching memory evidence:

- a repo-local `memory/YYYY-MM-DD.md` entry written by
  `governance_tools.memory_record`
- entry text or metadata referencing the governance mutation, commit, F-7
  update, framework lock update, or adoption/update scope
- date or commit-window correlation with the governance mutation

## Non-Goals

This design does not propose:

- a daily memory freshness gate
- blocking commits because a repository has not written memory recently
- reconstructing missing historical session records
- synthesizing daily memory entries for dates that had no captured session
- treating absent memory as proof of governance failure
- making pre-commit fail on memory silence
- changing `memory_record.py`
- changing `session_end_hook.py`
- changing `session_closeout_entry.py`
- changing hook enforcement semantics
- changing F-7 completion semantics
- changing receipt schema

## Affected Surfaces

Likely future read-only reporting surfaces:

- `governance_tools.f7_full_update`
- `governance_tools.external_repo_readiness`
- `governance_tools.session_closeout_entry`
- reviewer-handoff or adoption-audit reporting

`session_closeout_entry` is listed only as a future candidate surface. It is
not targeted for the first implementation tranche unless separately approved.

Surfaces intentionally not targeted for the first tranche:

- pre-commit blocking
- pre-push blocking
- CI blocking
- runtime closeout schema changes
- fleet-wide rollout automation

## Boundary And API Considerations

The advisory must preserve four boundaries.

1. Repo-local memory authority

   The target repository owns its own memory evidence. A framework repo memory
   entry is not sufficient proof that a consuming repo recorded its own
   governance mutation.

2. Advisory, not enforcement

   The first implementation must report warning evidence only. It should not
   alter exit status unless a future separately reviewed selective-blocking
   decision authorizes that behavior.

3. Governance mutation, not elapsed time

   The detector should trigger from governance-surface activity, not from
   "days since last memory file".

4. Current evidence, not historical reconstruction

   If a gap is found, the correct remediation is one corrective memory note that
   records the gap. It must not fabricate missing daily session evidence.

## Failure Paths Or Risk Points

### False positive: normal memory silence

Some repositories may have no governance-relevant work for days or weeks. The
advisory must not warn solely because memory is old.

### False positive: product-only commits

Product documentation or code commits should not trigger this warning unless
they also touch governance surfaces.

### False negative: pure hook installation

Local `.git/hooks` changes are not tracked by git and may not be visible in
commit history. A future implementation can inspect hook state in readiness
checks, but should not claim complete hook mutation history.

### Authority confusion

The detector must not accept the framework repo memory as a substitute for the
target repo memory. Doing so would recreate cross-repo authority leakage.

### Scope inflation

The advisory must not become a full memory workflow gate, daily-memory gate, or
fleet adoption gate in its first tranche.

## Evidence Plan

A future implementation should include focused evidence:

1. A fixture repository with a governance-surface commit and no matching memory
   entry reports `governance_memory_gap_advisory`.
2. A fixture repository with the same governance-surface commit and matching
   repo-local canonical memory entry reports no warning.
3. A fixture repository with old memory but no governance-surface mutation
   reports no warning.
4. A fixture repository with product-only commits reports no warning.
5. F-7 dry-run or external readiness output includes the advisory without
   changing existing success/failure status.

Suggested output fields:

```json
{
  "governance_memory_gap": {
    "status": "warning",
    "governance_mutation_detected": true,
    "matching_repo_memory_evidence": false,
    "candidate_commits": ["<sha>"],
    "candidate_surfaces": ["governance/framework.lock.json"],
    "claim_ceiling": "advisory only; does not prove governance failure"
  }
}
```

## Implementation Tranche Recommendation

First implementation tranche:

```text
DONE = add read-only governance mutation memory-gap advisory to external repo
readiness/F-7 reporting, with fixture tests; no blocking behavior.
```

Allowed first-tranche files should be limited to:

- one read-only helper or function for classifying governance-surface mutation
- one integration point, preferably `external_repo_readiness` or
  `f7_full_update`
- focused tests and fixtures
- documentation update for advisory meaning

Do not implement more than one reporting surface in the first tranche unless
the first surface cannot expose the advisory cleanly.

## Open Questions

1. Matching window

   Should matching memory evidence be same date, same commit, or within an
   explicit commit range? The safest first version is commit-reference match
   when available, with same-date as advisory context only.

2. Submodule pointer detection

   For submodule consumers, should a gitlink change alone be sufficient to
   count as governance mutation? The CFU trigger suggests yes, but this needs a
   fixture.

3. Corrective memory recommendation

   Should the advisory print an exact `memory_record.py --project-root <repo>`
   command? This would improve recovery, but must avoid suggesting historical
   reconstruction.

4. Router coverage

   Should missing `AGENTS.md` memory workflow router be a separate warning or a
   contributing reason under this advisory? The CFU audit suggests it is a
   contributing structural cause, but not the same defect.

## Claim Ceiling

This spec supports only:

- a design target for warning on likely consuming-repo governance memory gaps
- a distinction between governance mutation evidence gaps and daily memory
  freshness
- a proposed first implementation tranche

This spec does not support claiming:

- the advisory exists
- consuming repos are now protected from memory gaps
- missing daily memory is a governance failure
- CFU has been corrected
- pre-commit or pre-push enforcement changed
- F-7 semantics changed
