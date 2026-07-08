---
status: design-only
scope: conversation-output compliance validation
runtime_behavior_change: no
enforcement_change: no
---

# Conversation Output Validation Gap

## Purpose

This note records a structural gap: the framework can validate repository
files, hooks, receipts, memory, and update artifacts, but it does not currently
validate whether a live agent conversation response actually followed the
required response blocks and claim-boundary wording.

The goal is to make the gap explicit before adding any new defense surface.
This note does not create a validator, adapter, hook, gate, managed block, or
consumer-repo requirement.

## Observed Failure

In VS Code Copilot Chat-style environments, the agent may not consistently emit
the full governance-oriented response shape expected by canonical governance
documents. Examples include omitted or shortened:

- Governance Contract / Bounded Context / Loading Declaration fields;
- final-report fields such as `not_claimed` / Cannot claim;
- plain-language glosses for machine fields;
- manual-update claim boundaries;
- operator-facing adoption table relay.

The failure is not limited to one missing instruction. It comes from a missing
verification layer: after an agent sends a chat response, no framework tool
currently checks that response text against the expected output contract.

## Current Verified Layers

The framework already has validation surfaces for several layers:

| Layer | Existing validation surface | What it can prove |
| --- | --- | --- |
| Repository file structure | `governance_tools/governance_drift_checker.py` and authority consistency tools | Tracked governance files and metadata are structurally consistent. |
| Commit / push workflow | managed hooks and runtime smoke | Local commit/push-time checks ran and reported their result. |
| Memory workflow | `governance_tools/memory_workflow.py` | Current memory edits used the canonical writer and guard path. |
| Update artifacts | updater/F-7 reports, receipts, maturity summary, adoption summary | The update/reporting tool emitted required machine and human-facing fields. |

None of these surfaces proves that a live conversation response included the
required blocks after the model generated it.

## Gap Boundary

Conversation-output compliance is different from repo-state compliance:

- repo-state checks inspect files and artifacts that exist on disk;
- hook checks run before Git operations;
- runtime hooks inspect event payloads when an adapter invokes them;
- conversation-output checks would need access to the final response text after
  model generation.

The current framework does not have a post-response transcript hook for VS Code
Copilot Chat. Copying `runtime_hooks/**` files into a consumer repo does not
make them execute in that environment.

## Existing Inputs That Would Be Relevant

A future design can reuse existing contracts and report surfaces:

- `governance/RESPONSE_ENVELOPE_CONTRACT.md` for result-first reporting,
  evidence separation, and `not_claimed` / Cannot claim behavior.
- `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` for update statuses,
  `manual_update`, `destructive_manual_update`, and adoption summary relay.
- `governance/F7_FULL_UPDATE.md` for full-update conclusion wording.
- `docs/governance/operator-facing-ai-governance-report-ladder-2026-07-07.md`
  for repo-owner-facing report layers.
- `docs/governance/agent-governance-score-rubric-2026-07-07.md` and
  `docs/governance/independent-seed-scorecard-protocol-2026-07-08.md` for
  transcript review and scoring constraints.

## Candidate Validation Targets

A later conversation-output checker, if justified, should start report-only and
target concrete fields:

- final response has a result-first summary;
- required `not_claimed` / Cannot claim content appears for governed tasks;
- machine fields are paired with plain-language glosses when surfaced;
- manual-update paths do not claim `completed`, `latest`, or full adoption;
- adoption summary table rows are relayed when update tools require relay;
- final response separates evidence, risk, next action, and non-claims.

## Environment Constraints

The strongest constraint is adapter availability.

VS Code Copilot Chat-style sessions may load instruction files such as
`copilot-instructions.md` or `AGENTS.md`, but they do not necessarily expose a
post-response hook that can run repository code after each assistant message.

Therefore, a future implementation must not assume:

- `runtime_hooks/adapters/*` is invoked by Copilot Chat;
- copying hook files into a consumer repo makes them execute;
- repository CI can observe ephemeral chat output;
- a passing repo-state validator proves chat-output compliance.

## Candidate Paths

Three paths are plausible, with different claim ceilings:

1. Transcript review aid:
   - Input: copied transcript or closeout text.
   - Output: report-only missing-field findings.
   - Claim ceiling: checks supplied text only; does not enforce live sessions.

2. Scored benchmark/replay:
   - Input: selected transcripts under the independent scorecard protocol.
   - Output: evidence-bound scoring of response quality.
   - Claim ceiling: evaluates sampled behavior only.

3. Native adapter integration:
   - Input: final response text from an environment that exposes a supported
     post-response hook.
   - Output: report-only or advisory conversation-output compliance check.
   - Claim ceiling: applies only to adapters that actually invoke it.

The VS Code Copilot Chat case should start with path 1 or path 2 unless a real
post-response execution hook is proven available.

## Anti-Regrowth Check

Before implementing any new checker, a future slice must answer:

- Which observed failure is being addressed?
- Why do existing file, hook, receipt, memory, update, and scorecard surfaces
  not cover it?
- What existing output or rule would the new checker replace or consolidate?
- What decision should change when the checker reports a finding?
- When should the checker be reviewed, downgraded, or retired?

If those questions cannot be answered, the gap should remain documented but no
new defense should be added.

## Recommended Next Slice

Do not implement tooling first.

The next safe slice is a read-only design/review step:

1. collect two or three real transcript examples where response-format
   compliance mattered;
2. classify which missing fields would have changed the user's decision;
3. decide whether this belongs in transcript review, benchmark scoring, or a
   real adapter path.

## Claim Ceiling

This note records a validation gap only.

It does not prove any agent response was compliant or non-compliant. It does not
add output validation, enforce response format, install an adapter, change
runtime hooks, modify baselines, or make VS Code Copilot Chat execute framework
code.
