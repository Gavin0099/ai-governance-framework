# E1 Phase 2 — Real Rule Mutation Safety Contract

> **Purpose**: Define the legal and security boundaries for the dynamic mutation runner to prevent it from becoming a destructive tool.
> **Scope**: Applied specifically to E1-B Phase 2 (Real Rule Mutation).

## Core Principles

1. **Isolation of Destruction**: Mutation is allowed only in temporary, isolated environments.
2. **Authorization Boundary**: The runner is a validator, not a writer. It has no authority to commit changes or modify project metadata (like `PLAN.md`).
3. **Controlled Entropy**: All mutations must be pre-defined and allowlisted. Random or uncontrolled mutation is prohibited.

---

## Safety Constraints (SC)

### SC-1: Temporary Worktree Only
- All mutations **MUST** be executed within a temporary `git worktree`.
- The main working tree **MUST NEVER** be modified or accessed in write-mode by the runner.
- The temporary worktree must be destroyed immediately after verification.

### SC-2: Allowlisted Mutation Patches
- The runner can only apply mutations defined in the `docs/e1-mutation-catalog.md`.
- Arbitrary code modification is strictly forbidden.

### SC-2.1: Mutation Patch Authority
- Each mutation must be implemented as a dedicated `.patch` file or a specific line-deletion rule.
- All mutation patches **MUST** be human-reviewed and committed to the repository before they can be used by the runner.
- The runner has NO authority to generate or "hallucinate" new mutation patches at runtime.

### SC-3: Mandatory Failure Contract
- Every mutation must be paired with an **expected test command** and an **expected failure outcome**.
- A **protected mutation** is one that causes the expected governance failure (matching E1-C violation codes), thereby proving the rule's active enforcement.

### SC-4: P0 Governance Regression
- If a mutation **survives** (i.e., the system remains `ok=True` or the expected failure does not trigger), it is classified as a **P0 Governance Regression**.
- This indicates the governance rule is either missing, bypassed, or effectively dead-code.

### SC-5: Zero-Commit Authority
- The runner itself **MUST NOT** have the authority to `git commit`, `git push`, or modify `PLAN.md`.
- All proof results must be written as separate artifacts (e.g., `artifacts/governance-proof-report.json`) for human audit.

### SC-6: Audit Trail
- The runner must log the exact `git apply` command and the subsequent test command used for each proof.

### SC-7: Cleanup Verification
- The runner **MUST** verify the successful removal of the temporary worktree and its associated files.
- Verification includes a post-cleanup check of `git worktree list` and a filesystem existence check for the temp path.
- **Residual mutation environment = Hard Failure**: If cleanup cannot be verified, the runner must exit with a critical error and block further execution until manual intervention or a clean state is restored.

---

## Status: Contract Active (Draft)

- **Rule mutation proof**: NOT STARTED
- **Dynamic mutation runner**: NOT YET

Compliance with this contract is a prerequisite for starting any E1-B Phase 2 implementation.
