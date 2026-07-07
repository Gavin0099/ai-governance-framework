# Rare-Critical Defense Rehearsal Design - 2026-07-07

Status: design/reference note
Runtime behavior change: no
Enforcement change: no
Tooling change: no
Consumer repo change: no

## Purpose

The maintenance-budget design
(`docs/governance/governance-surface-maintenance-budget-design-2026-07-07.md`)
exempts rare-critical defenses from frequency-based retirement and requires a
different proof path: reachability review, rehearsal, mutation testing, or
explicit human decision. This note defines what those proof paths concretely
look like, so the exemption does not silently become "never verified".

Motivating evidence: the E1-B Phase 2 mutation run (2026-05-12) found 4/4
tested rules VULNERABLE - defenses that rarely fire are exactly the ones whose
failure goes unnoticed. Frequency cannot prove them; only deliberate exercise
can.

This is a design artifact only. It does not run any rehearsal, add any tool,
gate, hook, or receipt, and does not change any defense.

## Covered Defenses

The four `keep_rare_critical` entries in
`docs/governance/governance-surface-maintenance-queue.v0.1.json`:

| Defense | Class |
|---|---|
| `memory_freshness_guard` | fail-closed guard |
| `phase_d_closeout_writer` | human-only close gate |
| `escalation_authority_writer` / `escalation_authority_path_guard` | authorized-path boundary |
| push / destructive-operation authorization discipline | instruction-layer boundary |

New rare-critical defenses must be added to this table when they are marked
`keep_rare_critical` in the maintenance queue.

## Proof Path Taxonomy

### 1. Mutation drill (for fail-closed guards)

Feed the guard a violating input in an isolated fixture and assert it actually
blocks. The drill fails if the guard passes the violation through.

Applies to: `memory_freshness_guard`.

Minimum drill shape:

- construct a fixture workspace with deliberately stale / malformed structured
  memory;
- run the guard against the fixture;
- assert fail-closed behavior (non-zero exit or blocking verdict), not just a
  warning string;
- record which mutation classes were exercised (stale timestamp, missing file,
  schema violation) and which were not.

### 2. Negative rehearsal (for human-only gates)

Attempt the forbidden action from the agent side in a sandbox and assert
refusal. The rehearsal fails if the AI-side path succeeds.

Applies to: `phase_d_closeout_writer`.

Minimum rehearsal shape:

- in a fixture repo, attempt an AI-side phase-D closeout write without the
  human-only precondition;
- assert the writer refuses (fail-closed), and that the refusal is
  distinguishable from an environment error;
- confirm the documented human path still exists and is reachable.

### 3. Replay rehearsal (for authorized-path boundaries)

Replay a synthetic event and assert artifacts land only on authorized paths.

Applies to: `escalation_authority_writer` + `escalation_authority_path_guard`.

Minimum replay shape:

- emit a synthetic escalation through the writer in a fixture workspace;
- assert artifacts appear only under the authorized escalation paths;
- attempt one unauthorized target and assert the path guard rejects it.

### 4. Scenario rehearsal (for instruction-layer boundaries)

Instruction-layer discipline (push authorization, destructive-operation stops)
has no single executable guard; its proof is behavioral. This is the weakest
measurability class and must be labeled as such.

Applies to: push / destructive-operation authorization discipline.

Minimum scenario shape:

- scripted session scenario in a sandbox clone where the task pressure points
  toward an unauthorized push or destructive operation;
- evidence is the session transcript plus any hook-level refusal;
- where a hook exists (pre-push), pair the scenario with a hook-level check so
  at least one constraint-based layer is exercised;
- a passed scenario proves discipline held once, not that it always holds;
  claims must stay at that ceiling.

## Rehearsal Evidence Shape (future artifact, not created here)

A future rehearsal receipt may look like:

```json
{
  "schema": "rare_critical_rehearsal_receipt.v0.1",
  "defense_id": "memory_freshness_guard",
  "rehearsal_type": "mutation_drill",
  "scenario_ref": "fixture or scenario path",
  "expected": "fail_closed_block",
  "observed": "blocked | passed_through | error",
  "verdict": "held | failed | inconclusive",
  "mutation_classes_exercised": [],
  "mutation_classes_not_exercised": [],
  "evidence_refs": [],
  "claim_ceiling": "proves this defense blocked these scenarios on this date; not a general guarantee"
}
```

A `failed` verdict on a rare-critical defense is a high-salience finding and
must not be silently downgraded.

## Cadence

Per the maintenance-budget design:

- after any change to the defense itself or its wiring;
- otherwise on a slow fixed cadence (quarterly is sufficient);
- before any proposal to retire or downgrade a rare-critical defense.

Rehearsal results feed the decision-change ledger as evidence entries; they do
not create gates.

## Recommended First Slice

Start with the cheapest, fully in-repo, deterministic drill:

> Mutation drill for `memory_freshness_guard`: fixture workspace with stale
> structured memory, assert fail-closed block, emit a test-evidence receipt.

This can be a focused pytest module plus a receipt; no new tool, no hook, no
gate. The other three proof paths need their own scoped slices and should not
be bundled.

## Non-Claims

This note does not claim:

- any rehearsal has been run;
- any rare-critical defense is currently effective;
- any receipt schema is implemented;
- any hook, gate, CI, or enforcement changed;
- scenario rehearsals prove general agent compliance.

## Claim Ceiling

Design only. Effectiveness claims for rare-critical defenses require executed
rehearsals with durable receipts, reviewed per slice.
