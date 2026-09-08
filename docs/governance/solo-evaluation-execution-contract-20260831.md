# Solo Evaluation Execution Contract

Status: **OWNER-AUTHORIZED / FROZEN / PRE-ID / EXECUTION NOT AUTHORIZED**

Date: 2026-08-31

## 1. Problem and current repository truth

The qualification phase is closed, but the adopted Solo protocol does not yet
instantiate the model, treatment packet, budget, permissions, arm order,
anonymous-label method, attempt-consumption boundary or ledger event schema.
Creating a Pair ID before those values are fixed would make Pair 0 irreversible
without a reproducible definition of the sole arm difference.

This contract is controlled by:

- Solo protocol commit `5778fe230fc5581916240828a03edfdb9259c791`,
  blob `cfb2624622d3c3ae56998091265cf8a396d9530a`, SHA-256
  `0eb4561564edf1620038900f46c441b30204fb939499556c60fcc921822a00cf`;
- Formal/Solo route split commit
  `ea46e4018b266d63ff0597ab4109d02b360b7b91`;
- final qualification checkpoint commit
  `1ff66ebd6dab87babc1ec47a14ca4dd95b6b2248`.

This is the owner-authorized instantiation of values already required by the
adopted protocol; it is not a protocol amendment, scoring-rule expansion or a
way to bypass the protocol's 6,000-byte compactness ceiling.

Qualification is `CLOSED / 7 OF 7 VALID SLOTS QUALIFIED`. Pair IDs, Attempt
IDs and arm executions are all `0` when this contract is frozen.

## 2. Target outcome, scope and non-goals

Target outcome: freeze one executable Control/Treatment contract and one
append-only ledger schema before any irreversible ID exists.

In scope: the seven qualified slots, pair/arm identity rules, admission,
treatment mounting, equal-arm environment, ordering, anonymous labels,
correctness/cost capture, failure semantics and ledger transitions.

Non-goals: creating a ledger file or any ID, materializing a consumer snapshot,
running an arm, changing an oracle or task, adding a validator, enabling
network access, cleaning temporary evidence, updating memory, repairing Formal
Gate 3, or authorizing push.

Affected surfaces are limited to this normative contract, the future ledger
path named in Section 8, the future arm controller and the isolated scoring
context. The ledger event fields are the only API defined here. No runtime,
validator, schema file, hook or consumer repository is implemented or changed
by this slice.

## 3. Frozen evaluation set and pair identity

Only the seven valid slots in `1ff66ebd` may be used: Pair 0 and A1–A6, with
A5-prime/ordinal 059 in the A5 slot. A5/ordinal 058 remains
`NOT_QUALIFIED` history and is forbidden from Solo execution.

The next slice creates one immutable Pair ID per slot. Each Pair binds slot,
category, repository, Base commit, oracle blob(s), required cases and the
qualification evidence reference. A Pair ID cannot be deleted, reused,
rebound, replaced or reassigned after creation. Results cannot cause task
selection, deletion or replacement.

Each Pair has exactly two planned arm records: `CONTROL` and `TREATMENT`.
Each arm may receive exactly one canonical Attempt ID. The study ceiling is
seven Pair IDs and fourteen consumed canonical attempts.

## 4. Frozen arm execution configuration

### 4.1 Model and budget

- Model selector: `gpt-5.6-sol`.
- Reasoning effort: `high`.
- Wall-clock cap: 1,800 seconds from task exposure.
- Tool-call cap: 60 top-level host-recorded tool invocations from task exposure.
- Retries inside an admitted arm: `0` after a terminal disposition.
- Fresh context: required for every arm; no conversation reuse.
- Provider-internal cache control: `UNAVAILABLE`; no cache-equivalence claim is
  permitted. Application-level prior-arm context and artifacts are absent.

Before task exposure, the controller records the runtime-reported model/build
string and Codex client/host identity. Both arms of a Pair must report identical
available strings. If the provider exposes no immutable backend build ID, record
`backend_build=UNAVAILABLE`; only selector, effort and exposed runtime identity
equality may be claimed. A differing available identity is
`PRE_ATTEMPT_INFRA_FAILURE / STOP`.

### 4.2 Tools and permissions

Both arms receive the same offline, isolated consumer snapshot and may use only:

- repository file read/search and scoped file editing;
- local shell commands in that snapshot;
- repository-provided build/test/type/lint commands;
- read-only Git inspection of the snapshot and diff/status of arm changes.

Both arms are denied network, web/connectors, package installation, credentials,
secrets, subagents, external messaging, consumer-repo mutation, qualification
artifacts, historical fix refs/diffs/messages, hidden oracle bytes/results and
the other arm's outputs. Filesystem write permission is limited to the arm's
snapshot and its designated temporary directory. A prohibited-tool attempt is
agent behavior after admission and is recorded, not silently retried.

### 4.3 Sole treatment difference

`CONTROL` receives no Skill packet: `treatment_state=ABSENT`.

`TREATMENT` receives exactly this existing packet as one additional developer
instruction after the common baseline context and before the identical task
prompt:

- Path: `artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md`
- Blob: `a37320e37f587fc45f9fd5797d91bb9f2762ac71`
- SHA-256: `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14`
- Bytes/LF/CR: `1,373 / 24 / 0`

The packet is instruction-injected, not copied into the consumer snapshot.
Step 8 does not grant treatment-time validator output; neither arm receives
such output. The task prompt, Base, visible files, tools, permissions, timeout,
budget and scoring remain identical. Any additional arm difference is
`ARM_PARITY_FAILURE / STOP`.

## 5. Frozen arm order and anonymous scoring

Order is deterministic and alternating; it cannot change after this freeze:

| Slot | First | Second |
|---|---|---|
| Pair 0 | CONTROL | TREATMENT |
| A1 | TREATMENT | CONTROL |
| A2 | CONTROL | TREATMENT |
| A3 | TREATMENT | CONTROL |
| A4 | CONTROL | TREATMENT |
| A5 | TREATMENT | CONTROL |
| A6 | CONTROL | TREATMENT |

At Pair creation, the controller generates two independent 128-bit opaque
hexadecimal scoring labels using the operating-system CSPRNG. The controller
records each label-to-arm mapping in the controller-only ledger, while the
fresh scoring context receives only identity-stripped outputs named by opaque
label and has no ledger access. Scores must be appended before an `UNBLINDED`
event reveals the mapping. Label generation failure is a pre-attempt stop.

## 6. Admission and attempt consumption

Before an Attempt ID is created, all of these must pass: Pair binding; exact
Base/oracle/qualification identities; isolated snapshot materialization;
resolution and CWD containment; required executable availability; identical
model/tool/permission/budget configuration; fresh arm context; writable ledger;
and no task or hidden oracle exposure.

An admitted arm proceeds in this order:

1. generate its unique Attempt ID;
2. append `ATTEMPT_ADMITTED` durably;
3. expose the task to the fresh arm context;
4. append `TASK_EXPOSED` immediately.

Consumption begins when the task is exposed. An admitted ID whose task exposure
fails remains reserved and cannot be reused; disposition is
`ADMITTED_NOT_EXPOSED / STOP` pending a revision-bound owner decision.

Failure before Attempt-ID creation is `PRE_ATTEMPT_INFRA_FAILURE / STOP` and
does not consume an attempt. After task exposure, crash, timeout, abandonment,
tool misuse, build/test failure, regression, incorrect/no solution, excess
cost or workspace contamination remains the canonical arm result. Even a
proven evaluator-only post-admission failure remains visible as
`HARNESS_FAILURE`; any replacement attempt requires a new owner decision and
cannot silently replace the original.

## 7. Correctness, regressions and cost

The evaluator applies the same frozen oracle and required cases to both arms.
It records required-case pass/fail, unintended regressions, applicable
build/type/lint status, observable correctness, allowed-scope compliance,
repository mutation and final disposition. Apparent plausibility cannot
override the oracle, and the oracle cannot be edited to fit an output.

Per attempt, record wall-clock milliseconds, top-level tool calls, model/tool
turns, files modified, retries, owner interventions and token/input/output/cost
fields when the host exposes them. An unavailable metric is the literal token
`UNAVAILABLE`; its definition cannot be replaced after results are visible.

## 8. Append-only ledger schema

Future ledger path:
`artifacts/evidence/solo-evaluation-20260831/attempt-ledger.ndjson`.
This slice does not create it.

Schema ID: `solo_attempt_ledger.v1`. Each state transition is one UTF-8,
no-BOM, LF-terminated JSON object. Existing lines are never updated or deleted.
Required common fields are:

| Field | Rule |
|---|---|
| `schema_version` | exact `solo_attempt_ledger.v1` |
| `event_seq` | integer, starts at 1 and increases by exactly 1 |
| `event_id` | unique UUIDv4 |
| `event_type` | one allowed transition token below |
| `timestamp_utc` | RFC 3339 UTC timestamp |
| `pair_id` | immutable ID; null only before Pair creation |
| `attempt_id` | immutable ID; null until admission |
| `slot`, `category`, `repository`, `arm` | frozen Pair/arm bindings |
| `frozen_identities` | protocol, contract, qualification, Base, oracle and treatment identities |
| `execution_contract` | model/build, budget, tools, permissions, order and scoring label |
| `admission` | named preflight results and task-exposure state |
| `execution` | status, timestamps, terminal reason and evidence refs |
| `correctness` | required cases, regressions, scope and final disposition |
| `cost` | frozen metrics or `UNAVAILABLE` |

Allowed event order per Pair/arm is:

`PAIR_CREATED` → `ATTEMPT_ADMITTED` → `TASK_EXPOSED` →
`EXECUTION_TERMINAL` → `SCORING_RECORDED` → `UNBLINDED`.

`PRE_ATTEMPT_INFRA_FAILURE` may be appended after `PAIR_CREATED` with null
`attempt_id`. `ADMITTED_NOT_EXPOSED` may follow `ATTEMPT_ADMITTED`. No later
event may rewrite an earlier disposition. Ledger append/fsync failure,
duplicate ID, sequence gap or invalid transition is `LEDGER_FAILURE / STOP`.

## 9. STOP rules and risk points

Immediately STOP on frozen-identity mismatch, oracle/harness mutation,
cross-arm leakage, ledger failure, resolution escape, CWD or governance-output
misrouting, unprovable arm parity, or inability to classify agent versus
infrastructure failure. STOP never authorizes retry.

Risk/limitation: this remains solo-controlled. CSPRNG labels and a fresh scorer
reduce bias but do not transfer control authority. Backend build and token/cost
fields may be unavailable. These limits reduce the claim; they do not convert
Solo evidence into Formal Gate 3 evidence.

## 10. Evidence plan, claim ceiling and next tranche

Evidence for the next tranche must show this contract's commit/blob/SHA-256,
Pair binding, zero prior IDs, ledger creation with schema-valid first event, and
unchanged qualification identities. No execution may precede a separate owner
authorization.

This artifact may claim only `SOLO_EXECUTION_CONTRACT_FROZEN`. It cannot claim
that a ledger, Pair, Attempt, arm, score or Skill effect exists; cannot reopen
Formal Gate 3; and cannot repair or replace prior terminal evidence.

Recommended next tranche: create the append-only ledger and Pair 0 Pair record,
verify both planned arm records and opaque labels, then STOP before generating
an Attempt ID or exposing the task.
