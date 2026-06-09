# Runtime Noise Baseline & Boundary - 2026-06-09

## Scope

Observation-only baseline for runtime hook output and local runtime dirty-state
noise.

This artifact does not change hook behavior, validators, schemas, threshold
behavior, runtime enforcement, CodeBurn ingestion, or #17 memory authority
behavior.

## Current Noise Sources

| source | observed noise | reviewer value | current boundary |
| --- | --- | --- | --- |
| `scripts/run-runtime-governance.sh` pre-push smoke | long repeated smoke output across `claude_code`, `codex`, `gemini`, and shared harnesses | useful as PASS/FAIL signal, low value when full logs repeat on every push | keep behavior unchanged; future compression needs baseline data |
| `runtime_hooks/core/session_start.py` | repeated contract/rules/suggested pack summaries | useful for startup routing, noisy when unchanged | print summary now; future candidate: changed/missing-only details |
| `runtime_hooks/core/pre_task_check.py` | advisory warnings can include repeated repo signals | useful when warning is new or actionable | future candidate: warning code/count first, detail via artifact |
| `runtime_hooks/core/post_task_check.py` | post-task summaries and snapshots | useful when task changed runtime evidence | prefer artifact references over inline detail |
| `runtime_hooks/core/session_end.py` | session close artifacts and candidate snapshots | useful for closeout, noisy if full packet content is echoed | keep artifact-first boundary |
| `governance_tools/session_end_hook.py` | broad gate, memory, CodeBurn, canonical path, and closeout human output | high reviewer value on failure; high token risk on repeated PASS | defer refactor/compression until measured |

## Dirty Artifact Baseline

These paths were observed as recurring local runtime dirty state during
read-only analysis, focused tests, and push-hook execution:

| path | observed trigger | proposed boundary |
| --- | --- | --- |
| `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson` | hook / query / push runtime receipt append | tracked evidence today, but behaves like local runtime ledger during ordinary runs; do not stage unless explicitly in scope |
| `artifacts/session-index.ndjson` | hook / query / push session index append | tracked operational ledger today; do not stage unless explicitly in scope |
| `.tmp-pytest/` | repo-local pytest `--basetemp` / cache output | local-only test temp; ignored as of #17 negative-path fixture slice |
| `artifacts/runtime/` | runtime smoke / hook output | local runtime artifacts; already ignored |
| `memory/candidates/*.json` | session close candidate snapshots | local candidate artifacts; already ignored |

## Tracked vs Local-Only Boundary

Tracked evidence should be intentionally promoted and reviewer-facing:

- scoped governance artifacts under `artifacts/governance/`;
- committed compact receipts or inventories when explicitly in DONE scope;
- PLAN and memory records written through the canonical memory writer;
- test fixtures and focused tests used as regression surface.

Local-only runtime noise should not be staged by default:

- runtime smoke outputs;
- session candidate snapshots;
- session indexes created by hook execution;
- receipt ledger appends caused by ordinary hook/query runs;
- pytest temp/cache directories.

## Token-Sensitive Sections

The highest token-risk surfaces are:

1. repeated full runtime-governance smoke output on push;
2. repeated `suggested_rules_preview`, validator, and contract summaries when
   unchanged;
3. full warning detail inline when warning count/code would be enough;
4. full JSON-like artifacts copied into chat instead of referenced by path.

## Compression Candidate Boundary

Future hook-output compression should be considered only after comparable
CodeBurn observations exist.

Candidate output shape:

```text
Hook result: PASS | WARN | FAIL
Harnesses: <passed>/<total>
Warnings: <count> [top codes]
Artifacts: <path>
Required action: <one line | none>
```

Do not implement this shape without a separate scoped slice and focused tests.

## Immediate Handling Rule

Until runtime artifact routing is changed, agents should treat recurring
runtime dirty files as local execution noise unless the user explicitly scopes
them into the task.

Recommended response when they appear:

```text
Workspace state: NOT CLEAN due to runtime ledger noise.
Dirty files:
- artifacts/claim-enforcement/claim-enforcement-receipts.ndjson
- artifacts/session-index.ndjson
Action: restore these files unless the current DONE explicitly includes runtime ledger promotion.
```

## Claim Ceiling

CLAIMED:

- runtime hook output noise inventory;
- recurring runtime dirty artifact baseline;
- tracked vs local-only boundary proposal;
- token-sensitive output sections identified;
- future compression trigger boundary.

NOT CLAIMED:

- token reduction;
- hook output behavior change;
- runtime artifact routing change;
- validator, schema, threshold, or enforcement change;
- CodeBurn before/after evidence;
- #17 blocking readiness.
