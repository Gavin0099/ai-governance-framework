# AI Governance Framework

AI Governance Framework is a **claim-control and failure-exposure system** for AI-assisted engineering workflows.

It does not try to prove AI is always correct.  
It enforces boundaries on what AI can change, what evidence is required, and what claims are admissible.

## Why This Exists

In real repositories, common AI workflow risks are:
- scope overreach
- evidence-light summaries presented as proof
- test-pass overclaimed as system safety
- observation records misused as enforcement authority
- session output promoted to long-term memory without eligibility checks

This framework addresses those risks with contract-bound execution, artifact-backed verification, and fail-closed decisions.

## Current Status (Entry View)

- Required repo verified ratio: see latest matrix snapshot in `artifacts/session/`
- Structural readiness and freshness are tracked separately
- Evidence freshness window is configurable (`GOV_MATRIX_EVIDENCE_WINDOW_DAYS`, default `7`)
- Trend auto-append is enabled (`governance/fleet/scope_normalized_trend.jsonl`)

For status semantics:
- `verified`: admissible evidence linked to repo head and within freshness window
- `candidate_or_above`: structural readiness (hooks/framework/agents path ready)

## Key Documents

- Fleet status and boundaries:
  - `governance/fleet/operational_semantics_v1.md`
  - `artifacts/session/governance_required_7of10_semantic_checkpoint_20260527.md`
- External repo onboarding SOP:
  - `governance/fleet/external_repo_onboarding_sop.md`
- Framework explainer (long-form):
  - `docs/ai-governance-framework-explainer.md`

## External Repo Onboarding (Short Path)

1. Add framework as submodule
2. Run external onboarding gap scan
3. Human decision on `contract.yaml` domain/risk
4. Initialize memory skeleton (project facts human-authored)
5. Install hooks and verify real push trigger
6. Run runtime smoke
7. Produce reviewer handoff

Detailed steps: `governance/fleet/external_repo_onboarding_sop.md`

## Claim Boundary (Normative)

This framework currently supports:
- bounded failure containment
- reviewer-checkable observability
- artifact-backed claim admissibility

This framework does **not** claim:
- universal semantic correctness proof
- automatic truth judgment
- production safety guarantee from test pass alone
- “matrix-visible = verified” equivalence

## Runtime Entry Point

- Runtime governance entry: `scripts/run-runtime-governance.sh`
- Matrix script: `artifacts/session/governance_repo_matrix_20260525.ps1`

