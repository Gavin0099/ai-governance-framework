# AGENTS Rule Aggregation Artifact Contract

This document defines the persisted artifact shape for aggregated AGENTS
rule-promotion candidates.

Canonical path:

- `artifacts/governance/agents_rule_candidates.json`

## Scope

This contract only defines the artifact payload shape.

It does not:

- connect runtime sources
- declare promotion complete
- mutate `AGENTS.md`
- authorize automatic rule creation

## Minimal Payload

```json
{
  "schema_version": "0.1",
  "generated_at": "2026-04-24T00:00:00Z",
  "source": "manual_or_test_fixture",
  "candidates": [],
  "suppressed_candidates": [],
  "ledger_refs": []
}
```

## Rules

1. artifact must be schema-validated
2. artifact is not promotion authority
3. artifact must not imply `AGENTS.md` was modified
4. runtime source integration is explicitly out of scope for v0.1
5. suppressed candidates must remain visible under `suppressed_candidates`

## Candidate Entries

`candidates` and `suppressed_candidates` both contain aggregation-result-shaped
entries.

At minimum each entry must carry:

- `candidate_id`
- `counted_evidence_refs`
- `duplicate_evidence_refs`
- `evidence_count`
- `first_seen_at`
- `last_seen_at`
- `evidence_window_days`
- `repo_specificity`
- `resurfacing_allowed`
- `resurfacing_reason`
- `suppressed_by_ledger`

Additional machine-readable fields are allowed as long as they do not claim
promotion authority.

## Suppressed Visibility

Suppressed candidates must not disappear from the artifact.

They must remain visible so operators and reviewers can see:

- what candidate was suppressed
- why it is suppressed
- whether resurfacing is blocked by ledger state

This prevents rejection history from being erased by omission.

## Ledger References

`ledger_refs` exists for traceability only.

It links the artifact to reviewer ledger records but does not replace those
records and does not become a promotion decision surface by itself.

## Authority Boundary

This artifact may:

- persist aggregated candidate state
- persist suppressed candidate state
- preserve ledger traceability

It may not:

- mark rules as promoted
- auto-update `AGENTS.md`
- bypass reviewer approval
- hide suppressed candidates
