# Self-Governance F4 Authority Override Hardening Design

Status: DESIGN ONLY / REPORT ONLY
Date: 2026-07-05
Scope: F4 `authority_override` self-service residual on the B0 selective
blocking path

## DONE

DONE = the F4 override-abuse residual has a hardening design with an honest
capability boundary, a policy-mode model whose default changes nothing, and a
rollout order, without changing guard, workflow, CI, hook, policy file, or
blocking behavior.

## Why F4 Is the Next Residual

Ordering rationale across the open red-team residuals:

- **F4 (this design)**: the override is a self-service bypass *on the blocking
  path itself* — one inline line defeats the only enforcement the framework
  currently has. Highest-leverage residual, and its design can start now
  because it needs no observation data to define the modes.
- F5 (repo-state vs diff-scoped gate): explicitly waiting on observation data;
  narrowing the gate without evidence would be a silent claim change.
- F2 prevention: detector landed 2026-07-05; whether warnings should become
  blockers needs at least one real disable event or an observation window.
- F6 blocking promotion: its own design already requires a separate RFC.
- B1 (fabricated anchors): the RFC defers it until B0 has operated in
  practice.

## Current Behavior

With `governance/memory_blocking_policy.json` enabling B0:

- an entry carrying any non-empty `authority_override:` value is excluded from
  blocking; the block downgrades to a warning;
- `authority_override_used` is emitted as an audit record (never blockable);
- workflow / CI surface the audit code when the override occurs in the current
  memory diff;
- no verification of the override value exists: `authority_override: myself
  lol` is as effective as a genuine reviewed exception.

## Honest Capability Boundary

Text-only governance cannot verify that an override was truly authorized: the
same actor writes the entry, the override line, and any receipt. Hardening can
only do three things:

1. raise the cost of an override from one inline line to a versioned,
   repo-visible artifact;
2. move the override out of the memory entry (easy to miss in review) into a
   dedicated governance path (hard to miss in review);
3. let a repository opt out of the escape hatch entirely.

No mode below may ever be described as preventing override abuse by a
determined self-approver. The deliverable is reviewability, not authorization
truth.

## Policy Mode Model

Add one optional field to `memory_blocking_policy.json`
(additive; `policy_schema` stays `memory_blocking_policy.v0.1` because absent
fields must keep exact current behavior):

```json
{
  "override_mode": "allowed | receipt_required | disallowed"
}
```

| Mode | Inline override effect | Codes |
| --- | --- | --- |
| `allowed` (default, current) | downgrades block to warning | `authority_override_used` |
| `receipt_required` | downgrades only when a valid override receipt exists; otherwise the block stands | `authority_override_used` (attested) / `authority_override_rejected` (no or invalid receipt; block stands) |
| `disallowed` | never downgrades; block stands | `authority_override_rejected` |

Absent or unknown `override_mode` values: absent means `allowed`; an unknown
value is a policy error (`blocking_policy_unknown_override_mode`), following
the F3 rule — a typo must not silently select a weaker or stronger mode.

`authority_override_rejected` is a report-only audit record accompanying a
block that already stands; it is never independently blockable, mirroring
`authority_override_used`.

## Override Receipt Shape

Suggested path (one file per override, keyed by token):

`governance/authority_override_receipts/<override_token>.json`

The inline field then carries the token:
`authority_override: <override_token>`.

```json
{
  "receipt_schema": "authority_override_receipt.v1",
  "override_token": "unique token matching the inline field",
  "reason": "brief human-readable reason",
  "attested_by": "reviewer or operator identity string",
  "linked_commit": "commit hash of the change being overridden",
  "overridden_file": "memory/YYYY-MM-DD.md",
  "cannot_claim": [
    "receipt does not prove approval authority",
    "receipt does not prove the reason is true",
    "receipt does not prove the overridden violation is safe"
  ]
}
```

Conventions follow the receipt family (`receipt_schema`, `reason`,
`linked_commit`, `cannot_claim`) established by the F2 disable receipt.
Token matching binds receipt to entry without fragile entry-text digests: the
detector requires the inline value to equal `override_token` and the entry to
live in `overridden_file`. Editing the entry keeps the binding; moving the
override to another file breaks it visibly.

## Receipt Validation Ceiling

Identical in spirit to the F2 disable receipt:

- valid = JSON parses, schema matches, required string fields non-empty,
  `cannot_claim` non-empty, `linked_commit` resolves when a git worktree is
  available, `override_token` matches the inline value, `overridden_file`
  matches the entry's file;
- invalid receipts are visible (`authority_override_receipt_invalid`) and do
  not count as attestation;
- stale receipts (receipt exists but no in-repo entry carries the token)
  warn `authority_override_receipt_stale`, mirroring the F2 stale rule;
- validity never proves the attestor had authority.

## Rollout

1. Docs-only design: this document.
2. Fixtures: pin current `allowed` behavior as the explicit default and pin
   the expected verdicts of the two stricter modes before they exist.
3. Loader + guard support for `override_mode` with default `allowed`
   (behavior unchanged; stricter modes exercised only in tests).
4. Separate policy decision for this repository: choose the mode with
   observation data from the B0 gate (override events observed so far: none).
5. Only then, if `receipt_required` is chosen, implement receipt validation
   as part of the same policy decision.

Each step keeps its own claim ceiling; step 3 must not be described as
override hardening being active.

## Non-Goals

- No change to guard, workflow, CI, hook, or the active policy file in this
  slice.
- No identity verification, signatures, or cryptographic attestation.
- No claim that any mode prevents a determined self-approver.
- No blocking promotion of `authority_override_used` or any audit code.
- No F5 gate narrowing, F6 blocking promotion, or B1 anchor work.
- No retroactive invalidation of overrides recorded before a mode change.

## Cannot Claim

- override abuse is prevented in any mode;
- a receipt proves real approval or authority;
- `disallowed` mode is safe for every repo (it removes the escape hatch; a
  broken gate then requires a policy edit, which is why the F2 kill switch
  must stay functional);
- this design is implemented anywhere yet.
