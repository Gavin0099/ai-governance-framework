# Manual Governance Update Advisory Design - 2026-07-03

Status: proposal/design-only

This note defines an advisory-only path for detecting likely manual AI
Governance updates in consuming repositories. It records a design direction
only. It does not implement hooks, gates, updater receipts, consumer repo
repairs, or enforcement.

## Problem

Recent consuming-repo update trials showed three different update paths:

- governed updater/F-7 paths can now show `human_readable_adoption_summary`,
  `final_report_requirement`, and lock-vs-checkout consistency.
- manual submodule/gitlink/lock edits can still bypass the updater entirely.
- if a manual edit bypasses the updater, the framework can only make that risk
  visible later; it cannot prove compliance or prevent the bypass without a
  separate enforcement decision.

The observed failure pattern is not one bug. It is a reporting gap:

- a repo can have a framework checkout moved without matching
  `framework.lock.json`;
- a repo can have both checkout and lock moved by hand, leaving no visible
  updater/F-7 evidence;
- an agent can summarize the manual update as latest or completed unless the
  local instructions and tools force a weaker claim.

## Design Goals

- Surface likely manual governance updates before commit or review.
- Keep the signal advisory-only and non-blocking.
- Avoid claiming semantic proof that the updater was or was not used.
- Reuse existing `lock_consistency` and update-reporting language where
  possible.
- Separate cheap local mismatch detection from receipt-based evidence
  detection.

## Non-Goals

- No blocking hook.
- No CI, gate, runtime, or pre-push enforcement.
- No consumer repo edits in this design slice.
- No automatic lock repair.
- No claim that an advisory proves misuse.
- No v1.3.0 release-prep claim.

## Signal 1: Lock vs Checkout Mismatch

Signal 1 checks whether a staged or working-tree governance update leaves
`framework.lock.json` inconsistent with the checked-out framework HEAD.

This signal is cheap and can be implemented without a new receipt format.

Candidate trigger:

- staged or working-tree change touches a governance framework submodule
  gitlink, framework checkout path, or `governance/framework.lock.json`;
- local report-only comparison says `lock_consistency` is not `consistent` or
  `not_applicable`.

Candidate advisory wording:

```text
AI Governance advisory: framework lock and checkout are not consistent.
If this is a manual update, report it as manual_update and do not claim
completed/latest/full adoption. To complete a governed update, run the
updater/F-7 path and relay the human_readable_adoption_summary table.
```

Expected coverage:

- catches CFU-style pointer/checkout updates where the lock remains stale;
- catches lock-only edits that do not match the checkout;
- does not require updater receipt evidence.

False positives to tolerate:

- merge or rebase temporarily stages a gitlink/lock mismatch;
- revert commits intentionally restore older lock state;
- the operator is preparing a multi-step update and has not yet completed the
  second step.

Because those false positives are legitimate, Signal 1 must remain advisory.

## Signal 2: No Governed Update Evidence

Signal 2 detects the harder case: checkout and lock are mutually consistent,
but the update was still performed manually without updater/F-7 evidence.

This cannot be implemented honestly until governed update tools produce an
evidence artifact.

Required preceding slice:

- define a report-only update receipt format, for example
  `governance/.update-receipt.json`;
- have updater/F-7 write or stage that receipt during apply;
- include at least: tool name, tool version or framework commit, target repo,
  before/after framework commit, lock commit, timestamp, mode, and claim
  boundary;
- make receipt absence an advisory signal only.

Candidate trigger after receipt support exists:

- staged gitlink or `governance/framework.lock.json` changed;
- lock and checkout are consistent;
- no current update receipt is present for the same target commit and tool
  action.

Candidate advisory wording:

```text
AI Governance advisory: governance checkout and lock changed, but no current
updater/F-7 receipt was found. If this was manual, report manual_update. If a
governed update was intended, rerun the updater/F-7 path and include the
receipt evidence.
```

Receipt spoofability boundary:

- a receipt is review evidence, not proof;
- a user or agent can forge or copy a receipt;
- the advisory is a lexical/evidence tripwire, not semantic enforcement.

## Hook Distribution Model

Current hook installation copies managed hook files from
`scripts/hooks/{pre-commit,pre-push}` into each consuming repo's `.git/hooks`
directory and writes an `ai-governance-framework-root` config file.

Implication:

- changing hook logic in the framework does not automatically update already
  installed consumer hooks;
- consumers need a governed updater/F-7 refresh or hook reinstall to receive
  the new advisory;
- a future advisory implementation must not claim fleet-wide coverage until
  each consumer hook has been refreshed or inspected.

## Coverage Boundary

Only repos with installed framework hooks can benefit from a hook advisory.

The advisory does not cover:

- consumers without framework hooks;
- manual updates where hooks are bypassed;
- changes committed with `--no-verify`;
- direct remote commits that never execute local hooks;
- stale copied hooks that predate the advisory.

This limitation is acceptable because the signal is a warning surface, not an
enforcement surface.

## Recommended Tranches

1. Implement Signal 1 as advisory-only local mismatch detection.
   - Scope: hook helper or hook-called Python checker plus focused tests.
   - No receipt format.
   - No blocking behavior.

2. Define and implement governed update receipts.
   - Scope: updater/F-7 apply paths plus tests.
   - Receipt should be report-only and reviewable.
   - Do not treat receipt presence as proof of semantic correctness.

3. Implement Signal 2 after receipts exist.
   - Scope: advisory detection for changed gitlink/lock without matching
     receipt.
   - No blocking behavior.

4. Measure coverage.
   - Read-only inspect representative consumers for hook freshness and whether
     the advisory can run.
   - Do not claim fleet coverage from framework-side implementation alone.

## Claim Ceiling

This design can support an advisory warning that a governance update appears
manual, incomplete, or not evidenced by the governed updater path.

It cannot claim:

- the update is definitely unsafe;
- the updater was definitely bypassed;
- hooks are installed everywhere;
- consumers are repaired;
- full governance adoption;
- hook, CI, pre-push, gate, or runtime enforcement;
- release readiness.
