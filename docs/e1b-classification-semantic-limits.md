# E1b Classification — Semantic Limits

> **Purpose**: Pin the three design boundaries exposed by the Phase A misclassification
> test suite (test_e1b_misclassification.py).  These notes prevent test results from
> being narrated beyond what they actually prove.
>
> **Scope**: lifecycle_class, recent_lifecycle_class, Phase 2 gate verdict.
>
> **Status**:釘住 — 2026-04-17.  Update only when a boundary is deliberately changed
> with a PLAN.md policy entry.

---

## 1. `transitioning_active` — Neutral, Not Directional

**What the tests prove**:
Both "genuinely improving" and "persistently oscillating" repos are classified
`transitioning_active` when session count is sufficient and no dominant-stuck or
stable-ok pattern is reached.  The system deliberately stays agnostic.

**Policy note** (one sentence):
> `transitioning_active` is an observation that a repo has enough data and genuine
> variety — it is NOT a claim that the repo is improving, stabilizing, or trending
> in any direction.

**What this means for consumers**:

| Permitted | Not permitted |
|-----------|---------------|
| "repo has enough sessions and genuine state variety" | "repo is improving" |
| "repo is not stuck and not converged" | "repo shows positive adoption trend" |
| use as a gate input (not stuck_absent) | use alone to justify promotion |

**Risk transfer notice**:
The directional information is shifted to `recent_lifecycle_class` (rolling window).
This does not eliminate the risk — it relocates it.  See Section 2.

---

## 2. `recent_lifecycle_class` — Direction Reference, Not Verdict

**What the tests prove**:
The rolling-window signal (`recent_lifecycle_class`) CAN distinguish an improving
repo from an oscillating one, because an improving repo's recent sessions converge
to `stable_ok`.  An oscillating repo's recent window stays `transitioning_active`.

**Policy note** (one sentence):
> `recent_lifecycle_class` is a directional reference signal derived from the last
> `_LC_RECENT_WINDOW` sessions — it is NOT a trend verdict and MUST NOT single-handedly
> drive a promotion or gate-advance decision.

**What this means for consumers**:

| Permitted | Not permitted |
|-----------|---------------|
| use as supplementary evidence in multi-signal review | use alone to declare "adoption confirmed" |
| observe convergence across multiple sessions | treat `stable_ok` here as proof of long-term stability |
| include in human reviewer context | map to "trend confirmed" in automated policy |

**Remaining open question** (not closed by Phase A tests):
Does any existing consumer or report surface `recent_lifecycle_class` with language
that implies verdict authority?  Must be audited before Phase C documentation.

---

## 3. Phase B Temporal Accumulation — Policy Confidence, Not Model Capability

**What the tests prove**:
The classification system does NOT use timestamps.  Three sessions from the same
burst context and three sessions spread over months yield identical `lifecycle_class`
values.  The n=3 threshold is a session-count floor, not a temporal-diversity filter.

**Policy note** (one sentence):
> Accumulating more sessions over time increases reviewer confidence and policy
> defensibility — it does NOT improve model classification accuracy, because the
> current system has no temporal-diversity reasoning.

**What this means for Phase B / Phase C**:

| Phase B does | Phase B does NOT |
|--------------|-----------------|
| raise external confidence that observations span real sessions | make the classifier itself better at distinguishing burst vs distributed |
| provide evidence of pattern persistence across calendar time | guarantee temporal diversity within any single repo's classification |
| lower "all data from one burst" interpretation risk for reviewers | change how `lifecycle_class` or `recent_lifecycle_class` are computed |

**Consequence for promote decision language** (Phase C constraint):
The Phase C promote decision MUST NOT say:
> "We observed for longer, so classification is now more reliable."

It MUST say something like:
> "Extended observation provides policy-defensible confidence that patterns are
> not burst artifacts — the classification accuracy itself is unchanged."

---

## Summary Table

| Signal | What it is | What it is NOT |
|--------|------------|----------------|
| `transitioning_active` | neutral: n >= 3, not stuck, not stable | directional claim; improvement evidence |
| `recent_lifecycle_class` | directional reference (rolling window) | trend verdict; promotion proxy |
| `READY` gate verdict | quantitative conditions met (policy choice) | proof that proxy set is universally valid |
| Phase B time accumulation | reviewer confidence / policy defensibility | model capability improvement |

---

## 4. Phase 2.5 Metric Authority Resolution

**Contract**:
- v2 metrics are candidate operational indicators, not final semantic authority.
- Phase 2 readiness MUST NOT be concluded solely from shadow-metric narration.
- Legacy entropy is retained as reporting-only historical heuristic.
- Phase 3 outputs must stay observation-only until semantic authority is explicitly promoted.

**Implementation note (2026-04-19)**:
- `scripts/analyze_e1b_distribution.py` now emits:
  - `authority_status=candidate_operational_indicator`
  - `phase2_semantic_lock_required=true`
  - `phase3_observation_only=true`
  - `phase3_interpretation=null`
  - explicit forbidden interpretation fields (`trend_direction`, `cross_repo_correlation`, etc.)

**Boundary**:
These fields are guardrails against semantic drift. They are not, by themselves,
proof that Phase 2 semantics are fully validated for promote decisions.
