---
status: design-only
authority: reference
scope: AI Governance update/adoption reporting
created: 2026-07-02
---

# Unified AI Governance Update Status Envelope

## Problem

Consuming repositories can receive an AI Governance update and still not know
whether they have a complete governance adoption surface.

Recent dogfood exposed three distinct failure modes:

- a tool path updated a framework pointer or lock but did not show the
  operator-facing adoption table;
- a manual submodule checkout path bypassed the updater and therefore bypassed
  `final_report_requirement`;
- a repository could have three different framework states at once: the
  committed lock, the dirty working-tree lock, and the checked-out submodule
  `HEAD`.

The current framework already has useful parts:

- `governance_maturity_summary` explains the visible adoption surface;
- `human_readable_adoption_summary` gives operators a table they can read;
- updater and F-7 outputs now carry `final_report_requirement`;
- F-7 tracks `framework_lock_commit` and warns when release freshness is not the
  same as commit freshness.

What is missing is one first-class update/adoption status envelope that is used
consistently by updater, F-7, onboarding, and manual-path reporting language.

## Current Repository Truth

Observed surfaces for this design:

- `governance_tools/external_governance_submodule_updater.py`
  - emits `governance_maturity_summary`;
  - emits `final_report_requirement`;
  - discovers nonstandard governance submodule paths through `.gitmodules` URL
    matching.
- `governance_tools/f7_full_update.py`
  - emits `governance_maturity_summary`;
  - emits `final_report_requirement`;
  - has `framework_lock_commit` and `adopted_commit_current` diagnostics.
- `governance_tools/onboard_latest_governance.py`
  - reports `repo_native_verified`, `head_ok`, `ts_ok`, actions, and matrix
    classification;
  - does not currently emit `governance_maturity_summary`,
    `human_readable_adoption_summary`, or `final_report_requirement`.
- `scripts/onboard-latest-governance.ps1`
  - wraps `governance_tools.onboard_latest_governance --format human`;
  - does not add an adoption table by itself.
- `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` and
  `governance/F7_FULL_UPDATE.md`
  - require update reports to surface the adoption summary table when present;
  - currently do not define a unified status envelope for manual or
    destructive manual update paths.
- `docs/governance/governance-maturity-summary-design-2026-07-01.md`
  - defines the report-only adoption summary presentation layer;
  - does not define lock-vs-checkout consistency.

## Target Outcome

Every AI Governance update path should produce, or explicitly fail to produce,
one status envelope with these layers:

1. framework update result;
2. adoption status result;
3. lock-vs-checkout consistency;
4. final-report table relay requirement;
5. cannot-claim boundary.

The envelope is a reporting surface. It is not a gate, an enforcement layer, a
repair action, or proof of full adoption.

## Proposed Envelope

```yaml
ai_governance_update_result:
  report_only: true
  framework_update_status:
    value: already_current | update_available | updated | manual_update | destructive_manual_update | blocked | not_submodule_consumer | not_verified
    source: updater | f7_full_update | onboard_latest_governance | manual_path | derived
  adoption_status:
    value: minimal | partial | full_candidate | not_governed | unknown | not_reported
    source: governance_maturity_summary.user_facing_status | not_reported
  lock_consistency:
    value: consistent | lock_behind_checkout | lock_ahead_of_checkout | mismatch | unknown | not_applicable
    source: framework.lock.json adopted_commit vs framework checkout HEAD
  governance_maturity_summary:
    value: present | not_available | not_run
    reason: <required when not present>
  human_readable_adoption_summary:
    value: reported | not_reported
    reason: <required when not reported>
  final_report_requirement:
    value: present | not_available
    source: updater | f7_full_update | onboard_latest_governance | not_available
  cannot_claim: []
  evidence_refs: []
```

## Status Semantics

### `framework_update_status`

- `already_current`: the governed update path verified that the framework
  checkout/pointer and target framework `HEAD` already match.
- `update_available`: a newer target framework `HEAD` is known, but no update
  was applied.
- `updated`: the governed update path applied the update and verified the
  target framework state.
- `manual_update`: a human or agent changed the framework pointer, checkout, or
  lock outside the governed updater/F-7 path.
- `destructive_manual_update`: a manual path discarded local framework
  checkout state, cleaned files, reset, or otherwise removed uncommitted state
  before or during the update.
- `blocked`: the update could not proceed due to a concrete blocker.
- `not_submodule_consumer`: the repository does not use a governance submodule.
- `not_verified`: the agent cannot safely determine update status.

`manual_update` and `destructive_manual_update` are not success states. They
are disclosure states. They must not be reported as a complete AI Governance
update unless a governed tool is run afterward and reports a complete envelope.

### `adoption_status`

Use `governance_maturity_summary.user_facing_status` when available:

- `minimal`
- `partial`
- `full_candidate`
- `not_governed`
- `unknown`

Use `not_reported` when no summary was produced.

`full_candidate` is still only a visible-surface candidate. It does not prove
runtime enforcement, semantic correctness, memory completeness, fleet/CI
enforcement, or release readiness.

### `lock_consistency`

This field catches the CFU-style failure where the repo has multiple framework
states at once.

Suggested initial interpretation:

- `consistent`: `governance/framework.lock.json` `adopted_commit` matches the
  resolved framework checkout `HEAD`.
- `lock_behind_checkout`: `adopted_commit` differs from checkout `HEAD`, and
  the lock commit is an ancestor of the checkout `HEAD` when local git ancestry
  can be checked without fetch.
- `lock_ahead_of_checkout`: `adopted_commit` differs from checkout `HEAD`, and
  the checkout `HEAD` is an ancestor of the lock commit when local git ancestry
  can be checked without fetch.
- `mismatch`: both values exist but ancestry cannot classify them as simple
  ahead/behind using local metadata.
- `unknown`: the lock or checkout `HEAD` cannot be read safely.
- `not_applicable`: no framework lock is expected for the current topology.

This check must be no-fetch. `consistent` means "consistent with local files and
local git metadata", not "current against the true remote".

## Output Path Mapping

### External Submodule Updater

Current state:

- already emits `governance_maturity_summary`;
- already emits `final_report_requirement`;
- already discovers nonstandard submodule paths through `.gitmodules` URLs.

Next implementation should add:

- `ai_governance_update_result`;
- `lock_consistency`;
- manual/destructive statuses only when explicitly detected or passed through
  by a caller.

### F-7 Full Update

Current state:

- already emits `governance_maturity_summary`;
- already emits `final_report_requirement`;
- already has adopted-commit diagnostics.

Next implementation should add:

- `ai_governance_update_result` in JSON and human output;
- lock consistency as a visible field;
- preservation of existing `final_status` behavior.

F-7 `final_status` must not be replaced by this envelope. The envelope is a
presentation and claim-boundary layer.

### Onboard Latest Governance

Current state:

- reports fleet acceptance signals;
- does not show the adoption table or final-report requirement.

Next implementation should add:

- best-effort `governance_maturity_summary` for the target repo;
- `final_report_requirement`;
- `ai_governance_update_result`;
- a clear boundary that `repo_native_verified` is evidence-chain integrity, not
  full adoption or enforcement.

### Manual Path Reporting

Manual paths include direct git checkout, direct submodule fast-forward, direct
lock edit, or "clean and checkout" flows that bypass updater/F-7.

Protocol wording should require:

- `framework_update_status=manual_update` or
  `framework_update_status=destructive_manual_update`;
- `adoption_status=not_reported` unless the summary is explicitly run;
- `human_readable_adoption_summary=not_reported` unless the table is relayed;
- cannot-claim list stating that the operation is not a complete AI Governance
  update.

For destructive manual updates, final reports must also list the inspected
discard surface before the destructive action. If no pre-discard inventory was
captured, the report must say so.

## Boundary And API Considerations

- Keep the envelope report-only and non-blocking.
- Do not change updater/F-7 success criteria in the first implementation
  tranche.
- Do not change hook, CI, pre-push, gate, runtime, or memory behavior.
- Do not add fetch-by-default behavior.
- Do not make the envelope a committed status receipt.
- Reuse `governance_maturity_summary` for adoption status rather than creating
  another taxonomy.
- Lock consistency is a local consistency signal, not a remote freshness claim.

## Failure Paths And Risk Points

- If `governance_maturity_summary` fails, envelope should still render with
  `governance_maturity_summary=not_available` and a reason.
- If lock consistency cannot be checked, envelope should render
  `lock_consistency=unknown`, not suppress the field.
- If a manual update bypasses all framework tools, the framework cannot force
  compliance. Protocol can only define the correct disclosure.
- If onboarding uses an old snapshot, the envelope must not over-read matrix
  classification as adoption completeness.
- If a consumer repo has pre-existing dirty work, envelope output must stay
  separate from dirty-tree disposition.

## Evidence Plan

For the first implementation tranche, focused tests should cover:

- submodule consumer updated/current path emits `ai_governance_update_result`;
- `human_readable_adoption_summary` present results in
  `final_report_requirement=present`;
- `governance_maturity_summary` failure still yields a report-only envelope;
- lock matches checkout -> `lock_consistency=consistent`;
- lock differs from checkout -> visible non-consistent value;
- onboard latest governance emits the envelope in human and JSON output;
- manual/destructive statuses are documented in protocol/baseline text, not
  treated as successful updater outputs.

Validation should use:

```text
python -B -m pytest tests/test_external_governance_submodule_updater.py tests/test_f7_full_update.py <future onboard test file> -p no:cacheprovider
python -B -m py_compile <changed python files>
git diff --check -- <changed files>
```

## Implementation Tranche Recommendation

Implement in two narrow follow-up slices:

1. Tooling envelope helper and updater/F-7 wiring.
   - Candidate files:
     - `governance_tools/governance_maturity_summary.py`
     - `governance_tools/external_governance_submodule_updater.py`
     - `governance_tools/f7_full_update.py`
     - focused tests.
   - Include `lock_consistency`.
   - Preserve existing updater/F-7 status semantics.

2. Onboard/reporting and protocol propagation.
   - Candidate files:
     - `governance_tools/onboard_latest_governance.py`
     - `scripts/onboard-latest-governance.ps1` only if wrapper wording changes
       are needed;
     - `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`;
     - `governance/F7_FULL_UPDATE.md`;
     - `baselines/repo-min/AGENTS.md`;
     - focused tests.
   - Add manual/destructive disclosure wording.
   - Keep this advisory/reporting-only.

## Claim Ceiling

This design note claims only:

- a proposed status envelope;
- current repository truth observed from the listed files;
- a reporting-only implementation direction;
- an evidence plan for future slices.

This design note does not claim:

- agents will comply;
- any consumer repo is repaired;
- manual update paths are prevented;
- full AI Governance adoption can be proven from this envelope;
- runtime enforcement, hook/CI enforcement, memory completeness, domain
  correctness, or release readiness;
- any tooling behavior changed.
