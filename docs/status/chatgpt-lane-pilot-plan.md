# ChatGPT Lane Pilot Plan (5 Runs)

Date: 2026-05-08  
Goal: establish the first comparable ChatGPT governance baseline under the same KPI schema used for Copilot/Claude.

## 1) Pilot Scope

- Target sample size: **5 runs**
- Mode: **stabilization-first**, no new governance feature rollout
- Output requirement: every run must be auditable under the same completion contract

## 2) Completion Contract (must pass per run)

A run counts as completed only when all are true:

1. semantic slice commit exists  
2. same-repo closeout session exists with `closeout_status=valid`  
3. closeout `task_intent` is compatible with slice purpose and time order is valid  
4. ledger row includes:
   - `commit_hash`
   - `session_id`
   - `closeout_covered: yes`
   - `mapping_confidence: high`

If any item is missing, mark run as `incomplete` and do not count as pilot pass.

## 3) Run Design (minimal but representative)

Use 5 bounded slices that cover both docs/control and implementation-touch surfaces:

1. docs-only consistency patch  
2. reviewer-facing wording + claim boundary patch  
3. cross-file sync patch (small)  
4. validator/tooling narrow patch  
5. remediation patch for a previously observed mapping/closeout gap

Constraint:
- no repo-wide refactor
- no mixed giant commit
- one semantic slice per run

## 4) Per-Run Checklist

Before run:
- declare primary target(s) and out-of-scope
- set task_intent text for closeout compatibility

During run:
- keep path-limited change
- avoid over-claim wording

After run:
- perform closeout in same repo/session
- verify session-index append with `valid`
- backfill ledger with `yes/high`
- run summary/detail consistency check

## 5) Pilot KPI Capture

Capture these fields per run:
- `engineering_runs_total`
- `closeout_valid_total`
- `closeout_missing_total`
- `closeout_valid_ratio`
- `mapped_high_total`
- `mapped_high_ratio`
- `scope_violation_total`
- `claim_overreach_total`
- `reviewer_edit_effort` (if available)
- token notes (engineering vs governance narration vs retry, if available)

Use:
- `docs/status/kpi-snapshot-template.md`

## 6) Success Criteria (for this 5-run pilot)

Minimum pass bar:
- 5/5 runs satisfy completion contract
- `closeout_valid_ratio` does not regress across the 5 runs
- `mapped_high_ratio` reaches >= 0.80 by run 5
- no hard scope violation

If pass bar fails:
- classify failure type (closeout missing / mapping mismatch / intent mismatch / wording over-claim)
- patch process first, then re-run failed slices

## 7) Non-Goals

- no claim of engineering correctness uplift from this pilot alone
- no enforcement escalation from this pilot alone
- no deterministic cognition claim

## 8) Deliverables

After run 5, produce:

1. `docs/status/chatgpt-lane-pilot-summary.md`
2. updated row in `docs/status/kpi-snapshot-template.md`
3. one paragraph comparison against current Copilot/Claude lanes:
   - execution maturity
   - audit mapping maturity
   - observed governance friction

