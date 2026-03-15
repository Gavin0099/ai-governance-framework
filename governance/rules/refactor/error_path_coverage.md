# Error Path Coverage

## Rule ID
`REF-ERROR-001`

## Enforcement
`hard-stop`

## Requirement
Refactor tasks must make error-path behavior explicit before and after the change:

- produce `error_path_inventory` during pre-task planning
- submit `error_behavior_diff` during post-task review
- flag any intentional behavior change so a reviewer can treat it as a behavior change, not a pure refactor

## `error_path_inventory` format
Each error case must include:

- `error_id`: unique identifier
- `trigger`: condition that causes the error path
- `pre_refactor_behavior`: expected behavior before the refactor
- `affected_by_refactor`: `true` or `false`

## `error_behavior_diff` format
Each affected error case must include:

- `error_id`: reference back to the inventory entry
- `pre_behavior`: behavior before the refactor
- `post_behavior`: behavior after the refactor
- `status`: `unchanged`, `changed`, or `removed`
- `reviewer_note`: required when `status` is not `unchanged`

## Hard-stop conditions
- `error_path_inventory` missing
- an `affected_by_refactor: true` error case has no matching `error_behavior_diff` entry
- `status: changed` or `status: removed` without a `reviewer_note`

## Scope boundary
This rule validates structure and reviewer-facing traceability only.

- The framework checks that the inventory and diff exist and are internally consistent.
- The framework does **not** prove that the error-case list is exhaustive.
- Exhaustiveness and semantic correctness remain a reviewer and testing responsibility.
