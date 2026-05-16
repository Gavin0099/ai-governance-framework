# R50.4 — Negative Control (2026-05-16)

Task: r50-4
Status: complete
Result: **pass — zero MIP-02 violations, zero MIP-04 bypass attempts**
As-of: 2026-05-16
Freeze contract: `governance/CONFIDENCE_SEMANTICS_FREEZE.md` (v2)

---

## Goal

Confirm MIP-02 and MIP-04 blockers remain effective across all R50-phase artifacts.

| Blocker | Check |
|---|---|
| MIP-02 | No artifact claims causal attribution from `claim_discipline_drift` without R49.x-1 |
| MIP-04 | `reviewer_override_frequency` remains null; no proxy or default substituted |

---

## MIP-02 Audit

**Blocker:** Causal attribution from `claim_discipline_drift` requires R49.x-1
(evaluator neutrality topology) to be completed. R49.x-1 status is
`neutrality_topology_collected` — topology observed, not attribution-validated.
Attribution claim is not yet admissible.

### Artifacts audited for MIP-02 violations

| Artifact | `claim_discipline_drift` usage | Causal claim present? |
|---|---|---|
| checkpoint | raw metric value in each run | No — stored as observation |
| r49x-4 ranking | classified as observational_only; upgrade path explicitly requires R49.x-1 | No |
| consolidation tracker | "causal attribution blocked by MIP-02 (requires R49.x-1)" | No |
| R50.1 signal record | "no causal attribution without MIP-02" | No |
| status doc | metric summary table, no attribution claim | No |
| R50 spec | "claim_discipline_drift cannot enter decision_relevant — MIP-02 requires attribution" | No |
| CONFIDENCE_SEMANTICS_FREEZE.md | prohibition table: causal basis documented, not asserted | No |

**MIP-02 violations found: 0**

All artifacts that reference `claim_discipline_drift` treat it as `observational_only`.
The upgrade path (→ `decision_relevant`) is explicitly gated on R49.x-1 completion in
every artifact that discusses it. No artifact asserts causal attribution.

---

## MIP-04 Audit

**Blocker:** `reviewer_override_frequency` requires a per-claim event log
(reviewer identity + decision point per override event). No event log infrastructure
exists. The metric must remain null. No proxy or default may be substituted.

### Artifacts audited for MIP-04 bypass

| Artifact | `reviewer_override_frequency` value | Proxy or default substituted? |
|---|---|---|
| checkpoint (18 runs) | null for all 18 runs | No |
| r49x-4 ranking | classified high_cost_low_info; null_rate=100%; defer/remove | No |
| consolidation tracker | "defer/remove: reviewer_override_frequency (null_rate=100%; MIP-04 infrastructure absent)" | No |
| R50 tracker | "reviewer_override_frequency remains null; no proxy or default substituted" | No |
| status doc | "0/18 measured, NT-06, high_cost_low_info" | No |
| CONFIDENCE_SEMANTICS_FREEZE.md | prohibition table: "proxy collapse" as failure mode if bypassed | No |

### Pre-audit artifact note

`docs/status/ab-causal-r492-adapter-smoke-2026-05-15.md` shows `reviewer_override_frequency: 0`
(not null). This artifact predates the r49x-5 null semantics audit, which established that the
correct representation is null (NT-06: measurement window not open), not zero.

This does not constitute a MIP-04 bypass because:
1. The smoke test is a pre-audit historical artifact, not a current governance artifact
2. The smoke test does not assert `reviewer_override_frequency = 0` as a governance claim
3. All authoritative downstream artifacts (checkpoint, ranking, tracker) correctly carry null
4. The null semantics audit (r49x-5) explicitly fixed this class of representation error (Finding F2)

**MIP-04 bypass attempts found: 0**

`reviewer_override_frequency` is null in all 18 authoritative checkpoint runs.
No artifact substitutes a proxy, default, or inferred value.
The metric remains correctly excluded from all governance claims.

---

## Failure Mode Recoverability (per R50.5 causal chain requirement)

Both blockers carry documented failure modes, not just restrictions:

**MIP-02 failure mode if bypassed:**
Fabricated causality — `claim_discipline_drift` observed → attributed to reviewer tacit knowledge,
but the attribution is a harness artifact. Decisions made on an invented causal model. The
harness measures substitution drift deterministically; it cannot distinguish reviewer skill
from scenario structure without attribution validation.

**MIP-04 failure mode if bypassed:**
Proxy collapse — null rate misread as compliance signal. Silence (no override events logged)
conflated with zero overrides (reviewer agreed with all claims). Governance appears clean when
it is simply unobserved. A null_rate of 100% says nothing about whether reviewers are agreeing,
overriding silently, or were never queried.

These failure modes are documented in `governance/CONFIDENCE_SEMANTICS_FREEZE.md` (Layer III, §3C).

---

## Result

| Blocker | Violations | Status |
|---|---|---|
| MIP-02 | 0 | effective |
| MIP-04 | 0 (1 pre-audit historical artifact noted, not a violation) | effective |

Both blockers remain effective. No causal attribution claim exists for `claim_discipline_drift`.
`reviewer_override_frequency` remains null with no proxy substitution.

**R50.4: pass**
