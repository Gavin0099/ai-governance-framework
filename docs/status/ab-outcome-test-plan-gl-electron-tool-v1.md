# A/B Outcome Test Plan (gl_electron_tool, Single-Repo, Single-Agent)

- date: 2026-05-13
- objective: validate whether governance improves engineering outcome (not only behavior style)
- scope: one repo, one agent lane, controlled A/B comparison
- boundary: observational-to-candidate-outcome uplift only; no quality/reasoning proof claim

## 1. Test Design

- repo: `E:\BackUp\Git_EE\gl_electron_tool`
- agent lane: choose one lane only for this round (recommended: `chatgpt`)
- arm A: minimal-governance (no contract pressure; keep same task + same reviewer rule)
- arm B: governance-enabled (current runtime governance path)
- run count: `A=10`, `B=10` (total 20)
- task pack: same task pack and order for both arms

## 2. Controlled Variables

Keep these identical between A and B:

1. task pack content and difficulty
2. reviewer and acceptance rule
3. closeout rule and commit boundary
4. execution window (same day/range if possible)
5. evidence capture path and log schema

## 3. Outcome Metrics (Fixed)

1. `review_minutes_median`
2. `reopen_revert_rate = (reopen_count + revert_count) / total_changes`
3. `stability_degraded_rate = degraded_rows / total_rows`
4. `post_merge_defect_count_7d`
5. `time_to_close_median`

## 4. Data Capture Files

- `docs/status/ab-outcome-window-<window_id>-review-log.ndjson`
- `docs/status/ab-outcome-window-<window_id>-rework-log.ndjson`
- `docs/status/ab-outcome-window-<window_id>-stability-log.ndjson`
- `docs/status/ab-outcome-window-<window_id>-defect-log.ndjson`
- `docs/status/ab-outcome-window-<window_id>-summary.md`

Each row must include:

- `window_id`
- `arm` (`A` or `B`)
- `lane`
- `run_id`
- required metric fields
- `evidence_ref` (artifact path)

## 5. Decision Gates

Promote from observational to `candidate_outcome_uplift` only when all are true:

1. `review_minutes_median` improves by `>= 15%` in B vs A
2. `reopen_revert_rate` in B is not worse than A
3. `stability_degraded_rate` in B is not worse than A
4. no data-consistency failure in logs

If any gate fails: remain `observational_only`.

## 6. Execution Steps

1. freeze task pack and reviewer rules
2. run Arm A (10 runs), capture logs
3. run Arm B (10 runs), capture logs
4. compute 5 metrics for A and B
5. write summary with pass/fail per decision gate
6. record claim boundary (no over-claim)

## 7. Summary Template

```md
# AB Outcome Summary <window_id>

- repo:
- lane:
- A runs:
- B runs:

## Metrics
- review_minutes_median: A= , B= , delta=
- reopen_revert_rate: A= , B=
- stability_degraded_rate: A= , B=
- post_merge_defect_count_7d: A= , B=
- time_to_close_median: A= , B= , delta=

## Gate Check
1. review_minutes improvement >=15%: pass/fail
2. rework not worse: pass/fail
3. stability not worse: pass/fail
4. data consistency clean: pass/fail

## Decision
- result: observational_only / candidate_outcome_uplift
- boundary: no quality/reasoning proof claim
```

## 8. Claim Boundary

Allowed:

- "B shows candidate outcome uplift under this controlled window"

Not allowed:

- "governance universally improves quality"
- "reasoning uplift proven"
- "deterministic correctness achieved"

