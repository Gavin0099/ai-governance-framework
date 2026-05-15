# AB Causal Cross-Repo Observation Test Plan (2026-05-15)

As-of: 2026-05-15  
Scope: external observation after r35-r39 closeout (`threshold_dependent_persists`)  
Policy: keep strict gate unchanged; no claim upgrade wording drift

## Objective

Verify whether current AI governance effect is:

1. repo-specific threshold effect, or  
2. transferable mechanism effect under strict conditions.

## Fixed Protocol (Do Not Change)

- seed policy: `350101`, `350102`, `350103`
- `max_retry=3`
- checkpoint required
- strict gate (unchanged):
  - any arm must satisfy `pass_count=3/3` and `unsupported_count=0` to become `mechanism_stable_candidate`
  - if `unsupported_count=0` and no arm reaches 3/3 pass: `threshold_dependent_persists`
  - if any required arm is `unsupported>0`: `inconclusive`

## Repo Selection

Select 2 repos with different characteristics:

- Repo A: tooling/infrastructure-heavy
- Repo B: product/feature-heavy

## Per-Repo Run Matrix (Minimal First Pass)

For each repo:

- Arm 1: baseline strict configuration
- Arm 2: one-cause-one-fix arm (single variable only; no mixed changes)
- Seeds per arm: `350101`, `350102`, `350103`

Total per repo: `2 arms x 3 seeds = 6 cases`

## Required Artifacts Per Repo

- `ab-causal-<repo-id>-cross-repo-status-2026-05-15.md`
- `ab-causal-<repo-id>-cross-repo-checkpoint-2026-05-15.json`
- per-case condition-break result JSONs

## Output Contract (Per Case)

Each case must include:

- `completed` / `attempts_used`
- `pass|fail`
- `unsupported`
- `injected_controls` (if any)
- `causal_threat_probe`

## Cross-Repo Decision Rules

- If both repos remain `threshold_dependent_persists` under strict gate:
  - conclude low transferability of current mechanism family
  - open new hypothesis lineage (new mechanism family), do not continue threshold tuning
- If at least one repo has an arm with `3/3 pass` and `unsupported=0`:
  - mark repo-conditional mechanism viability
  - run replication in a third repo before any global claim upgrade

## Claim Boundary (External Wording)

Allowed:

- "Current AI governance effect is observable but condition-dependent."
- "Strict-regime mechanism stability is not yet established across repos."

Disallowed:

- "Mechanism robustness confirmed"
- "Generalized uplift proven"

## Execution Checklist

1. confirm repo contract and harness injection compatibility
2. lock arms and seeds before execution
3. run all cases with checkpoint/resume enabled
4. verify `unsupported_count` before gate interpretation
5. publish per-repo status and checkpoint
6. publish cross-repo summary with unchanged strict gate wording

