# AI Governance Framework Explainer

## 0. Why This Framework

AI Governance Framework does not try to make AI “always correct.”  
It constrains AI workflow claims with contract, evidence, boundary, and reviewable receipts.

Core purpose:
- convert AI execution into a governed process
- expose failure states early
- prevent unsupported claims from being promoted as truth

Positioning:
- not a truth machine
- not autonomous safety certification
- yes to failure exposure + claim control

## 1. Status Boundary Model

Use explicit capability states:
- `Operational`
- `Partial`
- `Designed`
- `Optional / Adjacent`

Never write designed intent as already-operational capability.

Minimal rule selection remains `Partial` / `Advisory` unless a specific runtime
surface proves task-type loading and context reduction for the current task.

## 2. Three Layers (Do Not Collapse)

1. Single-run governance lifecycle  
2. Fleet governance layer  
3. Optional observation layer

Rules:
- run PASS does not imply fleet verified
- matrix presence does not imply run correctness
- observation does not imply enforcement authority

## 3. Single-Run Lifecycle

1. request intake
2. pre-hook authority and contract shaping
3. contract-bound execution
4. independent artifact inspection
5. decision gate
6. closeout receipt

Task contract caveat: this is not a single guaranteed YAML artifact today.
Required evidence is closest to operational enforcement. Done definition is
composed from gate and claim-ceiling outputs. Allowed and forbidden scope remain
advisory/reviewer-guarded unless a specific gate implements stronger checking.
7. memory eligibility check

Principle:
- AI explanation is claim source
- artifacts/diff/tests/schema are evidence sources

## 4. Decision and Fail-Closed

Decision semantics should be separated from implementation details.

Concept level may include:
- PASS
- FAIL
- BLOCKED
- NEEDS_REVIEW
- PASS_WITH_DOWNGRADED_CLAIMS

But only code-path-supported outputs are operationally claimable.

Fail-closed means:
- unknown authority => no auto-authorization
- insufficient evidence => no claim promotion
- scope ambiguity => review/block

## 5. Fleet Governance (Current Practical Semantics)

Fleet layer tracks cross-repo maturity and evidence admissibility.

Important separation:
- `verified` = admissible evidence + head match + freshness window
- `candidate_or_above` = structural readiness (hooks/framework/agents path)

Current stabilized interpretation:
- evidence window is configurable (`GOV_MATRIX_EVIDENCE_WINDOW_DAYS`), default `7`
- trend captures both structural and freshness dimensions
- closeout maintenance mode is `event-driven+stale-warning`

This avoids false “10 -> 0 -> 10” interpretation caused by freshness-only drop.

## 6. Observation Layer Boundary

Usage/runtime metadata can inform review but cannot alone authorize enforcement decisions.

Observation != Enforcement.

## 7. Non-Claims

This framework does not claim:
- universal semantic correctness proof
- automatic truth judgment
- production safety proof from passing one test
- matrix row visibility as verified status
- closeout receipt presence as full governance completion

## 8. External Repo Onboarding

Use:
- `governance/fleet/external_repo_onboarding_sop.md`

Shortly:
1. submodule integration
2. onboarding gap scan
3. human domain/risk contract decision
4. memory skeleton initialization
5. hook install + real push trigger verification
6. runtime smoke
7. reviewer handoff

## 9. Final Position

AI Governance Framework is not “AI autopilot.”  
It is a contract/audit/receipt/boundary system for AI actions and claims in repositories.

