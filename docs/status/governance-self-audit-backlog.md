# Governance Self-Audit Backlog

**Source**: Cross-agent analysis + source code review (2026-05-08)
**Context**: Derived from evaluating the framework's own evidence gaps and structural blind spots.

---

## P0 — Cannot Skip

### 1. `governance_inflation_audit.py`

The framework has no mechanism to measure whether its own tools are actually used.

Minimum stats required:

| Metric | Flag Threshold |
|--------|---------------|
| Tool usage rate (per governance tool) | < 20% → `INFLATION_SUSPECTED` |
| Test-of-test ratio | > 40% → `SELF_REFERENTIAL_RISK` |
| Runtime signal consumption rate | < 30% → `DEAD_SIGNAL` |
| Advisory warnings acted on | < 50% → `LOW_SIGNAL_VALUE` |
| Docs referenced by agent/reviewer | measure & baseline |

Without this, governance inflation is undetectable from inside the framework.

### 2. No-Governance Baseline Runs

All current runs are under governance context. This makes it impossible to distinguish:
- Governance effect
- Prompt anchoring
- Model prior

**Minimum requirement**: 3 runs per agent, same task, same repo, no governance prompt, no runtime hooks. Record scope drift / claim overreach / artifact pollution.

---

## P1 — Strengthen Credibility

### 3. Evidence Tier Labels on Session Artifacts

Current session artifacts and docs make claims without marking their evidence tier.

Required labels (per the 3-tier framework):
- `framework-supported` — repo/source/runtime/tests directly support this
- `run-observed` — seen in multi-run behavior, not guaranteed
- `hypothesis` — inferred, trend, unverified

Apply to: chatgpt-lane-run-ledger, session-index claims, reviewer-handoff claims.

### 4. Procedural Drift Detection in ChatGPT Lane Validator

`validate-chatgpt-lane-ledger.py` currently checks:
- closeout_covered
- mapping_confidence

It does **not** check whether the original task intent was completed (vs replaced by process).

Add a field or heuristic to detect: "did the agent complete the stated task, or did process-following substitute for the objective?"

### 5. Narrow Claim Scope in Framework Docs

Remove or explicitly disclaim any implicit suggestion that this framework:
- Makes AI more intelligent
- Deterministically controls reasoning
- Proves outcome-level quality improvement

These are out of scope. Leaving them implicit creates false reviewer expectations.

---

## P2 — Further Validation

### 6. Ablation Study Design

Define a controlled comparison:

| Condition | Description |
|-----------|-------------|
| No governance | Same task, no governance docs/hooks |
| Docs only | Governance docs in context, no runtime hooks |
| Runtime only | Hooks active, no governance docs |
| Full governance | Current setup |

Note: must account for model-prior differences between agents before comparing.

### 7. Outcome Metrics Definition

Define what "governance works" means in measurable terms:
- Reviewer time (does governance reduce or increase it?)
- Revert rate
- Artifact pollution incidents
- Scope violation count
- Claim overreach frequency

These are needed before any "governance is effective" claim can be made at evidence tier `framework-supported`.

---

## Structural Note

The most important reframe from this analysis:

> The framework can audit AI. It cannot currently audit itself.

The P0 items above close that gap.

---

*Backlog recorded: 2026-05-08*
*Derived from: cross-agent comparative analysis + source code review*
