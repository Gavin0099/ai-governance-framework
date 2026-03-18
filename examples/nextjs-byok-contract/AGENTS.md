# Next.js BYOK AI Governance Rules

## Purpose

This contract defines mandatory AI constraints for Next.js applications that
implement Bring-Your-Own-Key (BYOK) patterns with OpenAI or compatible APIs.
Violations in this domain silently shift API costs from the user to the
application owner and expose the application to unbounded cost amplification.

## Core Constraints

- The agent must not generate or modify `generateEmbedding()` calls in ingest
  routes without confirming that a user-provided API key is passed along.
- The agent must not add a new POST / PUT / DELETE / PATCH route handler without
  including a rate-limiting check (e.g., `Ratelimit`, `rateLimit`, `withRateLimit`).
- The agent must not assume that TypeScript compilation succeeds without
  evidence (`tsc: 0 errors` in diagnostics or a passing CI build).

## No-Assumption Policy

The agent must not assume any of the following without a concrete source:

- Whether a route file uses the user's API key or the application owner's key
- Whether an existing route already has rate limiting in a parent middleware
- Whether a TypeScript build is currently clean

If a required fact is missing, stop and ask for clarification.

## Validator Failure Policy

- A `BYOK_*` or `ROUTE_*` rule in advisory mode must be acknowledged in the
  PR description if the agent's changes produce a violation.
- The agent must not claim a violation is benign without a triage record.

## PLAN.md Freshness Policy

- Before starting any task, verify that `PLAN.md` is not stale.
- Run `session_start.py` (or the hook equivalent) at the start of each session.
- A stale PLAN.md (> threshold days) is a blocking signal — do not proceed
  with architectural changes until PLAN.md is updated.

## Scope Boundary

- This contract is a pre-merge static pattern checker.
- It does not replace TypeScript compiler checks, integration tests, or code review.
- Passing all checks does not guarantee correct BYOK behaviour end-to-end.

## Related Documents

- `rules/byok.md`
- `WORKFLOW.md` (session-start and hook configuration)
