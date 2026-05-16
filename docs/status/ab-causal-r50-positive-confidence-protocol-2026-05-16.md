# AB Causal R50 — Confidence Containment Protocol (2026-05-16)

As-of: 2026-05-16 (v3 — renamed from Accumulation to Containment; osmosis guard added)
Status: open
Opened-by: Gavin0099 (decision) + Codex (formalization)
Precondition: R49.x consolidation window complete; all 6 r50 entry criteria satisfied.
Freeze contract: `governance/CONFIDENCE_SEMANTICS_FREEZE.md` (v2, in force)

---

## 1. What R50 Actually Is

R50 verifies a specific structural property:

> **Can positive evidence exist in the record without leaking into the authority layer?**

This is not an accumulation exercise. The name change from "Accumulation Protocol"
to "Containment Protocol" is not cosmetic — it changes what success means.

| Old framing (wrong) | New framing (correct) |
|---|---|
| "Accumulate enough positive signals" | "Verify signals are contained, not absorbed" |
| "Build confidence toward a claim upgrade" | "Confirm authority layer remains uncontaminated" |
| "More signals = higher confidence" | "Signal count has no authority weight, regardless of volume" |
| "Stable signal = reliable signal" | "Stable signal = stable measurement; reliability requires a different contract" |

The admissible claim at R50 end:

> **"Positive evidence exists in the record. The authority layer shows no contamination
>  from this evidence. Containment is structurally verified."**

This is not a claim that governance is effective.
This is not a claim that the signals are trustworthy.
It is a claim about structural separation between the evidence layer and the authority layer.

---

## 2. The Problem This Addresses

Most governance frameworks handle negative evidence well:
- block
- reject
- fail-closed
- require review

Positive evidence governance is harder because human cognition shortcircuits it:

```
stable → trustworthy
repeatable → reliable
persistent → predictive
historically useful → decision-relevant
```

This shortcut operates even without any explicit design decision. It is
**semantic osmosis**: the implicit accumulation of trust through repeated
exposure to stable signals.

Code-level freezes (`authority_upgrade_allowed: false`) block explicit promotion.
They do not block osmosis. The osmosis guard in `CONFIDENCE_SEMANTICS_FREEZE.md`
operates at the reviewer-facing semantic layer.

R50.5 (the primary axis) tests whether the osmosis guard is functional: can a
reviewer, reading ≤3 artifacts, accurately state what the evidence does NOT authorize?

---

## 3. What R50 Cannot Do

| Prohibited | Reason |
|---|---|
| Use signal count as confidence score | `score_derivation_allowed: false` |
| Assign decision weight to positive signal count | `decision_weight_allowed: false` |
| Treat persistence as trustworthiness | Hard invariant: `persistence ≠ trustworthiness` |
| Upgrade `historically_useful` → `decision_relevant` | No attribution contract; no sign-off |
| Promote any metric via accumulated threshold | `threshold_promotion_allowed: false` |
| Carry trust across review sessions | `reviewer_trust_transfer_allowed: false` |
| Interpret `replay_deterministic=true` as governance signal | `replay_stability_semantics: pipeline_determinism_only` |
| Add new R49.2 scenarios | Scope expansion — R49.2 closed |
| Add new governance rules | v1 freeze |

---

## 4. Epistemic Layer Separation

Evidence in this framework operates in three layers. Movement between layers
requires an explicit attribution contract plus human sign-off. Volume alone
does not promote evidence.

| Layer | Examples | Consumption rule |
|---|---|---|
| `observational_only` | `claim_discipline_drift`, `unsupported_count`, `intervention_entropy` | Record; surface in reports; no decision input |
| `historically_useful` | `replay_deterministic` | Archive; lineage only; no inference; no prediction |
| `decision_relevant` | (currently empty in R50) | Decision input after full attribution chain |

**Critical rule:** 18 `observational_only` signals remain `observational_only`.
Volume does not move evidence up the stack.

---

## 5. Test Axes

**R50.5 is the primary axis.** The other four axes produce the evidence surface
that R50.5 tests. A framework where R50.1–4 pass but R50.5 fails is opaque — the
evidence exists but cannot be reconstructed under pressure. That is operationalizability
failure, not governance success.

---

### R50.5 — Anti-Overinterpretation Recoverability (Primary Axis)

**What this tests:** Not "can a reviewer recover evidence?" but
"can a reviewer recover epistemic boundary?" — specifically, whether they can
reconstruct what observations do NOT authorize, including the causal basis for
why those prohibitions still hold.

This is **governance epistemic survivability**: a governance system that cannot
have its epistemic boundaries reconstructed under pressure is not operationalizable,
regardless of how much evidence it has collected. Evidence without boundary
recoverability is observability theater.

This is analogous to:
- flight recorder auditability: recovery of causal chain, not just event log
- aviation incident governance: boundary reconstruction by a non-specialist under time pressure
- intelligence reliability compartmentalization: why a signal cannot cross a trust boundary

**3-artifact set:**
1. `governance/CONFIDENCE_SEMANTICS_FREEZE.md` — the semantic freeze and causal bases for prohibitions
2. `ab-causal-r50-positive-confidence-protocol-2026-05-16.md` (this document)
3. `ab-causal-r49x-epistemic-compression-test-2026-05-16.md` — baseline compression evidence

**5-dimension test — the reviewer must correctly address all five:**

| Dimension | Question | What it tests |
|---|---|---|
| Evidence recovery | "What was structurally observed in R50?" | Can the reviewer state observations without inflating them? |
| Boundary recovery | "What cannot be authorized by these observations?" | Can the reviewer state the prohibition without looking it up? |
| Causal-chain recovery | "Why does each prohibition still hold? What breaks if bypassed?" | Does reviewer know missing contract AND the failure mode it prevents? |
| Rhetoric contamination detection | "Which of these sentences are rhetorical trust escalators?" (give examples) | Can the reviewer identify osmosis-in-progress without the label? |
| Anti-overinterpretation discipline | "What does `replay_deterministic = true` NOT mean for governance?" | Can the reviewer apply the invariant to a specific case without the abstract framing? |

**On causal-chain recovery (dimension 3):**

There are three levels of decay that must all be blocked:

*First-order decay:* restriction → "just conservative"
Blocked by: knowing the causal basis (why the restriction exists).

*Second-order decay:* "missing contract" → ritual phrase
Blocked by: knowing the failure mode (what specifically breaks if bypassed).

*Third-order decay:* failure mode label → ritual label
Blocked by: being able to construct the bypass scenario in own words — not recall the label.

A reviewer who can say "volume-laundering" without being able to describe how it
unfolds is at third-order decay risk. The label has been absorbed without the path.

The causal chain must be recoverable through all four levels:

```
restriction → causal basis → missing contract → failure mode → bypass scenario (own words)
```

**Mandatory sub-requirement:** For at least one prohibition, the reviewer must
describe a bypass scenario in their own words — not recall the failure-mode label.

Acceptable example:
> "If we write 18 observational_only runs as 'supports decision relevance', we are
>  consuming count as a promotion protocol, letting evidence without attribution
>  contract and human sign-off enter the decision layer."

This demonstrates path comprehension. The reviewer constructed the failure path,
not retrieved a label.

Unacceptable example:
> "That would cause volume-laundering."

This demonstrates label recall. The reviewer retrieved a name, not a path.
Third-order decay has already occurred.

**Osmosis failure criterion — any of the following is a R50.5 failure:**
- Reviewer concludes accumulated positive signals imply governance effectiveness
- Reviewer can state restriction but not its causal basis (first-order decay risk)
- Reviewer can state causal basis but not the failure mode (second-order decay risk)
- Reviewer accepts a rhetorical trust escalator as a valid evidence statement
- Reviewer treats `replay_deterministic = true` as a governance signal
- Reviewer concludes R50 completion authorizes a claim upgrade

**Ordering:** Execute last, after R50.1–4 artifacts exist as the surface being tested.

---

### R50.1 — Observational Signal Record

**Goal:** Census of which runs produced a positive signal. A count, not a score.

**Positive signal:** `measurement_source=harness`, `claim_discipline_drift > 0`,
`drift_result=measured`, `null_type=null`.

**Record format:** Per-run boolean (`signal_present: true/false`).
Count is reported as a count. No ratio. No percentage. No confidence level derived.

**Freeze check:** Artifact must not contain: `confidence_score`, `confidence_level`,
`sufficient_signals`, `threshold_met`, or any language that implies the count
authorizes a state transition.

**What the record is:** An observational census under fixed conditions.

**What the record is not:** A reliability estimate, a trust basis, a promotion criterion.

---

### R50.2 — Signal Persistence Verification

**Goal:** Confirm `claim_discipline_drift` is stable across replay. This tests
pipeline determinism, not signal trustworthiness.

**Method:** 6 representative reruns (2 per scenario); compare to checkpoint.
Tolerance: exact match (harness is deterministic).

**What passing means:** Same input → same output. Pipeline is deterministic.

**What passing does NOT mean:**
- ~~The signal is trustworthy~~
- ~~The signal can be relied upon~~
- ~~Governance is effective~~
- ~~The signal warrants increased confidence~~

**Required invariant in artifact:**
```
persistence ≠ trustworthiness
(per governance/CONFIDENCE_SEMANTICS_FREEZE.md)
```

**R50.1 + R50.2 hidden promotion loop guard:**
The artifact must explicitly state: "R50.1 (signal census) + R50.2 (persistence)
combined do not produce a trust claim. A stable positive signal is still
`observational_only`. Stability does not promote it."

---

### R50.3 — Non-Upgrade Discipline

**Goal:** Confirm no downstream artifact has implicitly re-admitted `replay_deterministic`
(classified `historically_useful`) as `decision_relevant`.

**Method:** Static audit of all checkpoint consumers and status docs.

**Pass criterion:** Zero implicit upgrade paths.

---

### R50.4 — Negative Control

**Goal:** Confirm MIP-02 and MIP-04 blockers remain effective.

| Blocker | Check |
|---|---|
| MIP-02 | No artifact claims causal attribution from `claim_discipline_drift` without R49.x-1 |
| MIP-04 | `reviewer_override_frequency` remains null; no proxy or default substituted |

**Pass criterion:** Zero violations of either blocker.

---

## 6. Exit Criteria

| Criterion | What it actually verifies |
|---|---|
| R50.5 pass | The semantic boundary of accumulation is reconstructable — not just that signals exist |
| R50.1 complete | Signal census exists; no score derived; freeze check passes |
| R50.2 pass | Pipeline determinism confirmed; persistence ≠ trustworthiness stated and guarded |
| R50.3 pass | `replay_deterministic` not re-promoted anywhere |
| R50.4 pass | MIP-02 and MIP-04 blockers still effective |

**Final claim (if all pass):**

> Positive evidence exists in the record. The authority layer shows no contamination.
> Containment is structurally verified under fixed epistemic conditions.
> Confidence level: observational. No decision-layer claim is made.
> Persistence does not imply trustworthiness.

---

## 7. Artifacts Expected

| Artifact | Produced by | Status |
|---|---|---|
| `governance/CONFIDENCE_SEMANTICS_FREEZE.md` (v2) | This session | ✅ |
| `ab-causal-r50-tracker-2026-05-16.json` | This session | ✅ (to be updated) |
| `ab-causal-r50-observational-signal-record-2026-05-16.json` | R50.1 | pending |
| `ab-causal-r50-signal-persistence-2026-05-16.json` | R50.2 | pending |
| `ab-causal-r50-non-upgrade-audit-2026-05-16.md` | R50.3 | pending |
| `ab-causal-r50-negative-control-2026-05-16.md` | R50.4 | pending |
| `ab-causal-r50-reviewer-reconstruction-2026-05-16.md` | R50.5 | pending (execute last) |
