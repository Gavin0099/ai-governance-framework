# Runtime Phase Execution Policy v0.1

This slice defines runtime governance execution phases.

Goal:

- make blocking behavior explicit
- prevent hidden gates
- prevent async audit from retroactively mutating an execution verdict

This slice is not about runtime speed.
It is about keeping governance from becoming an opaque second runtime.

## Taxonomy

### `sync_gate`

Blocking, synchronous execution gate.

- may stop or block execution
- must be visible to the operator
- must not be hidden behind advisory wording

Examples:

- `precondition_gate`
- `forbidden_claims`
- `invalid_evidence_schema`

### `sync_advisory`

Synchronous reviewer-visible advisory.

- may warn or degrade confidence
- must not silently block execution
- must not be treated as a hidden gate

Examples:

- `required_evidence_missing`
- `assumption_check_missing`

### `async_closeout`

Deferred closeout work after execution.

- may write closeout artifacts
- may summarize runtime outcomes
- must not change the already-issued synchronous verdict

Examples:

- `canonical_closeout`
- `daily_memory_append`

### `async_audit`

Deferred audit / trace / candidate surfacing.

- may publish reviewer-visible audit artifacts
- may surface candidate memory or governance signals
- must not retroactively upgrade or downgrade the synchronous verdict

Examples:

- `memory_candidate_snapshot`
- `memory_promotion_candidate`
- `cross_repo_drift_analysis`

### `manual_review_only`

Human-only authority path.

- AI may surface or prepare material
- final authority must remain with human review

Examples:

- `reviewer_promotion_decision`

## Execution Rules

- only `sync_gate` may block execution
- `sync_advisory` must never become a hidden gate
- `async_closeout` must not reopen synchronous execution decisions
- `async_audit` must not retroactively change verdicts
- runtime phase decisions must come from the declared phase mapping, not ad hoc per-hook reinference

## Explicitly Excluded

- rollback automation
- multi-step self-correction loop
- automatic remediation engine
- policy auto-promotion
