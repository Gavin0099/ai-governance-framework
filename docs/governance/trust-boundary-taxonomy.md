# Trust Boundary Taxonomy for Agent Runtimes v0.1

Status: reviewer-facing taxonomy draft.

Source specimen:
- https://github.com/nousresearch/hermes-agent
- https://raw.githubusercontent.com/NousResearch/hermes-agent/main/SECURITY.md
- https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md

## Purpose

This taxonomy classifies agent runtime surfaces by governance boundary strength.
It uses Hermes Agent as a specimen because Hermes exposes representative agent
surfaces: memory, context files, skills, plugins, tool execution, messaging
gateways, schedulers, subagents, checkpoints, and rollback.

This taxonomy does not adopt Hermes and does not assert that Hermes provides
this framework's governance guarantees.

## Boundary Classes

### Load-Bearing Boundary

A mechanism that can constrain execution even when the model is adversarial,
confused, or prompt-injected.

Current v0.1 examples:
- OS process isolation
- container or VM isolation with restricted filesystem and network access
- operating-system user separation
- external policy enforcement outside the model prompt

Claim ceiling:
- may support containment claims only when independently configured and tested
- must include concrete configuration and validation evidence

Not claimed by this taxonomy:
- safety of any specific sandbox
- correctness of the sandbox policy
- completeness against kernel, hypervisor, or host escape classes

### In-Process Heuristic

A model-adjacent or application-level mechanism that can reduce risk, add
friction, or improve reviewability, but cannot be treated as containment when
the model itself is adversarial.

Examples:
- approval prompts
- tool allowlists presented to the agent
- pattern scanning
- redaction filters
- context-file instructions
- prompt-based policy reminders
- response envelope requirements

Claim ceiling:
- may support reviewability, friction, and structural disclosure claims
- must not be described as runtime containment without an external boundary

### Reviewer Aid

A mechanism that helps a human reviewer reconstruct what happened.

Examples:
- structured reports
- response envelopes
- evidence references
- checkpoints
- rollback descriptions
- run ledgers

Claim ceiling:
- may support observability and auditability claims
- does not prove authority correctness, semantic correctness, or evidence truth

### Persistent Instruction Surface

A durable surface that can shape later agent behavior.

Examples:
- memory
- context files
- skills
- saved prompts
- repo instructions

Claim ceiling:
- may be useful as operational continuity
- must be treated as a prompt-injection and governance-contamination surface
  unless protected by external review and promotion rules

### Execution Surface

A surface through which the agent can cause side effects.

Examples:
- terminal backends
- plugins
- toolsets
- messaging gateways
- schedulers
- subagents with delegated tools

Claim ceiling:
- must be classified by maximum side-effect potential
- approval UX alone is not containment
- delegated execution does not imply isolation unless the subagent boundary is
  backed by OS-level or external enforcement

## Hermes-Derived Surface Mapping

| Hermes surface | Governance classification | Safe claim | Unsafe claim |
| --- | --- | --- | --- |
| Persistent memory | Persistent instruction surface | improves continuity; requires contamination controls | memory is trusted governance state |
| Context files | Persistent instruction surface | provides local instructions | context files are authoritative policy by themselves |
| Skills | Persistent instruction + execution surface | packages repeatable procedures | agent-created skills are promoted governance rules |
| Plugins/toolsets | Execution surface | exposes side-effect channels to classify | tool allowlist equals containment |
| Terminal backends | Execution surface | side-effect boundary requiring isolation | terminal approval alone contains adversarial execution |
| Messaging gateways | Execution surface | external communication surface requiring authority review | gateway presence is safe by default |
| Cron automation | Execution surface | scheduled execution surface requiring replay and authority controls | scheduled agent action is self-authorized |
| Subagents | Delegated execution surface | delegation surface requiring boundary description | subagent means OS isolation |
| Checkpoint/rollback | Reviewer aid | improves recovery and reconstruction | rollback proves safety |

## Response Envelope Implications

When reporting work involving an agent runtime surface:
- `scope` must name the exact surface being discussed.
- `task_authority` must identify whether the work came from user request, repo
  policy, followup, hook trigger, or autonomous action.
- `claim_ceiling` must state whether the claim is documentation, static
  structure, runtime enforcement, or external containment.
- `not_claimed` must explicitly list runtime enforcement, semantic correctness,
  evidence truthfulness, and authority correctness unless they were separately
  validated.
- `evidence_refs` may point to commands or artifacts, but does not prove
  relevance or truth by itself.

## Forbidden Wording Without Evidence

These phrases require an explicit load-bearing boundary reference or downgrade:
- runtime enforced
- sandboxed
- contained
- authority confirmed
- evidence validated
- behaviorally safe
- semantically verified

Allowed downgraded forms:
- documented only
- structural validation only
- reviewer-facing profile only
- in-process heuristic only
- not a containment boundary

## Non-Goals

This taxonomy does not provide:
- Hermes integration
- runtime hook enforcement
- automatic event detection
- authority correctness validation
- semantic evidence validation
- OS sandbox implementation
- RBAC or separation-of-duty implementation
