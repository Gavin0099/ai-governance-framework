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

**Forced Ownership Routing (required, not advisory):**

Expiry alone is not governance. Every `author_provisional` record must carry a
forced routing path so debt cannot silently age in place.

Required fields in escalation record:
- `forced_owner`: role accountable for driving Tier 1 closure
- `forced_escalation_target`: next reviewer authority path (team/role)
- `forced_route_due_date`: explicit date for ownership handoff completion
- `forced_route_status`: `assigned | in_progress | overdue | completed`

Routing consequence rules:
1. On provisional expiry, `forced_route_status` must transition to at least
   `assigned` on the same update that reverts state to `pending_human_validation`.
2. If `forced_route_status=overdue`, any release artifact that cites this
   escalation as resolved is invalid and must be blocked.
3. If routing fields are absent, escalation state is treated as
   `governance_incomplete` regardless of remediation implementation status.

This turns expiry from delayed ignoring into enforceable accountability.

**Authority Writer Monopoly (trust-root requirement):**

`authority` artifacts are valid only when produced by the canonical writer path:
`governance_tools/escalation_authority_writer.py`.

Implications:
- schema-valid JSON is not sufficient for authority legitimacy
- artifacts emitted by other tools/scripts are untrusted by default
- release consumers must fail closed on untrusted provenance
  (`release_blocked` with `untrusted_escalation_provenance`)

This enforces: `only authority path may produce authority artifact`.

**Coverage Claim Consequence Mapping (hard-stop surfaces):**

Claim invalidation must map to concrete consequences. For protected claims
(`stable trend`, `readiness progression`, `promotion confidence`,
`lifecycle comparison`):

- missing `coverage_era` reference => claim is invalid
- `coverage_era != CURRENT` without explicit caveat
  `not_supported_under_current_coverage` => claim is invalid

Invalid protected claims must hard-stop at:
1. promotion proposal artifacts
2. release gate summaries citing readiness/resolution
3. governance report signoff for Phase B/E2 completion

Reviewer discretion cannot downgrade these hard-stops to warnings.

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

## Trust Root Debt (explicitly open)

Current status is:
- validator authority semantics are defined
- provenance enforcement at runtime is still missing

This is a **trust root debt**, not a minor follow-up and not a closed item.
Until runtime writes validator provenance with enforcement semantics, closure
authority remains partially trust-based rather than fully auditable.

### Log Production Gap (known, not fixed)

`assess_authority_directory()` determines whether authority artifacts are
**required** by checking `phase-b-escalation-log.jsonl`. If the log is absent
or empty, the system returns `no_escalation_expected → ok=True`, treating it
as a clean no-escalation state.

**The gap**: the log is the sole trigger for `authority_required=True`. If the
log is never written or is deleted, the system silently degrades to
`no_escalation_expected → ok=True` even when active escalation cases exist.
This is equivalent to an authority bypass through the production path.

**Mitigation path** (not yet implemented):
1. Cross-verify escalation log presence against `e1b-phase-b-escalation-decisions.md`
   — if the decisions doc records active cases but no log exists, treat as
   governance gap, not clean state.
2. Or enforce append-only / write-once semantics on the log at the writer level,
   preventing silent deletion.

**Why this matters before Gap 2**: Gap 2 routes authority assessment through
`phase2_aggregation_consumer.build_phase2_gate()`, making the promotion gate
fail-closed when `authority_ok=False`. But if the log production gap allows
`authority_ok=True` when it should be `False`, the fail-closed guarantee is
conditional on log integrity — which is not yet enforced. Claiming "promotion
path is fail-closed" without fixing this gap is a false completion claim.

## E2 Deferral Governance Boundary

Deferral is allowed; silent suspension is not.
Once constitutional evidence is sufficient to start legitimacy review, the
system must not continue as if E2 were still purely observational.

Minimum contract:
1. `constitutional_evidence_trigger` must be explicit and replayable from evidence refs.
2. `legitimacy_review_started` must be emitted after trigger reach (no indefinite limbo).
3. If trigger is reached but review is not started, status is **process violation**.
4. Process violation must map to hard consequences (not warnings):
   - release readiness claim blocked
   - OP-HC legitimacy/promotion claim blocked
   - governance completion signoff blocked

## Trigger Detection Authority (anti-veto)

To prevent creator-veto-by-silence, trigger recognition requires an auditable
detection path, not personal acknowledgment.

Required detection record fields:
- `declared_by`
- `detection_inputs`
- `decision_time`
- `evidence_refs`

If evidence shows trigger conditions met but no detection record exists, that is
itself a governance process violation and must be treated fail-closed by
consumers.

## Practical Accessibility Boundary (anti-priesthood)

`expensive != expert-only` is necessary but insufficient. A system can be
formally open yet practically closed.

Legitimacy claims must include a practical accessibility audit at least covering:
- language clarity for non-creator reviewers
- artifact readability for decision lineage
- precedent replay cost without insider context
- social confidence cost for raising challenges

If the audit indicates technically open but practically closed participation,
authority-distribution claims are invalid until corrected.

---

> **Layer**: [OP] Operational Policy — subject to revision as independent reviewer
> availability changes and as E2 evidence accumulates.
> This contract does not define the *content* of validation; it defines the *authority*
> that makes validation legitimate.
