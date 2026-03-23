# Step 7 Rebaseline Checklist

> Purpose: rerun the three baseline task shapes after Step 7 `output tier separation`
> so token savings and remaining deferred work can be evaluated from fresh data.

## Scope

Re-measure these three flows:

1. `L0` UI / presentation task
2. `L1` normal implementation task
3. `Onboarding` / adoption task

Do not compare new runs against pre-Step-7 intuition only.
Always compare against the current committed baselines:

- [L0-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L0-baseline.md)
- [L1-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L1-baseline.md)
- [onboarding-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/onboarding-baseline.md)

## Preflight

- Pull latest `main`
- Confirm Step 7 commit is present: `e35f60c`
- Use the same Python/runtime path as the previous payload audit runs
- Clear expectation drift:
  - `L0` should stay clearly below the old L1 baseline
  - `L1` should improve mainly from output compression, not from domain removal
  - `Onboarding` should reflect `summary-first` impact before any new deferred optimization

## Commands

### L0

```bash
python runtime_hooks/core/session_start.py ^
  --project-root . ^
  --rules common ^
  --risk low ^
  --oversight auto ^
  --memory-mode candidate ^
  --task-level L0 ^
  --task-type ui ^
  --task-text "Update button label in UI" ^
  --format json
```

### L1

```bash
python runtime_hooks/core/session_start.py ^
  --project-root . ^
  --rules common ^
  --risk medium ^
  --oversight auto ^
  --memory-mode candidate ^
  --task-level L1 ^
  --task-type schema ^
  --task-text "Refactor state generator module" ^
  --format json
```

### Onboarding

```bash
python runtime_hooks/core/session_start.py ^
  --project-root . ^
  --rules common ^
  --risk medium ^
  --oversight auto ^
  --memory-mode candidate ^
  --task-level L1 ^
  --task-type onboarding ^
  --task-text "Adopt governance baseline for external repo" ^
  --format json
```

## What To Record

For each run, capture:

- task shape: `L0` / `L1` / `Onboarding`
- commit SHA
- date
- whether output is `ok`
- `task_level`
- `repo_type`
- `output_tier`
- total token estimate
- top token contributors
- whether `domain_contract` loaded
- whether Tier 3 artifact path was emitted
- notable warnings / blockers

## Decision Questions

After the three reruns, answer these before doing more optimization work:

1. Did Step 7 materially reduce `L1` and `Onboarding`, or mostly just `L0` presentation?
2. Is `kdc-adapter-summary.md` still the highest-yield deferred item?
3. Is `Step 3b` full memory refactor still justified after the new baseline?
4. Does `Onboarding` still deserve its own short-circuit, or is `summary-first` enough?

## Recording Template

Copy this into the relevant baseline file or a dated note.

```markdown
## Step 7 Rebaseline — <task-shape>

- Date: <YYYY-MM-DD>
- Commit: <sha>
- Command: `<exact command>`
- ok: <true|false>
- task_level: <L0|L1|L2>
- repo_type: <value>
- output_tier: <1|2|3>
- estimated_tokens: <number>
- domain_contract_loaded: <true|false>
- tier3_artifact_ref: <path or none>
- top_token_sources:
  - <source 1>
  - <source 2>
  - <source 3>
- notable_warnings:
  - <warning or none>
- delta_vs_current_baseline:
  - <L0/L1/onboarding delta>
- interpretation:
  - <what changed after Step 7>
- next_decision:
  - <stop / defer / continue specific optimization>
```

## Exit Criteria

You are done with Step 7 rebaseline when:

- all three task shapes were rerun
- each has a recorded token number
- each has a short interpretation
- one updated comparison summary exists
- deferred items are re-ranked from measured data, not estimates
