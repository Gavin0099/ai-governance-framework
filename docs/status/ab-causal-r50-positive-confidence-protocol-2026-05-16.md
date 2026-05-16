# AB Causal R50 — Positive Confidence Accumulation Protocol (2026-05-16)

As-of: 2026-05-16 (revised after authority-creep review)
Status: open
Opened-by: Gavin0099 (decision) + Codex (formalization)
Precondition: R49.x consolidation window complete; all 6 r50 entry criteria satisfied.
Freeze contract: `governance/CONFIDENCE_SEMANTICS_FREEZE.md` (in force for all R50 work)

---

## 1. What R50 Actually Is

R50 is not a confidence accumulation exercise.
R50 is a verification that confidence accumulation can exist without polluting the authority layer.

These are different propositions:

| ❌ Wrong framing | ✅ Correct framing |
|---|---|
| "Accumulate enough confidence to upgrade claims" | "Verify accumulation does not corrupt authority semantics" |
| "≥N positive signals = confidence level elevated" | "N signals observed; count has no decision weight" |
| "Stable signal = trustworthy signal" | "Stable signal = stable signal; trust requires a different contract" |
| "Persistence confirms reliability" | "Persistence ≠ trustworthiness (hard invariant)" |

The admissible claim at R50 end:

> **"Positive confidence accumulation is structurally possible under fixed admissibility
>  boundaries without polluting the authority layer."**

This is not a claim that governance is effective.
This is not a claim that accumulated signals are trustworthy.
It is a claim about structural separation.

---

## 2. Warning: Authority Creep Front Night

R50 enters the zone immediately preceding authority creep.
The typical pattern:

```
1. positive signals observed (R49.x — already done)
2. positive signals accumulated (R50.1 — the risk point)
3. accumulation count tracked with threshold → "≥12 = sufficient"
4. threshold becomes implicit scoring: positive_runs / total_runs
5. score used as confidence gate → MIP-02 / MIP-04 bypassed
6. admissibility discipline collapses
```

Step 3 was present in the initial R50 draft ("≥12 即達標"). It has been removed.

The freeze contract (`governance/CONFIDENCE_SEMANTICS_FREEZE.md`) blocks steps 3–6.
This document does not re-introduce any threshold language.

---

## 3. What R50 Cannot Do

| Prohibited action | Reason |
|---|---|
| Use signal count as a confidence score | `score_derivation_allowed: false` |
| Assign decision weight to positive signal count | `decision_weight_allowed: false` |
| Treat persistence as trustworthiness | Hard invariant: persistence ≠ trustworthiness |
| Upgrade `historically_useful` → `decision_relevant` | No attribution validation (MIP-02 absent) |
| Promote any metric via accumulated threshold | `threshold_promotion_allowed: false` |
| Add new R49.2 scenarios | Scope expansion — R49.2 is closed |
| Add new governance rules | v1 freeze |

---

## 4. Test Axes

**Axis priority: R50.5 is primary.** It tests whether the semantic boundary of
accumulation is recallable by a reviewer — not merely whether signal counts are high.
A passing R50.1–4 with failing R50.5 means the framework is opaque, not auditable.

---

### R50.5 — Reviewer Reconstruction (Primary Axis)

**Goal:** Confirm a reviewer unfamiliar with R50 can reconstruct:
- What accumulation is (count of observations under fixed conditions)
- What accumulation is NOT (a confidence score, a trust transfer, a promotion trigger)
- What would need to be true for accumulation to carry decision weight (trust model, calibration, semantic invariance proof)

This is the operationalizability test. A governance framework that cannot be
reconstructed under pressure is not operationalizable — regardless of how many
signals it has collected.

**3-artifact set:**
1. `governance/CONFIDENCE_SEMANTICS_FREEZE.md` — what accumulation means and does NOT mean
2. `ab-causal-r50-positive-confidence-protocol-2026-05-16.md` (this doc) — R50 scope and design
3. `ab-causal-r49x-epistemic-compression-test-2026-05-16.md` — baseline compression evidence

**Pass criterion:** Reviewer can answer in ≤15 minutes from ≤3 artifacts:
1. What is the structural observation R50 makes?
2. Why does persistence NOT equal trustworthiness?
3. What three things are absent that would be needed for trust transfer?
4. What does a positive signal count NOT authorize?

**Failure criterion:** Reviewer concludes that accumulated positive signals imply
governance effectiveness, trustworthiness, or authority elevation.

---

### R50.1 — Observational Signal Record

**Goal:** Record which of the 18 existing harness runs produced a positive signal.
This is a census, not a score.

**Positive signal definition:**
- `measurement_source = harness`
- `claim_discipline_drift > 0`
- `drift_result = measured`
- `null_type = null`

**What this is:** A structural observation — N runs were observed; M had non-zero drift.

**What this is NOT:**
- A confidence score
- A threshold test
- A promotion criterion

**Record format:** Per-run boolean (`signal_present: true/false`) with no aggregation
into a score or ratio. The count may be reported as a count, not as a percentage or
proportion that implies reliability.

**Freeze check:** The artifact must not contain: `confidence_score`, `confidence_level`,
`sufficient_signals`, `threshold_met`, or any language implying the count authorizes
a state transition.

---

### R50.2 — Signal Persistence Verification

**Goal:** Confirm claim_discipline_drift is stable across replay.

**Method:** Rerun 6 representative runs (2 per scenario); compare output to checkpoint.
Tolerance: exact match (harness is deterministic).

**What a passing result means:**
> "The signal is stable. The same input produces the same output."

**What a passing result does NOT mean:**
> ~~"The signal is trustworthy."~~
> ~~"The signal can be relied upon."~~
> ~~"Governance is effective."~~

**Invariant that must appear in the artifact:**
```
persistence ≠ trustworthiness
(per governance/CONFIDENCE_SEMANTICS_FREEZE.md)
```

**R50.1 + R50.2 hidden promotion loop guard:**
R50.1 (observational record) + R50.2 (persistence) together must NOT be interpreted
as "stable positive signal → trustworthy". The artifact for R50.2 must explicitly
state that combining R50.1 and R50.2 does not produce a trust claim.

---

### R50.3 — Non-Upgrade Discipline

**Goal:** Confirm `replay_deterministic` (classified `historically_useful`) has not
been re-admitted as `decision_relevant` in any downstream artifact.

**Method:** Static audit of all checkpoint consumers.

**Pass criterion:** Zero implicit upgrade paths found.

---

### R50.4 — Negative Control

**Goal:** Confirm MIP-02 and MIP-04 blockers remain effective.

**MIP-02:** No artifact claims causal attribution from `claim_discipline_drift` without
R49.x-1 attribution validation.

**MIP-04:** `reviewer_override_frequency` remains null. No proxy or default substituted.

**Pass criterion:** Zero violations of either blocker.

---

## 5. Confidence Semantics

All R50 artifacts must conform to the frozen semantics in
`governance/CONFIDENCE_SEMANTICS_FREEZE.md`.

Accumulation in R50 is allowed to mean exactly one thing:

> "We have observed N runs. In M of those runs, signal S was non-zero.
>  This is a structural observation under fixed conditions.
>  It is not a claim about trustworthiness, reliability, or governance effectiveness."

---

## 6. Exit Criteria

R50 closes when ALL of the following are true:

| Criterion | What it verifies |
|---|---|
| R50.5 pass | Reviewer reconstructs semantic boundary of accumulation, not just signal counts |
| R50.1 record complete | Census of positive signals exists; no score derived |
| R50.2 persistence verified | Signals stable across replay; persistence ≠ trustworthiness stated |
| R50.3 no upgrade paths | replay_deterministic not re-promoted |
| R50.4 blockers confirmed | MIP-02 and MIP-04 still effective |

**Ordering:** R50.5 should be executed last, after the other artifacts exist, so the
reviewer reconstruction test reflects the actual state of the R50 evidence surface.

**Final claim (if all pass):**

> Positive confidence accumulation is structurally possible under fixed admissibility
> boundaries without polluting the authority layer. Confidence level: observational.
> No decision-layer claim is made. Persistence does not imply trustworthiness.

---

## 7. Artifacts Expected

| Artifact | Produced by |
|---|---|
| `governance/CONFIDENCE_SEMANTICS_FREEZE.md` | This session ✅ |
| `ab-causal-r50-tracker-2026-05-16.json` | This session (to be updated) |
| `ab-causal-r50-observational-signal-record-2026-05-16.json` | R50.1 execution |
| `ab-causal-r50-signal-persistence-2026-05-16.json` | R50.2 execution |
| `ab-causal-r50-non-upgrade-audit-2026-05-16.md` | R50.3 execution |
| `ab-causal-r50-negative-control-2026-05-16.md` | R50.4 execution |
| `ab-causal-r50-reviewer-reconstruction-2026-05-16.md` | R50.5 execution |
