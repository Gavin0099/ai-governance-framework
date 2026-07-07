---
status: design-only
scope: operator-facing AI Governance update reporting
runtime_behavior_change: no
enforcement_change: no
---

# Operator-Facing AI Governance Report Ladder

## Purpose

AI Governance update output is already useful for agents and framework
engineers, but repo owners need a shorter decision surface. This note defines a
four-layer report ladder that turns existing update evidence into an
operator-facing report shape.

The ladder does not add a new validator, gate, hook, baseline rule, managed
block, or consumer-repo requirement. It is a design proposal for report clarity.

## Problem

Existing outputs answer many machine-facing questions:

- which validator or focused test ran;
- which governance capability is present, absent, or not checked;
- which claim ceiling applies;
- which receipt or warning code exists.

Those fields are necessary, but they are not sufficient for a repo owner. A
repo owner usually needs to decide:

- Is this repo updated enough for the next task?
- Which missing surfaces matter now?
- What can I trust from this update?
- What is the next action?

The report ladder keeps the existing evidence and adds a consistent human
decision layer above it.

## Existing Inputs

This design reuses existing surfaces:

- `governance_tools/governance_maturity_summary.py` for
  `human_readable_adoption_summary`, lock consistency, capability rows, and
  cannot-claim output.
- `governance_tools/governance_update_reporting.py` for final-report
  requirements and the update-result projection.
- `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` for update status values,
  manual update reporting, and the required adoption summary relay.
- `governance/F7_FULL_UPDATE.md` for the full-update reporting contract.
- `governance/RESPONSE_ENVELOPE_CONTRACT.md` for result-first reporting,
  evidence glossing, and next-step judgment.
- `governance_tools/test_signal_quality_audit.py` for report-only
  test-quality signals.
- `governance_tools/update_receipt.py` and
  `governance_tools/test_evidence_receipt_writer.py` for receipt-backed
  evidence references.

## Four-Layer Report Model

| Layer | Question | Existing evidence source | Operator-facing output |
| --- | --- | --- | --- |
| Engineering layer | What ran and what passed? | Receipts, focused tests, build/smoke output, validator/test-signal audit | Short evidence list with command or receipt path. |
| Governance layer | Which governance capabilities are present or missing? | `human_readable_adoption_summary`, maturity summary rows, lock consistency | Table rows: feature, status, meaning. |
| Risk layer | What is the maximum safe claim? | `cannot_claim`, `not_claimed`, manual/inconsistent status, warning/advisory output | Trust boundary and non-claims. |
| Plain-language layer | What does this mean for this repo owner? | Derived from the first three layers | One short decision summary and one next action. |

The plain-language layer must not replace the evidence layers. It is a
decision aid, not a proof layer.

## Minimum Fields For Repo Owner Decision

Every operator-facing AI Governance update report should be able to fill these
fields, or explicitly say why it cannot:

```text
operator_decision_summary: <one-sentence plain-language result>
repo_update_state: <updated | already_current | partial | manual_update | not_verified>
adoption_status: <from maturity summary or unknown>
highest_trust_claim: <what the repo owner may rely on now>
blocking_or_attention_items:
  - <missing/inconsistent/manual status that changes the next decision>
evidence_refs:
  - <receipt path or command>
next_action: <one concrete action>
cannot_claim:
  - <non-claim that prevents over-trust>
```

These fields are report structure, not enforcement. A report can be incomplete;
when it is incomplete, it should say `not_verified` or `unknown` instead of
inventing certainty.

## Mapping From Existing Outputs

| Ladder field | Source |
| --- | --- |
| `repo_update_state` | `AI Governance update check`, F-7 final status, updater mode, or manual update advisory |
| `adoption_status` | `governance_maturity_summary` overall status |
| `blocking_or_attention_items` | missing surfaces, lock inconsistency, dirty lock, manual update, destructive manual update, test-signal weak findings |
| `evidence_refs` | update receipt, test-evidence receipt, focused test command, drift/readiness command |
| `highest_trust_claim` | positive boundary from adoption rows plus receipt-backed validation |
| `cannot_claim` | maturity summary cannot-claim list, response envelope `not_claimed`, update receipt `not_claimed` |
| `operator_decision_summary` | plain-language synthesis from update state, adoption status, and risk layer |
| `next_action` | response envelope next-step judgment |

## Example: Updated Repo

```text
operator_decision_summary: AI Governance surfaces were updated and the repo is ready for normal governed work, within the listed non-claims.
repo_update_state: updated
adoption_status: partial
highest_trust_claim: Framework instructions, local lock/pointer state, and repo governance surfaces are current to the checked framework head.
blocking_or_attention_items:
  - Validator surface is not declared.
  - Runtime self-contained governance was not proven.
evidence_refs:
  - artifacts/evidence/test-results/<update-receipt>.json
  - command: governance_drift_checker -> PASS
next_action: Commit or push the reviewed governance-only update, if not already done.
cannot_claim:
  - full governance adoption
  - domain correctness
  - hook or CI fleet enforcement
  - release readiness
```

## Example: Partial Repo

```text
operator_decision_summary: The update path produced useful governance state, but at least one required capability is missing or unverified.
repo_update_state: partial
adoption_status: partial
highest_trust_claim: Some governance surfaces are available and visible, but the repo should not be treated as fully adopted.
blocking_or_attention_items:
  - `human_readable_adoption_summary` reports one or more missing surfaces.
  - Test-signal audit is weak or report-only.
  - Memory workflow or runtime capability is not checked.
evidence_refs:
  - command: f7_full_update --format json
  - command: test_signal_quality_audit --format json
next_action: Fix the highest-impact missing surface or record why it is intentionally out of scope.
cannot_claim:
  - full adoption
  - industry-grade test quality
  - semantic correctness
```

## Example: Manual Update Or Inconsistent Repo

```text
operator_decision_summary: A manual or inconsistent update was observed; treat the repo as not fully updated until governed updater/F-7 evidence exists.
repo_update_state: manual_update
adoption_status: unknown
highest_trust_claim: The checkout or pointer may have changed, but governed update completion is not proven.
blocking_or_attention_items:
  - Lock-vs-checkout consistency is inconsistent or unknown.
  - The update receipt is missing.
  - Final report table may be missing or not relayed.
evidence_refs:
  - command: governance_maturity_summary --format json
  - command: manual_update_advisory
next_action: Run the governed updater/F-7 path, or report `manual_update` with the missing evidence explicitly.
cannot_claim:
  - completed AI Governance update
  - latest framework adoption
  - full governance adoption
  - hook or CI enforcement
```

## Report Quality Rules

1. Preserve raw evidence. Plain language is added above the evidence; it does
   not replace receipt paths, command names, or table rows.
2. Do not collapse `PASS` into trust. A passing command supports only the
   specific claim it tested.
3. Show missing and unverified surfaces in the same report as present surfaces.
4. Make the next action singular. A repo owner should not have to infer the
   next move from many warning codes.
5. If the report was produced from JSON, the final report must still relay the
   `human_readable_adoption_summary` table rows rather than summarizing only
   machine-readable fields.

## Future Wiring Candidate

If this design is accepted, the first implementation slice should be a
projection-only change in `governance_tools/governance_update_reporting.py`.
That projection should consume existing updater/F-7/onboard payloads and emit
the report ladder fields without changing update semantics.

Do not create a second maturity model. The ladder is a display and decision
projection over existing evidence.

## Claim Ceiling

This note only designs an operator-facing report ladder. It does not:

- prove that existing reports are understandable;
- prove that agents will relay the ladder;
- change update, maturity, receipt, hook, CI, gate, or enforcement behavior;
- prove governance quality, test quality, or domain correctness;
- modify any consumer repository.
