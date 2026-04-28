# A/B Baseline Sanitization

## Purpose

Define a reproducible, auditable de-governance baseline for Group A in A/B smoke tests.

Without this sanitization, A/B can be contaminated by hidden governance context,
prompt priors, or residual authority hints.

## Scope

This document applies only to A/B smoke-test setup.
It is not a runtime authority contract.

## Group A: Required Removals

The ungoverned baseline must remove or disable governance-specific authority surfaces:

- `GOVERNANCE_ENTRY.md`
- `AGENTS.md`
- governance sections in `PLAN.md`
- `runtime_hooks/`
- `governance_tools/`
- reviewer-surface artifacts tied to governance enforcement
- authority declaration documents
- closeout contract documents
- memory promotion contract documents

## Group A: Required Retentions

The baseline must preserve normal engineering signals:

- business or product code
- test suite
- build system
- feature documentation
- regular project README

## Group A: Prohibited Test Contamination

During Group A runs, the following are prohibited:

- manual prompts such as "follow governance rules"
- extra reviewer command injection that references governance authority
- hidden authority hints in system/task prompt text

## Group A: Semantic Neutralization

The baseline should avoid implicit governance inference caused by repository semantics.

Recommended neutralization:

- avoid authority-specific naming patterns
- avoid reviewer-verdict terminology in retained docs
- avoid release-ready or governance-complete terminology
- avoid preserved artifact folders whose names imply governance enforcement
- avoid example names that directly encode governance assumptions where practical

If semantic contamination cannot be fully removed, it must be explicitly recorded as:

- `semantic_residual_present`

## Verification Checklist

Before running Group A, record:

1. Removed surfaces list (with path evidence)
2. Retained surfaces list (with path evidence)
3. Prompt contamination check (`no governance hints injected`)
4. Runtime dependency check (`no governance runtime path callable`)

If any item is unresolved, mark A-group state as:

- `baseline_invalid`

and do not compare A/B results.

## Baseline Quality Classification

Use graded baseline quality instead of binary valid/invalid:

- `baseline_invalid`
Meaning: structural contamination remains (for example governance runtime path still callable).
Effect: do not run comparative A/B conclusion.

- `baseline_degraded`
Meaning: structural sanitization is complete, but semantic contamination is non-trivial.
Effect: comparative claims are allowed only with explicit confidence downgrade.

- `baseline_directional_only`
Meaning: semantic residuals remain and cannot be cleanly neutralized.
Effect: results are directional observation only, not comparative proof.
