# Enforcement Promotion Policy

> Authority: governance operational evidence standard
> Purpose: prevent promotion of warn-only CI to blocking enforcement without observed interception
> Scope: `interception-ledger-check` job in `.github/workflows/governance.yml`

---

## Three Hard Rules

1. **CI attachment proves governance can execute on lifecycle boundary.**
   It does not prove governance is effective or should enforce.

2. **`--warn-only` remains until the first observed interception.**
   The ledger must contain at least one entry in `artifacts/governance/intercepted-events.ndjson`
   with `evidence_basis: observed` before `--warn-only` may be removed.

3. **No phase, ontology, or protocol work may be used as enforcement-promotion evidence.**
   Semantic expansion is not operational evidence.

---

## Explicit Non-Evidence

The following do NOT count toward enforcement promotion:

| Signal | Why it fails |
|--------|-------------|
| CI job ran successfully N times | Proves `governance_present`, not `governance_effective` |
| All tests passing | Proves `test_derived` coverage, not `observed` execution |
| Topology analysis (E1-B Phase 2) | Proves vulnerability surface, not interception |
| Retroactive analysis entries in ledger | `retroactive_analysis` basis explicitly excluded |
| Session count or uptime | Ambient activity, not governed interception |

`CI-present evidence cannot be counted as interception evidence.`

---

## Promotion Criteria (exact)

Removing `--warn-only` from the `interception-ledger-check` CI job requires:

- At least one entry in `artifacts/governance/intercepted-events.ndjson`
- with `evidence_basis: observed`
- and `materiality` of `high` or `medium`

This condition is machine-checked by `tests/test_enforcement_promotion_gate.py`.

---

## Current Status

`governance_present: demonstrated`
`governance_effective: not demonstrated`
`enforcement_promotion: blocked — no observed interception`
