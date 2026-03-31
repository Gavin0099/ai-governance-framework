# Insufficiency-Like Preconditions Example

This example is intentionally small and intentionally incomplete.

It exists to demonstrate the current boundary of the first executable DBL
slice, not to pretend that semantic sufficiency is already solved.

> This example demonstrates a current boundary, not a sufficiency capability.
> A passing result here only shows that explicit precondition signals are
> present. It must not be interpreted as semantic adequacy detection.

## Purpose

The first minimal DBL slice currently checks explicit missing-state signals.

It does **not** yet determine whether a provided prerequisite is:

- relevant to the actual task
- complete enough for the task
- strong enough to support safe implementation

This example shows an insufficiency-like case where something exists in form,
but may still be poor evidence in substance.

## Example contract

```yaml
preconditions_missing_spec:
  - protocol_implementation

preconditions_missing_sample:
  - pdf_parser
```

## Example task texts

These texts deliberately include explicit signals that satisfy the current
first-slice gate even though the evidence could still be weak or irrelevant:

- `Implement protocol handling for firmware packets using legacy-spec.md`
- `Implement a PDF parser using sample file happy-path-report.pdf`

Under the current slice, these are treated as **present** because:

- `legacy-spec.md` contains an explicit spec-like signal
- `happy-path-report.pdf` contains an explicit sample-like signal

## What this example proves

- the current gate is explicit-missing-state only
- the first slice can be passed by formally present but potentially weak evidence
- insufficiency is not yet part of runtime decision-making

## What this example does not prove

This example does **not** mean the current gate is wrong.

It means the first slice has a deliberate boundary:

- absence is in scope
- semantic sufficiency is not yet in scope

This example should therefore be used as:

- a reconstruction example
- a reviewer expectation-setting example
- a precursor to future adversarial / insufficiency validation

Not as proof that the framework already validates evidence quality.
