# Runtime Governance Status

Updated: 2026-03-15

## Summary

The repository is no longer a prompt-only governance framework.

It now operates as an AI coding runtime-governance framework with:

- multi-harness event normalization
- shared runtime enforcement
- loadable rule packs
- typed rule-pack categories
- agent and skill governance assets
- advisory rule, skill, and agent suggestions
- proposal-time architecture impact estimation
- session-start governance context
- proposal-to-runtime change-control summaries
- session lifecycle closeout
- memory curation and promotion policy
- evidence-based runtime validation
- governance self-audit

Practical status:

- overall maturity: `v1.0.0-alpha`
- current phase: `runtime spine complete, proposal-time guidance and evidence-aware enforcement active, adoption hardening in progress`

## Completed

### Governance Constitution

Core governance documents are present and actively referenced:

- `governance/SYSTEM_PROMPT.md`
- `governance/HUMAN-OVERSIGHT.md`
- `governance/AGENT.md`
- `governance/ARCHITECTURE.md`
- `governance/REVIEW_CRITERIA.md`
- `governance/TESTING.md`
- `governance/NATIVE-INTEROP.md`
- `PLAN.md`

Assessment:

- maturity: `85%`
- strong document coverage
- runtime alignment now exists for key parts of the constitution

### Contract / State

Machine-readable governance state is now established through:

- `governance_tools/contract_validator.py`
- `governance_tools/state_generator.py`

Key runtime-facing fields:

- `RULES`
- `RISK`
- `OVERSIGHT`
- `MEMORY_MODE`

State generation now also includes:

- advisory `rule_pack_suggestions`
- `suggested_rules_preview`
- advisory `suggested_skills`
- advisory `suggested_agent`
- `proposal_guidance`
- optional `architecture_impact_preview`
- suggested `language/framework` packs from repository signals
- advisory `scope` pack suggestions from task text

Assessment:

- maturity: `85%`
- stable enough to drive runtime checks
- suggestion flow is now part of the state, but does not mutate the active contract
- proposal-time guidance is available before implementation begins

### Rule Pack System

The rule-pack layer now supports:

- discovery
- typed categories
- content loading
- runtime injection
- advisory suggestion

Current categories:

- `scope`
- `language`
- `framework`
- `platform`
- `custom`

Current built-in packs:

- scope: `common`, `refactor`
- language: `python`, `cpp`, `csharp`, `swift`
- framework: `avalonia`
- platform: `kernel-driver`

Key files:

- `governance_tools/rule_pack_loader.py`
- `governance_tools/rule_pack_suggester.py`

Assessment:

- maturity: `85%` as a loadable governance-context system
- intentionally not a policy engine

### Agent / Skill Governance Layer

The repository now defines a pre-change governance interaction layer through:

- `.github/copilot-instructions.md`
- `.github/agents/*.agent.md`
- `.github/skills/*/skill.md`

Current built-in roles:

- `advanced-agent`
- `python-agent`
- `cli-agent`

Current built-in skills:

- `code-style`
- `python`
- `governance-runtime`
- `human-readable-cli`

Assessment:

- maturity: `75%`
- strong enough to provide repo baseline, role guidance, and behavior policy
- still advisory, not a mandatory activation layer

### Runtime Governance Skeleton

The runtime path is now real:

`AI event -> normalize -> dispatcher -> session_start/pre_task/post_task -> session_end`

Key files:

- `runtime_hooks/core/session_start.py`
- `runtime_hooks/core/pre_task_check.py`
- `runtime_hooks/core/post_task_check.py`
- `runtime_hooks/core/session_end.py`
- `runtime_hooks/dispatcher.py`
- `scripts/run-runtime-governance.sh`

Multi-harness adapters exist for:

- Claude Code
- Codex
- Gemini

Assessment:

- maturity: `85%`
- skeleton is complete
- enforcement is shared across CI and local pre-push
- session-start context is now part of the shared runtime path
- CI/runtime smoke now preserves startup notes, JSON envelopes, change-control summaries, and an index artifact
- still not fully impossible to bypass in every development path

### Adoption / Onboarding

Current onboarding-facing assets now include:

- `requirements.txt`
- `start_session.md`
- `governance_tools/quickstart_smoke.py`
- `governance_tools/example_readiness.py`
- external repo onboarding / readiness / smoke / report / index tooling

Assessment:

- maturity: `75%`
- strong enough for evaluation and internal trials
- still improving trust signals, release communication, and first-run ergonomics

### Memory Lifecycle

The memory system now has a real lifecycle:

`snapshot -> curated candidate -> promotion policy -> durable memory`

Key files:

- `memory_pipeline/session_snapshot.py`
- `memory_pipeline/memory_curator.py`
- `memory_pipeline/promotion_policy.py`
- `memory_pipeline/memory_promoter.py`

Assessment:

- maturity: `80%`
- strong separation between raw session output and durable project truth
- proposal-time concerns, proposal summaries, and public API diff summaries now enter the audit trail

### Evidence / Signal Ingestion

The repository now ingests and interprets runtime evidence through:

- `governance_tools/test_result_ingestor.py`
- `governance_tools/failure_test_validator.py`
- `governance_tools/failure_completeness_validator.py`
- `governance_tools/public_api_diff_checker.py`
- `governance_tools/driver_evidence_validator.py`
- `governance_tools/refactor_evidence_validator.py`
- `governance_tools/architecture_impact_estimator.py`
- `governance_tools/change_proposal_builder.py`
- `governance_tools/change_control_summary.py`
- `governance_tools/change_control_index.py`

Current support:

- `pytest-text`
- `junit-xml`
- `sdv-text`
- `msbuild-warning-text`
- `sarif`
- `wdk-analysis-text`
- naming/signal-based failure-path validation
- lightweight public API surface diff
- driver-oriented evidence validation from external analysis output
- proposal-time architecture impact reporting
- reviewable change-control summaries derived from startup/runtime artifacts

Assessment:

- test evidence ingestion: `80%`
- failure completeness: `70%`
- interface stability evidence: `75%`
- driver evidence ingestion: `75%`
- proposal-time impact estimation: `70%`

### Architecture / Governance Audit

Current enforcement and audit helpers:

- `governance_tools/architecture_drift_checker.py`
- `governance_tools/governance_auditor.py`

Assessment:

- drift detection: `70%`
- governance self-audit: `70%`

## Alpha / Seed Areas

These areas are useful, but still intentionally lightweight:

### Failure-Path Validation

Current behavior:

- detects `invalid_input`
- detects `boundary`
- detects `failure_path`
- optionally detects `rollback_cleanup`
- accepts richer metadata for exception and cleanup verification

Current limitation:

- still partly heuristic
- not yet semantic test-behavior verification

### Drift Detection

Current behavior:

- cross-project private include checks
- suspicious include-directory checks
- refactor boundary-drift heuristics
- before/after dependency-edge diff for includes/imports/usings

Current limitation:

- not yet a full dependency/import/include graph analyzer
- still heuristic-first, not a semantic architecture model

### Rule-Pack Suggestion

Current behavior:

- auto-suggests language/framework packs from repo signals
- suggests scope packs from task text
- suggests skills and a likely agent
- exposes `suggested_rules_preview`
- `state_generator.py` and `pre_task_check.py` expose these suggestions without mutating the active contract

Current limitation:

- scope remains advisory only
- suggestions do not auto-bind the contract
- skills and agents are suggested, not activated automatically

### Kernel-Driver Governance

Current behavior:

- `kernel-driver` exists as a `platform` pack
- seed rules cover IRQL boundaries, memory / buffer trust boundaries, and cleanup / unwind symmetry
- `driver_evidence_validator.py` enforces evidence expectations from normalized checks
- preferred evidence sources include SDV / SAL / WDK-style diagnostics

Current limitation:

- no KMDF / WDM / UMDF specialization yet
- runtime still depends on normalized external evidence rather than deep driver semantics

### Proposal-Time Guidance

Current behavior:

- `architecture_impact_estimator.py` emits structured impact reports
- `change_proposal_builder.py` collects task, rule, impact, and guidance into a single proposal artifact
- `session_start.py` exposes startup context for agent handoff and initialization
- `change_control_summary.py` merges proposal/startup context with runtime outcomes into a single reviewable summary
- `change_control_index.py` provides a lightweight index over generated startup/change-control artifacts

Current limitation:

- impact estimation is still heuristic-first
- guidance remains advisory rather than an automatic gate

## Current Position

The most important completed asset is not any single checker or rule pack.

It is the runtime governance pipeline:

`AI coding event -> session-start guidance -> runtime checks -> session close -> curated memory -> reviewable change-control summary`

This means the repo has already crossed the line from:

- prompt framework

to:

- runtime governance framework

The strongest current direction of travel is:

`evidence-based enforcement -> proposal-time guidance -> reviewable change-control artifacts -> lightweight semantic verification`

## Next Steps

### 1. Deeper Semantic Verification

Goal:

- keep moving from high-signal evidence checks toward stronger semantic proof

Recommended work:

- deepen `public_api_diff_checker.py` beyond surface extraction
- continue evolving `architecture_drift_checker.py` toward broader structural reasoning
- tighten failure completeness with richer evidence semantics

Why this is first:

- the runtime spine already exists; the next meaningful gains come from more trustworthy verification

### 2. Workflow Embedding

Goal:

- reduce adoption friction in normal day-to-day development

Recommended work:

- continue improving human-readable pre/post outputs
- surface proposal guidance and evidence expectations earlier
- make startup and handoff context easier to consume from agent tooling
- keep startup/change-control summaries easy to review from CI artifacts and local smoke runs

Why this matters:

- the next bottleneck is not missing validators, but whether developers naturally stay on the governance path

### 3. Kernel-Driver Pack Refinement

Goal:

- grow driver governance without turning the repo into a driver-development platform

Recommended work:

- keep `kernel-driver` as the generic high-risk platform pack
- only split into `kmdf`, `wdm`, `umdf` when usage patterns justify it
- avoid adding platform-specific lifecycle engines to core runtime

Why this matters:

- the seed pack is useful today, but premature specialization would add maintenance cost

### 4. Evidence Ingestion Expansion

Goal:

- ingest more realistic external analysis outputs without bloating validators

Recommended work:

- add kinds such as `wdk-analysis-text`, `compiler-warning-json`, or `sarif`
- keep validators focused on evidence presence and policy mapping
- avoid embedding heavy parser logic directly in runtime hooks

Why this matters:

- this improves evidence quality while preserving current framework boundaries

### 5. Agent-Agnostic Context Injection

Goal:

- make governance context easier to activate consistently across multiple agent surfaces

Recommended work:

- extend `session_start` into more native adapter and workflow entry points
- keep rule/skill/agent activation advisory, but easier to consume
- avoid hidden automatic contract mutation

Why this is later:

- the repository already has startup context; the next step is broadening adoption without over-automating

### 6. Review Surface Tightening

Goal:

- make proposal-time and runtime-time governance outputs easier to consume as one review object

Recommended work:

- keep refining `change_control_summary.py` and `change_control_index.py`
- ensure startup JSON envelopes, human notes, and summaries remain aligned
- avoid requiring reviewers to manually correlate multiple raw artifacts

Why this matters:

- the artifact chain now exists; the next improvement is lowering review friction

## Boundary To Protect

The main risk is no longer missing skeleton pieces.

The main risk is complexity creep.

This repository should remain:

- a governance framework

Not become:

- a full AI development platform
- a policy-engine ecosystem
- a generic orchestration OS

Practical rule:

- rule packs provide governance context
- skills provide behavior guidance
- runtime checks and policies make decisions
- suggestion layers propose, but do not silently bind contracts
