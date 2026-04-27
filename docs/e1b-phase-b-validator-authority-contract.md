# E1b Phase B — Validator Authority Contract

> **Purpose**: Define who can sign off Phase B closure and what evidence counts as valid.
> **Why this exists**: The escalation record (`e1b-phase-b-escalation-decisions.md`) uses
> `pending_human_validation` without defining validator qualifications. Without this contract,
> closure attempts default to whoever is available — usually the framework author — producing
> self-certification. This document makes the authority model explicit.

---

## Core Principle

**Phase B closure must not be self-certifying.**

The framework author is the least appropriate primary validator for framework behavior claims,
because author cognition is the source of the design choices being tested. Author validation
can only be a secondary layer, never the sole authority.

This is the same reason a test suite does not prove code correctness when written by the same
person who wrote the code.

---

## Validator Qualification Tiers

### Tier 1 — Independent Human Reviewer (preferred)

Qualifies as primary closure authority.

**Requirements:**
- Has not authored the escape pattern definitions being tested (E1–E4)
- Has not authored the composition guardrail being validated
- Has read the audit checklist (`docs/e1b-consumer-audit-checklist.md`) independently,
  without walkthrough from the framework author
- Produces a written judgment with at least one self-challenge attempt
  ("What would I conclude if I were wrong?")

**Examples:** domain owners of adopting repos; external governance reviewers; project
collaborators who joined after Phase A completion.

### Tier 2 — Framework Author with Independence Protocol

Qualifies as provisional closure authority when no Tier 1 reviewer is available,
subject to explicit independence constraints.

**Required constraints:**
- At least 7 calendar days since the last engagement with the artifact being validated
- Validation is conducted using a re-read of source documents only (no recall from memory)
- Must explicitly document any prior familiarity that might bias the review
- Result is labeled `author_provisional` in the closure record, not `validated`
- A Tier 1 reviewer must retrospectively confirm within the next 3 Phase B observation cycles

**`author_provisional` closure semantics:**
- Engineering track: may proceed
- Governance track: remains `pending_independent_validation` (not closed)
- Downstream: `author_provisional` must be disclosed in any citation of closure status

### Tier 3 — AI-Assisted Review (not valid for closure)

**Explicitly excluded from closure authority**, regardless of sophistication.

Rationale: AI cognition does not model human decision-shift patterns. An AI reviewer
concluding "no decision-relevant misinterpretation" cannot substitute for a human
reviewer failing to be misled. The failure mode being tested is human cognition under
realistic context.

AI review (including adversarial simulation) may be used as:
- Pre-screening to identify obvious issues before human review
- Documentation of potential escape patterns for human reviewers to examine
- Round N validation structure (not as the deciding round)

---

## Evidence Validity Requirements

Valid Phase B closure evidence must meet **all three** of the following:

### E1 — Freshness

- Evidence was produced **after** the composition guardrail was implemented
- Evidence is not a reuse of pre-guardrail observations

### E2 — Realistic Context

- Evidence came from a realistic usage session, not a constructed test
- Observer role is honestly recorded (human / AI-assisted / adversarial_simulation)
- Context included noise or mixed signals (not a clean, idealized scenario only)

### E3 — Decision Impact Assessment

- Reviewer explicitly answered all three audit questions (Q1 / Q2 / Q3)
  per `docs/e1b-consumer-audit-checklist.md`
- `impact_scope` and `decision_confidence_shift` are recorded
- Reviewer documented at least one self-challenge attempt

---

## Closure Gate Rules

### Standard Closure (preferred)

All four Phase B conditions met (coverage / zero decision_relevant / human check / no concentration)
**and** at least one Tier 1 reviewer has signed off on the escalation under evaluation.

Record format in `e1b-phase-b-escalation-decisions.md`:
```
- mitigation_validation_state: validated
- validator_tier: tier1_independent
- validator_id: <role-description, not personal name>
- validation_date: YYYY-MM-DD
- validation_evidence_ref: <doc or session ref>
```

### Provisional Closure (fallback)

Tier 2 review has been completed under independence protocol.
Engineering track may proceed; governance track records `pending_independent_validation`.

Record format:
```
- mitigation_validation_state: author_provisional
- validator_tier: tier2_author_provisional
- independence_constraints_met: yes
- days_since_last_engagement: N
- provisional_expiry_date: YYYY-MM-DD  (28 calendar days from validation_date)
- retrospective_tier1_required_by: YYYY-MM-DD (within 3 observation cycles)
```

**Tier 2 Aging and Escalation Rules (anti-creep):**

Tier 2 is a safety valve, not a legitimate closure path. The following rules
prevent it from becoming the de facto standard:

1. **Expiration**: `author_provisional` expires after **28 calendar days**.
   After expiration, closure reverts to `pending_human_validation` unless
   Tier 1 confirmation has been received.

2. **Visible debt**: Every open `author_provisional` closure must appear in
   the escalation record header as an unresolved item. Consumers of the
   escalation log must see provisional debt, not clean closure status.

3. **No stacking**: A second `author_provisional` cannot extend the first.
   Expiry of one provisional requires Tier 1 or explicit waiver (see below),
   not a new provisional.

4. **Release gate**: Any release artifact citing this escalation as "resolved"
   must disclose `author_provisional` status. Citing provisional closure as
   clean closure is a governance integrity violation.

5. **Waiver path** (last resort): If Tier 1 remains unavailable after
   provisional expiry, the framework maintainer may record an explicit policy
   waiver with `waiver_reason` and `waiver_expiry`. Waived closures are
   explicitly not equivalent to validated closures and must be disclosed as such.
   Waivers must be reviewed at next governance checkpoint.

### Closure Blocked

If neither Tier 1 nor Tier 2 with independence protocol is available,
closure is blocked. Record remains `unverified_mitigation`.

**Blocked closure does NOT prevent:**
- Continued Phase B observation accumulation
- Engineering improvements to the guardrail
- Provisional use of the guardrail in production

**Blocked closure DOES prevent:**
- Citing this escalation as "resolved" in Phase B completion claims
- Using this escalation's status as evidence in E2/E3 arguments

---

## Current Escalation Status (esc-20260417-001)

| Field | Current State | Target |
|-------|--------------|--------|
| `mitigation_validation_state` | `pending_human_validation` | `validated` or `author_provisional` |
| validator tier required | Tier 1 preferred; Tier 2 acceptable under protocol | — |
| author self-validation | **Not permitted without independence protocol** | — |
| evidence required | Fresh (post-guardrail), realistic context, Q1/Q2/Q3 answered | — |

---

## Why This Contract Matters

Without explicit validator authority:
1. Closure defaults to whoever is available → self-certification
2. The closure record has no defensible legitimacy
3. Phase B completion claims inherit the same legitimacy problem
4. E2 ("survives outside creator") cannot be claimed if governance closure requires creator

This contract is the minimum necessary to prevent Phase B from being
a creator-bottlenecked governance theater.

---

> **Layer**: [OP] Operational Policy — subject to revision as independent reviewer
> availability changes and as E2 evidence accumulates.
> This contract does not define the *content* of validation; it defines the *authority*
> that makes validation legitimate.
