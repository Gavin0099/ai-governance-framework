# Runtime Governance Status

Updated: 2026-03-13

## Summary

The repository is no longer a prompt-only governance framework.

It now operates as an AI coding runtime-governance framework with:

- multi-harness event normalization
- shared runtime enforcement
- loadable rule packs
- session lifecycle closeout
- memory curation and promotion policy
- governance self-audit

Practical status:

- overall maturity: `v0.8`
- current phase: `runtime skeleton complete, enforcement depth still growing`

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

Assessment:

- maturity: `85%`
- stable enough to drive runtime checks

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
- `custom`

Current built-in packs:

- scope: `common`, `refactor`
- language: `python`, `cpp`, `csharp`, `swift`
- framework: `avalonia`

Key files:

- `governance_tools/rule_pack_loader.py`
- `governance_tools/rule_pack_suggester.py`

Assessment:

- maturity: `85%` as a loadable governance-context system
- intentionally not a policy engine

### Runtime Governance Skeleton

The runtime path is now real:

`AI event -> normalize -> dispatcher -> pre/post checks -> session_end`

Key files:

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
- still not fully impossible to bypass in every development path

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

### Evidence / Signal Ingestion

The repository now ingests and interprets test evidence through:

- `governance_tools/test_result_ingestor.py`
- `governance_tools/failure_test_validator.py`

Current support:

- `pytest-text`
- `junit-xml`
- naming/signal-based failure-path validation

Assessment:

- test evidence ingestion: `75%`
- failure completeness: `60%`

### Architecture / Governance Audit

Current enforcement and audit helpers:

- `governance_tools/architecture_drift_checker.py`
- `governance_tools/governance_auditor.py`

Assessment:

- drift detection: `60%`
- governance self-audit: `70%`

## Alpha / Seed Areas

These areas are useful, but still intentionally lightweight:

### Failure-Path Validation

Current behavior:

- detects `invalid_input`
- detects `boundary`
- detects `failure_path`
- optionally detects `rollback_cleanup`

Current limitation:

- mostly naming/signal based
- not yet semantic test-behavior verification

### Drift Detection

Current behavior:

- cross-project private include checks
- suspicious include-directory checks
- refactor boundary-drift heuristics

Current limitation:

- not yet a dependency/import/include graph analyzer

### Rule-Pack Suggestion

Current behavior:

- auto-suggests language/framework packs from repo signals
- suggests scope packs from task text

Current limitation:

- scope remains advisory only
- suggestions do not auto-bind the contract

## Current Position

The most important completed asset is not any single checker or rule pack.

It is the runtime governance pipeline:

`AI coding event -> runtime checks -> session close -> curated memory`

This means the repo has already crossed the line from:

- prompt framework

to:

- runtime governance framework

## Next Steps

### 1. Strengthen Refactor Enforcement

Goal:

- make refactor governance demand stronger evidence, not just load rules

Recommended work:

- add enforcement signals for interface stability
- require stronger regression proof when `RULES` includes `refactor`
- verify partial-cleanup and rollback safety more directly

Why this is first:

- it closes the gap between "refactor as contract" and "refactor as evidence-backed decision"

### 2. Strengthen Failure Completeness

Goal:

- move beyond test-name heuristics

Recommended work:

- ingest richer test metadata
- detect exception-path coverage
- detect rollback/cleanup verification
- distinguish "tests passed" from "required failure evidence exists"

Why this matters:

- current runtime can see test evidence
- it still needs deeper confidence about error paths

### 3. Drift Detection v2

Goal:

- upgrade from heuristic pattern matching to more structural analysis

Recommended work:

- include/import graph analysis
- module boundary diff
- public/private API drift checks

Why this matters:

- this is the next step for catching "tests green, architecture drifted"

### 4. Advisory Suggester Integration

Goal:

- improve operator experience without allowing silent governance drift

Recommended work:

- expose `rule_pack_suggester.py` output through `state_generator.py`
- keep `language/framework` as suggestions
- keep `scope` explicitly advisory

Why this is later:

- usability should come after stronger evidence and enforcement depth

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
- runtime checks and policies make decisions
- suggestion layers propose, but do not silently bind contracts
