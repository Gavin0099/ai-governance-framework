# Knowledge Base

## Runtime Governance Maturity Snapshot

- The repository now operates as an AI Coding Runtime Governance Framework with a full runtime spine:
  `session_start -> pre_task_check -> post_task_check -> session_end -> memory pipeline`.
- Multi-harness runtime support exists for Claude Code, Codex, and Gemini through native payload normalization, shared events, adapters, and dispatcher routing.
- Rule-pack governance is no longer limited to language packs; it now includes scope, language, framework, platform, and custom categories.
- Proposal-time governance is active. `architecture_impact_estimator.py` and `change_proposal_builder.py` produce structured previews before implementation begins.
- Reviewable change-control artifacts are now part of the governance surface via startup handoff notes, JSON envelopes, `change_control_summary.py`, and `change_control_index.py`.

## Evidence And Enforcement

- Evidence ingestion currently supports `pytest-text`, `junit-xml`, `sdv-text`, `msbuild-warning-text`, `sarif`, and `wdk-analysis-text`.
- Evidence is not only collected; it already feeds runtime decisions through:
  - `failure_completeness_validator.py`
  - `refactor_evidence_validator.py`
  - `public_api_diff_checker.py`
  - `driver_evidence_validator.py`
  - `architecture_drift_checker.py`
- Current enforcement is evidence-aware and boundary-aware, but it is not yet full semantic governance.

## Boundary To Protect

- Packs provide governance context.
- Skills provide behavior guidance.
- Runtime checks and policies make decisions.
- Suggestions remain advisory and must not silently mutate the active contract.
- The repository should continue to act as a governance framework, not become a generic AI orchestration OS.

