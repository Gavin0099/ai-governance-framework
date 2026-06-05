# Contract-Guided Response Template

Use this when a coding response should show domain-governed reasoning rather than only an implementation progress log.

## Required shape

1. Rule basis
- Name the relevant domain rule family or constraint category.
- If the exact rule ID is unknown, state the closest active boundary explicitly.

2. Untouched safety boundaries
- State which driver-sensitive or hardware-sensitive paths are intentionally not changed.
- Call out IRQL, paging, interrupt, locking, MMIO, register access, DMA, or lifecycle boundaries when relevant.

3. Safe extraction rationale
- Explain why the extracted helper or refactor is safe outside the privileged path.
- Be explicit about what remains pure logic versus what remains domain-facing code.

4. Verification evidence
- Report what actually ran.
- Prefer build/test/validator output over intent such as "now update tests" or "should compile".

5. Scope justification
- Explain why the changed files are the minimum useful set.
- If the diff is broad, say why the extra files were necessary.

## Short example

- Rule basis: this change isolates device-ID mapping from the driver-facing PCI config path, so the helper stays outside IRQL-sensitive and WDK-dependent code.
- Untouched boundaries: no change to register access, interrupt paths, dispatch routines, pageable annotations, or locking behavior.
- Safe extraction rationale: the new helper only maps `device_id -> config` using plain C data and `stdint.h`; it does not touch kernel types or side-effecting driver calls.
- Verification evidence: unit test rebuilt with zero WDK headers and passed through the local test script; no new WDK stubs were introduced.
- Scope justification: only the mapping helper, one call site, the focused unit test, and the test build script changed.
