# Decision Boundary First Slice

> Status: planning note
> Created: 2026-03-31
> Depends on: `docs/decision-boundary-layer.md`

---

## Purpose

This note freezes the acceptance boundary for the first runtime-facing slice of
the Decision Boundary Layer.

It exists to prevent the obvious failure mode:

> trying to prove the whole model at once, then introducing too much new
> runtime surface before any single slice has demonstrated value.

---

## First slice goal

The first slice should prove one thing only:

> a pre-decision boundary can change a real runtime verdict in a way that is
> reviewer-reconstructable from artifact alone.

That is enough for version one.

---

## Included in slice 1

Slice 1 includes only minimal precondition handling for implementation start.

Target checks:

- `missing_sample`
- `missing_spec`
- `missing_fixture`

Allowed outcomes:

- `analysis_only`
- `restrict_code_generation_and_escalate`
- `stop`

Task-level expectation:

- `L0`: may degrade to exploration or analysis-only with warning
- `L1`: must at least escalate when prerequisite is missing
- `L2`: may hard-stop when prerequisite is required for correctness

### Temporary contract surface

Slice 1 currently uses a deliberately narrow contract interface.

Supported fields:

- `preconditions_missing_sample`
- `preconditions_missing_spec`
- `preconditions_missing_fixture`

Example:

```yaml
preconditions_missing_sample:
  - pdf_parser

preconditions_missing_spec:
  - protocol_implementation

preconditions_missing_fixture:
  - bugfix
```

This is a **first-slice temporary contract surface**.

It is intentionally:

- flat
- explicit
- easy to inspect in `contract.yaml`
- limited to missing-state checks only

It is **not** yet:

- the final Decision Boundary Layer schema
- a general-purpose precondition authoring model
- a semantic sufficiency model
- a nested policy language

In particular, slice 1 does **not** infer:

- pseudo-presence
- semantic insufficiency
- sample/spec quality
- evidence completeness beyond explicit presence signals in task context

If later versions introduce a richer schema, this first-slice surface should be
treated as a bootstrap interface, not as the long-term shape of DBL authoring.

---

## Explicitly excluded from slice 1

Do not include the following in the first runtime slice:

- full repo identity enforcement
- any identity-only escalate / stop behavior
- proposal semantic classification
- broad repo taxonomy design
- capability constraint expansion beyond existing scope/evidence surfaces
- new invariant authoring system
- new policy precedence branches beyond what is minimally needed for the first gate
- pseudo-presence or semantic-insufficiency validation beyond explicit missing-state checks

---

## Why this ordering

Minimal precondition gates are the best first proof point because they:

- map directly to real mistakes
- are easy for reviewers to understand
- are easy to trace in artifacts
- can degrade instead of only blocking
- avoid the identity taxonomy problem in the first iteration

Identity should come later as:

1. loadable input
2. trace surface
3. eventually, bounded enforcement

Not as the first hard gate.

First-slice rule:

- identity may be loaded
- identity may appear in trace and reviewer-facing artifacts
- identity must not, by itself, change verdict to `escalate` or `stop`

---

## Acceptance criteria

Slice 1 is successful only if all are true:

1. A missing prerequisite changes the runtime verdict.
2. The changed verdict is visible in trace or artifact.
3. A reviewer can explain why the verdict changed without extra author context.
4. The implementation does not introduce a duplicate truth source.
5. The feature adds less complexity than the failure mode it prevents.
6. False stop / false escalate cases can be observed and classified rather than hand-waved away.

If any of these fail, stop and revise before adding more layers.
