# External-Tooling Replaceability Inventory — governance_tools/ and the Skill Library

Status: **read-only strategic assessment, decision input only.** No tool is
changed, removed, or replaced by this document. Nothing here is a commitment or a
roadmap. This is the owner's direction ("the Skill Library and those Python tools
are well-suited to being replaced by external tooling") worked into a candidate
list for a later decision.

Rigor ceiling: this is a **name/category-level triage** over the 198 files in
`governance_tools/*.py`, grouped by apparent function. Per-tool replaceability
must be confirmed by reading each tool's actual contract before any action. A
category marked "replaceable" means a mature external equivalent exists for that
*kind* of check, not that a given file is a drop-in swap today.

## The one hard data point from this session

The pre-push bug (`D−C` will measure exactly this) is an "ignore-stdin" logic
error. The in-house Python guard missed it **and** shellcheck/ruff/mypy would not
catch it either — and in fact none of the three is even installed. So "replace
in-house checks with external tools" is **defect-type-dependent**: it helps for
commodity checks (schema, lint, diff, policy), and does nothing for
logic-correctness bugs, which need tests/oracles regardless of who ships the
linter. Keep that boundary in mind reading the table.

## A. Strong replace candidates (mature external equivalent exists)

| Category (example tools) | Mature external tool | Note |
|---|---|---|
| JSON/YAML schema + envelope validation (`contract_validator`, `response_envelope_validator`, `*_schema`, `claim_enforcement_receipt_validator`, `driver_evidence_validator`) | JSON Schema (`jsonschema`/`ajv`), Pydantic, CUE | Largest single cluster; receipt/envelope shapes are ordinary schema validation. |
| Code hygiene / whitespace / format / shell (`output_mode_enforcer` partial, the `git diff --check` usage, hook lint) | ruff, shellcheck, pre-commit | Commodity; well-served upstream. |
| Public-API / interface diff (`public_api_diff_checker`, `architecture_drift_checker` partial) | `griffe` (Python API diff), `oasdiff` (OpenAPI) | External diff is stronger for shape; behavioral compat still needs tests. |
| Mutation / test-sensitivity (`mutation_proof_runner`, `mutation_proof_runner_phase2`) | `mutmut`, `cosmic-ray` | Directly replaceable for the sensitivity-oracle role. |
| Test-result ingest (`test_result_ingestor`, `*_smoke` harnesses) | pytest + JUnit XML, standard CI runners | Ingest/format is commodity; the governance *interpretation* is not (see C). |
| Policy gates as boolean rules (`gate_policy`, `expansion_boundary_checker`, `violation_triage` partial) | OPA/Rego, Conftest | Policy-as-code is mature; only the *rule content* is bespoke. |
| External SaaS integrators (`notion_integrator`, `linear_integrator`) | Official Notion / Linear SDKs | Already thin wrappers; upstream SDKs reduce maintenance. |
| Version-bump recommendation (`version_bump_guard`, `governance_version_check`, `framework_versioning`) | commitlint + semantic-release, conventional-commits tooling | Note: this is the very tool whose *logic* bug we are studying — replacing it would still need the outgoing-ref behavior specified and tested. |

## B. Partial — external tool covers the mechanism, not the semantics

| Category | What external tools give | What stays in-house |
|---|---|---|
| Drift/freshness (`governance_drift_checker`, `doc_drift_checker`, `*_drift`) | file hashing, diffing, staleness detection | which artifacts are authoritative and what "drift" means for governance |
| Reviewer/release snapshots (`reviewer_handoff_*`, `release_*`, `trust_signal_snapshot`) | data collection, templating | the trust model and claim ceilings being summarized |
| Onboarding/adoption (`adopt_governance`, `onboard_*`, `external_repo_*`) | scaffolding, git plumbing | the governance contract being installed |

## C. Not replaceable — bespoke governance semantics no off-the-shelf tool models

These encode domain-specific concepts unique to this framework; an external tool
would have to re-implement the concept, not the mechanism:

- **Receipt↔output-commit binding + clean-worktree admissibility** (the exact
  discipline this whole session kept hitting). No linter models "this receipt
  must be anchored to the commit it validated."
- **Canonical memory authority + non-canonical-writer guard**
  (`memory_authority_guard`, `memory_workflow`, `memory_janitor`, the
  `governance_tools.memory_record` writer).
- **Session closeout provenance** (`session_end_hook`, `manage_agent_closeout`,
  `closeout_audit`, `session_closeout_entry`).
- **Gate promotion / oversight semantics** (`gate_policy` promotion side,
  `escalation_authority_writer`, `change_control_summary`).
- **The four-arm experiment scoring / claim-evidence checklist**
  (`skill_ab_scorer`, `round_a_evaluator`, `test_signal_quality_audit`).

## D. The Skill Library specifically

The Skill Library's *behavior guidance* (recipes that tell an agent how to do a
task) is not the same layer as a validator. Per the program's four-layer
boundary, a Skill "tells the agent how" while an External Validator "provides an
independent check signal." So:

- The **validator/oracle** role inside or alongside a Skill is a strong replace
  candidate (Section A: schema, lint, diff, mutation).
- The **method-guidance** role (the recipe text itself) is not a linter and has
  no external drop-in; it is content, not tooling. Replacing it means writing
  better guidance, not adopting a tool.

This is exactly the split the Bug Fix experiment's `C−B` (governance/evidence
treatment) vs `D−C` (external validator treatment) is built to measure. The
inventory says *where* external tools plausibly help; the experiment is how we'd
show they actually do.

## E. Suggested decision path (not executed)

1. Start with Section A's largest, lowest-risk cluster — schema/envelope
   validation — as a candidate consolidation onto one external validator.
2. Require the same evidence discipline for any swap: a regression showing the
   external tool catches what the in-house tool caught, before removing anything.
3. Keep Section C in-house; do not attempt to externalize governance semantics.
4. Treat every swap as its own slice with its own review; do not bulk-delete.

## Cannot claim

- That any specific file is a confirmed drop-in replacement (name/category triage
  only; per-tool confirmation requires reading each contract).
- That external tools improve correctness on logic bugs (the session's data point
  says they do not for this defect class).
- That replacing anything is approved; this is decision input, not a decision.
