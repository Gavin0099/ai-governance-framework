# Governance Document Freshness Classification Audit - 2026-06-25

Status:

```text
docs-only
classification-audit
no behavior change
no governance_tools change
no hook change
no validator change
no enforcement change
```

## Problem

The `governance/` directory contains executable configuration, live authority
routing inputs, agent-facing contracts, reviewer reference material, and
historical design records. Several files are old or have stale headers, but
age alone is not enough to decide whether a file is wrong, active, or safe to
ignore.

The failure risk is two-sided:

- treating old reference material as active runtime authority; or
- treating active consumed documents as harmless stale prose.

This audit classifies governance documents by consumption path and stale-risk
so follow-up repair can be prioritized without rewriting high-blast-radius
governance surfaces blindly.

## Current repository truth

Evidence read for this audit:

- `governance/REVIEW_CRITERIA.md`, because this is a review/audit task.
- `PLAN.md`, the current planning authority.
- `AGENTS.md`, which defines conditional governance routers.
- `governance/AUTHORITY.md`, the registered authority table.
- `governance/AGENT.md`, `governance/SYSTEM_PROMPT.md`,
  `governance/HUMAN-OVERSIGHT.md`, `governance/NATIVE-INTEROP.md`,
  `governance/MEMORY_AUTHORITY_CONTRACT.md`, `governance/PLAN.md`,
  `governance/RULE_REGISTRY.md`, `governance/TESTING.md`,
  `governance/ARCHITECTURE.md`, and `governance/gate_policy.yaml`.
- `runtime_hooks/core/session_start.py`.
- `governance_tools/authority_loader.py`.
- `governance_tools/gate_policy.py`,
  `governance_tools/rule_classifier.py`,
  `governance_tools/memory_authority_guard.py`.
- `git ls-files governance/*.md` plus last-touch metadata for the tracked
  governance markdown set.
- Search evidence across `governance_tools/`, `runtime_hooks/`, `tests/`,
  `.github/`, `docs/`, `.agents/`, and `AGENTS.md` for consumption signals.

## Key correction: AUTHORITY default_load is live input

`governance/AUTHORITY.md` is not merely a stale registry.

`runtime_hooks/core/session_start.py` imports and calls:

```text
load_authority_table(governance_dir)
filter_for_session(authority_table, include_on_demand=...)
validate_session_payload(allowed_governance_files, authority_table)
```

The code comments state:

```text
L0 -> always-load only
L1/L2 -> always + on-demand
```

`governance_tools/authority_loader.py::filter_for_session()` appends any
non-human-only entry with `default_load == "always"` and, for L1/L2, appends
`default_load == "on-demand"` entries.

Important boundary:

```text
Observed: AUTHORITY default_load drives allowed_governance_files and the L0
forbidden-load guard/audit surface.

Not observed: session_start directly injects the full text of those documents
into the agent prompt. The observed behavior is allowlist/gate/audit-list
construction, not proven content injection.
```

This changes the risk model. A stale `default_load: always` row can be an
active allowlist error even if no full document text is injected.

## Consumption path categories

Use these categories for classification:

- `AGENTS router`: root `AGENTS.md` conditionally instructs agents to read the
  document for a task class.
- `session_start authority-tier`: `runtime_hooks/core/session_start.py` consumes
  the document's `default_load` tier via `authority_loader`.
- `governance_tools direct read`: a tool opens, parses, validates, or cites the
  document directly.
- `tests`: tests assert the document exists, is routed, or has particular
  behavior.
- `CI/hook`: hook or CI behavior depends on the document or tool that reads it.
- `AUTHORITY registration`: the file is listed in `governance/AUTHORITY.md`.
- `reference-only`: cited by docs or humans, but no direct runtime/tool
  consumption was found in this audit.
- `historical`: decision, closeout, or draft record whose main value is
  historical trace, not current instruction.

## Status categories

- `current-authority`: active and aligned with current workflow.
- `current-but-readable-stale`: still broadly valid, but header, wording, or
  encoding/readability is stale.
- `stale-active-risk`: stale or misleading content is consumed by an active
  tool/router/allowlist path.
- `old-but-current`: old file with stable semantics and no identified
  contradiction.
- `historical-draft`: old design/draft material that should not be used as
  current authority.
- `executable-config`: consumed as configuration or registry; do not clean up
  by age alone.
- `reference-cluster`: useful reference set; freshness should be assessed as a
  cluster before rewriting.

## Priority summary

### P0 - active allowlist / authority-tier risk

| File | Last changed | Consumption | Status | Finding |
|---|---:|---|---|---|
| `governance/AUTHORITY.md` | 2026-06-24 | `session_start authority-tier`, `AUTHORITY registration`, tests | `stale-active-risk` | Header says `updated: 2026-03-23` despite later edits; rows classify `SYSTEM_PROMPT.md`, `AGENT.md`, and `governance/PLAN.md` as `agent-runtime` / `canonical` / `always`; this drives `allowed_governance_files`, so row errors are live allowlist errors, not only prose drift. |
| `governance/PLAN.md` | 2026-04-09 | `session_start authority-tier`, `AUTHORITY registration` | `stale-active-risk` | File is a meta-template about how root `PLAN.md` should be structured, but it is registered as an always-loaded canonical runtime document. This risks confusing the actual root `PLAN.md` planning authority with a template/reference document. |

Recommended first repair:

```text
Design an AUTHORITY tier correction slice that updates header freshness and
reclassifies governance/PLAN.md before changing any prompt-like content.
```

Do not directly rewrite `SYSTEM_PROMPT.md` or `AGENT.md` in the same slice.

### P1 - consumed and stale, needs targeted review before edit

| File | Last changed | Consumption | Status | Finding |
|---|---:|---|---|---|
| `governance/SYSTEM_PROMPT.md` | 2026-04-20 | `session_start authority-tier`, `AUTHORITY registration`, tests/adoption docs | `current-but-readable-stale` pending deeper content review | Contains old mandatory initialization, dynamic loading declaration, and governance contract output language. Because it is in the always tier, it is an active allowlist exposure. This audit did not prove full text injection, so do not claim prompt pollution; classify as stale allowlist exposure plus stale instruction risk. |
| `governance/AGENT.md` | 2026-05-29 | `session_start authority-tier`, `AUTHORITY registration`, tests/adoption docs | `current-but-readable-stale` | Still defines repo engineering governance and L0/L1/L2 posture. It is not simply superseded by root `AGENTS.md`; root `AGENTS.md` explicitly delegates repo engineering governance to `governance/`. Risk is overlapping or stale ceremony wording, not total replacement. |
| `governance/HUMAN-OVERSIGHT.md` | 2026-04-08 | `AUTHORITY registration`, adoption/auditor/task-level references | `current-but-readable-stale` pending content review | Old and highly referenced. Prior core audit missed it. Needs content review before deciding whether it is stale-active-risk or old-but-current. |
| `governance/MEMORY_AUTHORITY_CONTRACT.md` | 2026-04-30 | `governance_tools.memory_authority_guard` contract reference, tests | `stale-active-risk` | Describes old bullet-style daily memory (`- what changed:`, `commit hash:`). Current canonical writer emits structured fields (`memory_type`, `writer`, `commit`, `commit_hash`, `memory_binding`, etc.) and legitimate runtime observations can be unbound with sentinel commit text. Human-facing contract is stale relative to current writer/guard semantics. |
| `governance/NATIVE-INTEROP.md` | 2026-04-08 | `AUTHORITY registration`, adoption/docs/tests references | `current-but-readable-stale` pending content review | Old but consumed as a native-safety reference. No contradiction was proven in this audit; do not rewrite by age alone. |
| `governance/ARCHITECTURE.md` | 2026-04-08 | `AUTHORITY registration`, tests/adoption/docs references | `current-but-readable-stale` | Readability/encoding is stale, but broad boundary guidance remains plausibly useful. Needs targeted readability refresh, not semantic overhaul. |
| `governance/TESTING.md` | 2026-04-10 | `AUTHORITY registration`, tests/adoption/docs references | `current-but-readable-stale` | Readability/encoding is stale, but core testing discipline remains broadly aligned. Needs targeted readability refresh and modern memory/runtime examples later. |
| `governance/REVIEW_CRITERIA.md` | 2026-05-29 | `AGENTS router`, `AUTHORITY registration`, tests/docs references | `current-but-readable-stale` | Active review router target. Content has mojibake/readability issues. Semantics broadly match current skeptical review discipline, but should be refreshed before broad reviewer-facing use. |

### P1 - current active protocols, not stale by age

| File | Last changed | Consumption | Status | Finding |
|---|---:|---|---|---|
| `governance/MEMORY_PROTOCOL.md` | 2026-06-10 | `AGENTS router`, memory workflow docs/tool references | `current-authority` | Current canonical memory writer and workflow dispatcher contract. No freshness issue identified. |
| `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` | 2026-06-08 | `AGENTS router` | `current-authority` | Extracted router target and still aligned with governed update posture. |
| `governance/F7_FULL_UPDATE.md` | 2026-06-11 | `AGENTS router` | `current-authority` | Current F-7 reporting/stage contract. |
| `governance/GOVERNANCE_SURFACE_RULES.md` | 2026-06-08 | `AGENTS router` | `current-authority` | Current conditional router target for governance-sensitive files. |
| `governance/RESPONSE_ENVELOPE_CONTRACT.md` | 2026-06-24 | `AGENTS router`, `AUTHORITY registration`, tests/docs references | `current-authority` | Recently updated for glossing and next-step judgment. No freshness issue identified. |

### P1 - executable config / registry, do not clean by age alone

| File | Last changed | Consumption | Status | Finding |
|---|---:|---|---|---|
| `governance/gate_policy.yaml` | 2026-04-14 | `governance_tools.gate_policy`, session_end hook, tests | `executable-config` | Old but live. Contains fields still consumed by tools (`fail_mode`, `blocking_actions`, `skip_test_result_check`, `hook_coverage_tier`, `canonical_audit_trend`). Do not edit just because old. |
| `governance/RULE_REGISTRY.md` | 2026-04-08 | `governance_tools.rule_classifier`, tests/adoption docs | `executable-config` | Old but live registry. Readability may be stale, but rule pack names are machine-read. Any change affects classification and tests. |

## Cluster classification

### `governance/rules/**`

Last changed: mostly `2026-04-09`.

Consumption:

- rule pack files are part of the registry/rule-pack surface;
- some individual files have few direct textual references, but they should be
  treated as a cluster because rule selection is registry-driven.

Status:

```text
reference-cluster / executable-rule-pack-cluster
```

Finding:

```text
Do not list every old rule file as a stale defect. Treat governance/rules/**
as a rule-pack cluster. Refresh only when a rule pack is actively used in a
consuming repo and a concrete contradiction or readability failure is observed.
```

Representative files:

- `governance/rules/common/core.md`
- `governance/rules/python/coding.md`
- `governance/rules/refactor/*.md`
- `governance/rules/cpp/build_boundary.md`
- `governance/rules/csharp/*.md`
- `governance/rules/kernel-driver/*.md`
- `governance/rules/avalonia/*.md`
- `governance/rules/swift/*.md`
- `governance/rules/gl-hub-vendor-cmd/spec-truth.md`

### Semantic / interpretability docs

Files:

- `governance/EPISTEMIC_BASE_ASSUMPTIONS.md`
- `governance/METRIC_INTERPRETABILITY_CONTRACT.md`
- `governance/NULL_ONTOLOGY.md`
- `governance/SEMANTIC_FAILURE_MODES.md`
- `governance/SEMANTIC_FAILURE_TAXONOMY.md`
- `governance/CONFIDENCE_SEMANTICS_FREEZE.md`

Status:

```text
reference-cluster
```

Finding:

```text
These files encode semantic and interpretability boundaries. Some are
referenced by docs/tests, but they were not shown to drive live hooks or
session_start tiering. Do not rewrite them as part of the AUTHORITY freshness
repair. Reassess as a separate semantic-doc pass if a concrete contradiction is
found.
```

### Structural promotion docs

Files:

- `governance/STRUCTURAL_PROMOTION_CONTRACT.md`
- `governance/STRUCTURAL_PROMOTION_COVERAGE_CLOSEOUT_2026-04-30.md`
- `governance/STRUCTURAL_PROMOTION_DECISION_2026-04-30_CLAIM_DISCIPLINE_GUARDRAIL.md`
- `governance/STRUCTURAL_PROMOTION_DECISION_2026-04-30_CONVENTIONS.md`

Status:

```text
historical
```

Finding:

```text
These preserve promotion decisions and closeout context. Age is expected.
Do not refresh unless the structural-promotion process itself is reopened.
```

### Fleet docs

Files:

- `governance/fleet/agents_md_minimum_standard.md`
- `governance/fleet/evidence_tier_policy.md`
- `governance/fleet/external_repo_onboarding_sop.md`
- `governance/fleet/known_incidents.md`
- `governance/fleet/operational_semantics_v1.md`

Status:

```text
reference-cluster / current fleet reference
```

Finding:

```text
Fleet docs are older than the latest F-7 updater hygiene work, but this audit
did not prove contradiction. Do not rewrite them in the AUTHORITY repair slice.
If F-7 external rollout resumes, refresh fleet docs against the current managed
updater behavior as a separate slice.
```

### Review projection docs

Files:

- `governance/review_projection/projection-contract.md`

Status:

```text
historical-draft / reference-cluster
```

Finding:

```text
No live consumption was identified in this audit. Keep as historical/reference
unless review-projection tooling is resumed.
```

## Full tracked markdown inventory

| File | Last changed | Consumption summary | Classification |
|---|---:|---|---|
| `governance/AGENT.md` | 2026-05-29 | session_start tier; AUTHORITY; tests/docs | current-but-readable-stale |
| `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` | 2026-06-08 | AGENTS router | current-authority |
| `governance/ARCHITECTURE.md` | 2026-04-08 | AUTHORITY; tests/docs | current-but-readable-stale |
| `governance/AUTHORITY.md` | 2026-06-24 | session_start tier source; tests/docs | stale-active-risk |
| `governance/CLAIM_ENFORCEMENT_EVIDENCE_POLICY.md` | 2026-06-18 | docs/reference | old-but-current |
| `governance/CONFIDENCE_SEMANTICS_FREEZE.md` | 2026-05-16 | semantic reference | reference-cluster |
| `governance/EPISTEMIC_BASE_ASSUMPTIONS.md` | 2026-05-15 | semantic reference | reference-cluster |
| `governance/F7_FULL_UPDATE.md` | 2026-06-11 | AGENTS router | current-authority |
| `governance/GOVERNANCE_SURFACE_RULES.md` | 2026-06-08 | AGENTS router | current-authority |
| `governance/HUMAN-OVERSIGHT.md` | 2026-04-08 | AUTHORITY; adoption/auditor refs | current-but-readable-stale |
| `governance/MEMORY_AUTHORITY_CONTRACT.md` | 2026-04-30 | memory authority guard reference | stale-active-risk |
| `governance/MEMORY_PROTOCOL.md` | 2026-06-10 | AGENTS router; memory workflow | current-authority |
| `governance/METRIC_INTERPRETABILITY_CONTRACT.md` | 2026-05-15 | semantic reference | reference-cluster |
| `governance/NATIVE-INTEROP.md` | 2026-04-08 | AUTHORITY; tests/docs | current-but-readable-stale |
| `governance/NULL_ONTOLOGY.md` | 2026-05-15 | semantic reference | reference-cluster |
| `governance/PHASE_D_CLOSE_AUTHORITY.md` | 2026-05-11 | human-only authority; tools/docs refs | old-but-current |
| `governance/PLAN.md` | 2026-04-09 | session_start tier via AUTHORITY | stale-active-risk |
| `governance/RESPONSE_ENVELOPE_CONTRACT.md` | 2026-06-24 | AGENTS router; AUTHORITY; tests/docs | current-authority |
| `governance/REVIEW_CRITERIA.md` | 2026-05-29 | AGENTS router; AUTHORITY; review tasks | current-but-readable-stale |
| `governance/RULE_REGISTRY.md` | 2026-04-08 | rule_classifier; tests/docs | executable-config |
| `governance/SEMANTIC_FAILURE_MODES.md` | 2026-05-15 | semantic reference | reference-cluster |
| `governance/SEMANTIC_FAILURE_TAXONOMY.md` | 2026-05-15 | semantic reference; docs/tests refs | reference-cluster |
| `governance/STRUCTURAL_PROMOTION_CONTRACT.md` | 2026-04-30 | structural-promotion reference | historical |
| `governance/STRUCTURAL_PROMOTION_COVERAGE_CLOSEOUT_2026-04-30.md` | 2026-04-30 | closeout/history reference | historical |
| `governance/STRUCTURAL_PROMOTION_DECISION_2026-04-30_CLAIM_DISCIPLINE_GUARDRAIL.md` | 2026-04-30 | decision record | historical |
| `governance/STRUCTURAL_PROMOTION_DECISION_2026-04-30_CONVENTIONS.md` | 2026-04-30 | decision record | historical |
| `governance/SYSTEM_PROMPT.md` | 2026-04-20 | session_start tier; AUTHORITY; tests/docs | current-but-readable-stale |
| `governance/TESTING.md` | 2026-04-10 | AUTHORITY; tests/docs | current-but-readable-stale |
| `governance/copilot-instructions-template.md` | 2026-06-03 | adoption/template reference | old-but-current |
| `governance/fleet/agents_md_minimum_standard.md` | 2026-05-25 | fleet reference | reference-cluster |
| `governance/fleet/evidence_tier_policy.md` | 2026-05-25 | fleet reference | reference-cluster |
| `governance/fleet/external_repo_onboarding_sop.md` | 2026-06-13 | fleet onboarding reference | old-but-current |
| `governance/fleet/known_incidents.md` | 2026-05-28 | fleet incident reference | reference-cluster |
| `governance/fleet/operational_semantics_v1.md` | 2026-05-27 | fleet semantics reference | reference-cluster |
| `governance/review_projection/projection-contract.md` | 2026-05-11 | review projection reference | historical-draft |
| `governance/rules/avalonia/ui_thread.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/avalonia/viewmodel_boundary.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/common/core.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/cpp/build_boundary.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/csharp/native_boundary.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/csharp/threading.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/gl-hub-vendor-cmd/spec-truth.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/kernel-driver/cleanup-unwind.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/kernel-driver/irql.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/kernel-driver/memory-boundary.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/python/coding.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/refactor/behavior_lock.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/refactor/boundary_safety.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/refactor/error_path_coverage.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/refactor/interface_stability.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/refactor/no_partial_cleanup.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/refactor/required_regression_tests.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/swift/concurrency.md` | 2026-04-09 | rule-pack cluster | reference-cluster |
| `governance/rules/swift/native_interop.md` | 2026-04-09 | rule-pack cluster | reference-cluster |

## Recommended next tranche

Next tranche should be design-only or docs-only:

```text
Prepare a narrow AUTHORITY repair proposal that:
1. fixes AUTHORITY header freshness;
2. distinguishes AUTHORITY registration from session_start authority-tier
   consumption;
3. reclassifies governance/PLAN.md away from runtime always-load if verified
   safe;
4. does not rewrite SYSTEM_PROMPT.md, AGENT.md, HUMAN-OVERSIGHT.md, or
   MEMORY_AUTHORITY_CONTRACT.md in the same slice;
5. includes focused tests or review evidence if AUTHORITY table rows change
   session_start allowed_governance_files.
```

Do not bundle this with:

- memory contract rewrite;
- prompt-like document rewrite;
- rule pack refresh;
- fleet document refresh;
- semantic taxonomy refresh.

## Claim ceiling

This audit claims:

- which governance markdown files are tracked;
- which consumption paths were observed by static search and targeted source
  reads;
- that `session_start` consumes AUTHORITY tiers to build
  `allowed_governance_files`;
- that no full-content prompt injection from `session_start` was proven;
- that `AUTHORITY.md` and `governance/PLAN.md` are the highest-priority
  freshness risks because their tiering affects live session-start allowlist
  behavior.

This audit does not claim:

- any runtime behavior changed;
- any hook, validator, or enforcement changed;
- any stale document was repaired;
- any prompt-like document is currently injected into the agent prompt;
- every document's semantic content was fully reviewed;
- the classifications are permanent;
- old reference clusters are wrong merely because they are old.
