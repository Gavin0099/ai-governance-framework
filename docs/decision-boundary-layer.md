# Decision Boundary Layer

> Status: proposed design direction
> Created: 2026-03-31
> Purpose: define the machine-consumable constraint surface that should exist before AI-assisted implementation begins

---

## Why this exists

The framework already governs AI work at the session and task boundary:

- `session_start`
- `pre_task_check`
- `post_task_check`
- drift checks
- artifacts and reviewer handoff

That is strong on discipline, evidence, and replay.

It is weaker at a different point:

> before the system decides what kind of solution is even allowed,
> whether implementation may begin,
> and how much change is permitted for this task.

This document names that missing surface explicitly.

It is not an "entry prompt" layer.
It is not another documentation bundle.
It is a proposed **pre-decision constraint system** that the runtime can consume, trace, and review.

---

## Core idea

The missing problem is not simply "repo-specific context."

The real problem is:

> constraints that matter before implementation starts are often implicit,
> human-local, or only present in prior conversation.

If those constraints are only written in a repo note, they can still be ignored.
To become governance-relevant, they must be:

- structured enough to be consumed
- attached to a decision point
- included in trace output
- governed by precedence
- able to degrade, not only hard-stop

This document calls that whole surface the **Decision Boundary Layer**.

---

## Scope

This layer is intended to answer four questions before implementation:

1. What class of repo/problem is this?
2. What classes of solution are invalid even if technically possible?
3. What must exist before implementation is allowed to begin?
4. How much change is this task allowed to make?

Those are different questions.
They must not be collapsed into one "context file."

---

## The four constraint layers

### Layer 0: Identity Constraint

Purpose:
- constrain repo routing and solution framing
- prevent category mistakes before deeper reasoning begins

Examples:
- this is a firmware tool repo, not a GUI application
- this is a proxy group-buy system, not a bookstore
- this is a CLI-first tool, not a web service

This layer should answer:
- what this repo is
- what it is not
- what misclassifications are explicitly forbidden

Suggested shape:

```yaml
repo_identity:
  repo_type: firmware_tool
  repo_purpose: usb_hub_firmware_update
  forbidden_misclassification:
    - gui_application
    - web_service
```

This layer is not useful if it remains metadata only.
It must be consumable by decision routing.

Required runtime effect:
- if the proposed solution class conflicts with `repo_identity`, the system must at least `escalate`
- high-risk mismatches may `reject`

---

### Layer 1: Invariant Constraint

Purpose:
- constrain the allowed solution space inside this repo or domain

Examples:
- matching must be automatic
- manual selector UI is forbidden
- public flashing path must remain single-owner

These are not "context notes."
They are local policy and should live in a formal contract source, not only in `CLAUDE.md` or equivalent repo notes.

This layer should answer:
- what solution classes are disallowed
- what product or domain invariants must remain true
- what patterns require escalation even if they compile and pass tests

Suggested shape:

```yaml
local_invariants:
  forbidden_patterns:
    - manual_matching_selector
    - silent_fallback_write_path
  required_behavior:
    - automatic_matching_only
```

Required runtime effect:
- invariant violations should appear in the same decision path as other contract-driven policy
- they must be traceable as constraint-based rejections, not just prose guidance

---

### Layer 2: Precondition Constraint

Purpose:
- decide whether implementation is allowed to begin

Examples:
- parser work requires sample files
- protocol implementation requires spec and error-handling definition
- migration work requires rollback plan

This layer is the most immediately valuable part of the model.
It catches "started correctly according to form, but without enough grounding to implement safely."

However, a simple existence check is not enough.
There are three levels:

1. explicit absence
2. pseudo-presence
3. semantic insufficiency

Examples:
- spec missing entirely
- spec exists but does not cover this case
- sample exists but lacks failure-path coverage

So preconditions need validation, not just presence tests.

Suggested shape:

```yaml
preconditions:
  sample_data:
    required_for:
      - pdf_parser
    degradation:
      L0: allow_exploration_with_warning
      L1: escalate
      L2: stop
  spec_validation:
    required_sections:
      - protocol_definition
      - error_handling
      - boundary_conditions
    degradation:
      L0: analysis_only
      L1: escalate
      L2: stop
```

Required runtime effect:
- preconditions must be checked by `pre_task_check` or an equivalent pre-task validation path
- absence or insufficiency must produce a deterministic verdict
- the verdict must support degradation, not only binary stop/pass

---

### Layer 3: Capability Constraint

Purpose:
- limit how much change this task is permitted to make

Examples:
- no new framework introduction
- no public API break
- no cross-module refactor
- no persistence schema change in an L0/L1 fast path

These are not repo identity and not domain invariants.
They are task-bounded mutation constraints.

This layer is already partially present in the framework through:
- scope control
- public API diff tooling
- refactor evidence requirements
- task level and risk handling

The missing piece is to surface them as one coherent pre-decision layer.

Suggested shape:

```yaml
capability_constraints:
  allowed_change_scope:
    - local_module_only
  forbidden_change_classes:
    - public_api_break
    - new_framework_introduction
    - cross_module_refactor
```

Required runtime effect:
- capability violations should trigger scope-based escalation or rejection
- they must be evaluated before large implementation begins, not only after diff review

---

## Why this is not just CLAUDE.md

Repo-local context files can still be useful, but their scope must stay narrow.

They are appropriate for:
- vocabulary
- repo orientation
- quick framing
- links to canonical sources

They are not a safe primary home for:
- invariants
- hard gates
- deterministic policy

If hard constraints live only in repo-local prose, they remain weakly enforced.

Recommended rule:

- repo-local orientation docs may describe
- formal constraint sources must decide

### CLAUDE.md scope boundary

If a repo uses `CLAUDE.md` or an equivalent local orientation file, its role
must be explicitly limited.

Allowed content:

- repo identity summary
- vocabulary and naming conventions
- quick orientation for major folders or entrypoints
- links to canonical sources of truth

Forbidden content:

- hard-stop rules
- task gate logic
- policy precedence rules
- capability constraints that affect verdicts
- duplicate copies of contract-driven invariants
- enforcement logic
- gate conditions

In other words:

- `CLAUDE.md` is not a policy source
- `CLAUDE.md` is not a gate source
- `CLAUDE.md` may help framing
- `CLAUDE.md` must not silently become enforcement

---

## Decision model integration

This layer is only meaningful if it is consumed by the runtime.

Minimum required consumers:

- `session_start`
  - may load identity/framing context
  - may attach preview data for trace

- `pre_task_check`
  - must evaluate preconditions
  - should evaluate identity mismatches and capability overreach

- decision model / runtime verdict path
  - must apply precedence and degradation policy

Minimum trace outputs:

- which constraints were loaded
- which constraints were evaluated
- which verdict they influenced
- whether the result was pass / warn / restrict / escalate / stop

If these are not observable in artifacts, this layer is not yet governance-relevant.

---

## Policy precedence

Once identity, invariant, precondition, and capability constraints all exist, precedence must be explicit.

Otherwise different sessions and reviewers will resolve conflicts differently.

A starting model:

1. Precondition constraint
2. Invariant constraint
3. Capability constraint
4. Identity constraint

This order is only a proposed default.
It must be reviewed against the existing v2.6 precedence model before adoption.

Declarative interpretation:

- precondition answers "may this task begin implementation now?"
- invariant answers "is this solution class allowed here at all?"
- capability answers "is this amount/type of change allowed for this task?"
- identity answers "is this proposal framed as the right kind of repo/problem?"

The important point is not the exact order.
The important point is:

> precedence must be defined, not improvised.

---

## Degradation paths

A pure hard-gate system will eventually become too rigid.

The framework already has strong replay, artifact, and review capabilities.
That means some failures should degrade rather than only stop.

Examples:

```yaml
missing_sample:
  L0: allow_exploration_with_warning
  L1: escalate
  L2: stop

spec_incomplete:
  L0: analysis_only
  L1: restrict_code_generation_and_escalate
  L2: stop
```

This keeps the system from collapsing into "AI can never proceed" while still making missing grounding visible, reviewable, and deterministic.

Task-level binding is required.

The same degradation must not apply equally to every task level.
At minimum, the design must be able to express:

- degradations allowed in `L0`
- degradations that force escalation in `L1`
- degradations that become hard stop in `L2`

Without task-level binding, degradation paths will turn into self-excusing bypasses.

---

## Non-goals

This layer should not become:

- a second copy of the governance constitution
- a replacement for domain contracts
- a free-form repo diary
- a new catch-all schema for every local preference

If it grows without a decision consumer, it becomes context inflation.
If it duplicates existing rules, it becomes governance duplication.

---

## Relationship to current entry-layer documents

The current `entry-layer` documents were written to stop unjustified runtime expansion.

That boundary remains useful.

This document does not argue that the old entry layer should be reintroduced as-is.
Instead, it reframes the actual need:

- not more observation
- not more runtime surface by default
- but a smaller, explicit decision-boundary model tied to real verdicts

In other words:

- `entry-layer-boundary.md` remains a valid anti-expansion constraint
- this document describes what a justified successor would need to be

---

## Minimal implementation path

If this direction is pursued, start with the smallest path that changes real decisions:

1. Add machine-readable `repo_identity`
2. Add one or two precondition validators with degradation paths
3. Route both through `pre_task_check`
4. Emit trace showing which boundary constraint changed the verdict
5. Only then consider broader invariant/capability expansion

If step 4 cannot be achieved, stop.
That would mean the system added structure without adding verifiable value.

---

## First runtime slice recommendation

The first runtime slice should not attempt to implement the full four-layer
model at once.

Recommended order:

1. Minimal precondition gate
2. Minimal capability hook
3. Identity as input and trace surface
4. Identity as enforcement

Reasoning:

- preconditions are easiest to validate against real mistakes
- capability constraints already align with existing evidence/scope tools
- identity is valuable, but high risk to overfit or under-specify too early

The first slice should therefore target only a narrow, high-value subset:

```yaml
first_slice:
  includes:
    - missing_sample
    - missing_spec
    - missing_fixture
  degradation_actions:
    - analysis_only
    - restrict_code_generation_and_escalate
    - stop
  excludes:
    - full identity enforcement
    - full invariant expansion
    - repo taxonomy growth
```

Success for the first slice means:

- the boundary changes a real verdict
- the reason is visible in trace
- reviewer can reconstruct the decision from artifact alone
- the slice does not duplicate existing contract truth
- false stop / false escalate cases are observable and explainable

Deliberately deferred:

- semantic identity classification
- multi-layer conflict resolution beyond the initial precedence model
- broad invariant authoring for many repos
- new repo taxonomy work
- pseudo-presence and semantic-insufficiency validation beyond the minimal first slice
- capability runtime enforcement beyond reuse of existing evidence / scope surfaces

---

## Alignment with existing framework surfaces

This layer should reuse existing framework strengths instead of renaming them.

Current alignment candidates:

- precondition constraint
  - `pre_task_check`
  - runtime contract
  - proposal guidance / escalation path

- capability constraint
  - public API diff checks
  - refactor evidence
  - scope control
  - source-of-truth boundary checks

- invariant constraint
  - domain contracts
  - rule packs only where they already act as formal policy input

- identity constraint
  - repo typing only after a bounded first slice proves trace value

If an implementation cannot point to one of these existing surfaces, it may be
inventing a parallel system rather than extending the current one.

---

## Success criteria

This layer is only successful if it can demonstrate all of the following:

- a wrong proposal class is caught by identity routing
- a missing or insufficient prerequisite changes the verdict deterministically
- the decision is reconstructable from artifact alone
- the new layer does not require duplicate truth sources in repo notes and contracts
- token and complexity growth remain bounded

Without those properties, this should remain a design memo, not runtime behavior.
