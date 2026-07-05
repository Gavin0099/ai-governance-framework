# Self-Governance F2 Valid-Disable Attestation Design

Status: DESIGN ONLY / REPORT ONLY
Date: 2026-07-05
Scope: F2 valid-disable prevention policy design for
`governance/memory_blocking_policy.json`

## DONE

DONE = the F2 valid-disable residual is split into a report-only attestation
design without changing guard, workflow, CI, hook, policy, or blocking
behavior.

## Context

Red-team round 2 fixed the silent policy-disable path only at the visibility
layer: CI now emits `blocking_policy_changed_in_current_diff` when
`governance/memory_blocking_policy.json` appears in the current diff. That is
still visibility, not prevention. A reviewer can ignore the warning and merge a
valid `enabled: false` change or policy-file deletion.

Directly blocking all valid disables is the wrong next step. The policy file is
also the emergency kill switch for B0 selective blocking. If the gate breaks
and the disable path is itself blocked, the repo can deadlock in a state where
the broken gate cannot be turned off through a normal reviewed change.

The next report-only slice should therefore distinguish loud, reviewable
disable attestations from silent disables. It must not claim that a receipt
proves real human approval.

## State Model

The design uses three honest states:

| State | Meaning | Detector ceiling |
| --- | --- | --- |
| `active` | Policy file exists and `enabled: true` with known blockable codes | Current selective-blocking behavior |
| `attested_disabled` | Policy file exists, `enabled: false`, and a disable receipt exists with valid shape | A versioned statement exists; approval truth is not verified |
| `unattested_disabled` | Policy file exists with `enabled: false` and no valid receipt | Report-only warning candidate |

Avoid the name `authorized_disabled` unless every use includes the following
claim ceiling: "authorized" means "a versioned attestation artifact with valid
shape exists"; it does not mean the signer truly had authority, the approval
happened, or the reason is true. `attested_disabled` is preferred because it
does not smuggle an authority claim into the state name.

## Policy Deletion Semantics

Policy deletion is different from `enabled: false`.

- `enabled: false` is statically observable after merge: the file remains and
  the detector can compare it with the receipt.
- Deletion is diff-boundary-bound: the deletion is observable only in the diff
  where the file is removed. After merge, "policy was deleted" and "this repo
  never adopted a policy file" are indistinguishable from repository state
  alone.

Therefore, the clean design is:

- the valid disable path keeps the policy file and sets `enabled: false`;
- policy deletion is always treated as unsanctioned in the diff that deletes
  the file;
- a receipt does not legitimize deletion, because there is no need to delete
  the policy when `enabled: false` exists.

Candidate report-only codes:

- `blocking_policy_disabled_without_attestation`: policy file says
  `enabled: false`, but no valid disable receipt is present.
- `blocking_policy_deleted_without_attestation`: policy file is deleted in the
  current diff. This is diff-scoped and unconditional.

## Disable Receipt Shape

Suggested path:

`governance/memory_blocking_policy_disable_receipt.json`

Suggested minimal fields:

```json
{
  "receipt_schema": "memory_blocking_policy_disable_receipt.v1",
  "reason": "brief human-readable reason",
  "attested_by": "reviewer or operator identity string",
  "linked_commit": "commit hash that introduced the disable",
  "cannot_claim": [
    "receipt does not prove approval authority",
    "receipt does not prove the reason is true",
    "receipt does not prove semantic safety of disabling the gate"
  ]
}
```

The field names intentionally match the repo's emerging receipt family:
`receipt_schema`, `reason`, `linked_commit`, and `cannot_claim`. This should
stay compatible with future receipt work such as evidence receipts, claim
semantic attestations, or F4 override-hardening receipts without forcing a
single universal schema now.

## Receipt Validation Ceiling

A valid receipt proves only shape and reviewability:

- JSON parses;
- `receipt_schema` matches the expected version;
- required fields have the expected types;
- `linked_commit` resolves to a git commit object when checked in a git
  worktree.

It does not prove:

- `attested_by` is a real authorized reviewer;
- the same person actually approved the disable;
- the reason is accurate;
- the linked commit semantically authorized the disable;
- disabling the gate is safe.

`linked_commit` should reuse the existing commit-anchor provenance semantics:
resolve to a commit object, but do not infer approval truth from existence.

## Invalid Receipt Behavior

A malformed or schema-mismatched receipt must be visible and must not count as
an attestation. This follows the F1/F3 hardening rule: bad control-plane input
cannot silently masquerade as intentional disablement.

Candidate report-only code:

- `blocking_policy_disable_receipt_invalid`

Examples that should trigger it:

- invalid JSON;
- missing or mismatched `receipt_schema`;
- required field missing;
- required field has the wrong type;
- `linked_commit` is present but does not resolve to a commit object when git
  provenance is available.

The invalid receipt warning is report-only in the first implementation slice.
It may later become a blocker only through a separate policy decision.

## Expiration Semantics

An `expires_at` or `re_enable_by` field is useful for review discipline, but it
introduces time-dependent behavior: the same repository state can be accepted
today and warned tomorrow.

To preserve deterministic core policy state, expiration must not flip
`attested_disabled` into `unattested_disabled`. If added, expiry should emit a
separate report-only warning:

- `blocking_policy_disable_receipt_expired`

That isolates clock dependence in one explicit code.

## Future F4 Reuse

This design is intentionally adjacent to F4 `authority_override` hardening:
both are honor-system attestations that make an escape hatch auditable without
proving the signer had authority. A future F4 slice can reuse the same receipt
shape conventions, but this F2 slice does not implement or require F4 override
prevention.

## Suggested Rollout

1. Docs-only design: this document.
2. Report-only fixtures: prove current valid disable and deletion behavior, and
   pin the new expected warnings.
3. Report-only detector: emit disable/deletion/invalid-receipt warnings without
   changing `clean`, blockers, or policy behavior.
4. Observation: review real policy changes and false positives.
5. Separate prevention policy decision: decide whether any of these warnings
   should become blockers.

## Non-Goals

- No blocking change in this design slice.
- No prevention of valid `enabled: false` changes.
- No protected-path enforcement.
- No proof of human approval or reviewer authority.
- No claim that a receipt proves semantic safety.
- No deletion-state detection after the deletion diff has already merged.
- No universal receipt schema for all governance artifacts.
