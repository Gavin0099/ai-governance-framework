# Confidence Semantics Freeze Contract

As-of: 2026-05-16
Scope: R50 and all downstream phases until explicitly superseded by human reviewer sign-off
Authority: Gavin0099 (decision); Codex (formalization)

---

## Purpose

This contract exists because R50 enters a regime where positive signals are being
accumulated. Without explicit semantic constraints, this accumulation naturally
evolves into a scoring / threshold / promotion mechanism — even without any
deliberate design decision to do so.

The creep pattern is:

```
positive_signals accumulate
→ count is tracked
→ threshold emerges ("≥12 is enough")
→ score is derived (positive_runs / total_runs)
→ score threshold gates reviewer trust
→ MIP-02 / MIP-04 blockers are bypassed via accumulated score
```

This contract blocks that path at the semantic level.

---

## Frozen Semantics

```json
{
  "confidence_accumulation_mode": "observational_only",
  "authority_upgrade_allowed": false,
  "decision_weight_allowed": false,
  "ranking_allowed": false,
  "threshold_promotion_allowed": false,
  "score_derivation_allowed": false,
  "implicit_trust_transfer_allowed": false
}
```

### Definitions

**`authority_upgrade_allowed: false`**
No accumulated positive signal count may increase the authority weight of any
metric, reviewer profile, or governance claim. Accumulation is a count,
not an authority.

**`decision_weight_allowed: false`**
No positive signal count may be used as input to a governance decision gate,
confidence gate, or claim promotion gate. The count is observable; it has no
decision weight.

**`ranking_allowed: false`**
No metric or reviewer profile may be ranked higher based on accumulated positive
signal count. Ranking requires a different attribution contract (MIP-02) that
is not yet satisfied.

**`threshold_promotion_allowed: false`**
No threshold (e.g., "≥12 positive signals") may trigger a state transition in
admissibility, authority, or claim level. A threshold is only valid as a
stopping condition for observation, not as a promotion criterion.

**`score_derivation_allowed: false`**
No confidence score may be derived from the ratio of positive signals to total
runs (e.g., `positive_runs / total_runs`). Such a score would imply a
calibrated reliability model that does not exist.

**`implicit_trust_transfer_allowed: false`**
Persistence does not equal trustworthiness. A signal that is stable across
replay is a stable signal — not a trusted signal. Trust transfer requires:
- A bounded reliability model (absent)
- Reviewer calibration evidence (absent)
- Semantic invariance proof (absent)

---

## The Invariant

```
persistence ≠ trustworthiness
```

This invariant is not a warning. It is a hard boundary.

Any artifact, report, or decision that treats a persistent signal as a trusted
signal — without the three elements above — is a semantic violation of this contract.

---

## What Accumulation IS Allowed To Mean

Accumulation in R50 is allowed to mean exactly one thing:

> "We have observed N runs. In M of those runs, signal S was non-zero.
>  This is a structural observation under fixed conditions.
>  It is not a claim about trustworthiness, reliability, or governance effectiveness."

No more. No less.

---

## R50.5 Primacy Rule

R50.5 (Reviewer Reconstruction) is the primary verification axis for this freeze.

If a reviewer, reading ≤3 artifacts, concludes that accumulated positive signals
imply trust, decision authority, or governance effectiveness — R50.5 **fails**.

The purpose of R50.5 is not to confirm that signal counts are recallable.
The purpose of R50.5 is to confirm that the **semantic boundary of accumulation**
is recallable: a reviewer must be able to state what accumulation does NOT mean,
not only what it does mean.

---

## Exit Condition

This contract remains in force until:
1. A bounded reliability model is authored, human-reviewed, and signed
2. Reviewer calibration evidence is collected across ≥2 independent reviewers
3. A semantic invariance proof connects persistence to a defined trust model

None of these conditions are in scope for R50. This contract does not expire
within R50.
