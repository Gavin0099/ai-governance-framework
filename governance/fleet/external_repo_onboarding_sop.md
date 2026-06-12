# External Repo Onboarding SOP

Status: v1.1
Scope: onboard a consuming repository into `ai-governance-framework` with minimal ambiguity.

This SOP covers the **submodule consumer** path only (see
[`docs/ADOPTION_MODEL.md`](../../docs/ADOPTION_MODEL.md)). It does not
apply to external contract repos or copy-based consumers — those classes
have different evidence duties and automation ceilings.

## Goals

- Establish a reproducible onboarding path for external repos.
- Keep governance adoption fail-closed without forcing schema expansion.
- Separate human decisions (domain/risk) from automation steps.

## Step 0: Classify the Consumer Role

Before any onboarding step, classify the target repo against
[`docs/ADOPTION_MODEL.md`](../../docs/ADOPTION_MODEL.md) using read-only
diagnosis.

Rules:
- If the repo already contains copied framework files, it is a copy-based
  consumer: stop, run the provenance audit first; do not layer a submodule
  on top of an unaudited copy.
- If classification is ambiguous, stop at diagnosis and report. A
  classification step must not silently become a remediation step.

Acceptance:
- Target classified as a (prospective) submodule consumer; otherwise this
  SOP does not apply.

## Step 1: Add Framework as Submodule

In target repo root (use your organization's framework remote URL):

```bash
git submodule add <framework-remote-url> ai-governance-framework
git submodule update --init --recursive
```

Acceptance:
- `ai-governance-framework/` exists.
- Submodule pointer is tracked by the target repo.

## Step 2: Run External Onboarding Gap Scan

Run onboarding/readiness scan from framework against the target repo.

Minimum output required:
- machine-readable gap report
- human-readable summary

Typical gaps:
- hooks missing
- framework lock missing
- AGENTS.md still scaffold
- no admissible closeout evidence

Acceptance:
- Gap list is explicit and actionable.

## Step 3: Human Decision on `contract.yaml`

Human owner must decide and write:
- `domain`
- `risk tier` (or equivalent risk posture field)

Rules:
- Do not auto-guess domain/risk from code heuristics.
- No placeholder values.

Acceptance:
- Contract validation passes.
- Domain/risk rationale is reviewer-explainable.

## Step 4: Initialize Memory Skeleton

Create minimum memory files and keep project facts human-authored.

Required baseline:
- `memory/YYYY-MM-DD.md`
- `memory/02_tech_stack.md` (or local alias expected by current tooling)

Rules:
- Agent may scaffold structure.
- Project facts content must be filled/confirmed by humans.

Acceptance:
- Memory schema check passes.
- Project facts are non-empty and repo-specific.

## Step 5: Install Hooks and Verify Real Trigger

Install `pre-commit` and `pre-push` hooks and framework-root config.

Then run a real commit/push trial (not file-existence only).

Acceptance:
- Hook validator reports `valid=true`.
- Push path shows runtime governance hook execution.

## Step 6: Run Runtime Smoke

Run runtime smoke checks (session_start / pre_task / post_task).

Acceptance:
- Smoke passes (or bounded advisories only).
- Required runtime artifacts are produced.

## Step 7: Produce Reviewer Handoff

Handoff report must include:
- onboarding gaps and remediations
- contract domain/risk decisions
- hook install and push-trigger evidence
- runtime smoke evidence
- remaining blockers and next-step recommendation

Acceptance:
- Reviewer can decide go/no-go without re-running discovery.

## Claim Ceiling After Completing This SOP

Completing all steps supports exactly this claim:

> This repository is an onboarded submodule consumer with onboarding
> evidence at the recorded commit.

It does **not** support:

- fleet rollout or consumer-generality claims (one repo, one evidence);
- per-update currentness claims going forward (those require the managed
  F-7 update path with per-update verification evidence);
- "governance complete" — onboarding is entry, not closure.

## Non-Goals

- No schema expansion during onboarding unless failure-driven and approved.
- No evidence-contract weakening to “make ratio green”.
- No bulk multi-repo onboarding in one stream.

## Recommended Minimal Verified Path

For required repos with known pattern:
- `hooks + framework.lock + fresh closeout (+ dirty explained)`

This path is preferred when it satisfies existing contract semantics without introducing new governance concepts.

