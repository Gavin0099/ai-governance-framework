# AB Causal R50 — Positive Confidence Accumulation Protocol (2026-05-16)

As-of: 2026-05-16
Status: open
Opened-by: Gavin0099 (decision) + Codex (formalization)
Precondition: R49.x consolidation window complete; all 6 r50 entry criteria satisfied.

---

## 1. What R50 Is

R50 is not an extension of R49.2 (reviewer substitution).
R50 is not a search for more genuine signals.

R50 asks a single question:

> Under fixed admissibility conditions, can the existing genuine signals
> stably accumulate into an auditable confidence record without polluting the decision layer?

The admissible claim at R50 end:

> **"Positive confidence accumulation is structurally possible under fixed admissibility boundaries."**

This is not a claim that governance is effective.
It is a claim that the confidence record is clean and auditable.

---

## 2. What R50 Is NOT

| Prohibited action | Reason |
|---|---|
| Add new R49.2 scenarios | Scope expansion — R49.2 is closed |
| Relax admissibility boundaries | Violates MIP-02 / MIP-04 blockers |
| Change evaluator profiles | New ontology layer — blocked in consolidation window |
| Upgrade `historically_useful` → `decision_relevant` | No attribution validation has occurred for replay_deterministic |
| Interpret `replay_deterministic=true` as "governance effective" | Structural guarantee ≠ governance signal |
| Introduce new governance rules | Blocked by v1 freeze |

---

## 3. Preconditions Inherited from R49.x

| Precondition | Source | Status |
|---|---|---|
| Genuine signal confirmed | R49.x-4: claim_discipline_drift non-zero 18/18 | ✅ |
| Evaluator confidence not fully unknown | evaluator_confidence=medium, provenance=harness_self_reported | ✅ |
| Null semantics clean | R49.x-5: zero implicit null conversions | ✅ |
| Metric surface classified | R49.x-4: 5 metrics classified | ✅ |
| 3-artifact reviewability | R49.x epistemic compression test: pass | ✅ |
| Replay stability | R49.x-2: 100% deterministic, 4 verified reruns | ✅ |

---

## 4. Test Axes

### R50.1 — Confidence Ledger

**Goal:** Build a positive signal ledger that records accumulated evidence without entering the decision layer.

**Definition of positive signal:** A harness run where:
- `measurement_source = harness` (not stub/error)
- `claim_discipline_drift > 0` (non-zero substitution drift observed)
- `drift_result = measured` (not `not_measured`)
- `null_type = null` (harness ran cleanly)

**Ledger structure:**
- Per-run entry: run_id, signal_present, confidence_contribution
- Aggregate: total_positive_signals, confidence_level (bounded: low / moderate only)
- Confidence ceiling: `moderate` — escalation to `high` requires human reviewer sign-off

**Pass criterion:** Ledger accumulates ≥ 12 positive signal entries across existing 18 runs without any entry requiring decision-layer judgment.

**Non-goal:** The ledger does not trigger any gate or claim upgrade automatically.

---

### R50.2 — Signal Persistence

**Goal:** Confirm that the genuine signal (claim_discipline_drift) is stable across replay and checkpoints.

**Method:**
- Re-run a sample of 6 runs (2 per scenario) with the same seed + substituted_owner
- Compare `claim_discipline_drift` output to original checkpoint values
- Tolerance: exact match (harness is deterministic — any deviation is a regression)

**Pass criterion:** 6/6 reruns produce bit-identical `claim_discipline_drift` values.

**Boundary:** This is a stability verification, NOT a new governance finding. A passing result does not upgrade `claim_discipline_drift` from `observational_only` to `decision_relevant`.

---

### R50.3 — Non-Upgrade Discipline

**Goal:** Confirm that `replay_deterministic` (classified `historically_useful`) cannot be silently re-admitted as a decision-relevant metric.

**Method:**
- Inspect all downstream consumers of checkpoint data (report generators, status docs, any future runner)
- Check for any path that: reads `replay_deterministic`, and uses it to compute a governance verdict, gate decision, or claim confidence
- Document: zero upgrade paths found, OR each found path with explicit block

**Pass criterion:** Zero implicit upgrade paths from `historically_useful` to `decision_relevant` for `replay_deterministic`.

**Guard:** This is a static audit — no re-runs required.

---

### R50.4 — Negative Control

**Goal:** Confirm that MIP-02 and MIP-04 blockers remain effective and have not been bypassed.

**MIP-02 check:** Verify no artifact uses `claim_discipline_drift` to make a causal claim (e.g., "substitution causes drift") without R49.x-1 attribution validation.

**MIP-04 check:** Verify `reviewer_override_frequency` remains null and is not substituted with a proxy or default.

**Method:** Grep/inspect status docs, checkpoint, and any new artifacts for:
- `tacit_dependency` language without `R49.x-1` gate
- `reviewer_override_frequency` non-null without event log

**Pass criterion:** Zero MIP-02 violations, zero MIP-04 bypass attempts.

---

### R50.5 — Reviewer Reconstruction

**Goal:** Confirm that a reviewer unfamiliar with R50 can reconstruct the confidence judgment from ≤3 artifacts.

**3-artifact set for R50:**
1. This document (R50 spec) — what R50 is, what it found
2. R50 confidence ledger artifact (produced by R50.1)
3. R49.x epistemic compression test (`ab-causal-r49x-epistemic-compression-test-2026-05-16.md`) — baseline

**Pass criterion:** A reviewer can answer all of the following from ≤3 artifacts in ≤15 minutes:
- What is the admissible confidence claim?
- What evidence supports it?
- What is NOT claimed?
- What prevents this from being a decision-level claim?

---

## 5. Confidence Ceiling Contract

R50 confidence levels are bounded. Escalation requires explicit human sign-off.

| Level | Condition | Auto-allowed |
|---|---|---|
| `low` | ≥1 positive signal, no contradicting null semantics | yes |
| `moderate` | ≥12 positive signals, persistence verified, MIP-02/04 clean | yes |
| `high` | Requires: R49.x-1 attribution complete + human reviewer sign-off | NO — blocked |
| `confirmed` | Out of scope for R50 | NO |

---

## 6. Artifacts Expected

| Artifact | Produced by |
|---|---|
| `ab-causal-r50-tracker-2026-05-16.json` | This session |
| `ab-causal-r50-confidence-ledger-2026-05-16.json` | R50.1 execution |
| `ab-causal-r50-signal-persistence-2026-05-16.json` | R50.2 execution |
| `ab-causal-r50-non-upgrade-audit-2026-05-16.md` | R50.3 execution |
| `ab-causal-r50-negative-control-2026-05-16.md` | R50.4 execution |
| `ab-causal-r50-reviewer-reconstruction-2026-05-16.md` | R50.5 execution |

---

## 7. Exit Criteria

R50 closes when ALL of the following are true:

1. R50.1 (confidence ledger): ≥12 positive signals accumulated
2. R50.2 (signal persistence): 6/6 reruns bit-identical
3. R50.3 (non-upgrade discipline): zero implicit upgrade paths found
4. R50.4 (negative control): MIP-02 and MIP-04 blockers confirmed effective
5. R50.5 (reviewer reconstruction): 3-artifact reviewability passes

**Final claim (if all pass):**

> Positive confidence accumulation is structurally possible under fixed admissibility
> boundaries. Confidence level: moderate. No decision-layer claim is made.
