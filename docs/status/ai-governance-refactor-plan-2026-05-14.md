# AI Runtime Reliability Refactor Plan v2 (Governance-Compatible)

As-of: 2026-05-14  
Owner: GavinWu  
Status: ready_to_execute_v2

## Goal

Convert the current governance stack into a runtime reliability layer by:
- preserving necessary auditability,
- adding minimum viable control loops,
- and removing governance layers that do not reduce real failure.

Terminology note:
- Primary term in this plan: `runtime reliability layer`
- Compatibility alias: `governance` (kept for backward compatibility in existing artifacts/tools)

## North Star Metrics (must be tracked each phase)

1. failure_rate_by_class
2. critical_safety_incident_rate
2. mttr_minutes
3. rollback_success_rate
4. cost_per_successful_task
5. p95_latency_seconds

## Operating Principles

- Rule count is not success.
- New control layer must prove measurable reliability gain.
- If same reliability can be achieved with fewer controls, compress.
- Claims stay bounded to observed protocol/task distribution.

## Failure Classification Matrix (R1 hard requirement)

All failures must be classified into exactly one primary class (plus optional secondary tags):

- cognition
- orchestration
- governance
- economics
- determinism
- safety

Each class must define:
- severity levels (S0-S3)
- detectability signal
- owner
- target SLO
- recovery path

No single aggregate failure rate may be used without class breakdown.

## Phase R1 (Week 1): Baseline and Layer Inventory

Objective: establish measurable baseline and classify current controls/failures.

Tasks:
1. Build control inventory table for existing layers:
   - layer_id
   - type (assurance/control)
   - runtime_cost
   - observed_reliability_impact
2. Capture baseline metrics from recent windows/runs.
3. Build Failure Classification Matrix and map last N incidents.
4. Mark each layer:
   - keep
   - uncertain
   - candidate_remove

Deliverables:
- `docs/status/governance-layer-inventory-2026-05-14.md`
- `docs/status/reliability-baseline-2026-05-14.md`
- `docs/status/failure-classification-matrix-2026-05-14.md`

Exit Gate:
- baseline metrics complete
- every major layer classified with initial hypothesis
- failure taxonomy mapped for recent incidents

## Phase R2 (Week 2): Minimum Control Plane (MVP)

Objective: add corrective capability, not more reporting.

Tasks:
1. Degradation mode switch:
   - when risk threshold hit, switch task to safe/manual path
2. Rollback contract:
   - versioned policy/prompt/memory checkpoint + deterministic rollback command
   - side-effect boundary model with action classes:
     - reversible
     - irreversible
     - compensating
     - forbidden-autonomous
   - checkpoint boundary and compensation path per action class
3. Cost throttle:
   - max token and retry budget; over-budget => fail-closed or degrade mode
4. Conflict arbitration:
   - deterministic tie-break rule for multi-agent disagreement
5. Execution freeze:
   - trigger: unknown unsafe state, authority conflict, cost runaway, state corruption
   - behavior: stop autonomous side effects; allow observe/diagnose only

Deliverables:
- `docs/status/control-plane-mvp-spec-2026-05-14.md`
- `docs/status/side-effect-boundary-model-2026-05-14.md`
- `docs/status/deterministic-execution-envelope-spec-2026-05-14.md`
- `docs/status/recovery-engineering-roadmap-2026-05-14.md`
- runtime hook updates + tests (paths decided during implementation)

Exit Gate:
- each control path has at least one passing and one fail-closed test
- freeze mode exercised in at least one test path

## Phase R3 (Week 3): Control-Plane Compression Experiment

Objective: prove minimal control-plane set for target reliability.

Method:
1. fix target thresholds:
   - failure_rate <= baseline * 0.9
   - rollback_success_rate >= baseline
2. remove one uncertain layer per run batch.
3. run interaction sensitivity tests:
   - pair ablation
   - grouped ablation for tightly coupled layers
4. compare delta on reliability and cost.
5. permanently remove layers with no measurable reliability contribution.

Deliverables:
- `docs/status/governance-compression-results-2026-05-14.md` (kept filename for compatibility)
- layer decision table (remove/keep + evidence)
- interaction sensitivity appendix

Exit Gate:
- at least 20% control-plane surface reduced OR explicit evidence why not compressible
- no regression in critical safety incident rate

## Phase R4 (Week 4): Condition-Break Reliability Validation

Objective: verify control robustness under stress, not normal flow only.

Run set:
1. hidden-metrics arm
2. normalized-output arm
3. high-ambiguity tasks
4. exploration-required tasks

Required checks:
- no critical guardrail breach
- rollback path works under at least one induced failure
- cost throttle triggers correctly
- arbitration path exercised at least once
- freeze trigger and recovery path both exercised

Deliverables:
- `docs/status/reliability-condition-break-status-2026-05-14.md`

Exit Gate:
- 3/4 condition-break runs pass
- zero unresolved critical safety issue

## Claim Policy (External Wording)

Allowed:
- "governance-associated observable uplift is provisionally confirmed under current protocol"
- "auditability and procedural integrity are strong"

Not allowed unless new evidence exists:
- "mechanism proven"
- "causal isolation complete"
- "generalized across distributions"

Preferred wording for new reports:
- "runtime-reliability-associated observable uplift is provisionally confirmed under current protocol"

## Trust Boundary Architecture (new mandatory track)

Define explicit authority matrix by role:
- planner
- coder
- reviewer
- auditor

For each role define:
- allowed actions
- forbidden actions
- escalation path
- veto/override rights

Deliverable:
- `docs/status/trust-boundary-architecture-2026-05-14.md`

## 30-Day Success Criteria

1. Control plane MVP in production path.
2. Measurable reliability improvement with bounded cost growth.
3. Governance surface compressed with explicit evidence.
4. Claim language remains epistemically bounded.
5. Trust boundary matrix enforced on runtime action paths.

## Positioning Anchor

See:
- `docs/status/ai-runtime-systems-positioning-2026-05-14.md`
- `docs/status/deterministic-execution-envelope-spec-2026-05-14.md`
- `docs/status/recovery-engineering-roadmap-2026-05-14.md`
- `docs/status/failure-lifecycle-state-machine-2026-05-14.md`
- `docs/status/recovery-capability-matrix-2026-05-14.md`
- `docs/status/deterministic-boundary-contract-2026-05-14.md`
- `docs/status/side-effect-journal-schema-2026-05-14.md`

## Sequencing Update (before R1 metric fill)

1. finalize semantics contracts:
   - failure lifecycle state machine
   - recovery capability matrix
   - deterministic boundary contract
   - side-effect journal schema
2. wire runtime incident/recovery logging to these schemas.
3. only then populate baseline metrics (to avoid taxonomy drift contamination).
