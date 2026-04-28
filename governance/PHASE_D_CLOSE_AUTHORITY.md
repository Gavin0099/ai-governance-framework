# Phase D Close Authority Contract

> document-status: canonical
> authority-chain: governance/AUTHORITY.md → PHASE_D_CLOSE_AUTHORITY.md → all subordinate surfaces
> audience: human-only
> default-load: never (agent must not load autonomously)
> updated: 2026-04-28

---

## Constitutional Status

This document is the **canonical authority source** for Phase D close semantics
in the AI Governance Framework.

All other documents, artifacts, and signals that reference, describe, or imply
Phase D completion status are **subordinate** to this contract. No derived or
reference document may override the authority established here.

This contract is registered in `governance/AUTHORITY.md` at authority level
`canonical`. Reviewers encountering contradictions between this document and
any other source — including README, PLAN.md, version tags, commit history, or
generated summaries — must treat this document as the governing source.

Agent systems must not load this document to derive Phase D status
autonomously. The purpose of this document is to govern human reviewer judgment,
not to provide runtime signals.

---

## Precedence Declaration

When evaluating Phase D completion claims, this contract takes precedence over:

| Signal | Precedence Status |
|--------|-------------------|
| `README.md` completion description | Subordinate — descriptive only, never authoritative |
| `PLAN.md` phase marker (`[x]`) | Subordinate — reflects state, does not confer authority |
| Implementation presence (code merged) | Non-authoritative |
| Commit history / merge confirmation | Non-authoritative |
| Version tags or release notes | Non-authoritative |
| Generated status summaries (AI-produced) | Non-authoritative |
| AI-produced assertions of Phase D completion | Explicitly excluded |
| Absence of open issues or tickets | Non-authoritative |
| State validator `recommended_phase_d_status` output | Non-authoritative (advisory only) |

**None of the above, individually or collectively, constitute a valid Phase D
completion claim under this contract.**

A completion claim is valid if and only if it satisfies the requirements
defined in § Required Authority Artifacts (reserved — pending review of this
constitutional section).

---

## What This Contract Does Not Claim

Governance contracts drift by over-claiming scope. The following are explicitly
outside the scope of this document:

- This contract does not govern Phase A–C or Phase E–G completion semantics.
- This contract does not define what implementation work was done in Phase D.
- This contract does not certify the quality or correctness of implementation.
- This contract does not describe the Phase D milestone — only the authority
  chain for declaring it closed.
- This contract is not itself a completion certificate. It defines the rules
  for issuing one.

---

## Explicit Non-Claims

This section defines what cannot constitute a valid Phase D completion claim.
Absence of a prohibition here does not imply permission. This section is
operative as written.

### NC-1: AI Self-Certification is Prohibited

An AI agent system — including the framework's own governance tools — may not:

- Produce a reviewer closeout artifact on behalf of a human reviewer
- Call `write_phase_d_closeout()` or any equivalent to assert completion
- Use its own output as evidence that Phase D is complete
- Pre-generate a closeout artifact for later human "approval"

Rationale: the gate is meaningless if the system that builds the gate can also
pass it. AI constructs the validator; AI does not pass the validator.

### NC-2: Implementation Completion is Not Completion Authority

The following signals do not constitute Phase D completion, individually or
collectively:

- All planned code being merged
- All tests passing
- All implementation slices marked done
- A clean git working tree or clean CI
- Absence of open issues, tickets, or escalations

Implementation completion is a prerequisite for Phase D close consideration.
It is not an authority artifact. A system with all tests passing and no open
issues remains in `resumable` state until a valid authority artifact exists.

### NC-3: State Validator Output is Advisory Only

The output `recommended_phase_d_status = "completed"` from
`validate_state_reconciliation()` is an advisory signal. The validator observes
conditions; it does not authorize closure. A reviewer reading
`recommended = "completed"` must still produce an independent closeout artifact.
The validator output cannot substitute for that artifact.

### NC-4: Documentation Actions Do Not Confer Authority

The following actions do not constitute Phase D completion:

- Updating README to describe Phase D as complete
- Setting PLAN.md phase marker to `[x]`
- Version bump, release tag, or CHANGELOG entry
- Commit message or PR description claiming Phase D completion
- This document being written, merged, or registered in AUTHORITY.md

Documentation describes completion after authority is established. It does not
create authority. Updating documentation before a valid closeout artifact exists
is a governance violation, not a completion act.

### NC-5: Proxy Signing is Prohibited

A human reviewer may not:

- Delegate closeout signing to an AI system
- Accept an AI-generated closeout artifact as their own signed confirmation
- Pre-authorize a future AI-generated closeout artifact
- Countersign an artifact they did not independently produce

Reviewer identity in the closeout artifact must correspond to a human who
independently evaluated the completion conditions at the time of signing.

---

## Required Authority Artifacts

This section defines the minimum requirements for a valid Phase D completion
claim. Requirements are ordered by logical precedence: authority event
semantics first, artifact presence second, schema fields last.

### A1: Required Authority Event

Phase D completion requires an **explicit reviewer decision** to accept
closeout responsibility.

The following are **insufficient** for authority transfer:

- Passive observation of passing tests or clean CI
- Merge approval of implementation code
- Absence of objection or silence
- Agreement with a generated summary or advisory output
- "Looks good", "LGTM", or equivalent shorthand

A valid authority event is one where a human reviewer independently evaluates
the completion conditions and explicitly accepts responsibility for declaring
Phase D closed. The decision must be contemporaneous with signing, not
retrospective pre-authorization.

### A2: Required Canonical Artifact

The authority event must be recorded in exactly one canonical artifact:

```
artifacts/governance/phase-d-reviewer-closeout.json
```

No alternate path, generated summary, status file, or derived projection may
substitute this artifact:

| Path | Status |
|------|--------|
| `artifacts/governance/phase-d-reviewer-closeout.json` | Canonical — required |
| Any other file path | Invalid substitute |
| Generated summaries (`*.summary.json`, etc.) | Invalid substitute |
| Session closeout reports | Invalid substitute |

The artifact must be present in the repository at the canonical path for any
completion claim to be valid. Validation tools must fail-closed when absent.

### A3: Required Writer Attribution

The artifact must contain attributable reviewer identity sufficient for
independent audit:

- `reviewer_id` must be present and non-empty
- The value must identify a specific human — not a role, team, or system
- Anonymous, collective, or inferred attribution is invalid
- AI-system identifiers in `reviewer_id` are invalid regardless of content

Auditability requirement: a third party must be able to determine, from the
artifact alone, which human accepted closeout responsibility.

### A4: Required Explicit Acceptance

The artifact must record an explicit acceptance act, not implicit agreement:

- `reviewer_confirmation: "explicit"` — signals the confirmation was
  deliberate, not inferred
- `confirmed_at` — non-empty timestamp of the explicit acceptance

The following do not constitute explicit acceptance:

- Absence of a rejection
- Comment-only review without responsibility declaration
- Approval of a different artifact or scope
- Retrospective acknowledgment after the fact

### A5: Required Independence Declaration

The reviewer must declare independence from the implementation author:

- `confirmed_conditions` must include at least one entry asserting reviewer
  independence (e.g., `"reviewer_independent_of_author"`)
- Self-review — author reviewing their own work — is not a valid authority act
- Independence must be declared explicitly, not inferred from org structure

Rationale: authority transfer requires that the accepting party is not the same
party that produced the work being accepted.

### A6: Required Confirmed Conditions

The artifact must record the evidence basis on which the reviewer accepted
closeout responsibility:

- `confirmed_conditions` must be a non-empty list
- Each entry must represent a substantive condition the reviewer evaluated
- Required coverage (minimum):
  - Phase C surface gap status confirmed resolved
  - Validator output reviewed
  - Fail-closed semantics understood and accepted
  - No unresolved blocking conditions remain

Rationale: the list records the reviewer's decision basis, enabling independent
audit of whether the authority act was well-founded.

### A7: Required Integrity Constraints

Once written, the closeout artifact is immutable for authority purposes:

- Silent overwrite or replacement invalidates authority trust
- Post-hoc modification of `reviewer_id`, `confirmed_at`, or
  `confirmed_conditions` invalidates the authority act
- A modified artifact requires a new complete authority event
- Partial updates (editing individual fields without re-signing) are not valid

Validation tools must treat schema version mismatch or unexpected field
modification as an integrity failure, not a warning.

---

### Schema Fields (Derived Serialization of A1–A7)

Schema compliance is necessary but not sufficient for a valid authority act.
Fields are listed here as serializations of the requirements above, not as the
requirements themselves.

| Field | Required | Constraint | Maps to |
|-------|----------|------------|---------|
| `closeout_schema` | Yes | Fixed value | Integrity (A7) |
| `writer_id` | Yes | Must match trusted writer ID | Integrity (A7) |
| `writer_version` | Yes | Must match expected version | Integrity (A7) |
| `written_at` | Yes | Non-empty timestamp | Audit trail |
| `phase_completed` | Yes | Must be `"D"` | Scope |
| `verdict` | Yes | Must be `"completed"` | Explicit acceptance (A4) |
| `reviewer_id` | Yes | Non-empty, human-identifiable | Attribution (A3) |
| `confirmed_at` | Yes | Non-empty timestamp | Explicit acceptance (A4) |
| `confirmed_conditions` | Yes | Non-empty list | Decision basis (A6) + Independence (A5) |
| `reviewer_confirmation` | Yes | Must be `"explicit"` | Explicit acceptance (A4) |

---

## Pending Sections (Reserved — Non-Operative)

**Pending sections are non-operative until explicitly completed and reviewed.**
They MUST NOT be used as validation basis, completion basis, or reviewer
guidance. An empty or partially written section confers no authority.

Remaining sections pending constitutional review:

- § Reviewer Independence Rules
- § Validator Role Boundary
- § Failure Semantics (fail-closed)
