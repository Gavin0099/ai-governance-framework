# Entry-Layer Contract for AI Governance Framework

## Purpose

Define the minimum contract that lets workflow skills become runtime-recognizable
governance entrypoints instead of remaining a disconnected UX layer.

This specification does not try to make the repository a full workflow engine.
It defines the smallest closed loop that can later be recognized by runtime
governance without over-claiming enforcement or drifting into a second system.

The minimum closed loop is:

`tech-spec -> precommit -> create-pr`

## Why This Exists

This repository already has:

- runtime governance hooks
- reviewer handoff and trust surfaces
- focused workflow-oriented skills
- CI and repo-boundary validation

What it does not yet have is a contract that answers:

- what a workflow skill produces
- what runtime is allowed to recognize
- what relationship exists between those workflow steps
- what consequence class applies when a step is missing

Without that contract, workflow skills expand the number of entrypoints but do
not expand system understanding.

## Scope

This spec defines:

- the minimum workflow object model for the entry layer
- the edge semantics for the first closed loop
- the minimum recognition criteria for three workflow artifacts
- consequence classes that can be used before hard enforcement exists

This spec does not define:

- a generic DAG engine
- multi-agent orchestration
- automatic proof that an AI did not skip internal reasoning
- universal workflow coverage for every task
- replacement of domain/runtime evidence with workflow evidence

## Boundary To Preserve

This repository remains primarily:

- a runtime governance system
- an evidence and reviewer-surface system

The entry layer is an upstream coordination layer that can later feed runtime
recognition. It is not a separate governance authority.

## Minimal Closed Loop

The first closed loop is intentionally small.

### `tech-spec`

Role:

- convert non-trivial intent into a scoped, reviewable plan

### `precommit`

Role:

- produce local validation evidence before the change is prepared for reviewer
  handoff

### `create-pr`

Role:

- package scope, risk, and evidence into a reviewer-ready handoff

The design goal is not to prove every possible workflow path. The goal is to
make one meaningful path explicit, recognizable, and bounded.

## Workflow Object Model

Runtime should not trust a plain claim that a step was used.

The minimum recognizable unit is a verifiable workflow artifact, not a chat
statement and not a skill name alone.

### Object Types

#### 1. Workflow Artifact

A file or structured record created by a workflow step and intended for later
recognition.

This is the primary object runtime may inspect.

#### 2. Workflow Recognition Result

The runtime-side interpretation of whether a workflow artifact exists, is valid,
and is relevant to the current scope.

#### 3. Workflow Consequence Class

A classification of what missing or invalid recognition means before hard
enforcement is enabled.

## Artifact Envelope

All entry-layer workflow artifacts should conform to one minimum envelope.

Required fields:

- `artifact_type`
- `skill`
- `scope`
- `timestamp`
- `status`
- `provenance`

## Artifact Storage Convention

The minimum storage convention should also be explicit, so observation does not
depend on ad hoc file hunting.

Recommended path:

`artifacts/workflow-entry/<task-slug>/<artifact_type>.json`

Examples:

- `artifacts/workflow-entry/add-runtime-loop/tech_spec.json`
- `artifacts/workflow-entry/add-runtime-loop/validation_evidence.json`
- `artifacts/workflow-entry/add-runtime-loop/pr_handoff.json`

This convention is not itself a verdict. It is only the stable location that
lets a runtime-side observer ask whether recognizable artifacts exist for a
given observable task scope.

### Required Field Semantics

#### `artifact_type`

Identifies the kind of workflow artifact.

Examples:

- `tech_spec`
- `validation_evidence`
- `pr_handoff`

#### `skill`

Identifies which workflow skill produced the artifact.

Examples:

- `tech-spec`
- `precommit`
- `create-pr`

#### `scope`

Binds the artifact to a recognizable unit of work.

Minimum fields:

- `task_text` or equivalent task identifier
- relevant repository root
- changed surface hint such as file paths, diff scope, or PR scope

Runtime should not treat an artifact as applicable if scope cannot be matched to
the current work context.

#### `timestamp`

Records when the artifact was produced.

This allows later freshness or ordering rules without requiring them yet.

#### `status`

Captures the outcome class of the step.

Allowed minimum values:

- `completed`
- `passed`
- `failed`
- `partial`

#### `provenance`

Records how the artifact was produced.

Minimum fields:

- producing tool or skill identity
- repository path context
- tool or framework version when available

Without provenance, recognition may detect an artifact but should not assign it
high trust.

## Edge Semantics

Arrows are not enough. Each edge must declare what kind of relationship it
represents.

This spec recognizes four edge types.

### 1. `sequencing`

Meaning:

- one step normally happens before another

This is ordering guidance, not proof of prerequisite satisfaction.

### 2. `prerequisite`

Meaning:

- a later step is not considered fully valid unless the earlier artifact exists
  and is recognizable

### 3. `coverage`

Meaning:

- one step provides evidence for a later step's trustworthiness or completeness

### 4. `recommendation`

Meaning:

- a step is suggested under certain conditions but is not part of the minimum
  closed loop

## Closed-Loop Edge Definitions

For the minimum loop:

### `tech-spec -> precommit`

Edge types:

- `sequencing`
- `coverage`

Meaning:

- `tech-spec` should usually happen before validation for non-trivial work
- the spec provides scope context that helps interpret later validation evidence

This is not yet a strict prerequisite in the minimum version.

### `precommit -> create-pr`

Edge types:

- `prerequisite`
- `coverage`

Meaning:

- `create-pr` should not be treated as fully trusted unless local validation
  evidence exists
- `precommit` evidence covers the local validation aspect of reviewer handoff

## Recognition Rules

Recognition must remain specific enough for runtime use, but not so abstract
that it becomes a workflow engine.

### General Recognition Rule

An artifact is recognized only if:

- the envelope is structurally valid
- the scope can be matched to the current work context
- provenance is present
- status is meaningful for the artifact type

Artifact existence alone is insufficient.

## Workflow Observation Semantics

Before workflow artifacts influence policy, they should first be described in a
strictly observational language.

Allowed observation states:

- `recognized`
- `missing`
- `incomplete`
- `stale`
- `unverifiable`

These states are intentionally observational.

They do **not** mean:

- the AI certainly followed the workflow
- the AI certainly skipped the workflow
- the task is workflow-compliant
- the task is workflow-non-compliant

The safe statement boundary is:

- `recognized` means a recognizable artifact was observed
- `missing` means no artifact was observed at the expected location
- `incomplete` means an artifact exists but is missing required observable fields
- `stale` means an artifact exists but falls outside the freshness window
- `unverifiable` means an artifact exists but scope/provenance/structure does not
  justify treating it as a recognized observation

This observer should be described precisely as an artifact recognizer, not a
workflow recognizer.

Current observation subject:

- storage-backed workflow artifact traces written under the entry-layer storage
  convention

It does **not** directly observe:

- whether a workflow node was semantically completed
- whether the AI intentionally skipped a step
- whether a workflow story is true internally

### Observation Coverage Boundary

If `observation_coverage` is computed, it should be treated as an observation-only
coverage metric, not as a verdict or risk score.

Safe interpretation:

- how much of the minimum observable artifact loop is currently recognizable

Unsafe interpretation:

- whether the workflow was truly followed internally
- whether the task is compliant or non-compliant
- whether a policy consequence is automatically justified

In other words:

`observation_coverage` may summarize observable coverage, but it must not silently
become a disguised compliance score.

The term `workflow_score` should be avoided because it invites false ordering,
thresholding, and gate semantics.

## Observation Interpretation Guardrails

The machine-readable source of truth for consumer behavior is:

- `governance/workflow_observation_interpretation.v1.json`

That file exists to stop downstream consumers from silently translating
observation states into verdict language.

It also forbids a softer loophole:

- observation lane outputs may not, by themselves or through observation-only
  combination logic, be repackaged into compliance, intent, or policy-violation
  conclusions

### State Meaning Boundary

- `missing` means no artifact present at the expected storage location
- `incomplete` means artifact present but minimal envelope or payload fields are
  absent
- `stale` means artifact present but outside the current task freshness window
- `unverifiable` means artifact present but provenance, schema, scope, or time
  linkage is not trustworthy enough for recognition

### Forbidden Interpretation Baseline

The following direct translations are forbidden:

- `missing -> workflow was not done`
- `missing -> non-compliance`
- `unverifiable -> intentional bypass`
- `unverifiable -> deception`
- `stale -> task invalid`
- `recognized -> compliance verdict`

The following combination-style translations are also forbidden:

- `missing + stale + low observation_coverage -> non-compliance`
- `unverifiable + other observation warnings -> intentional bypass`
- `repeated observation-only missing states -> policy violation`

### Allowed Consequence Baseline

Until a later contract explicitly changes this, workflow observation states are
limited to:

- `hint`
- `advisory_note`
- `reviewer_visible_banner`

The following direct consequences are forbidden:

- `block`
- `raise_minimum_task_level`
- `force_extra_evidence`
- `mark_non_compliant`
- `mark_intentional_bypass`

These forbidden consequences remain forbidden even if a consumer only restates
them as an observation-only aggregate.

### Diagnostic Field Boundary

`failure_source_class` exists as a diagnostic aid only.

It is not:

- a consequence key
- a policy severity label
- a compliance proxy

Its role is to explain why recognition failed without becoming a shadow policy
engine.

When surfaced in observer output, diagnostic metadata should remain separate from
policy metadata. In other words, `failure_source_class` should not be nested
under a policy-shaped field such as `state_policy`, because that path invites
downstream consumers to misread a diagnostic label as a policy token.

## Minimal Artifact Definitions

### `tech_spec` Artifact

Produced by:

- `tech-spec`

Required payload fields:

- `task`
- `problem`
- `scope`
- `non_goals`
- `evidence_plan`

Recognition goal:

- runtime can tell that non-trivial work had an explicit scoped plan artifact

Recognition limits:

- runtime does not need to judge whether the spec is brilliant
- runtime only needs to judge whether a minimally valid scoped plan exists

### `validation_evidence` Artifact

Produced by:

- `precommit`

Required payload fields:

- `entrypoint`
- `mode`
- `result`
- `summary`

Recommended payload fields:

- `commands`
- `focused_surfaces`
- `artifacts`

Recognition goal:

- runtime can tell that the local gate actually ran and whether it passed,
  failed, or was only partial

Recognition limits:

- runtime should not treat a free-form pasted log as equivalent to structured
  validation evidence

### `pr_handoff` Artifact

Produced by:

- `create-pr`

Required payload fields:

- `change_summary`
- `scope_included`
- `scope_excluded`
- `risk_summary`
- `evidence_summary`

Recognition goal:

- runtime or reviewer surfaces can tell whether a reviewer-ready handoff exists
  and whether it references earlier evidence

Recognition limits:

- `pr_handoff` does not replace release, trust-signal, or domain-validation
  evidence

## Consequence Classes

This spec defines classes first, not hard penalties.

### `informational`

Meaning:

- recognized or missing state is recorded but has no trust impact yet

### `advisory_degradation`

Meaning:

- missing recognition lowers the quality of workflow guidance but does not reduce
  runtime trust directly

### `confidence_reduction`

Meaning:

- missing recognition should reduce confidence in the completeness of the
  handoff or process path

### `escalation_candidate`

Meaning:

- missing recognition may justify human review or additional scrutiny

### `verdict_prerequisite`

Meaning:

- a future class for steps that must exist before a later stage can be treated
  as valid

This class is defined now for forward compatibility but is not enabled by this
minimum contract.

## Initial Consequence Mapping

For the minimum closed loop:

### Missing `tech_spec`

Default class:

- `advisory_degradation`

Reason:

- the repository should notice that scoped planning is absent, but the minimum
  contract should not yet hard-block downstream work

### Missing or failed `validation_evidence` before `create-pr`

Default class:

- `confidence_reduction`

Possible escalation:

- `escalation_candidate`

Reason:

- reviewer handoff without local validation should not be treated as equally
  trustworthy

### Missing `pr_handoff`

Default class:

- `informational`

Reason:

- the current repository already has reviewer surfaces; this contract should not
  pretend that absence of a new artifact is a hard governance failure on day one

## Minimum Operable Contract Example

```yaml
entry_layer_contract:
  artifact_envelope:
    required_fields:
      - artifact_type
      - skill
      - scope
      - timestamp
      - status
      - provenance

  artifacts:
    tech_spec:
      produced_by: tech-spec
      required_payload:
        - task
        - problem
        - scope
        - non_goals
        - evidence_plan

    validation_evidence:
      produced_by: precommit
      required_payload:
        - entrypoint
        - mode
        - result
        - summary

    pr_handoff:
      produced_by: create-pr
      required_payload:
        - change_summary
        - scope_included
        - scope_excluded
        - risk_summary
        - evidence_summary

  edges:
    - from: tech_spec
      to: validation_evidence
      semantics: [sequencing, coverage]

    - from: validation_evidence
      to: pr_handoff
      semantics: [prerequisite, coverage]

  consequence_defaults:
    missing_tech_spec: advisory_degradation
    missing_validation_before_pr: confidence_reduction
    missing_pr_handoff: informational
```

## Explicit Non-Goals

This spec intentionally does not do the following:

- define a general workflow runtime
- define a generic node-and-edge orchestration platform
- claim that skill artifacts prove internal reasoning compliance
- require every task to traverse the full loop
- replace runtime, domain, test, or reviewer evidence with workflow artifacts

## Recommended Next Step

Do not add more workflow skills first.

Instead:

1. align `tech-spec`, `precommit`, and `create-pr` with this artifact contract
2. define where those artifacts should live and how they should be named
3. add runtime-side recognition logic for the minimum envelope only
4. keep consequence classes advisory until recognition is proven stable