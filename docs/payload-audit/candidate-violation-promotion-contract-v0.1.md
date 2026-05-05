# Candidate Violation Promotion Contract v0.1

This contract does not authorize automated escalation.

## Purpose

Clarify promotion boundary for `candidate_violation` signals:
- `candidate_violation` is always advisory
- promotion to `policy_violation` requires separate authority path

## Required Promotion Conditions

All required:
- `reviewer_confirmed = true`
- `authority_ref` present
- `evidence_ref` present
- `promoted_at` present
- `promotion_reason` present

## Forbidden Behaviors

- Do not auto-block because `candidate_violation=true`
- Do not auto-promote because detector confidence is high
- Do not generate `policy_violation` directly from report/analyze surface

## Runtime Output Contract

`post_task_check` emits `candidate_violation_promotion` with:
- `advisory_only=true`
- `auto_block_allowed=false`
- `auto_promotion_allowed=false`
- `promotion_eligible=true|false`
- `promotion_decision`
- optional `promoted_policy_violation` (authority-path result only)

## Boundary Rule

Even when promotion is eligible/constructed, runtime must not auto-inject it into
gate-blocking `policy_violations` without explicit authority workflow integration.
