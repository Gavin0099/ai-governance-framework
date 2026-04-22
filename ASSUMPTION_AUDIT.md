# ASSUMPTION AUDIT (Pre-Task Requirement)

## When To Apply

Run this before executing tasks that involve any of the following:

- Modifying existing API, CLI, or protocol behavior
- Deleting code, tests, or interfaces
- Changing data format or payload shape
- Refactoring cross-component logic

## Required Output (Must Produce Before Implementation)

### 1. Stated Premise

State the user's claim explicitly.

Examples:

- "Payload format is incorrect."
- "This function is unused."

### 2. Evidence Check

List concrete evidence supporting the premise:

- Code references (callers/usages)
- Tests
- Documentation/spec
- Runtime behavior

If no evidence exists, explicitly state:

`No direct evidence found.`

### 3. Alternative Causes

List at least 2 alternatives from different layers.

Examples:

- Payload encoding issue
- Vendor routing mismatch
- Library matching logic issue
- Incorrect API usage

### 4. Decision

Choose exactly one:

- `proceed` - evidence is sufficient
- `need_more_info` - evidence is missing/incomplete
- `reframe` - premise is likely incorrect

### 5. Reframed Task (If Needed)

If decision is `need_more_info` or `reframe`, rewrite the task as a verification step.

Example:

- Instead of: "Fix payload"
- Rewrite to: "Verify whether payload format or vendor routing is the actual cause"

## Notes

- This is a prompt/workflow layer, not governance-core authority.
- This requirement is advisory for runtime governance and should be reviewer-visible.
