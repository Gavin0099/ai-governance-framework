# Task-Cost Extract-First Diagnostic (2026-06-25)

Status: diagnostic-only  
Scope: existing 2026-06-25 git log + memory evidence  
Tooling change: no  
Schema change: no  
Enforcement change: no

## Purpose

This note records what can be extracted from existing repository evidence before
adding any new task-cost schema, telemetry, or logging system.

The motivating question was whether the framework already has a task-level
metric for:

- rework rate;
- human acceptance/review count;
- total tokens to correct result.

The answer is: not as a reliable task-level metric. Existing evidence supports a
smaller and more defensible signal first: discrepancies caught.

## Current Repository Truth

Existing surfaces already contain partial cost/review fields:

- `docs/ab-v1.2-run-ledger.md` has `task_id`, `accepted_change_count`,
  `reviewer.disposition`, and `tokens_per_reviewer_accepted_fix`.
- `docs/ab-implementation-pressure-scorecard-v1.2.md` defines
  `actionable_fix_latency_sec`, `tokens_per_reviewer_accepted_fix`,
  `reviewer_edit_effort`, and related pressure metrics.
- `governance_tools/ab_cost_parity_audit.py` detects missing cost fields.
- `governance_tools/ab_cost_hygiene.py` normalizes placeholder cost values.
- `governance_tools/gate_c_report.py` computes window/lane-level
  `reopen_revert_rate`.

These surfaces do not yet provide a reliable per-task lifecycle metric tying
human acceptance and token usage to a specific correct-result event.

## Extracted Signal: Discrepancies Caught

The cleanest observable signal from 2026-06-25 is not "rework rate"; it is
"discrepancies caught before they became durable misleading state."

The following discrepancy-caught events were observable from the day's git log
and memory records:

1. Consumer hygiene fix was implemented but not pushed, so it had zero
   cross-repo effect until delivery.
2. Consuming repo update reporting treated `repo_native_verified` /
   `head_ok` / `ts_ok` too strongly; the correction clarified that these are
   receipt/evidence-chain integrity signals, not governance enforcement or
   framework correctness.
3. `AUTHORITY.md` default-load metadata was not inert prose:
   `session_start` consumes frontmatter-derived authority metadata.
4. `governance/PLAN.md` had live frontmatter that incorrectly placed a
   meta-template in the always/canonical authority tier.
5. The report-only authority metadata checker found table/frontmatter drift:
   `RULE_REGISTRY.md` missing from `AUTHORITY.md`, and three table rows whose
   docs lacked parser-readable frontmatter.
6. The initial authority metadata repair memory under-described runtime impact:
   it needed to record that `MEMORY_PROTOCOL.md` and
   `RESPONSE_ENVELOPE_CONTRACT.md` entered the L1/L2 on-demand allowlist as a
   corrective alignment, while L0 remained unchanged.

Minimum supported count:

```text
discrepancies_caught >= 6
```

This count is mixed-type: it includes self-caught delivery/reporting issues,
pre-existing governance debt found by audit/checker work, and external-agent
overclaim detection. Sub-typing is deferred to the event vocabulary step.

This is the strongest signal extracted in this slice.

## Reviewer-Induced Rework

Reviewer-induced rework should be separated from planned debt repair.

Clean sample:

- `eeff1b4 -> 79016e3`: the memory record for the authority metadata repair was
  re-done after review identified that the claim ceiling failed to mention the
  L1/L2 on-demand allowlist impact.

Supported count:

```text
reviewer_induced_rework_samples = 1
```

This is a clean sample because the rework was caused by a review finding against
newly produced work, not by a planned repair of old governance debt.

## Planned Debt Repair Is Not Reviewer-Induced Rework

The following commits are correction/repair work, but they should not be counted
as reviewer-induced rework:

- `58c53ea` corrected consuming-repo update reporting.
- `ab7d559` repaired the `governance/PLAN.md` authority tier.
- `459f369` repaired authority table/frontmatter drift.

These are valuable, but they primarily repair pre-existing governance debt found
by audit/checker work. Counting them as "rework rate" would inflate the metric
and blur planned remediation with review-induced redo.

## Why Correction Ratio Is Contaminated

A naive correction ratio such as:

```text
correction commits / forward commits
```

is not a reliable task-level rework rate for this session.

It mixes at least four different phenomena:

- planned governance debt repair;
- reviewer-induced rework;
- proposal -> implementation -> memory commit structure;
- memory-only records that document work but do not change behavior.

The session therefore supports directional interpretation only:

```text
correction ratio = contaminated / not headline metric
```

The headline should remain:

```text
discrepancies_caught >= 6
reviewer_induced_rework_samples = 1
```

## Token-to-Correct-Result Gap

`total_tokens_to_correct_result` remains insufficient data.

The missing piece is not a field name. It is the absence of two bindable events:

1. A provider-backed or otherwise trustworthy token total for the task lifecycle.
2. A clear human acceptance event that marks "correct result reached" for that
   same lifecycle.

Without both, a new schema would merely create a new field that still records
`insufficient_data`.

This matches the existing cost-hygiene reality:

- current AB cost fields frequently contain `insufficient_data`;
- `ab_cost_parity_audit.py` already treats missing token/cost data as the
  primary diagnostic surface;
- token observability alone is not correctness evidence;
- acceptance/review events are not consistently encoded as machine-readable
  task lifecycle boundaries.

## Claim Ceiling

Can claim:

- Existing 2026-06-25 evidence supports at least six discrepancy-caught events.
- Existing 2026-06-25 evidence supports one clean reviewer-induced rework sample.
- Existing repo surfaces have partial cost/review fields but do not provide a
  reliable task-level outcome-cost metric.
- `total_tokens_to_correct_result` remains unavailable without token telemetry
  plus a bindable human acceptance event.

Cannot claim:

- Governance ROI percentage was measured.
- Rework rate is reliable at task level.
- Human acceptance count is complete across the session.
- Total tokens to correct result can be computed from current data.
- A new schema would solve the token-to-outcome binding problem.
- Token volume proves correctness, authority, or governance value.

## Next Step

If this line continues, the next useful work is not a broad schema.

Recommended next slice:

1. Define the minimum observable event vocabulary for:
   - discrepancy caught;
   - reviewer-induced rework;
   - planned debt repair;
   - human acceptance event.
2. Test whether those events can be extracted from existing git + memory for one
   more session without new instrumentation.
3. Only after extraction proves useful, consider a small append-only record
   format for the single missing event that cannot be recovered.

Do not add token fields until provider-backed token telemetry and acceptance
events can be bound to the same task lifecycle.
