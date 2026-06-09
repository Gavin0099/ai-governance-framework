# Artifact Write-Path Inventory - 2026-06-09

Status: inventory only

## Purpose

This inventory records currently observed artifact write paths that can affect
runtime noise, dirty workspace state, reviewer-facing evidence, or historical
claim-enforcement debt.

This slice does not move files, delete files, change hooks, change validators,
change schemas, change thresholds, or change enforcement behavior.

## Inventory

| Write path | Writer / source | Trigger | Current routing | Evidence role | Proposed classification | Caveat |
| --- | --- | --- | --- | --- | --- | --- |
| `artifacts/runtime/candidates/<session_id>.json` | `runtime_hooks/core/session_end.py` | session end candidate closeout | `artifacts/runtime/` is gitignored | runtime closeout candidate | runtime local side effect | Candidate evidence is not a promoted reviewer artifact by default. |
| `artifacts/runtime/curated/<session_id>.json` | `runtime_hooks/core/session_end.py` | session end closeout promotion path | `artifacts/runtime/` is gitignored | curated runtime closeout | runtime local side effect unless explicitly promoted | Promotion semantics are separate from git tracking. |
| `artifacts/runtime/summaries/<session_id>.json` | `runtime_hooks/core/session_end.py` | session end summary emission | `artifacts/runtime/` is gitignored | runtime summary | runtime local side effect | Useful for local diagnosis, but should not dirty tracked state. |
| `artifacts/runtime/verdicts/<session_id>.json` | `runtime_hooks/core/session_end.py` / session-end hook | session end verdict emission | `artifacts/runtime/` is gitignored | runtime verdict | runtime local side effect | Runtime completeness audits read this path. |
| `artifacts/runtime/traces/<session_id>.json` | `runtime_hooks/core/session_end.py` / pre-task/post-task surfaces | runtime trace emission | `artifacts/runtime/` is gitignored | runtime trace | runtime local side effect | High-volume path; compression policy can be considered later. |
| `artifacts/runtime/runtime_phase_summary.json` | `runtime_hooks/core/session_end.py` | session end phase classification | `artifacts/runtime/` is gitignored | runtime phase summary | runtime local side effect | Not a reviewer-facing stable artifact unless separately promoted. |
| `artifacts/runtime/canonical-audit-log.jsonl` | `governance_tools/session_end_hook.py` | session-end canonical path audit | `artifacts/runtime/` is gitignored | advisory observability ledger | runtime local side effect | Append-only observation substrate, not authority of truth. |
| `artifacts/runtime/incident-log.ndjson` | `governance_tools/runtime_reliability_observation.py` | runtime reliability observation | `artifacts/runtime/` is gitignored | incident observation | runtime local side effect | Safe append failure is non-blocking. |
| `artifacts/runtime/recovery-log.ndjson` | `governance_tools/runtime_reliability_observation.py` | runtime recovery observation | `artifacts/runtime/` is gitignored | recovery observation | runtime local side effect | Same routing as incident log. |
| `artifacts/runtime/side-effect-journal.ndjson` | `governance_tools/runtime_reliability_observation.py` | runtime side-effect observation | `artifacts/runtime/` is gitignored | side-effect observation | runtime local side effect | Relevant to future dirty-state isolation policy. |
| `artifacts/runtime/determinism-boundary-log.ndjson` | `governance_tools/runtime_reliability_observation.py` | determinism boundary observation | `artifacts/runtime/` is gitignored | determinism observation | runtime local side effect | Observation-only. |
| `artifacts/runtime/closeout-receipts/<id>.json` | `governance_tools/session_closeout_entry.py` | explicit closeout entry command | `artifacts/runtime/` is gitignored | closeout receipt | runtime local side effect unless explicitly promoted | Closeout receipt proves evidence-chain shape, not framework correctness. |
| `artifacts/runtime/trigger-evidence.jsonl` | `governance_tools/session_closeout_entry.py` | closeout trigger evidence append | `artifacts/runtime/` is gitignored | closeout trigger evidence | runtime local side effect | Append-only; not automatically promoted. |
| `artifacts/runtime/smoke/*` | `scripts/run-runtime-governance.sh` | runtime governance smoke | `artifacts/runtime/` is gitignored | smoke output | runtime local side effect | CI may upload this directory as external artifact. |
| `artifacts/session/claim-enforcement/<session_id>/claim-enforcement-check.json` | `runtime_hooks/core/session_end.py` | claim-enforcement raw packet emission | `artifacts/session/` is gitignored | raw claim-enforcement packet | runtime local side effect | CE-1D.2 moved new raw packets here to avoid polluting repo-facing claim-enforcement root. |
| `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` | `governance_tools/claim_enforcement_receipt_writer.py` | compact receipt append | tracked file | compact receipt ledger | ambiguous tracked runtime ledger | Policy says repo-facing compact evidence index is tracked only on manual promotion/review, not every runtime run. Current runtime can still dirty it. |
| `artifacts/claim-enforcement/session-*` | historical claim-enforcement writers / legacy packets | legacy raw packet output | timestamp-shaped dirs are gitignored; historical tracked dirs still exist | legacy raw packets | historical legacy debt | CE-1D advisory disposition retained these in place; no migration or cleanup in this slice. |
| `artifacts/claim-enforcement/<uuid-or-other>/claim-enforcement-check.json` | historical / dirty raw packet sources | legacy or orphan raw packet output | not covered by timestamp-shaped ignore pattern | legacy or orphan raw packet | historical or current dirty debt | Requires separate CE-1D disposition or dirty-work audit before movement/deletion/staging. |
| `artifacts/session-index.ndjson` | `runtime_hooks/core/session_end.py` | session end append | tracked file | session summary ledger | ambiguous tracked runtime ledger | Current policy has not decided whether this remains tracked evidence or moves to local runtime state. |
| `artifacts/governance/*.md` / `*.json` | manual governance slices | explicit evidence capture | tracked when staged | reviewer-facing governance evidence | promoted reviewer artifact | Should only be written by scoped evidence-capture work, not ordinary hook execution. |
| `artifacts/release-package/**` | `governance_tools/release_package_snapshot.py` | release package snapshot command | tracked when staged | release/reviewer evidence | promoted reviewer artifact | Valid only when release/package snapshot is the approved slice. |
| `artifacts/trust-signals/**` | `governance_tools/trust_signal_snapshot.py` | trust signal snapshot command | tracked when staged | trust signal evidence | promoted reviewer artifact | Not an ordinary runtime hook output. |
| `artifacts/reviewer-handoff/**` | `governance_tools/reviewer_handoff_snapshot.py` | reviewer handoff snapshot command | tracked when staged | reviewer handoff evidence | promoted reviewer artifact | Should remain explicit and scoped. |
| `docs/payload-audit/<session_type>-<YYYY-MM-DD>.jsonl` | `runtime_hooks/core/payload_audit_logger.py` | payload audit logging | docs path, not runtime artifact path | payload audit observation | ambiguous reviewer/runtime ledger | Outside `artifacts/`; future policy should decide whether this is reviewer-facing evidence or runtime local state. |
| `artifacts/codeburn*.db` and smoke DB files | CodeBurn tests / ingestors | token and closeout ingestion tests | tracked/untracked mix depends on file | token observation / test DB | ambiguous historical/test artifact | Not changed in this slice; future CodeBurn cleanup should separate fixture DBs from runtime DBs. |

## Current Boundary

Observed routing is already partly separated:

- `artifacts/runtime/**` is ignored and should remain the default local-runtime
  destination for ordinary hook, smoke, trace, verdict, and closeout side effects.
- `artifacts/session/**` is ignored and is the canonical runtime destination for
  new raw claim-enforcement packets after CE-1D.2.
- `artifacts/governance/**`, `artifacts/release-package/**`,
  `artifacts/trust-signals/**`, and `artifacts/reviewer-handoff/**` are
  reviewer-facing only when produced by an explicit approved slice.
- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` and
  `artifacts/session-index.ndjson` are the main ambiguous tracked ledgers because
  runtime/session-end paths can append to them.

## Recommended Next Decision

The next runtime dirty-isolation policy should decide the status of the two
ambiguous tracked ledgers:

1. Keep them tracked, but require manual promotion/review before staging.
2. Move ordinary runtime appends to an ignored local path and generate a compact
   reviewer-facing snapshot only on explicit evidence capture.
3. Keep current paths but add hook/output guidance that ordinary runs must not
   claim a clean workspace until these ledgers are restored, staged, or explicitly
   included in scope.

No option is selected by this inventory.

## Claim Ceiling

CLAIMED:

- Artifact write paths were inventoried from current code and documentation.
- Paths were classified as runtime local side effect, promoted reviewer artifact,
  historical legacy debt, or ambiguous tracked runtime ledger.
- The highest-risk dirty-state candidates are identified as
  `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` and
  `artifacts/session-index.ndjson`.

NOT CLAIMED:

- runtime artifact routing changed;
- hook behavior changed;
- validator behavior changed;
- schema changed;
- threshold or enforcement behavior changed;
- tracked ledgers fixed;
- historical CE-1D packets migrated, deleted, receipted, or cleaned;
- token usage reduced;
- #17 readiness changed.
