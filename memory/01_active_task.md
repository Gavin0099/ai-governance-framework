# Active Task

## Current Focus

- **Phase E: Software Fundamentals as AI Governance**
- Goal: Use software engineering fundamentals (Mutation Proof, Spec Ambiguity Detection) to constrain AI Coding risks.
- Principle: **Validity before Expansion** — prove existing governance is real before adding more.

## Current Status

- **Phase D Closed**: Officially marked `passed` in PLAN.md; reviewer closeout artifact `artifacts/governance/phase-d-reviewer-closeout.json` signed by `Gavin0099`.
- **E1-A Mutation Catalog Established**: `docs/e1-mutation-catalog.md` defines critical failure modes (Mutation vs Fixture) and exact violation codes.
- **E1-B Phase 1 Protected**: `governance_tools/mutation_proof_runner.py` established; initial 3/3 negative fixtures (forged artifact, missing root, state mismatch) verified as PROTECTED.
- **E1 Phase 2 Safety Contract Established**: `docs/e1-phase2-safety-contract.md` defines 6 mandatory safety constraints for real rule mutation.
- **Enforcement Policy**: PLAN.md now mandates: "No mutation contract = No enforcement claim".
- **Current Boundaries**: E1 complete: NO | Rule mutation proof: NOT STARTED | Dynamic mutation runner: NOT YET.

## Next Steps

- **E1-B Phase 2: Real Rule Mutation**: Design and implement the `git worktree` + `patch` infrastructure to test code-level bypasses without using mocks.
- **E2: Spec Ambiguity Validator**: Research heuristic/semantic signals for detecting ambiguous terms in PLAN.md and requirements.
- **E3: Production → Spec Loop**: Define the learning contract for promoting production incidents into executable prevention (property tests/specs).
- **Maintenance**: Keep `governance-proof-report.json` updated after any governance tool change.
