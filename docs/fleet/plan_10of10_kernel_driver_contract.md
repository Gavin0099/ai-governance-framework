# Plan: 10/10 Required Verified — Kernel-Driver-Contract

## Status

- current: 9/10 required verified → **10/10 in progress (2026-05-26)**
- target: 10/10 required verified
- blocker repo: Kernel-Driver-Contract
- remaining blockers (from matrix): `fw_unknown`, `agents=scaffold`

## Decision Gate Result (2026-05-26)

```
10/10 Decision Gate Result:
- checker_alternate_path_supported: false
  - call chain: PS1 → external_repo_readiness.py:253 → assess_agents_calibration_maturity()
  - agents_calibration_maturity.py:138 hardcodes repo_root / "AGENTS.md"; no contract.yaml lookup
- worth adding framework capability (Option A): defer — one repo case; blast radius covers all 20 repos
- selected option: B
- reason: Option A blast radius too high for single-repo case; Option C wraps tool limitation as domain
  exception (exception list inflation risk); Option B with machine-readable boundary markers gives
  clean semantic separation and preserves Option A migration path via script extraction
- pollution risk accepted: yes, with explicit boundary markers:
    <!-- governance:section_start=fleet_overlay --> / <!-- governance:section_end=fleet_overlay -->
- domain contract owner confirmed Option B acceptable: yes (2026-05-26)
```

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

## Decision Rule (Non-Negotiable)

> If a repo's `AGENTS.md` is an authoritative **domain contract document**, fleet governance calibration **must not modify or overwrite** that document's domain authority.
> Fleet governance calibration may only be added as a **parallel document**, explicitly referenced by `contract.yaml` or equivalent, with a clear boundary marker.

Consequence: 10/10 cannot be achieved through semantic mixing. An `agents=scaffold→repo_specific_minimal` transition that contaminates domain authority is not an acceptable path.

## Pollution Risk Table

| Pollution type | Risk |
|---|---|
| Governance calibration pollutes domain contract | Kernel / IRQL / IRP rules diluted by generic governance blocks |
| Domain contract masquerades as agents calibration | Matrix treats repo as governance-calibrated; it is only domain-documented |

Both pollution directions invalidate the `repo_native_verified` claim.

## Options to Evaluate

### Option A: Separate files (preferred direction)

Proposed structure:

```
AGENTS.md                       # domain contract — kernel/IRQL/IRP rules; untouched
governance/fleet.AGENTS.md      # fleet governance calibration — 4 governance:key sections
contract.yaml                   # explicitly references both files and their purpose boundary
```

- `AGENTS.md` remains domain authority, not modified.
- `governance/fleet.AGENTS.md` carries the 4 governance:key sections scoped to kernel driver governance risks (driver signing, unsafe memory access, version gates).
- `contract.yaml` references both and defines which is domain authority vs governance overlay.

**Risk**: agents_calibration checker currently reads `AGENTS.md` only. Must not credit `governance/fleet.AGENTS.md` as calibration evidence until checker supports alternate lookup path. Do not force-change matrix to make this work — checker support is a prerequisite, not a workaround.

**Status**: pending checker support assessment before implementation.

### Option B: Clearly partitioned sections in AGENTS.md

- Add a clearly delimited `## Governance Calibration` block at the bottom of `AGENTS.md` with an explicit header warning it is a governance overlay, not a domain rule.
- The 4 sections describe kernel-driver-specific governance risks, not generic fleet slogans.

**Risk**: mixing semantics in one file. Acceptable only with explicit separation markers and only if the domain contract owner agrees the document can carry dual semantics.

### Option C: Declare Kernel-Driver-Contract exempt from agents calibration

- Acknowledge it as a domain contract repo where `agents=scaffold` is a permanent expected state.
- Add a `governance_calibration_note` to `framework.lock.json` explaining the exception.
- Accept that 10/10 means "10/10 with one permanent domain-contract exception documented."

**Risk**: weakens the verified definition for domain contract repos. Must be an explicit scope exception with a named justification, not a silent skip. This makes 10/10 a formal acknowledgment of non-convergence, not verified convergence.

## Framework Capability Separation

If Option A requires the agents_calibration checker to support an alternate lookup path, that change is a **framework capability change**, not a Kernel-Driver-Contract onboarding change.

These two must not be mixed in the same commit:

| Change type | Scope | Commit rule |
|---|---|---|
| Framework capability: alternate agents path support | ai-governance-framework | Separate commit; must have explicit rules (see below) |
| Repo onboarding: governance/fleet.AGENTS.md + contract.yaml | Kernel-Driver-Contract | Separate commit; only after capability is confirmed |

If the checker is extended to support alternate paths, the extension must enforce:
- Source must be declared by `contract.yaml` (not auto-discovered)
- `AGENTS.md` domain authority cannot be overwritten or superseded
- Alternate file provides fleet calibration only — domain rules live in `AGENTS.md`
- Matrix report must show `agents_source = governance/fleet.AGENTS.md` (not opaque)

Adding an alternate path that accepts any AGENTS-like file as calibration evidence is a new semantic vulnerability. The extension must be fail-closed on source declaration.

**Correct sequence for Option A:**

1. Confirm whether checker currently supports alternate path
2. If not: evaluate whether adding the capability is in scope for this session
3. If in scope: implement as a separate framework commit with the rules above
4. Only then: onboard Kernel-Driver-Contract using the new path

## Prohibited Approaches

Do not do any of these three things:

| Prohibited action | Why |
|---|---|
| Modify `Kernel-Driver-Contract/AGENTS.md` to insert governance:key sections | Contaminates domain authority |
| Change checker to auto-fallback to `governance/fleet.AGENTS.md` without declaration | Creates source ambiguity |
| Declare Kernel-Driver-Contract temporarily exempt to hit 10/10 | Makes 10/10 a KPI metric, not governance convergence |

## Decision Gate

The first checkpoint of the 10/10 session is producing this gate result. No file edits before it is complete.

```
10/10 Decision Gate Result:
- checker_alternate_path_supported: true / false
- if true: declared_source_file: (must come from contract.yaml)
- if true: actual_checker_source_file: (must match declared)
- if true: matrix_reported_agents_source: true / false
- if true: domain_authority_file_untouched: true / false
- if true: source_ambiguity_detected: true / false
- if false: worth adding framework capability? yes / no / defer
- selected option: A / B / C / defer
- reason:
- pollution risk accepted? yes / no
```

Source ambiguity check: both `AGENTS.md` and `governance/fleet.AGENTS.md` exist, `contract.yaml` references one, checker must read exactly the declared source, matrix must report which source was used. If any mismatch: gate fails.

Answering these questions:

1. Does the agents_calibration checker currently support alternate lookup paths? (Inspect `governance_tools/` before assuming.)
2. Does the domain contract owner agree that `AGENTS.md` can carry a governance overlay (Option B), or is it off-limits?
3. Is Option C an acceptable permanent exception with explicit justification, or deferred debt that invalidates the 10/10 claim?

**Do not start file edits until one option is selected and the gate result is recorded.**

## Execution Order (Option A path only)

If Option A is selected after the gate:

- Step 0: Do not touch Kernel-Driver-Contract files
- Step 1: Inspect `governance_tools/` — confirm whether checker supports alternate AGENTS source
- Step 2: If not supported → stop onboarding; write framework capability plan; do not pursue 10/10 this session
- Step 3: If supported → confirm source declaration must come from `contract.yaml` (not auto-discovery)
- Step 4: Confirm matrix outputs `agents_source` field in per-repo row
- Step 5: Create `governance/fleet.AGENTS.md` in Kernel-Driver-Contract (separate commit from any framework change)
- Step 6: Rerun readiness + matrix
- Step 7: 10/10 checkpoint must record `verification_type = domain-contract-separated-calibration`

## Out of Scope for This Plan

- Changes to session_end_hook.py, gate_policy.py, or evidence admissibility criteria
- Schema changes to closeout receipts
- Any modification that would change the verified ratio for already-verified repos

## Snapshot Baseline

- pre-plan snapshot: `governance_repo_matrix_snapshot_20260526_153232.md`
- Kernel-Driver-Contract state: `matrix_only | hooks=Y | fw=N | agents=N | dirty_ok=Y | evidence=Y | head_ok=Y | ts_ok=Y`
