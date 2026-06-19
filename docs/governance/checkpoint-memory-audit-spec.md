# Checkpoint-Memory Consistency Audit Spec

Status: advisory-only spec
Date: 2026-06-19
Authority: user-approved spec slice
Implementation status: implemented as advisory CLI/reporting tool

## Purpose

Define an advisory audit that reports divergence between commits, checkpoint
surfaces, validation evidence, consumer hook state, and canonical memory
records.

This spec records the shape of the audit and its first advisory implementation.
It does not create a hook, CI gate, blocker, or policy contract for which
commits must have memory records.

## Trigger Evidence

Observed gaps motivating this spec:

- Memory workflow dispatch currently triggers on `memory/**` diffs, not every
  task slice or commit.
- `NO_COMMIT`, `WORKTREE`, `pending`, or `UNCOMMITTED` memory records are not
  automatically blockers when a `session_id` fallback exists.
- Local hook installation is a separate state from tool availability.
- Existing daily memory gates can verify that an outgoing range is referenced
  without requiring one memory record per commit.
- Consumer-repo memory symptoms can differ from framework-repo symptoms, but
  `NO_COMMIT` / pending records are reproducible in framework memory too.

## Inputs

All inputs are read-only.

| Input | Source | Use |
| --- | --- | --- |
| Recent commits | `git log` over a configured window; default candidate is `origin/main..HEAD`, with a future `--last N` override | Commit-to-memory comparison baseline |
| Memory records | `memory/YYYY-MM-DD.md` parsed for `commit`, `commit_hash`, `session_id`, `test_evidence`, `next_step`, and `plan_reconciliation` | Memory-to-commit and evidence-shape comparison |
| Checkpoint rollup surfaces | Candidate future inputs: runtime closeout receipts, session index exports, checkpoint rollup docs, or explicitly supplied artifact paths | Rollup-to-memory comparison |
| Validation evidence | Memory-declared PASS commands and any referenced receipt/log/artifact path | Evidence-shape comparison |
| Consumer install state | Target repo `.git/hooks/`, `.githooks/`, active `pre-commit` / `pre-push`, and memory workflow router text when explicitly supplied | Consumer coverage comparison |

## Mismatch Taxonomy

These findings are divergence signals, not violations.

| Code | Definition | Suggested action |
| --- | --- | --- |
| `commit_without_memory` | A commit in the selected window is not referenced by any parsed memory record. | Decide whether the commit required a memory record under a later contract. |
| `stale_no_commit_memory` | A memory record uses `NO_COMMIT`, `WORKTREE`, `pending`, or `UNCOMMITTED`, while later context suggests a real commit may now exist for that slice. | Add a corrective canonical memory record if the binding matters. |
| `unreceipted_validation` | A memory record declares validation PASS text without a receipt, log path, artifact path, or explicitly stated non-receipt evidence boundary. | Add evidence path or downgrade the validation claim. |
| `rollup_memory_divergence` | A supplied rollup/checkpoint surface references a commit or checkpoint not reflected in memory. | Reconcile rollup and memory, or mark the rollup as non-authoritative. |
| `consumer_uninstalled` | A supplied consumer repo lacks active non-sample hooks or memory workflow router coverage where coverage was expected. | Run or verify the consumer installation slice before claiming coverage. |

The taxonomy intentionally does not define which commits must have memory. That
belongs to a later contract slice.

First-version note: the advisory tool limits `stale_no_commit_memory` to
placeholder records in memory files whose `YYYY-MM-DD` filename matches a
selected commit date. This keeps recent-window audits from reporting the entire
historical placeholder backlog. It is a heuristic signal, not a violation rule.

## Output Schema

First implementation should emit JSON and a human summary. JSON shape:

```json
{
  "schema_version": "0.1",
  "generated_at": "2026-06-19T00:00:00Z",
  "scope": {
    "repo": "D:/ai-governance-framework",
    "window": "origin/main..HEAD"
  },
  "claim_class": "advisory",
  "blocking": false,
  "findings": [
    {
      "code": "commit_without_memory",
      "subject": "<commit_hash>",
      "evidence": "<git ref or file:line>",
      "suggested_action": "<reviewer action>",
      "severity": "advisory"
    }
  ],
  "summary": {
    "by_code": {
      "commit_without_memory": 0,
      "stale_no_commit_memory": 0,
      "unreceipted_validation": 0,
      "rollup_memory_divergence": 0,
      "consumer_uninstalled": 0
    },
    "total": 0,
    "clean": true
  }
}
```

Required first-version invariants:

- `claim_class` is always `advisory`.
- `blocking` is always `false`.
- All finding severities are `advisory`.
- Output does not authorize commit, push, release, completion, or enforcement
  claims by itself.

## Test Fixtures

Future implementation should include synthetic fixtures for:

- One clean case with zero findings and `summary.clean=true`.
- One `commit_without_memory` case.
- One `stale_no_commit_memory` case.
- One `unreceipted_validation` case.
- One `rollup_memory_divergence` case.
- One `consumer_uninstalled` case with only sample hooks.
- One consumer-installed case with active hooks/router coverage that does not
  emit `consumer_uninstalled`.

Fixtures should be local synthetic repos or temp directories. Tests must not
mutate the real repository, real hooks, real memory history, or consumer repos.

## Non-Goals

- No runtime hook.
- No CI gate.
- No blocker.
- No memory rewrite or auto-fix.
- No automatic memory promotion.
- No consumer repo mutation.
- No definition of which commits must have memory.
- No upgrade of divergence findings into violation authority.
- No release, Gate 3, P1-F, or semantic correctness claim.

## Future Slice Boundary

A later implementation slice may build an advisory reporting tool from this
spec. A separate contract slice is required before any blocker, hook, CI gate,
or "commit must have memory" rule is introduced.
