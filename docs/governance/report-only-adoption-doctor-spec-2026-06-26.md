# Report-Only Adoption Doctor Spec - 2026-06-26

Status: proposed
Scope: Tranche 2 design only
Risk: Medium when implemented, because the likely implementation touches
`governance_tools/`

## Problem

Tranche 1 made adoption class visible at the point of use: copy-based adoption
now states that it installs an audit surface and does not make the target repo
runtime self-contained.

That wording prevents the first wrong claim, but it does not help a reviewer or
implementer diagnose the current state of a consuming repo after the user starts
moving from copy-based adoption toward a submodule/full path. The observed
failure class needs a report-only diagnostic that answers "what adoption class
is this repo currently in?" without installing, deleting, fetching, staging, or
blocking anything.

## Current Repository Truth

- `PLAN.md` keeps copy-based consumers classified as audit-only, with
  automated update still not solved (`PLAN.md:307`).
- The full/submodule adoption UX proposal defines Tranche 2 as a report-only
  adoption doctor (`docs/governance/full-submodule-adoption-ux-proposal-2026-06-26.md:216`).
- That proposal asks the doctor to report adoption class, self-contained state,
  runtime-capable state, leftover root-level `runtime_hooks`, framework
  submodule path, stale pin status, and external framework dependency
  (`docs/governance/full-submodule-adoption-ux-proposal-2026-06-26.md:218`).
- The same proposal says stale pins are evidence, not automatic blockers
  (`docs/governance/full-submodule-adoption-ux-proposal-2026-06-26.md:307`).
- Tranche 1 is implemented in `adopt_governance.py`: copy-based output says
  `Runtime capability: not self-contained`, and help/check-env now route
  owned/runtime-governed repos toward the manual submodule/full path
  (`governance_tools/adopt_governance.py:67`, `governance_tools/adopt_governance.py:90`).
- `external_repo_readiness.py` already aggregates hook, drift, contract,
  project-facts, and framework-version checks, but it returns failure when the
  repo is not readiness-ready (`governance_tools/external_repo_readiness.py:511`).
  That pass/fail posture is too strong for this doctor.
- `hook_install_validator.py` can validate framework-root config and required
  framework files (`governance_tools/hook_install_validator.py:18`,
  `governance_tools/hook_install_validator.py:90`), but it also has validator
  semantics and nonzero failure exits (`governance_tools/hook_install_validator.py:265`).
- `framework_versioning.py` can read `governance/framework.lock.json` and assess
  release state (`governance_tools/framework_versioning.py:208`). It does not
  by itself prove submodule pin freshness against a remote.
- `docs/INTEGRATION_GUIDE.md` contains the current manual submodule sections
  that Tranche 1 points users toward, but it is currently mojibake-heavy. This
  spec does not repair that guide.

## Target Outcome

Create a reviewable design for a future report-only command that can inspect a
target repo and describe its adoption posture without changing it.

The future command should be able to say, with explicit reasons:

- whether the repo looks copy-based, repo-owned-framework-path, submodule
  consumer, or unknown;
- whether static self-contained prerequisites are present, absent, or unknown;
- whether runtime capability was not checked, unknown, or explicitly checked by
  a separate no-write smoke path;
- whether root-level leftover `runtime_hooks` exists outside the framework
  checkout;
- whether a framework submodule path exists and is initialized;
- whether a local remote-tracking comparison suggests the submodule pin is
  current versus local tracking, behind local tracking, ahead/diverged versus
  local tracking, unknown, or intentionally not checked;
- whether the observed framework dependency points outside the target repo.

## Scope

This spec authorizes a later implementation slice to add one report-only
diagnostic command, preferably as a new module such as:

```text
python -m governance_tools.adoption_doctor --repo <repo> \
  [--framework-root <path>] [--format human|json]
```

The smallest useful implementation tranche should:

- read only local filesystem and local git metadata by default;
- avoid network fetches by default;
- emit JSON and human formats;
- return exit code 0 when diagnostic findings exist;
- reserve nonzero exit codes for CLI misuse, unreadable paths, or internal
  exceptions;
- produce structured findings with severity `info`, `warning`, or `unknown`,
  but no blocking severity in Tranche 2;
- reuse existing helpers where their semantics fit, without importing their
  pass/fail exit behavior into the doctor;
- include focused tests for each diagnosis bucket.

## Non-Goals

Tranche 2 must not:

- install a framework submodule;
- update a submodule pin;
- fetch from remotes by default;
- delete root-level `runtime_hooks`;
- rewrite `.gitmodules`, `.git/config`, hooks, baseline files, `PLAN.md`, or
  memory files;
- call `adopt_governance.py` as a mutating operation;
- change drift-check, readiness, hook, pre-push, CI, runtime, or enforcement
  behavior;
- turn any finding into a gate, blocker, or failed readiness verdict;
- claim that self-contained status means full framework test success;
- claim that a repo-owned framework path proves hooks are installed, pin is
  fresh, runtime smoke passed, or the full installer ran.

## Affected Surfaces

Current slice:

- `docs/governance/report-only-adoption-doctor-spec-2026-06-26.md` only.

Likely future implementation slice:

- `governance_tools/adoption_doctor.py` or equivalent new report-only checker.
- `tests/test_adoption_doctor.py`.

Possible but deferred surfaces:

- A short pointer from `adopt_governance.py --help` or `--check-env` to the
  doctor after the doctor exists.
- Documentation updates to `docs/INTEGRATION_GUIDE.md` after a separate
  readability repair.

## Boundary And API Considerations

### Command Boundary

The doctor should be a read-only diagnostic, not a readiness validator. Its
top-level result should use language like:

```json
{
  "report_version": "0.1",
  "repo_root": "...",
  "adoption_class": {
    "value": "copy_based | repo_owned_framework_path | submodule_consumer | unknown",
    "confidence": "high | medium | low",
    "reasons": []
  },
  "self_contained": {
    "value": "yes | no | unknown",
    "checked": true,
    "reasons": []
  },
  "runtime_capable": {
    "value": "not_checked | yes | no | unknown",
    "checked": false,
    "reasons": ["runtime smoke is out of scope for the static doctor"]
  },
  "findings": []
}
```

### Adoption Class Rules

Suggested first-pass classification:

- `submodule_consumer`: `.gitmodules` declares a framework path, the path exists
  inside the repo, and the path looks like a framework checkout.
- `repo_owned_framework_path`: `--framework-root`, hook config, or common
  framework-path discovery resolves inside the repo and looks like a framework
  checkout, but submodule proof is missing or unknown.
- `copy_based`: governance audit surface exists, but no repo-owned framework
  checkout is found and any observed framework root points outside the repo.
- `unknown`: evidence is contradictory or insufficient.

The doctor should surface the evidence behind the classification rather than
hide it behind a single verdict.

### Self-Contained Rules

Static `self_contained=yes` should require repo-owned framework files sufficient
to resolve core framework runtime surfaces, at minimum:

- `governance_tools/`;
- `runtime_hooks/`;
- `governance/runtime_injection_snapshot.v0.yaml`;
- framework root path resolves inside the target repo.

Static `self_contained=yes` must not imply:

- hooks installed;
- submodule pin fresh;
- runtime smoke passed;
- all framework tests pass;
- runtime governance is enforced.

### Runtime-Capable Rules

Tranche 2 should keep `runtime_capable=not_checked` unless it implements a
dedicated no-write smoke probe. Static file presence is not enough to claim
runtime-capable execution.

If a later tranche adds a no-write smoke probe, it must keep these concepts
separate:

- self-contained static path resolution;
- runtime-capable selected entrypoint execution;
- full framework test suite success.

### Stale Pin Rules

Pin freshness should be local and report-only in the first implementation.

Allowed first implementation:

- compare the submodule HEAD with an already-present local remote-tracking ref;
- report `current_vs_local_tracking`, `behind_local_tracking`,
  `ahead_or_diverged_vs_local_tracking`, `unknown`, or `not_applicable`;
- include `remote_tracking_freshness` or `last_fetch` when local git metadata can
  support it; otherwise report `unknown`;
- do not fetch;
- do not fail the command when behind.

`current_vs_local_tracking` must not be rendered as simply `current`. Without a
fetch, the local remote-tracking ref can itself be stale, so this finding only
means the consumer pin matches the local view of the remote. It does not prove
the pin matches the true current remote head.

Not allowed in Tranche 2:

- fetch remote state;
- update the pin;
- decide that behind remote is automatically invalid.

### Output Semantics

Human output should lead with the adoption class and claim ceiling:

```text
Adoption Doctor

adoption_class      = copy_based
self_contained      = no
runtime_capable     = not_checked
report_only         = true

Claim boundary: this report does not install, update, delete, fetch, stage,
or enforce anything.
```

JSON output should be deterministic and use stable field names so reviewers can
diff fixture outputs.

## Claim Ceiling

This spec may claim:

- a proposed report-only diagnostic boundary;
- proposed classification fields and reasons;
- proposed static self-contained prerequisites;
- proposed local-only stale-pin comparison semantics;
- proposed tests and evidence for a later implementation.

This spec must not claim:

- the doctor exists;
- any consuming repo has been diagnosed;
- full/submodule installation is implemented;
- runtime governance is now self-contained in any repo;
- runtime capability has been verified;
- stale pins are blockers;
- hooks, CI, pre-push, or enforcement behavior changed.

## Failure Paths Or Risk Points

- A repo-owned framework path can be present without being a submodule. The
  doctor must not label that as `submodule_consumer` without `.gitmodules` or
  gitlink evidence.
- A submodule path can exist but be uninitialized or partial. That should report
  initialized-state evidence, not silently become `self_contained=yes`.
- A stale pin can be intentional. It should be a warning/finding, not a failure.
- Root-level `runtime_hooks` may be intentional in this framework repo but
  suspicious in a consuming repo. The doctor needs repo-context-aware wording.
- An explicit `--framework-root` outside the repo is useful for audit-only
  classification, but it is evidence against self-contained runtime claims.
- `external_repo_readiness.py` and `hook_install_validator.py` already have
  failure exits. Reusing their internals must not import their gate semantics.
- `docs/INTEGRATION_GUIDE.md` is the current manual path reference but has
  mojibake. The doctor should not depend on prose readability in that file.

## Evidence Plan

For this spec slice:

- `git diff --check -- docs/governance/report-only-adoption-doctor-spec-2026-06-26.md`
- portable ASCII check for this new spec file.

For the later implementation slice:

- focused tests for copy-based repo with external framework root;
- focused tests for repo-owned framework path without submodule proof;
- focused tests for submodule consumer with initialized framework checkout;
- focused tests for uninitialized or partial submodule checkout;
- focused tests for root-level leftover `runtime_hooks`;
- focused tests for external framework path dependency;
- focused tests for stale pin using local-only remote-tracking fixtures;
- focused tests that `current_vs_local_tracking` is not rendered as unqualified
  `current`;
- focused tests for no-fetch behavior by default;
- focused tests that findings exit 0;
- JSON parse test for stable schema;
- human output test for claim boundary wording.

Recommended commands for the later implementation:

```text
pytest tests/test_adoption_doctor.py -p no:cacheprovider
python -m governance_tools.adoption_doctor --repo <fixture> --format json
python -m governance_tools.adoption_doctor --repo <fixture> --format human
```

## Implementation Tranche Recommendation

Next implementation tranche:

1. Add `governance_tools/adoption_doctor.py` with local filesystem and local
   git metadata inspection only.
2. Implement JSON and human output.
3. Keep exit code 0 for diagnostic findings.
4. Add focused tests for the six core fixture classes:
   copy-based, repo-owned framework path, submodule initialized, submodule
   partial/uninitialized, root-level leftover runtime hooks, stale local
   remote-tracking pin.
5. Do not wire the doctor into adopt, pre-push, CI, readiness, or runtime
   enforcement in the same slice.

Deferred options, not commitments:

- add a no-write runtime smoke probe and then allow `runtime_capable=yes/no`;
- add a help pointer from `adopt_governance.py`;
- add remediation hints for manual submodule/full installation;
- repair `docs/INTEGRATION_GUIDE.md` readability.
