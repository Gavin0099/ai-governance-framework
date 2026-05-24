# Promotion Gate Canonicalization Contract v0.1

Status: active  
Scope: `governance_tools/change_control_summary.py` receipt digest generation

## Purpose

Define a deterministic canonicalization contract for `promotion_gate` receipt digest so
reviewers can distinguish semantic drift from serializer/log-format drift.

## Digest Input Surface (Allowlist)

Only the following fields are admissible digest inputs:

1. `task_provenance.status`
2. `requested_promoted`
3. `runtime.promoted_reported`
4. `runtime.public_api_diff_reported`
5. `signal_profile[*].signal_class`
6. `signal_profile[*].decision_effect`

Any field outside this allowlist is ignored for digest computation.

## Canonicalization Rules

1. Ordering:
   - `signal_profile` keys must be sorted lexicographically before hashing.
   - top-level digest payload is serialized with JSON `sort_keys=True`.
2. Null/missing normalization:
   - missing and `null` text-like fields canonicalize to empty string `""`.
   - for this contract, `task_provenance.status` missing == `null` == `""`.
3. Boolean normalization:
   - canonical `true`: `True`, non-zero numeric, `"1"`, `"true"`, `"yes"`, `"on"`
   - canonical `false`: `False`, zero numeric, `"0"`, `"false"`, `"no"`, `"off"`, `""`
4. String normalization:
   - text values are `str(value).strip()`.
5. Unknown fields:
   - ignored by design; must not affect digest.

## Missing vs Null Equivalence

For v0.1 canonical payload construction:

- `task_provenance.status` missing and `task_provenance.status: null` are equivalent.
- `signal_profile` entries missing `signal_class` or `decision_effect` normalize to `""`.

## Contract Versioning

`promotion_gate_contract_version` is part of the receipt payload and currently `0.1`.

Version bump required when any of the following change:

1. digest allowlist fields
2. canonicalization rules (ordering, type coercion, null/missing behavior)
3. serialization semantics used by digest input

## Backward Compatibility Rule

When introducing `v0.2+`, keep `v0.1` verifier path available for historical receipts or
provide an explicit migration verifier that can classify differences as:

- semantic drift
- canonicalization contract drift

