# Refactor No Partial Cleanup Rule Pack

- Refactor work must not leave partial side effects or half-cleaned resources on exception or midway failure paths.
- Cleanup, rollback, dispose, release, or revert behavior must be evidenced when the refactor touches resource ownership or multi-step operations.
- A refactor that preserves the happy path but weakens failure cleanup is not considered safe.
