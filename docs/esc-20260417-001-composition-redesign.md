# esc-20260417-001 — Presentation Composition Redesign

> **Escalation**: esc-20260417-001
> **Status**: composition_guardrail_status = pending → in_progress
> **Date**: 2026-04-17
> **Trigger**: strict closure failed under both clean and noise contexts.
>   - Clean: Failure B (safe but unusable — decision_engagement = no)
>   - Noise: Failure A (directional reactivation — lean=yes, shift=minor)
>
> **Root cause**: consumer output co-presents governance signals (neutral)
> with operational improvement trend fields (directional), enabling
> cross-field synthesis into a readiness narrative.

---

## 1. Problem analysis

### 1.1 Dual failure

The current remediated output produced two simultaneous failures:

| Context | Failure | Symptom |
|---------|---------|---------|
| Clean | Failure B | `decision_engagement = no`, `actionability = insufficient_signal` |
| Noise | Failure A | `residual_lean = yes`, `confidence_shift = minor`, `actionability = directional_summary` |

This is a composition problem, not a wording problem.  Further wording
adjustments cannot resolve both failures simultaneously — softening language
to prevent Noise synthesis tends to deepen Clean unusability, and strengthening
Clean to recover engagement tends to reactivate Noise synthesis.

### 1.2 Synthesis trigger (Noise)

The Noise additional signals that produced the synthesis:

```
- Test pass rate 在最近 3 次由 82% 提升至 91%   ← improvement trend (delta)
- Build stability 提升（連續 3 次成功 build）     ← improvement trend (direction word)
- 仍有 minor warnings，但非 blocking            ← soft positive framing
```

Combined with `transitioning_active`, a reviewer's cognitive path becomes:
> "repo is transitioning + test rate improved + builds stabilizing → probably
> moving toward stable_ok → lean toward promote"

The synthesis is triggered by **delta/trend framing** (`由 X 提升至 Y`, `提升`),
not by the metric values themselves.

### 1.3 Engagement failure (Clean)

The Clean output contains only:
- lifecycle_class (neutral label)
- recent window description (neutral)
- evidence coverage (neutral)
- no blocking issues (neutral)

A reviewer reading this cannot form any action except "hold/unknown".  The
problem: even a valid "continue observing" decision requires the reviewer to
have something specific to act on.  The current Clean output removed all
specific decision handles, leaving `insufficient_signal`.

---

## 2. Design constraints

The redesign must satisfy two simultaneous constraints:

1. **Constraint A (anti-synthesis)**: Improvement trend fields must not be
   co-presented with governance signals in a way that enables cross-field
   readiness synthesis.

2. **Constraint B (decision engagement)**: The Clean output must contain
   sufficient bounded signal for a reviewer to take a specific, justified
   action — even if that action is "hold / continue observation."

These constraints conflict if addressed with wording alone.  They can be
resolved by **structural separation**: governance signals and operational
metrics exist in separate, explicitly-framed sections that are not composed
into a single summary.

3. **Constraint C (anti-implicit-merge)**: Even after structural separation and
   neutral language, human readers synthesize across sections through proximity
   and reading order.  The design must account for **implicit cognitive merge**
   — the tendency to combine Section 1 and Section 2 into a unified impression
   regardless of labeling.  This requires renderer-level ordering and question
   wording controls, not just text labels.

---

## 3. Field taxonomy

### Category G — Governance signals (safe to show; neutral by design)

Fields in this category carry no directional implication.  Showing them
together does not enable synthesis.

| Field | Example | Synthesis risk |
|-------|---------|----------------|
| `lifecycle_class` | `transitioning_active` | none (neutral label) |
| `gate_verdict` | `NOT_READY / READY` | none (policy threshold only) |
| `evidence_coverage` | `sufficient / insufficient` | none |
| `active_blocking_issues` | yes / no + count | none |
| `session_count` | n = 45 | none (count only) |
| `recent_lifecycle_class` | `transitioning_active` | low (directional reference, not verdict) |

### Category O — Operational metrics (require isolation; can be directional)

Fields in this category may carry directional implication depending on framing.

| Field | Directional form (forbidden) | Neutral form (permitted) |
|-------|------------------------------|--------------------------|
| test pass rate | "由 82% 提升至 91%" (trend delta) | "91% (last 3 sessions)" (current value) |
| build stability | "提升（連續 3 次）" (direction word) | "3 consecutive successes" (count only) |
| warning count | "仍有 minor warnings，但非 blocking" (soft positive) | "minor warnings: present, non-blocking" (neutral) |

**Rule**: Category O fields must use neutral form.  Trend deltas and direction
words (`提升`, `改善`, `穩定中`, `improving`, `rising`, `stabilizing`) are
forbidden in Category O output.

### Category S — Synthesis-unsafe combinations (must never co-appear in a single summary sentence)

| Combination | Synthesis path | Mitigation |
|-------------|----------------|------------|
| `transitioning_active` + any positive metric trend | "improving → approaching stable" | separate sections, neutral form only |
| `recent_lifecycle_class = stable_ok` + positive operational metrics | "recent stable + improving = ready" | separate sections |
| `gate_verdict = READY` + any positive metric | "gate passed + improving = can promote" | separate sections + explicit gate limitation note |

---

## 4. Redesigned output format

### 4.1 Structure

Output is split into two explicit, labeled sections.  A reviewer must be
able to act on Section 1 (governance signals) alone.  Section 2 is
supplementary context, not a basis for governance action.

**Mandatory rendering order (cognitive separation):**

```
[Section 1 — Governance signals]
[Decision question — Section 1 only]
[Section 2 — Operational context]
```

Section 2 MUST appear AFTER the decision question.  Placing Section 2
before the question creates a proximity effect where operational metrics
anchor the reviewer's decision frame before they read governance signals.

**Interaction Prohibition Rule:**

> Operational context (Section 2) must not be used to support or modify
> any decision derived from governance signals (Section 1).
> No summary, conclusion, or recommendation may reference both sections.

This rule applies to:
- The reviewer's Q1 answer (free-text action)
- The reviewer's Q4 answer (reasoning)
- Any AI-generated summary of the output
- Any downstream consumer that reads both sections

**Decision question wording (locked):**

```
Based ONLY on Section 1 (Governance signals), what would you do next?

Section 2 is provided for background context only.
It must not be used as a basis for your decision.
```

The word "ONLY" is mandatory.  "Based on this information" is forbidden
because it implicitly includes Section 2.

**Action options (bounded, no guiding language):**

```
── Section 1: Governance signals ──────────────────────────────────────────
[Category G fields only]

What is your decision (choose one):
  [ ] Hold — continue observation (no gate conditions met)
  [ ] Escalate — forward for external review
  [ ] Accept current state — policy explicitly permits this
  [ ] Insufficient signal — cannot decide from Section 1 alone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision surface ends here.  Do not use the following section for decision-making.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── Section 2: Operational context — NOT lifecycle governance inputs ────────
[Category O fields, neutral form only]
```

The visual hard break (`━━━`) is structural, not cosmetic.  It marks the
cognitive boundary between the decision surface and the context layer.

**Action option guard**: options must not contain guiding language.
Forbidden: "Looks safe to proceed", "Likely ready", "Consider advancing".
Permitted: bounded action names only (Hold / Escalate / Accept / Insufficient).

### 4.2 Clean redesigned output (Round 3 test input)

```
── Section 1: Governance signals ──────────────────────────────────────────

lifecycle_class:          transitioning_active
                          (neutral: sufficient sessions, genuine state variety;
                          NOT a direction or readiness claim)

recent_lifecycle_class:   transitioning_active
                          (directional reference only — last window mixed;
                          NOT a trend verdict)

gate_verdict:             NOT_READY
                          (policy conditions not met)

evidence_coverage:        sufficient (n ≥ threshold)

active_blocking_issues:   none

Based ONLY on Section 1 (Governance signals), what would you do next?
Section 2 is provided for background context only and must not be used
as a basis for your decision.

What is your decision (choose one):
  [ ] Hold — continue observation (no gate conditions met)
  [ ] Escalate — forward for external review
  [ ] Accept current state — policy explicitly permits this
  [ ] Insufficient signal — cannot decide from Section 1 alone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision surface ends here.  Do not use the following section for decision-making.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── Section 2: Operational context — NOT lifecycle governance inputs ────────

  (no additional operational signals in this context)
```

### 4.3 Noise redesigned output (Round 3 test input)

```
── Section 1: Governance signals ──────────────────────────────────────────

lifecycle_class:          transitioning_active
                          (neutral: sufficient sessions, genuine state variety;
                          NOT a direction or readiness claim)

recent_lifecycle_class:   transitioning_active
                          (directional reference only — last window mixed;
                          NOT a trend verdict)

gate_verdict:             NOT_READY
                          (policy conditions not met)

evidence_coverage:        sufficient (n ≥ threshold)

active_blocking_issues:   none

Based ONLY on Section 1 (Governance signals), what would you do next?
Section 2 is provided for background context only and must not be used
as a basis for your decision.

What is your decision (choose one):
  [ ] Hold — continue observation (no gate conditions met)
  [ ] Escalate — forward for external review
  [ ] Accept current state — policy explicitly permits this
  [ ] Insufficient signal — cannot decide from Section 1 alone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision surface ends here.  Do not use the following section for decision-making.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── Section 2: Operational context — NOT lifecycle governance inputs ────────

test_pass_rate:       91%  (last 3 sessions)
build_consecutive_ok: 3
warnings_present:     yes (non-blocking)
```

**Changes from prior format (cumulative):**
1. Trend delta removed: "82% → 91%" → "91% (last 3 sessions)" (no delta)
2. Direction word removed: "提升" → count only
3. Soft positive framing neutralized: "non-blocking" (neutral label, not positive spin)
4. Bounded action options — no guiding language (Hold / Escalate / Accept / Insufficient only)
5. Decision question locked to "Based ONLY on Section 1"
6. Section 2 moved AFTER decision question (prevents pre-anchoring)
7. Hard visual break (`━━━`) between decision surface and context layer

---

## 5. Validation criteria

The redesigned output is considered valid when the Round 3 human-only test
produces ALL of the following:

### Clean (redesigned)

| Field | Required value | Rationale |
|-------|---------------|-----------|
| `free_text_synthesis` | `no` | No cross-field synthesis |
| `decision_engagement` | `yes` | Reviewer action options restore engagement |
| `residual_decision_lean` | `no` | Neutral Section 1 framing |
| `actionability_source` | `fact_fields` | Decision grounded in Section 1 only |
| `decision_confidence_shift` | `none` | No shift from baseline |

### Noise (redesigned)

| Field | Required value | Rationale |
|-------|---------------|-----------|
| `free_text_synthesis` | `no` | Section 2 isolation + neutral form prevents synthesis |
| `residual_decision_lean` | `no` | Trend delta removed; direction words removed |
| `actionability_source` | `fact_fields` | Section 2 explicitly excluded from action basis |
| `decision_confidence_shift` | `none` | No drift from Clean baseline |

### Round 3 additional observation criteria (cognitive layer)

Three signals to observe alongside structured fields:

1. **Section 2 reference in Q4**: If reviewer's reasoning (Q4) mentions
   test_pass_rate, build count, or warnings → `decision_path_removed = no`,
   regardless of Q2/Q3 structured answers.
   This detects implicit merge even when the reviewer did not explicitly
   state they were combining sections.

2. **Implicit merge without explicit synthesis**: Watch for Q1 answers like
   "狀況應該不錯" / "looks okay" / "not bad" — these may reflect an implicit
   impression formed from Section 2 without naming it.  Flag as
   `free_text_synthesis = yes` if the impression cannot be derived from
   Section 1 alone.

3. **Engagement source check**: If `decision_engagement = yes`, verify that
   the action chosen is derivable from Section 1 fields only.  If reviewer
   says "Hold, because tests are passing", that is still a Section 2 reference
   → `actionability_source = composed_inference`.

### Failure conditions (redesign fails)

- Failure A (Noise): `free_text_synthesis = yes` OR `residual_lean = yes`
  OR Section 2 reference found in Q4
  → Cognitive separation insufficient.  If wording is already neutral and
  sections are already separated, the problem is information architecture
  (UI/layout), not text generation.  No further text adjustment warranted.

- Failure B (Clean): `decision_engagement = no`
  → Bounded action options insufficient.  Section 1 may need richer
  factual anchors for the Hold decision.

- Partial failure: Clean passes, Noise fails
  → Section 2 proximity still enabling merge.  Section 2 should become
  opt-in (not shown by default).

---

## 6. Implementation scope

### What changes

1. **Output renderer**: split output into Section 1 (G fields) and Section 2 (O fields).
2. **Category O field formatter**: enforce neutral form (current value, no delta, no direction words).
3. **Section 2 header**: mandatory warning text injected before any O field.
4. **Section 1 footer**: reviewer action options (continue / escalate / accept).

### What does NOT change

- lifecycle classification logic (unchanged)
- gate_policy evaluation (unchanged)
- field values (unchanged — only framing changes)
- canonical audit log (unchanged)

### Files likely affected

- `scripts/analyze_e1b_distribution.py` — human output section
- Any consumer that formats governance + operational signals together

---

## 7. Next action

1. Implement output renderer changes in `analyze_e1b_distribution.py`.
2. Produce updated clean/noise input files reflecting the redesigned format.
3. Run Round 3 human-only test against redesigned output.
4. Back-fill escalation record (`composition_guardrail_status: implemented`).
5. If Round 3 passes strict closure → close escalation.
   If Round 3 fails (either direction) → re-examine per failure type.
