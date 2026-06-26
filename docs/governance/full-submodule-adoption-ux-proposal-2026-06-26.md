# Full / Submodule Adoption UX Proposal - 2026-06-26

Status: proposal-only
Scope: docs-only planning artifact
Runtime behavior change: no
Tooling behavior change: no
Enforcement change: no

## Problem

The current adoption path makes the easiest command look more complete than it
is.

`governance_tools/adopt_governance.py` is the natural first command for a new
consumer. It installs or refreshes the copy-based audit surface, but it does not
make the target repository self-contained for governed runtime use. A first-time
adopter can see `adopt` succeed and `governance_drift_checker` pass, then infer
that AI Governance is fully installed even though `governance_tools`,
`runtime_hooks`, and the runtime snapshot still resolve from an external
framework checkout or are absent from the target repository.

This is an onboarding UX failure, not a proof that thin/copy adoption is wrong.
Thin adoption remains valid for audit-only classification and review wording.
It is the wrong default mental model for repositories that the team owns,
modifies, and expects to govern during cross-platform or low-level code work.

The observed HBPlus.Avalonia onboarding logs show the failure mode:

- a thin adoption pass was initially described as complete because baseline and
  drift checks passed;
- later runtime checks exposed that execution surfaces were not self-contained;
- the repository was manually migrated to a submodule consumer path;
- the manual submodule path exposed further risks: stale pin selection,
  root-level leftover `runtime_hooks`, confusion between target repo
  `source_commit` and framework submodule pin, and partially failing framework
  full-suite tests.

The framework already has README-level classification reminders. Those reminders
did not prevent the observed wrong-mode interpretation. Therefore the first
repair should put the adoption-class boundary in the tool output that users see
while running adoption, not only in documentation they may not read.

## Current Repository Truth

Observed current facts in this repository:

- `governance_tools/adopt_governance.py --help` exposes only:
  - `--target`
  - `--framework-root`
  - `--refresh`
  - `--dry-run`
  - `--check-env`
- `adopt_governance.py` has no first-class `--mode submodule` or full-install
  command.
- `adopt_governance.py` currently ends with generic "Adoption complete. Next
  steps:" output. It does not explicitly say "audit surface only" or "not
  runtime self-contained" for copy-based adoption.
- README already says classification precedes tooling and that copy-based
  consumers support classification / audit wording only. This confirms the
  doctrine exists, but the HBPlus.Avalonia logs show doc-layer reminders are not
  sufficient for first-time users.
- `governance/F7_FULL_UPDATE.md` and
  `governance_tools/external_governance_submodule_updater.py` cover existing
  submodule consumer update behavior, not initial `git submodule add`.
- `external_governance_submodule_updater.py` requires a registered initialized
  submodule. It is update-not-install.
- Recent consumer hygiene work added `.gitignore` protection to adopt/refresh
  and the external submodule updater. A stale framework pin can miss that
  consumer-facing repair.

## Target Outcome

Define a staged UX repair that makes the adoption class visible at the point of
action and creates a path toward first-class full/submodule install support.

The target outcome is not "make every adoption foolproof." It is:

- make thin/copy adoption honestly report its boundary;
- steer owned/code-changing repositories toward submodule/full adoption;
- define `self-contained` and `runtime-capable` in checkable terms;
- propose a report-only doctor that can detect the same class of onboarding
  mistakes before they become runtime surprises;
- defer full installer implementation until after the wording and diagnostic
  contract are reviewed.

## Scope

This proposal covers:

- adoption-class wording for `adopt_governance.py` stdout;
- `--help` / `--check-env` use-case routing text at the tool layer;
- a checkable definition of `self-contained` and `runtime-capable`;
- a report-only adoption doctor concept;
- a deferred first-class submodule/full installer concept;
- non-goals and claim ceilings for each tranche.

This proposal does not implement any of those changes.

## Non-Goals

This proposal does not authorize:

- changing `adopt_governance.py` behavior;
- adding `--mode submodule`;
- adding or deleting a submodule in any consumer repo;
- changing `external_governance_submodule_updater.py`;
- changing runtime hook behavior;
- changing `governance_drift_checker.py` pass/fail semantics;
- adding hook, CI, pre-push, or enforcement behavior;
- cleaning HBPlus.Avalonia, gl_electron_tool, GLUpdateTool, or any other
  consuming repo;
- claiming full adoption is now easy or automated;
- claiming users cannot still select the wrong mode.

## Definitions

### Thin / Copy-Based Adoption

Thin adoption means the target repo receives the copy-based audit surface:

- repo-local governance / instruction files;
- protected baseline metadata;
- drift-checkable audit wording and classification;
- managed hygiene files when the current adopt path supports them.

Thin adoption does not imply that the target repo owns a copy or submodule of
the framework runtime surfaces.

Allowed claim:

- audit surface is installed or refreshed, if checks pass.

Not allowed claim:

- runtime hooks are self-contained;
- governance tools are repo-owned;
- execution-time governance can run without an external framework checkout;
- the target repo is ready for governed code modification solely because thin
  adoption passed.

### Self-Contained

`self-contained` means the target repo can resolve the governance framework's
tooling from repo-owned files, normally through a committed framework
submodule, without depending on a machine-local external checkout such as
`D:\...\ai-governance-framework`.

Minimum checkable conditions:

- a framework checkout exists under the target repo, usually
  `additional/ai-governance-framework`;
- the framework checkout contains `governance_tools`;
- the framework checkout contains `runtime_hooks`;
- the framework checkout contains the runtime snapshot required by the hooks;
- runtime commands can execute with paths inside the target repo / submodule;
- the parent repo records the submodule pointer in its index when submodule mode
  is claimed.

### Runtime-Capable

`runtime-capable` means selected runtime governance entrypoints can execute
against the target repo from repo-owned framework files.

Minimum checkable signals:

- a submodule-path `pre_task_check.py` or equivalent runtime entrypoint imports
  successfully;
- the runtime injection snapshot resolves;
- the command exits successfully for a representative no-mutation check;
- no external `PYTHONPATH` to a framework checkout outside the target repo is
  required.

Runtime-capable does not mean semantic correctness, full enforcement,
non-bypassability, or full framework test-suite success.

## Proposed Tranches

### Tranche 1 - Adoption-Class Output And Help Text

Add explicit boundary text to the natural adoption command output.

For thin/copy adoption, `adopt_governance.py` should print a block like:

```text
Adoption class: copy-based audit surface
Runtime capability: not self-contained

Copied / refreshed:
- AGENTS / PLAN / contract / baseline / drift-checkable audit surface

Not included:
- governance_tools
- runtime_hooks
- runtime injection snapshot

This repo is not runtime self-contained from thin adoption alone.
For repositories you own and modify, especially cross-platform or low-level code
repos, use the submodule/full adoption path before claiming governed runtime.
```

Also update `--help` and `--check-env` output to route by use case:

```text
Use copy-based adoption for audit-only classification.
Use submodule/full adoption for repos you own, modify, or expect to govern at
runtime.
```

Claim ceiling:

- improves user-visible wording;
- does not implement full install;
- does not change drift checks;
- does not make thin adoption runtime-capable.

### Tranche 2 - Report-Only Adoption Doctor

Add a report-only diagnostic command that answers:

- adoption class: copy-based / submodule consumer / unknown;
- self-contained: yes / no / unknown;
- runtime-capable: yes / no / unknown;
- root-level leftover `runtime_hooks`: present / absent;
- framework submodule path: found / not found;
- submodule pin freshness: current / behind remote / not checked;
- external framework path dependency: observed / not observed / not checked.

The doctor should exit zero in the first tranche and report findings with clear
claim ceilings. It should be modeled after existing report-only diagnostics in
this repository: useful for reviewers, not a gate.

Claim ceiling:

- detects likely onboarding mismatch;
- does not install anything;
- does not delete leftover hooks;
- does not update stale pins;
- does not block commits.

### Tranche 3 - First-Class Submodule / Full Install

After Tranche 1 and Tranche 2 are reviewed, consider a first-class installer
entrypoint such as:

```text
python governance_tools/adopt_governance.py --mode submodule --target <repo> \
  --url <framework-remote-url> --pin latest
```

or a dedicated script:

```text
scripts/install-governance-submodule.ps1
```

The installer should be designed, reviewed, and implemented separately. It would
wrap the currently manual path:

1. add or verify framework submodule;
2. choose and report pin target;
3. warn when requested pin is behind remote;
4. run adopt with `--framework-root` pointing at the submodule;
5. stage only the intended parent-repo surfaces;
6. detect thin-era leftover root-level runtime hooks;
7. report self-contained / runtime-capable status.

Claim ceiling:

- proposed only;
- not implemented by this proposal;
- not required for the first wording repair.

## Affected Surfaces

Likely future Tranche 1 surfaces:

- `governance_tools/adopt_governance.py`
- focused tests for stdout / help text, likely in existing adopt tests

Likely future Tranche 2 surfaces:

- a new report-only checker under `governance_tools/`, or a new mode in an
  existing adoption/readiness tool;
- focused tests for each diagnosis bucket.

Likely future Tranche 3 surfaces:

- `governance_tools/adopt_governance.py` or a dedicated install script;
- tests for submodule add/pin planning using temporary repos;
- docs linking the full install path.

Surfaces not expected in the first tranche:

- `runtime_hooks/**`;
- `schemas/**`;
- `.github/workflows/**`;
- pre-push hooks;
- enforcement policy.

## Boundary And API Considerations

The first tranche should be wording-only in behavior terms. It may change stdout
and help text, so tests that assert exact output may need updates. It should not
change which files are copied, refreshed, staged, or validated.

The doctor should remain report-only until enough real onboarding evidence shows
which findings are reliable blockers. A stale pin warning is useful evidence,
but it is not automatically a failure: a consumer may intentionally pin a
reviewed older framework version.

The full installer should not be bundled with stdout wording. Adding a
submodule, selecting a pin, and staging parent-repo changes are materially higher
risk than printing an honest boundary after thin adoption.

## Failure Paths Or Risk Points

1. Documentation-layer fix repeats a known miss

README already contains classification guidance. Another README-only reminder is
unlikely to fix the observed first-time path. The first repair must appear in
tool stdout / help.

2. Output text overclaims

If the new output says "full adoption available" before a first-class installer
exists, it creates a new false path. Wording must separate "recommended
submodule/full path" from "this command implemented that path."

3. Stale pin warning becomes false blocker

Behind-remote pins can be intentional. A doctor should report freshness and
consumer-facing missed fixes, not automatically fail.

4. Self-contained conflated with full test success

A repo can be self-contained and runtime-capable while the framework's complete
test suite still has unrelated external-service or environment failures.
Diagnostics must keep those concepts separate.

5. Root-level leftover hooks removed too early

Detecting leftover hooks is lower risk than deleting them. Cleanup should be a
separate approved action in a consumer repo.

6. Thin adoption delegitimized

Thin adoption remains valid for audit-only classification. The proposal should
not claim every consumer must use submodule mode.

## Evidence Plan

For Tranche 1 implementation:

- focused tests for `adopt_governance.py --help` text;
- focused tests or output capture for successful thin adopt / dry-run wording;
- `python governance_tools/adopt_governance.py --help`;
- existing adopt / drift / baseline focused tests.

For Tranche 2 implementation:

- fixtures for:
  - copy-based repo with no submodule;
  - submodule consumer with initialized framework checkout;
  - root-level leftover `runtime_hooks`;
  - stale pin compared to a mocked or local remote;
  - no external framework path dependency.
- report-only command output in JSON and human formats if added.

For Tranche 3 design:

- separate proposal before code;
- temporary-repo tests for submodule add / pin planning;
- explicit path-limited staging tests;
- no automatic deletion of consumer files without a dedicated cleanup flag and
  review.

## Implementation Tranche Recommendation

Recommended next implementation tranche after this proposal is reviewed:

1. Update `adopt_governance.py` stdout and `--help` / `--check-env` text to
   expose adoption class and use-case routing.
2. Add focused tests for that output.
3. Do not change adoption behavior.
4. Do not add doctor or installer in the same commit.

Deferred options, not commitments:

- report-only adoption doctor;
- first-class submodule/full installer;
- stale-pin freshness hints with remote comparison;
- leftover-hook cleanup workflow.

## Claim Ceiling

This proposal may claim:

- the current natural adoption entrypoint is thin/copy only;
- README-level classification guidance exists but is insufficient by itself for
  the observed first-time onboarding failure;
- a tool-output boundary is the smallest useful first repair;
- `self-contained` and `runtime-capable` can be defined in checkable terms;
- doctor and installer work should be staged separately.

This proposal must not claim:

- adoption tooling has changed;
- full/submodule install is implemented;
- runtime hooks are more reliable;
- stale pins are blocked;
- drift/readiness semantics changed;
- any consuming repo has been fixed;
- first-time users can no longer make the wrong choice.

