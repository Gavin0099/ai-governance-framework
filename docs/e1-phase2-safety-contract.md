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
- Each mutation must be implemented as a dedicated `.patch` file or a specific line-deletion rule that is reviewable by humans.
- Arbitrary code modification is strictly forbidden.

### SC-3: Mandatory Failure Contract
- Every mutation must be paired with an **expected test command** and an **expected failure outcome**.
- A "successful" mutation is one that results in a verifiable system failure (matching E1-C violation codes).

### SC-4: P0 Governance Regression
- If a mutation **survives** (i.e., the system remains `ok=True` or the expected failure does not trigger), it is classified as a **P0 Governance Regression**.
- This indicates the governance rule is either missing, bypassed, or effectively dead-code.

### SC-5: Zero-Commit Authority
- The runner itself **MUST NOT** have the authority to `git commit`, `git push`, or modify `PLAN.md`.
- All proof results must be written as separate artifacts (e.g., `artifacts/governance-proof-report.json`) for human audit.

### SC-6: Audit Trail
- The runner must log the exact `git apply` command and the subsequent test command used for each proof.
- Any failure to setup or cleanup the temporary worktree must hard-stop the runner.

---

## Status: Contract Active (Draft)

- **Rule mutation proof**: NOT STARTED
- **Dynamic mutation runner**: NOT YET

Compliance with this contract is a prerequisite for starting any E1-B Phase 2 implementation.
