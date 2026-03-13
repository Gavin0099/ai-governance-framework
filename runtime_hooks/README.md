# Runtime Hooks

This directory contains the runtime governance layer.

Core hooks:

- `core/pre_task_check.py`
- `core/post_task_check.py`
- `core/session_end.py`

Adapters:

- `adapters/claude_code/pre_task.py`
- `adapters/claude_code/post_task.py`
- `adapters/claude_code/normalize_event.py`
- `adapters/codex/pre_task.py`
- `adapters/codex/post_task.py`
- `adapters/codex/normalize_event.py`
- `adapters/gemini/pre_task.py`
- `adapters/gemini/post_task.py`
- `adapters/gemini/normalize_event.py`

Design rule:

- Keep tool-specific event mapping in adapters.
- Keep governance decisions in `core/`.
- Keep adapter behavior aligned with `ADAPTER_CONTRACT.md`.

Shared payload contract:

- `event_contract.md`
- `event_schema.json`

Normalization flow:

- native harness payload
- `adapters/<harness>/normalize_event.py`
- shared event shape
- `core/pre_task_check.py` or `core/post_task_check.py`

Active rule injection:

- `pre_task_check.py` now returns both rule-pack selection metadata and loaded active rule content
- active rules are loaded from `governance/rules/<pack>/*.md`
- runtime consumers should treat this payload as governance context, not as a general-purpose rule DSL
- current seed packs include `common`, `python`, `cpp`, `refactor`, `csharp`, `swift`, `avalonia`, `kernel-driver`
- pack categories distinguish `scope`, `language`, `framework`, and `platform`

Test-result handoff:

- `governance_tools/test_result_ingestor.py` converts runner output into normalized `checks`
- recommended flow: test runner output -> `test_result_ingestor.py` -> runtime `checks.errors / checks.warnings / checks.summary`
- supported evidence kinds now include `pytest-text`, `junit-xml`, `sdv-text`, `msbuild-warning-text`, and `sarif`

Public API handoff:

- `governance_tools/public_api_diff_checker.py` can be passed into `post_task_check.py` with `--api-before` and `--api-after`
- this is currently used as a lightweight interface-stability signal for `refactor` tasks

Kernel-driver evidence handoff:

- `governance_tools/driver_evidence_validator.py` is applied by `post_task_check.py` when `RULES` contains `kernel-driver`
- preferred evidence sources are external analysis and compiler diagnostics such as SDV / SAL / WDK outputs, merged into normalized `checks`

Dispatcher:

- `dispatcher.py` routes a shared event JSON payload directly to `pre_task_check` or `post_task_check`
- `smoke_test.py` runs documented native example payloads end-to-end
- `../scripts/run-runtime-governance.sh` is the shared enforcement entrypoint for hooks and CI

Session close:

- `core/session_end.py` closes a session into runtime audit artifacts
- emits `artifacts/runtime/candidates/<session_id>.json`
- emits `artifacts/runtime/summaries/<session_id>.json`
- creates candidate memory snapshots and applies conservative promotion policy

Examples:

- `examples/claude_code/*.native.json`
- `examples/codex/*.native.json`
- `examples/gemini/*.native.json`
- `examples/shared/*.shared.json`

Enforcement:

- local `pre-push` runs `scripts/run-runtime-governance.sh --mode enforce`
- CI runs the same script with `--mode ci`
- this keeps smoke coverage and focused runtime tests on the same execution path
