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

## Research Backlog — High-Value Hypotheses (Not Yet Operationalized)

These items are not roadmap commitments. They are validated hypotheses awaiting replay evidence before runtime formalization.

### R1. Governance Hallucination — Operational Definition

**Core definition:**
> A governance system where artifacts only accumulate, semantics only expand, and no runtime surface can reject or invalidate governance assertions — this system hallucinates legitimacy.

Distinction from governance inflation:

| Concept | Nature |
|---------|--------|
| Semantic inflation | governance surface expands (redundant/heavy/complex, but still deniable) |
| Governance hallucination | governance claims become unfalsifiable — no runtime rejection possible |

**Direction this points to:** The framework needs explicit **governance rejection surfaces** — mechanisms that can `reject / downgrade / invalidate / de-authorize / mark_unresolved` governance artifacts. Without this, artifacts accumulate legitimacy by existence alone.

**Status**: High-value hypothesis. Do not formalize until rejection surface design is clear.

---

### R2. Capability Laundering Detection

**Operational pattern:**
```
IF capability_claim_scope > capability_evidence_tier:
    flag: CAPABILITY_LAUNDERING
```

Known laundering patterns to detect:

| Claim in surface | Actual evidence | Laundering type |
|-----------------|-----------------|-----------------|
| runtime parity | artifact ingest only | scope inflation |
| enforcement | advisory hook | authority inflation |
| correctness | traceability | outcome inflation |
| autonomy | scripted replay | agency inflation |

**Status**: Advisory detection only — do not enforce until `capability_claim_scope` and `evidence_tier` taxonomies are stable. Premature hard rejection will cause arbitrary validator failures.

---

### R3. Session Tagging Auditability (Prerequisite for Natural/Instrumental Split)

**The dependency chain:**
```
natural_only analysis
  → requires reliable session classification
    → requires trustworthy session_type tags
      → requires tagging auditability
```

Untagged sessions default to `natural`, but they may include:
- untagged replay runs
- exploratory governance exercises
- partial instrumentation sessions

Without tagging auditability, `natural_only` analysis is a second-order governance hallucination.

**Required tagging metadata:**
- `tag_origin` — how was this tag assigned?
- `tag_confidence` — auto-inferred vs manually tagged
- `tag_evidence` — what artifact supports the tag?
- `tagged_by` — agent, hook, or human?

**Status**: Prerequisite for natural/instrumental split. Must precede any ecology-split claims.

---

### R4. Authority Compression Semantics

**Problem:** Non-authoritative legitimacy layers are accumulating:
`resumable / pending / non_authoritative / provisional / detector-only`

**Proposed compression:**
```yaml
authority_level:
  - authoritative       # has independent reviewer, artifacts verified
  - provisional         # no reviewer, but has clear upgrade path
  - non_authoritative   # no reviewer, no upgrade path — reference only
```

All other authority semantics become sub-fields, not top-level states.

**Key distinction to define:**
- `provisional` = reviewer absence is a known, resolvable condition
- `non_authoritative` = structural limitation, not expected to resolve

Without this distinction, the compression surface re-inflates.

**Status**: Design phase. Do not runtime-formalize until `reviewer_independence_pending` semantics are stable.

---

### R5. 3-Question Hard Rule — Layer 2 Only (AGENTS.md Checklist)

**The rule:**
Before adding any new governance semantic, answer:
1. Which replay surface will consume it?
2. Which reviewer decision will change because of it?
3. Which hostile case would misfire without it?

**Current layer: 2 (reviewer surface)** — add to AGENTS.md as reviewer checklist.

**Do not advance to Layer 3 (runtime) or Layer 4 (enforcement) until:**
- Observable which question blocks PRs most often
- Observable which question gets mechanically filled without thought
- Observable which question best predicts hostile fixture failures

**Reason for restraint:** Premature enforcement causes bureaucracy crystallization. The signal discovery phase must come first.

---

## Structural Note

The most important reframe from this analysis:

> The framework can audit AI. It cannot currently audit itself.

The P0 items close the audit gap. The Research Backlog items address the deeper question:

> How do we prevent governance itself from becoming a hallucination system?

---

*Backlog recorded: 2026-05-08*
*Research backlog appended: 2026-05-11*
*Derived from: cross-agent comparative analysis + governance survivability analysis*
