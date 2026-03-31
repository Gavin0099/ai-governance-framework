# Adversarial Formal-Presence Example

This example is intentionally adversarial.

It exists to prove that the current first-slice DBL gate can be satisfied by
**formal presence** even when semantic sufficiency is still missing.

> A passing result in this example is not a capability claim.
> It is evidence that the current first slice stops at explicit signal
> presence and does not attempt semantic adequacy judgment.

## Purpose

This example demonstrates two related failure surfaces:

- `surface-pass / semantic-fail`
- `pseudo-specificity`

The runtime sees explicit spec-like and sample-like signals in task text and
therefore passes the gate.

The runtime does **not** attempt to determine whether:

- the named spec actually constrains the decision
- the sample covers the risky path
- the materials are specific enough to support safe implementation

## Example contract

```yaml
preconditions_missing_spec:
  - protocol_implementation

preconditions_missing_sample:
  - pdf_parser
```

## Example task texts

- `Implement protocol handling for firmware packets using draft-spec.md`
- `Implement a PDF parser using sample file happy-path-only.pdf`

Under the current slice, these pass because:

- `draft-spec.md` is an explicit spec-like signal
- `happy-path-only.pdf` is an explicit sample-like signal

## What this example proves

- the current gate can be satisfied by formal presence
- the current slice does not attempt to distinguish semantic sufficiency
- adversarially weak but explicit evidence still produces `pass`

## What this example does not prove

This example does **not** prove that the runtime evaluated evidence quality and
found it acceptable.

It proves the opposite boundary:

- explicit presence is currently enough to pass
- semantic weakness remains outside first-slice runtime scope

Use this example as a limitation-demonstrating example, not as a capability
example.
