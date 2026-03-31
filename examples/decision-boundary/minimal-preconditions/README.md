# Minimal Preconditions Example

This example is intentionally small.

It exists to show how the first executable slice of the Decision Boundary Layer
can be triggered from a consuming contract without introducing a large demo
project.

## Purpose

This example demonstrates the current temporary contract surface for minimal
precondition gating:

- `preconditions_missing_sample`
- `preconditions_missing_spec`
- `preconditions_missing_fixture`

These fields are used by `runtime_hooks/core/pre_task_check.py` to change the
pre-task verdict when a task clearly requires a prerequisite that is not
explicitly present in the task context.

## Example contract

```yaml
preconditions_missing_sample:
  - pdf_parser

preconditions_missing_spec:
  - protocol_implementation

preconditions_missing_fixture:
  - bugfix
```

## What this example proves

- a consuming contract can opt into the first DBL runtime slice
- the slice changes verdict deterministically by task level
- reviewer-visible trace can show which precondition absence changed the result

## Expected effect by task level

- `L0` -> `analysis_only`
- `L1` -> `restrict_code_generation_and_escalate`
- `L2` -> `stop`

## Important limits

This example demonstrates the **first-slice temporary contract surface** only.

It is not:

- the final Decision Boundary Layer schema
- a semantic sufficiency model
- a quality check for samples, specs, or fixtures

Only explicit missing-state signals are supported in this slice.

The current implementation does **not** infer:

- pseudo-presence
- semantic insufficiency
- fake or low-quality sample/spec evidence

## Minimal task examples

These examples are sufficient to trigger the current runtime behavior:

- `Implement a PDF parser for hub update reports`
- `Implement protocol handling for firmware packets`
- `Bugfix the firmware updater retry path`

Adding explicit context such as `sample file report.pdf` will satisfy the
current `missing_sample` signal check for the first slice.
