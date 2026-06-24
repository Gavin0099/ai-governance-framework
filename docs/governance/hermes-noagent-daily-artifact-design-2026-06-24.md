# Hermes no_agent Daily Artifact Design - 2026-06-24

## Problem

The Windows Scheduled Task `AI Governance Hermes NoAgent Checklist` is active
and invokes `hermes_cli.main cron tick` at 09:00, but the 2026-06-24 run did
not produce a new checklist artifact.

The observed failure is not that Task Scheduler failed. The failure is that
Hermes had no due cron job to execute:

- Task Scheduler reported the task as `Ready`.
- The last task result was `0`.
- Hermes `cron/.tick.lock` was updated at 09:00.
- `logs/agent.log` recorded `09:00:04 - No jobs due`.
- `cron/jobs.json` contained `"jobs": []`.

This design chooses the minimal safe path to make the daily tick produce a
daily no_agent checklist artifact without widening into full Hermes agent,
provider, retention, or governance enforcement behavior.

## Current repository truth

- `PLAN.md` remains the current planning authority for repo direction.
- `docs/governance/hermes_no_agent_checklist/multi_repo_status.py` is the
  reviewed stdout-only read-only checklist script.
- `docs/governance/hermes_no_agent_checklist/multi_repo_status.config.json`
  pins the reviewed script hash and declares
  `claim_ceiling=observation_only_not_authority`.
- `docs/governance/hermes_no_agent_checklist/check_preflight.py` verifies:
  repo script hash, deployed script hash, deployed config hash, explicit repo
  list, isolated venv path, and `HERMES_HOME`.
- `docs/governance/hermes_no_agent_checklist/deploy_checklist.py` can deploy
  the reviewed script/config into `HERMES_HOME/scripts` with pre-copy and
  post-copy hash gates.
- `docs/governance/hermes_no_agent_checklist/generate_task_definition.py`
  generates Windows Task Scheduler dry-run definitions only; it does not
  install or run the task.
- `docs/governance/hermes_no_agent_checklist/install_checklist_task.ps1` is
  the reviewed human-run installer; it installs an OS scheduled task only when
  manually executed.
- The live authoring machine already has a scheduled task named
  `AI Governance Hermes NoAgent Checklist`, and canonical memory records that
  this OS-state is active on the machine but was not caused by tracking the
  installer source.
- Live `HERMES_HOME` inspection showed:
  - `C:\tmp\hermes-noagent-checklist-deploy-20260623\cron\jobs.json` has
    `"jobs": []`.
  - The latest `.md` artifacts are the 2026-06-23 manual/config probes.
  - The 2026-06-24 09:00 tick logged `No jobs due`.
- Hermes source truth from `E:\BackUp\Git_EE\hermes-agent`:
  - `hermes_cli/subcommands/cron.py` supports
    `hermes cron create <schedule> [prompt] --script ... --no-agent --workdir`.
  - `cron/jobs.py:create_job()` requires `script` when `no_agent=True`.
  - `create_job()` stores `no_agent`, `script`, parsed `schedule`, and
    `next_run_at` in `jobs.json`.
  - A cron expression such as `0 9 * * *` is a recurring schedule.
  - When `repeat` is omitted for a recurring schedule, `repeat.times` remains
    `None`, meaning it is not a one-shot job.
  - `cron/scheduler.py:tick()` runs due jobs and saves output under
    `cron/output/{job_id}/{timestamp}.md`; when no jobs are due it exits
    successfully and logs `No jobs due`.

## Target outcome

After a future implementation slice, the existing 09:00 scheduled tick should
find one reviewed no_agent Hermes cron job due and produce one daily checklist
artifact under:

```text
C:\tmp\hermes-noagent-checklist-deploy-20260623\cron\output\<job_id>\<timestamp>.md
```

The artifact remains an observation candidate, not authority.

## Scope

Design scope only:

- Compare two strategies:
  - persistent Hermes cron job registration;
  - Windows scheduled create-then-tick wrapper.
- Define the safer minimum path.
- Define preflight, registration, verification, and rollback evidence.
- Preserve the existing no_agent / no-provider / observation-only claim
  ceiling.

## Non-goals

- Do not register a cron job in this design slice.
- Do not edit `HERMES_HOME`.
- Do not install, uninstall, or modify Windows Scheduled Task state.
- Do not run `hermes cron tick`.
- Do not run the checklist script.
- Do not perform retention deletion.
- Do not call provider, LLM, network, or full Hermes agent paths.
- Do not change AI Governance runtime or enforcement behavior.
- Do not claim daily artifact generation is already working.

## Affected surfaces

Future implementation may touch:

- `HERMES_HOME/cron/jobs.json` on the authoring machine.
- `HERMES_HOME/cron/output/**` when a due tick later runs.
- Windows Task Scheduler only if the existing task must be updated, which is
  not the recommended first implementation tranche.
- Optional repo docs/memory recording the local OS-state observation.

Future implementation should not touch:

- `governance_tools/**`.
- `runtime_hooks/**`.
- AI Governance enforcement policy.
- Hermes source under `E:\BackUp\Git_EE\hermes-agent`.

## Boundary and API considerations

### Option A - persistent Hermes cron job registration

Register one recurring Hermes cron job in the isolated `HERMES_HOME`:

```powershell
$env:HERMES_HOME='C:\tmp\hermes-noagent-checklist-deploy-20260623'
& 'C:\tmp\hermes-cron-venv\Scripts\python.exe' -m hermes_cli.main cron create `
  '0 9 * * *' `
  --name 'AI Governance Hermes NoAgent Checklist Daily' `
  --deliver local `
  --script 'multi_repo_status.py' `
  --no-agent
```

Expected registration properties:

- `jobs.json` gains exactly one enabled job for the checklist.
- `schedule.kind == "cron"`.
- `schedule.expr == "0 9 * * *"`.
- `no_agent == true`.
- `script == "multi_repo_status.py"`.
- `deliver == "local"`.
- `repeat.times == null`.
- `next_run_at` is present.

This is the recommended direction. It fixes the actual observed failure:
`jobs.json` is empty while a daily tick already exists.

### Option B - Windows scheduled create-then-tick wrapper

Change the scheduled command so Windows creates a one-shot job and then ticks
each day.

This is not recommended as the first implementation because it makes Windows
Task Scheduler responsible for both registration and execution. It also risks
duplicate job creation if the create step succeeds and the tick step fails.

Keep this as a deferred fallback only if Hermes persistent cron registration
cannot preserve `no_agent` or cannot reliably produce one artifact per day.

## Claim ceiling

Can claim from this design:

- The 2026-06-24 no-artifact result is explained by empty Hermes job state:
  `jobs.json` had no due job.
- A persistent Hermes cron job is the narrowest proposed fix because the
  existing OS task already runs `cron tick`.
- The proposed job is no_agent only if the registered job stores
  `no_agent=true` and `script=multi_repo_status.py`.

Cannot claim from this design:

- Daily artifact generation is fixed.
- A persistent cron job has been registered.
- The existing scheduled task has been changed.
- The 09:00 task will produce tomorrow's artifact.
- Provider/LLM paths are impossible in all Hermes cron configurations.
- AI Governance enforcement changed.
- Hermes cron output is canonical governance evidence.

## Failure paths or risk points

- **No job due**: `jobs.json` remains empty or `next_run_at` is in the future;
  tick exits `0` with no artifact.
- **Wrong job mode**: registration omits `--no-agent`; Hermes would run the
  LLM/agent path.
- **Wrong script**: registration points to a script not matching the reviewed
  pin.
- **Duplicate jobs**: repeated registration creates multiple daily jobs unless
  an implementation slice first checks for an existing matching job.
- **Time drift**: `0 9 * * *` and Task Scheduler both express local time; an
  unexpected timezone/config change can shift `next_run_at`.
- **Preflight gap**: the current scheduled task runs preflight before tick, but
  registration itself must also be preflight-gated.
- **Artifact absence after registration**: a future tick may still produce no
  artifact if `next_run_at` is not due or the job is paused/disabled.
- **Artifact interpretation**: the generated `.md` remains observation-only and
  must be independently verified against live git when used for decisions.

## Evidence plan

For a future implementation slice:

1. Run `check_preflight.py` against the target `HERMES_HOME` and venv.
2. Read current `jobs.json` and refuse to register if a matching active
   checklist job already exists.
3. Register the persistent job with `--no-agent`, `--script
   multi_repo_status.py`, `--deliver local`, and schedule `0 9 * * *`.
4. Read `jobs.json` after registration and verify the expected fields:
   `no_agent`, `script`, `schedule.kind`, `schedule.expr`, `repeat.times`,
   `enabled`, `state`, and `next_run_at`.
5. Do not run `cron tick` in the registration slice unless explicitly
   authorized as a separate validation slice.
6. On the next scheduled run, verify:
   - Task Scheduler `LastRunTime` advanced;
   - `agent.log` reports one due job, not `No jobs due`;
   - one new `.md` artifact exists under `cron/output`;
   - artifact content matches the reviewed checklist script output shape.

Rollback for registration:

- Remove only the specific matching Hermes cron job by job id or name.
- Do not delete historical output artifacts unless a separate retention slice
  explicitly authorizes deletion.

## Implementation tranche recommendation

Recommended next tranche:

- Add a dry-run Hermes cron registration planner that:
  - runs existing package preflight;
  - reads `jobs.json`;
  - reports whether a matching job already exists;
  - emits the exact human-run `hermes cron create` command;
  - emits expected post-registration `jobs.json` checks;
  - does not mutate `HERMES_HOME`;
  - does not run tick.

Only after that dry-run planner is reviewed should a human-authorized
registration slice mutate `HERMES_HOME/cron/jobs.json`.

Deferred fallback:

- A Windows create-then-tick wrapper should only be considered if persistent
  Hermes registration fails to preserve a reviewed no_agent daily job.
