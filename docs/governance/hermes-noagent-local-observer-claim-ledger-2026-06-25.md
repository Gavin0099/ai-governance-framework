# Hermes no_agent Local Observer Claim Ledger - 2026-06-25

Status:

```text
docs-only
claim-ledger
no implementation
no runtime change
no scheduler change
no governance enforcement change
```

## Problem

Hermes has moved from mock/fixture integration toward a useful local
observation role: a reviewed no_agent cron job now produces a scheduled local
artifact. The risk is claim drift. A single successful scheduled artifact can
easily be over-read as reliability, governance compliance, provider safety, or
agent readiness.

This ledger classifies what is currently supported and what remains deferred so
future Hermes work can advance claims deliberately.

## Current repository truth

Repository planning and design truth read for this ledger:

- `PLAN.md` is the current planning authority and still frames Hermes as an
  executor-adapter line with explicit non-claims for real Hermes governance,
  full runtime reliability, and non-bypassable wrapping.
- `docs/governance/hermes-real-integration-contract-spec-2026-06-22.md`
  records that cron output is the observed natural file artifact surface for
  real Hermes, while interactive and ACP paths remain deferred.
- `docs/governance/hermes-noagent-daily-artifact-design-2026-06-24.md`
  records the daily artifact path design: the 2026-06-24 scheduled tick
  succeeded but produced no artifact because no Hermes cron job was due.
- `docs/governance/hermes_no_agent_checklist/multi_repo_status.config.json`
  pins the reviewed checklist script hash and declares
  `claim_ceiling=observation_only_not_authority`.
- `docs/governance/hermes_no_agent_checklist/check_preflight.py` verifies the
  reviewed package/deployed script/config alignment, explicit repo list, venv,
  and HERMES_HOME, but it does not prove registered job state or governance
  compliance.
- `memory/2026-06-24.md` records the persistent local Hermes cron job
  registration as a runtime observation with job id `025890509ebf`.
- `memory/2026-06-25.md` records the first successful unattended scheduled
  no_agent checklist artifact observation.

Observed local runtime anchors from the 2026-06-25 read-only observation:

- Windows Scheduled Task:
  `AI Governance Hermes NoAgent Checklist`.
- Task last run:
  `2026-06-25 09:00:01 +08`, result `0`.
- Task next run:
  `2026-06-26 09:00:00 +08`.
- HERMES_HOME:
  `C:\tmp\hermes-noagent-checklist-deploy-20260623`.
- Hermes job id:
  `025890509ebf`.
- Hermes job last status:
  `ok`.
- Hermes job next run:
  `2026-06-26T09:00:00+08:00`.
- Artifact:
  `C:\tmp\hermes-noagent-checklist-deploy-20260623\cron\output\025890509ebf\2026-06-25_09-00-05.md`.
- Artifact shape:
  contains `mode=hermes_cron_no_agent` and
  `claim_ceiling=observation_only_not_authority`.

## Target outcome

Provide a reviewer-readable claim ledger for Hermes no_agent local observer
work. The ledger should let future changes say exactly which claim tier they
advance and which claims remain unsupported.

## Scope

In scope:

- classify current Hermes no_agent local observer capabilities as:
  - `verified`;
  - `observed_once`;
  - `observed_twice`;
  - `not_verified`;
  - `deferred`;
- list evidence anchors for each supported claim;
- preserve non-claims for full agent, provider/LLM, ACP/interactive,
  governance compliance, retention deletion, and reliability;
- recommend the next smallest evidence tranche.

Out of scope:

- no source implementation;
- no cron tick;
- no scheduled task install, uninstall, or modification;
- no HERMES_HOME mutation;
- no provider, LLM, browser, web, image, or full agent path;
- no AI Governance adapter behavior change;
- no retention deletion.

## Claim classification

| Capability | Current tier | Supported claim | Evidence anchors | Cannot claim |
|---|---|---|---|---|
| Hermes cron no_agent package integrity | verified | Reviewed package and deployed script/config can be preflight-checked before scheduled runs. | `multi_repo_status.config.json`; `check_preflight.py`; deployed script/config hash checks recorded in prior memory. | Preflight proves registered job semantics, job execution, or governance compliance. |
| Persistent Hermes no_agent job registration | verified | Local HERMES_HOME contains one scheduled checklist job with `no_agent=true`, `script=multi_repo_status.py`, `deliver=local`, and cron schedule `0 9 * * *`. | `memory/2026-06-24.md`; `jobs.json` runtime observation; job id `025890509ebf`. | General job schema lifecycle, edit/delete/migration stability, or all Hermes cron configurations. |
| Windows scheduled task path | verified | A Windows Scheduled Task exists locally and invokes preflight followed by `hermes_cli.main cron tick`. | Task name `AI Governance Hermes NoAgent Checklist`; observed LastRun/NextRun; installer source in `install_checklist_task.ps1`. | OS-state portability, fleet deployment, or that tracking installer source itself installed the task. |
| Scheduled daily artifact production | observed_once | One unattended scheduled run produced a no_agent checklist artifact on 2026-06-25. | Task LastRunTime `2026-06-25 09:00:01 +08`; `jobs.json` `last_status=ok`; artifact path `...\025890509ebf\2026-06-25_09-00-05.md`; agent log output-saved line. | Recurrence reliability, ongoing daily production, or that future scheduled runs will succeed. |
| Recurrence observed twice | not_verified | No claim yet. | Requires a second later scheduled run and artifact. | Reliability, SLA, or stability. |
| Hermes as local observer | observed_once | Hermes can act as a low-risk local scheduled observation runner for a reviewed no_agent script. | The 2026-06-25 scheduled artifact and reviewed checklist package. | Hermes is a general agent runtime, sandbox, or authority layer. |
| Artifact as evidence | verified for shape, observed_once for scheduled production | Artifact shape is useful observation evidence at its timestamp. | Markdown artifact with `mode=hermes_cron_no_agent` and `claim_ceiling=observation_only_not_authority`. | Artifact is standing authority, live git truth, semantic correctness, or governance compliance. |
| Full Hermes agent / LLM path | deferred | No claim. | None in this line. | Full agent startup, LLM execution, autonomous tool use, credential safety, or provider behavior. |
| Provider-free runtime | not_verified | No claim. | Logs show provider plugins are loaded by the runtime, while the job itself is no_agent. | Runtime cannot call providers. `no_agent` is per-job, not provider-free runtime. |
| Interactive / ACP path | deferred | No claim. | Prior spec records these as stream/protocol shaped and deferred. | Interactive/ACP capture, response_file artifact generation, or governance coverage. |
| AI Governance compliance | not_verified | No claim. | Prior live artifact check found raw Hermes output lacks `[Governance Contract]`. | Governed execution, contract compliance, enforcement, or machine attestation. |
| Retention deletion | deferred | No claim. | Existing designs name retention as separate delete-capable work. | Cleanup is implemented, deletion is safe, or old artifacts are managed. |

## Boundary and API considerations

### Claim tiers

Use these tiers consistently:

- `verified`: static or state field was directly inspected and matched the
  expected value.
- `observed_once`: one runtime event occurred and produced expected evidence.
- `observed_twice`: two separate scheduled runtime events occurred and
  produced expected evidence.
- `not_verified`: a claim is plausible or desired but has not been evidenced.
- `deferred`: the surface is intentionally out of current scope.

`observed_twice` is not reliability. It is only stronger recurrence evidence
than `observed_once`.

### Authority semantics

The scheduled artifact is an observation candidate. Live git state remains the
authority for current repo status. AI Governance canonical memory remains under
the repo memory protocol. Hermes output does not become framework canonical
memory unless a later approved path converts it through the canonical writer.

### Provider boundary

The 2026-06-25 job is no_agent. That is a per-job property. It does not make
the Hermes runtime provider-free. Logs show provider plugins can be loaded by
the runtime; this ledger makes no claim that providers are impossible.

### Governance boundary

The artifact is not governance compliant merely because it exists. The prior
Hermes metadata strategy records that live Hermes cron output does not emit the
synthetic `[Governance Contract]` block used by the Tranche 1A fixture. Any
future governance metadata strategy must use sidecar/wrapper binding or a
separate approved predicate-native-artifact-class change.

## Claim ceiling

Can claim now:

- local HERMES_HOME has one persistent reviewed no_agent daily checklist job;
- local Windows Scheduled Task has invoked the preflight-gated tick path;
- one scheduled no_agent daily artifact was observed on 2026-06-25;
- the artifact is useful as timestamped observation evidence only.

Cannot claim now:

- recurrence reliability;
- scheduled production beyond the single observed run;
- provider-free runtime;
- full agent readiness;
- LLM/provider safety;
- interactive or ACP coverage;
- AI Governance compliance;
- non-bypassable enforcement;
- provenance machine-attestation;
- retention cleanup;
- semantic correctness of artifact content;
- that artifact content remains current after its timestamp.

## Failure paths or risk points

- The scheduled task may continue to run while the registered job is disabled,
  paused, deleted, or has a future `next_run_at`.
- Preflight may pass package integrity while the persistent job state is wrong;
  job-state verification is a separate check.
- A future scheduled tick can return success but produce no artifact if no job
  is due, as observed on 2026-06-24.
- The artifact can be stale immediately after repo state changes.
- `no_agent=true` prevents the job from entering the agent path for this
  script, but it does not sandbox arbitrary Python script behavior.
- Retention is delete-capable and must not be bundled with observation.

## Evidence plan

For the next read-only recurrence observation:

1. After the next scheduled 09:00 run, query the Windows Scheduled Task state.
2. Read `jobs.json` and verify:
   - `last_run_at` advanced;
   - `last_status == ok`;
   - `next_run_at` advanced to the following day;
   - job id remains `025890509ebf`;
   - `no_agent == true`.
3. Read the latest `cron/output/025890509ebf/*.md` artifact.
4. Verify artifact shape:
   - job id;
   - run timestamp;
   - `mode=hermes_cron_no_agent`;
   - `claim_ceiling=observation_only_not_authority`.
5. Independently verify any artifact repo-status claims against live git before
   using them for decisions.
6. Do not run manual tick in the recurrence observation slice.

## Implementation tranche recommendation

Recommended next tranche:

```text
read-only observe the next scheduled 09:00 run and, if successful, update this
ledger from observed_once to observed_twice for scheduled daily artifact
production.
```

Deferred tranches:

- expand the checklist script with additional read-only repo facts;
- design retention policy without deletion;
- add a separate Hermes self-health no_agent job;
- design sidecar/wrapper governance metadata;
- revisit full agent / interactive / ACP only after explicit authorization.

## Non-claims

This ledger does not implement anything. It does not run Hermes, mutate
HERMES_HOME, install or modify a scheduled task, call providers or LLMs, delete
artifacts, or change AI Governance enforcement.
