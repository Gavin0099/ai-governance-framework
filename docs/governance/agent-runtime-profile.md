# Agent Runtime Governance Profile v0.1

Status: profile schema draft and reviewer guide.

Derived from:
- `docs/governance/trust-boundary-taxonomy.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- Hermes Agent as a representative runtime specimen:
  https://github.com/nousresearch/hermes-agent

## Purpose

An agent runtime governance profile describes the side-effect surfaces,
persistent instruction surfaces, and trust boundaries of an agentic system in a
reviewer-readable format.

The profile is not a runtime gate. It is a structured description that helps a
reviewer see what the system can do, where authority comes from, and which
claims are only structural or heuristic.

## Profile Scope

The profile should cover:
- memory and durable state
- context files and repo instructions
- skills or procedural packages
- plugins and toolsets
- terminal or command execution backends
- external messaging gateways
- schedulers or cron automation
- subagents or delegated execution
- checkpoint, rollback, and recovery behavior
- response-envelope or reporting conventions

## Minimal Schema

```yaml
profile_id: governed-coding-agent
profile_version: 0.1
profile_authority: reviewer_draft
source_specimens:
  - name: hermes-agent
    url: https://github.com/nousresearch/hermes-agent
claim_ceiling:
  - reviewer-facing runtime surface profile only
  - no runtime enforcement claim
  - no semantic correctness claim
not_claimed:
  - OS sandbox implementation
  - authority correctness validation
  - evidence truthfulness validation
  - runtime hook enforcement
surfaces:
  - id: terminal
    type: execution_surface
    boundary_class: load_bearing_boundary_required
    max_side_effect: filesystem_and_process
    controls:
      - approval UX
      - workspace sandbox
    control_claim_ceiling: approval UX is heuristic unless backed by OS isolation
  - id: memory
    type: persistent_instruction_surface
    boundary_class: in_process_heuristic
    max_side_effect: future_instruction_influence
    controls:
      - canonical writer policy
    control_claim_ceiling: structural provenance only
response_envelope_implications:
  required_fields:
    - mode_source
    - task_authority
    - claim_ceiling
    - not_claimed
    - evidence_refs
evidence_refs:
  - artifact: docs/governance/trust-boundary-taxonomy.md
    result: PASS
```

## Field Semantics

`profile_id`
- Stable identifier for the profile.

`profile_version`
- Profile schema version. This is not a runtime version.

`profile_authority`
- Who or what authorized the profile.
- Allowed initial values: `reviewer_draft`, `user_request`,
  `repo_policy`, `external_audit`.

`source_specimens`
- External or internal systems used as analysis specimens.
- Specimens are not adopted by reference.

`claim_ceiling`
- Maximum claim the profile supports.
- For this v0.1 draft, the ceiling is reviewer-facing structural description.

`not_claimed`
- Required negative boundary.
- Must include runtime enforcement and semantic correctness unless separately
  proven.

`surfaces`
- List of agent runtime surfaces.
- Each surface must identify `type`, `boundary_class`, `max_side_effect`, and
  `control_claim_ceiling`.

`response_envelope_implications`
- How this profile changes reporting expectations.
- It does not modify the response envelope validator by itself.

`evidence_refs`
- Artifacts or commands supporting the existence of this profile.
- Evidence refs do not prove semantic relevance or truthfulness.

## Boundary Classes

Use the classes defined in `docs/governance/trust-boundary-taxonomy.md`:
- `load_bearing_boundary`
- `in_process_heuristic`
- `reviewer_aid`
- `persistent_instruction_surface`
- `execution_surface`

If a surface mixes classes, classify by the highest-risk side-effect path and
explain the lower-confidence controls under `control_claim_ceiling`.

## Claim Ceiling Vocabulary

Allowed capability wording:
- reviewer-facing profile
- static structural description
- surface inventory
- heuristic control
- load-bearing boundary required
- evidence reference recorded

Disallowed without separate proof:
- runtime enforced
- behaviorally safe
- semantically verified
- authority confirmed
- evidence validated
- sandboxed
- contained

## Static Validator

`governance_tools/runtime_profile_validator.py` provides a structural-only
validator for runtime profile YAML files.

It checks:
- required top-level profile fields
- minimum surface entry fields
- non-placeholder `claim_ceiling` and `not_claimed`
- `evidence_refs` shape: `command` or `artifact` plus `result`
- high-risk runtime wording has downgrade language in `not_claimed` or
  `control_claim_ceiling`

It does not check:
- runtime enforcement
- authority correctness
- evidence truthfulness
- evidence relevance
- semantic correctness
- OS sandbox correctness
- Hermes compatibility

## Relationship To Response Envelope Validation

The response envelope validator can check that fields and non-placeholder
evidence references exist. The runtime profile validator can check that a
profile YAML has the minimum reviewer-facing structure. Neither validator knows
whether a runtime profile is true.

Safe claim:
- response envelope structure can require runtime profile claim ceilings to be
  disclosed.
- runtime profile validation can reject missing profile fields and obvious
  placeholder evidence.

Unsafe claim:
- response envelope validation proves runtime surface safety or authority
  correctness.
- runtime profile validation proves runtime surface safety, containment, or
  authority correctness.

## Non-Goals

This profile draft does not add:
- Hermes integration
- runtime event detection
- runtime mode routing
- pre-commit or pre-push enforcement
- evidence relevance checking
- semantic evidence validation
- authority correctness engine
