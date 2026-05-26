# Plan: 10/10 Required Verified — Kernel-Driver-Contract

## Status

- current: 9/10 required verified
- target: 10/10 required verified
- blocker repo: Kernel-Driver-Contract
- remaining blockers (from matrix): `fw_unknown`, `agents=scaffold`

## Why This Is Not a Standard Onboarding

Kernel-Driver-Contract already passes: `hooks=Y`, `dirty_ok=Y`, `evidence=Y`, `head_ok=Y`, `ts_ok=Y`.

The two remaining blockers are structurally different from prior onboardings:

1. **`fw_unknown`** — `governance/framework.lock.json` is missing. This is mechanically simple to add.

2. **`agents=scaffold`** — The repo's `AGENTS.md` is a **domain contract document**, not a governance calibration template. It defines KSTATE/IRQL/IRP safety rules for kernel driver development. Writing generic governance:key sections into it risks semantic pollution of the domain contract.

## The Real Problem

Two semantically distinct documents are competing for the same file:

| Concern | Content type | Owner |
|---|---|---|
| Kernel domain rules (KSTATE, IRQL, IRP, dispatch) | Domain contract | Domain engineer |
| Governance calibration (risk_levels, must_test_paths, escalation_triggers, forbidden_behaviors) | Fleet governance | Governance framework |

The success condition for 10/10 is **not** "fill in AGENTS.md sections." It is:

> Prove that domain contract semantics and governance calibration semantics can coexist in this repo without either polluting the other.

## Options to Evaluate

### Option A: Separate files

- Keep `AGENTS.md` as domain contract, untouched.
- Add `governance/GOVERNANCE_CALIBRATION.md` with the 4 governance:key sections.
- Update agents_calibration checker to accept an alternate lookup path.

**Risk**: requires schema change to agents_calibration logic. Must not inflate verified ratio before checker supports alternate path.

### Option B: Clearly partitioned sections in AGENTS.md

- Add a clearly delimited `## Governance Calibration` block at the bottom of `AGENTS.md` with a comment header explaining it is a governance overlay, not a domain rule.
- The 4 sections describe kernel-driver-specific governance risks (driver signing, unsafe memory access, version gates), not generic fleet slogans.

**Risk**: mixing semantics in one file. Acceptable only if the domain contract block and governance block have explicit separation markers.

### Option C: Declare Kernel-Driver-Contract exempt from agents calibration

- Acknowledge it as a domain contract repo where agents=scaffold is expected.
- Add a `governance_calibration_note` to framework.lock.json explaining the exception.
- Accept that scope-normalized verified ratio uses a denominator of 9 (not 10) for this signal.

**Risk**: weakens the verified definition for domain contract repos. Must be an explicit scope exception, not a silent skip.

## Decision Gate

Before implementing, answer:

1. Is the kernel driver domain contract expected to serve as the governance calibration surface, or is it a separate document?
2. Does the agents_calibration checker need to change to support Option A, or is Option B sufficient?
3. Is Option C an acceptable permanent exception, or a deferred debt?

**Do not start file edits until one option is selected and its risk is accepted.**

## Out of Scope for This Plan

- Changes to session_end_hook.py, gate_policy.py, or evidence admissibility criteria
- Schema changes to closeout receipts
- Any modification that would change the verified ratio for already-verified repos

## Snapshot Baseline

- pre-plan snapshot: `governance_repo_matrix_snapshot_20260526_153232.md`
- Kernel-Driver-Contract state: `matrix_only | hooks=Y | fw=N | agents=N | dirty_ok=Y | evidence=Y | head_ok=Y | ts_ok=Y`
