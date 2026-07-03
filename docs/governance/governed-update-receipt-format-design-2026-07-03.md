# Governed Update Receipt Format Design - 2026-07-03

Status: proposal/design-only

This note defines a candidate receipt format for governed AI Governance update
tools. It is a design proposal only. It does not implement receipt writing,
Signal 2 advisory detection, hook behavior, gates, enforcement, consumer repo
edits, or release preparation.

## Problem

Signal 1 manual-update advisory can detect local lock-vs-checkout mismatch
without any new artifact. Signal 2 is different: it tries to detect a changed
governance checkout or lock that is mutually consistent but lacks evidence that
the governed updater/F-7 path was used.

Today, updater/F-7 apply paths do not write a durable update receipt. Without a
receipt, Signal 2 cannot distinguish:

- a governed update that ran correctly;
- a manual update that happened to update both checkout and lock;
- a copied or forged claim in a final report.

The receipt fills that evidence gap. It is review evidence, not proof.

## Proposed Path

Candidate receipt path:

```text
governance/.update-receipt.json
```

The path is intentionally under `governance/` because it is part of the
consumer repo's governance evidence surface. It should be committed or reviewed
with the same update that changes `governance/framework.lock.json` or the
framework checkout pointer.

The filename is singular because it represents the latest governed update
attempt for that repo. Historical sequences can be recovered from git history.

## Required Fields

The receipt should be JSON with stable top-level fields:

```json
{
  "receipt_version": "0.1",
  "receipt_type": "ai_governance_update",
  "tool": "external_governance_submodule_updater|f7_full_update",
  "tool_mode": "apply",
  "repo_root": "<absolute-or-repo-relative target repo>",
  "framework_root": "<absolute-or-repo-relative framework root>",
  "framework_before": "<commit-or-null>",
  "framework_after": "<commit>",
  "lock_adopted_commit": "<commit-or-null>",
  "lock_matches_checkout": true,
  "update_status": "updated|already_current|partially_updated|blocked",
  "generated_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "claim_boundary": [
    "receipt is review evidence, not proof",
    "no fetch truth is implied unless explicitly recorded",
    "consumer repo adoption is not proven complete"
  ],
  "not_claimed": [
    "full governance adoption",
    "hook/CI enforcement",
    "memory completeness",
    "domain correctness",
    "release readiness"
  ]
}
```

Optional fields may include:

- `remote_evidence`: whether the tool fetched or compared a remote tracking ref;
- `human_readable_adoption_summary_hash`: hash of the table that was shown;
- `final_report_requirement_hash`: hash of the required relay text;
- `warnings`: report-only warnings emitted by the update path;
- `tool_result_digest`: digest of the machine result object.

Optional fields must not become required for Signal 2 unless a separate design
slice upgrades the contract.

## Write Timing

Receipt writing should happen only after a governed apply path reaches a
well-defined result.

Recommended timing:

1. updater/F-7 computes the update result;
2. updater/F-7 writes updated governance surfaces, including
   `governance/framework.lock.json`;
3. updater/F-7 computes lock-vs-checkout consistency;
4. updater/F-7 writes `governance/.update-receipt.json`;
5. the receipt is staged or left visible for review with the changed governance
   surfaces.

The receipt should not be written for pure read-only dry-run unless a separate
dry-run receipt path is explicitly designed. Mixing dry-run and apply receipts
would weaken Signal 2.

## Staging Policy

Preferred behavior:

- if an apply path changes `governance/framework.lock.json` or a framework
  gitlink, the receipt should be staged with those changes when the tool stages
  update files;
- if the tool does not stage files, the receipt should still be written in the
  working tree and reported in final output;
- final output should identify whether the receipt was written and whether it
  was staged.

The receipt does not authorize auto-commit or auto-push.

## Signal 2 Consumption

After receipts exist, Signal 2 can become:

- staged governance framework gitlink or `governance/framework.lock.json`
  changed;
- local lock-vs-checkout comparison is `consistent`;
- matching `governance/.update-receipt.json` is absent, stale, or does not name
  the same `framework_after` / `lock_adopted_commit`.

Candidate warning:

```text
AI Governance advisory: governance checkout and lock changed, but no matching
governed update receipt was found. If this was manual, report manual_update.
If a governed update was intended, rerun updater/F-7 and include the receipt.
```

Signal 2 must remain advisory-only unless a later OP-HC slice explicitly
changes hook/gate behavior.

## Spoofability Boundary

A receipt can be forged, copied, edited, or left stale. It is not proof that a
tool actually executed. It only gives reviewers and hooks a local evidence
surface to inspect.

Therefore:

- receipt present does not prove governed update compliance;
- receipt absent does not prove manual bypass;
- receipt mismatch is an advisory finding, not an enforcement decision;
- receipt content must be reported with `not_claimed` boundaries.

## Compatibility Boundary

Existing consuming repos will not have this receipt until a future update tool
implementation writes it and the consumer runs that updated tool.

This design does not claim:

- existing consumers are repaired;
- existing update history becomes auditable;
- installed hooks automatically receive Signal 2 behavior;
- updater/F-7 evidence is non-bypassable.

## Recommended Tranches

1. Implement receipt writing in updater/F-7 apply paths.
   - Scope: updater/F-7 tool output and tests.
   - No hook Signal 2 consumption yet.

2. Add receipt-aware final output.
   - Report receipt path, staged status, and claim boundary.
   - Keep human and JSON output aligned.

3. Implement Signal 2 advisory.
   - Consume receipt only after its writer exists.
   - Keep hook behavior advisory-only.

4. Measure consumer coverage.
   - Read-only inspect representative repos for receipt presence after update.
   - Do not claim fleet coverage from framework implementation alone.

## Claim Ceiling

This design defines a candidate governed update receipt format.

It does not claim:

- updater/F-7 currently writes receipts;
- Signal 2 is enabled;
- manual updates are prevented;
- receipt evidence is proof;
- consumers are repaired;
- hook, CI, pre-push, gate, or runtime enforcement changed;
- release readiness.
