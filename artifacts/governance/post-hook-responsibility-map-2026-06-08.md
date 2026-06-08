# Post-Hook / Session-End Responsibility Map - 2026-06-08

## Scope

Read-only responsibility map for the largest post-hook and session-end files.

This artifact documents refactor candidates only. It does not move code, change
hook behavior, change validators, change schemas, change runtime behavior, or
claim token reduction.

## Current Size Snapshot

| File | Lines | Role | Risk |
| --- | ---: | --- | --- |
| `governance_tools/session_end_hook.py` | 1908 | session-end closeout, gate, audit, memory, token, and formatting orchestration | high |
| `runtime_hooks/core/session_end.py` | 1202 | runtime session-end wrapper and packet emission | high |
| `runtime_hooks/core/post_task_check.py` | 969 | post-task validation, domain policy, evidence, and formatting checks | high |
| `governance_tools/session_closeout_entry.py` | 401 | closeout entry helper | medium |

## Responsibility Map

### `governance_tools/session_end_hook.py`

Current responsibilities:

- closeout file presence and field parsing;
- closeout schema and content checks;
- evidence and tool-reference checks;
- readiness / activation state detection;
- memory tier and runtime contract construction;
- canonical path audit;
- canonical audit log append and trend computation;
- E1b observation synthesis;
- closeout tier evaluation;
- transcript ingestion for CodeBurn closeout binding;
- canonical usage audit;
- memory authority surface collection;
- gate policy evaluation and gate verdict derivation;
- human result formatting;
- CLI entrypoint.

Extraction candidates:

| Candidate module | Extracts | Risk | Do now? |
| --- | --- | --- | --- |
| `governance_tools/closeout_schema.py` | `_parse_fields`, `_check_schema`, `_check_content`, closeout candidate building | medium | no |
| `governance_tools/closeout_evidence.py` | evidence/tool-reference checks and failure signals | high | no |
| `governance_tools/canonical_path_audit.py` | canonical path audit, audit log append, trend computation | high | no |
| `governance_tools/memory_authority_surface.py` | memory authority guard collection surface | medium | no |
| `governance_tools/codeburn_closeout_bridge.py` | transcript ingest and CodeBurn token binding | medium-high | no |
| `governance_tools/session_end_format.py` | gate verdict labels and human output rendering | medium | no |

### `runtime_hooks/core/post_task_check.py`

Current responsibilities:

- runtime check merge;
- refactor evidence checks;
- public API diff schema and checks;
- failure completeness checks;
- driver evidence checks;
- runtime evidence classification;
- domain policy input classification;
- missing required evidence classification;
- provenance boundary audit;
- candidate violation promotion and consumption contracts;
- consumption pattern visibility;
- domain contract slimming;
- domain validator result merge;
- post-task result orchestration;
- advisory violation rendering;
- human result formatting;
- CLI entrypoint.

Extraction candidates:

| Candidate module | Extracts | Risk | Do now? |
| --- | --- | --- | --- |
| `runtime_hooks/core/post_task_public_api.py` | public API diff schema and merge checks | medium | no |
| `runtime_hooks/core/post_task_domain_policy.py` | domain policy input and missing evidence classification | high | no |
| `runtime_hooks/core/post_task_failure_completeness.py` | failure completeness and runtime evidence checks | medium | no |
| `runtime_hooks/core/post_task_candidate_violation.py` | promotion / consumption contract synthesis | high | no |
| `runtime_hooks/core/post_task_format.py` | advisory violation and human result formatting | medium | no |

## Must-Test Surface If Extraction Is Later Approved

Any future extraction must be behavior-preserving and must include focused tests
before commit.

Minimum tests:

- existing focused tests for `session_end_hook.py` and closeout receipt behavior;
- existing focused tests for `post_task_check.py`;
- fixture or golden-output comparison for human output if formatter code moves;
- `git diff --check` on moved files;
- no broad hook output wording change unless explicitly scoped.

Do not combine extraction with:

- threshold changes;
- hook output behavior changes;
- token optimization;
- MRS / router audit implementation;
- validator or schema changes;
- CodeBurn ingestion changes.

## Recommendation

Do not refactor now.

Reason:

- line count and multi-responsibility risk are real;
- current evidence shows maintainability risk, not runtime failure;
- no CodeBurn before/after baseline proves token impact;
- extraction would touch high-risk hook and closeout surfaces.

Safe next trigger:

- repeated bug in one responsibility area;
- repeated test fragility tied to one responsibility area;
- reviewer-approved behavior-preserving extraction slice;
- CodeBurn / hook-output observation showing a specific output surface causes
  material token/noise cost.

## Claim Ceiling

CLAIMED:

- current post-hook/session-end responsibility map;
- extraction candidate list;
- risk and must-test boundaries;
- recommendation to defer behavior-preserving extraction until an observed
  failure or reviewer-approved slice exists.

NOT CLAIMED:

- code was refactored;
- behavior changed;
- hook output changed;
- token usage reduced;
- validators changed;
- schemas changed;
- runtime behavior changed;
- CodeBurn ingestion changed;
- MRS / router audit / high-risk checker exists.
