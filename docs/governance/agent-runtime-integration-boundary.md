# Agent Runtime Integration Boundary v0.1

Status: reviewer-facing conceptual boundary doc. Structural only.

Derived from:
- `docs/governance/agent-runtime-profile.md`
- `docs/governance/trust-boundary-taxonomy.md`
- `docs/governance/checkpoint-memory-audit-spec.md`
- `docs/REVIEWER_ENTRYPOINT.md` (claim-class reading)

This document defines the boundary between a long-running, self-improving agent
runtime (an *executor*) and this framework's governance surface (the *authority*).
It is a thinking-and-review artifact, not an integration plan and not an
enforcement mechanism.

## Specimen scope (not a factual claim)

Where this doc refers to a "self-improving agent runtime" — persistent memory,
automated skill creation, cross-session continuity — it means a **runtime
*class*** (a *Hermes-like* / long-running agent runtime), not a verified
description of any specific external project. No functional claim about any
named external runtime is asserted or verified here. If a specific runtime's
behavior is ever cited as fact, it must be separately verified first.

## 1. Executor vs authority

The integration is asymmetric by design:

| Role | What it is | What it may do |
|---|---|---|
| **Executor** (agent runtime) | Reads the repo, accumulates experience, generates/improves skills, runs tasks | **Suggest.** Propose actions, procedures, and candidate rules |
| **Authority** (governance surface) | Task contract, claim ceiling, evidence binding, ratification, failure taxonomy | **Constrain and authorize.** Decide what may be claimed and what is admissible |

Core rule:

```
Executor memory may suggest.
Governance memory may constrain.
Only ratified governance memory may authorize a claim.
```

An executor is agent-agnostic from the governance side: a Hermes-like runtime,
Claude Code, Codex, or Cursor are all *just executors* behind the same task
contract and the same evidence gate. Integrating a new runtime requires no
governance special-casing — only that the runtime's outputs enter at the lowest
claim class and earn elevation through the existing gate.

## 2. Memory authority is an overlay, not a layer

A common misframing is to treat "governance memory" as a fourth memory layer
alongside episodic / semantic / procedural. It is not. **Authority is an
overlay that can sit on any content type.** Two orthogonal axes:

- **Content type**: episodic (what happened) / semantic (established facts and
  rules) / procedural (how to act — skills, workflows, playbooks)
- **Authority level**: suggestive / constraining / authorizing

The same episodic content may become governable only through an explicit binding
surface. Commit-bound records provide stronger reviewability; session-id fallback
is an advisory continuity mechanism and must not be treated as equivalent to a
commit-bound evidence record. Authority also requires a clean drift check — not a
different "kind" of memory.
The same procedural content can be an agent-suggested skill (advisory) or a
ratified workflow (authoritative). The governance question is never "what kind of
memory is this" but **"who has the right to move this cell into the *authorizing*
column."**

| | suggestive | constraining | authorizing |
|---|---|---|---|
| episodic | agent note | bound memory record | — |
| semantic | agent belief | claim ceiling | ratified rule |
| procedural | candidate skill | contract scope | ratified workflow |

## 3. The danger is self-ratification, not self-improvement

Self-improvement (proposal) is benign and often desirable. The failure mode is
**self-ratification**: proposal == adoption with no gate — an agent that
generates a skill and lets that skill take effect as authority on its own.

A skill is procedural content *asserting authority over future behavior*
("in situation X, act this way"). The skill-ecosystem's real governance risk is
therefore **claim-class spoofing**: prose that reads like a system instruction
being obeyed as if it were ratified.

The normative rules for skill claim class — default class at intake,
provenance-over-tone assignment, and ratification requirements — live in
`skill-claim-class-boundary-spec.md`. They are not restated here, to avoid drift.
A self-improving runtime is safe to couple **iff** its skill/memory outputs enter
at advisory/generated and earn elevation only through that spec's ratification
path — never enforced or canonical by default.

## 4. Non-bypassability is the unsolved precondition

Governance is a **global invariant**: it has value only where it holds
everywhere. An invariant with a hole is not a weaker invariant — it is not an
invariant. Coupling a completion-optimizing executor to a *voluntary* governance
layer creates predictable pressure toward the cheapest path to "done", which is
the path that skips the gate.

Currently verified bypass surfaces in this repo (read-only findings, not
defects-by-themselves but boundary gaps):

- local hooks not installed in a given checkout (`.git/hooks/` samples only)
- `NO_COMMIT` + `session_id` treated as bound; not a blocker
- CI blocks exactly one class (`active_non_canonical_writer`); the rest advisory
- consumer repos may have governance present but not installed/enabled

This means "agent as governed executor" is currently **aspirational, not
achieved**: the gate is bypassable, so it is not yet a load-bearing boundary.

### Ordering discipline (do not skip)

Closing this does **not** mean jumping to enforcement. The disciplined order is:

```
1. make bypass / divergence VISIBLE   (advisory audit — already specified)
2. define the contract                (which commits/validations MUST be bound)
3. only then consider a blocker        (enforce against a ratified contract)
```

Jumping straight to a blocker repeats the "log != authority" error: blocking in
the right direction but before the binding contract exists.

## 5. Relationship to the checkpoint-memory audit

This boundary is observable, not just conceptual. The five finding classes in
`checkpoint-memory-audit-spec.md` are the fingerprints of "an executor did work
but left no governed memory":

- `commit_without_memory`
- `stale_no_commit_memory`
- `unreceipted_validation`
- `rollup_memory_divergence`
- `consumer_uninstalled`

The checkpoint audit (advisory, step 1 above) is therefore the *detector* for an
executor routing around governance. This doc supplies the conceptual boundary; the
audit supplies the observable signal. Neither is enforcement.

## Claim ceiling

```yaml
claim_ceiling:
  - reviewer-facing conceptual / structural boundary only
  - no runtime, hook, CI, or blocker
  - no enforcement, no ratification gate implementation
  - no self-improvement runtime
  - no integration plan for any specific external runtime
not_claimed:
  - any named external runtime's functional behavior (specimen class only)
  - that the governance gate is currently non-bypassable
  - that skills are governed at execution time today
  - that executor memory is constrained today beyond existing advisory surfaces
```
