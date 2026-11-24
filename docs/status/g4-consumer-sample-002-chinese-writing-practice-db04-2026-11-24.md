# G4 Consumer Sample 002 — `chinese-writing-practice` `DB-04` Slice 1 (`PASS — Recovered via Session A -> B`)

- **Record Class**: Real Consumer Natural Work-Item Observation (**G4 Consumer Sample 002**, single work item spanning Session A + Session B)
- **Prior Sample Preserved**: `docs/status/g4-consumer-sample-001-english-vocab-trainer-issue375-2026-11-23.md` (`FAIL / NOT PERSISTED`) remains unchanged and is never overwritten by this sample.
- **Counting Discipline**: Session A and Session B belong to **one** natural work item (Sample 002). Session A's `PARTIAL / gate_blocked=True` outcome is preserved verbatim; this sample is recorded as **recovered via a follow-up session**, **not** first-pass success.
- **Date**: 2026-11-24
- **Archived Against Framework Main**: `0b5eb67f1268c62ac58cb2f81fc9c2c0f3bdb580`
- **Consumer Repository / Base**: `chinese-writing-practice` `origin/main@4d7a3f97e6b78ea2f8b326d22c37847cfc2c3007`
- **Consumer Adopted Governance Submodule**: `ai-governance-framework@1a30faedbaa8f4a4af14656b15797ccdbb6ed3fb`
- **Execution Environment**: Standalone git clone (`C:\Users\reiko\AppData\Local\Temp\cwp-g4-s1-db04\chinese-writing-practice`, branch `feat/db04-offline-queue-slice1`) + interactive `codex --no-daemon` (`codex-cli 0.171.0-alpha.13`) + independent read-only subagent review. Raw evidence backed up outside Temp to `E:\BackUp\Git_EE\_evidence_backup\g4-sample-002-cwp-db04-2026-11-24`.
- **Work Item**: `DB-04` Slice 1 — Pure JS offline family sync queue (`offlineQueue.mjs` + `tests/offline-queue.test.mjs`) with enqueue/dedupe, ordered retry/backoff flush, HTTP 409 / `PT409` / `40001` conflict draft preservation, and snapshot/restore validation.

---

## 1. Outcome Summary (Session A Preserved + Session B Recovery)

| Verification Dimension | Session A (`01a20b53-...`) | Session B (`01a20b81-...`) | Sample 002 Status |
|---|---|---|---|
| Product commits (local) | `805c226a5306ccfd915f93296e9c1b47a6d58968` (`offlineQueue.mjs`, `tests/offline-queue.test.mjs`, `+475`) | `a2a13dbb662e73b2fb0375961d283588fef2e9bd` (P2-1 `undefined` storage fix + 2 conflict tests, `+38/-1`) | **PASS (local; PR pending separately)** |
| Automated unit tests | `node --test tests/*.test.mjs` -> **81/81 PASS** (`643.7ms`) | `node --test tests/*.test.mjs` -> **84/84 PASS** (`753.5ms`) | **PASS** |
| Independent code review | Read-only subagent `151f68a6`: **0 P0 / 0 P1 / 2 P2 / 1 P3** | Read-only subagent `bb1e43b1`: **0 P0 / 0 P1 / 0 P2 / 0 P3** | **PASS (P2-2 explicitly deferred)** |
| Native `SessionStart` / `Stop` hooks | Auto-triggered; session identity matched | Auto-triggered; new session identity matched | **PASS** |
| R2 Ownership & Release | `generation=1`, `state=RELEASED` | `generation=2`, `state=RELEASED` | **PASS (natural A -> B handoff)** |
| Strict Gate (`hook_outcome`) | **`ok=False`, `gate_blocked=True`** (missing `artifacts/runtime/test-results/latest.json`) | **`ok=True`, `gate_blocked=False`, `errors=[]`** | **Recovered PASS (A's block preserved)** |
| Canonical daily memory | `memory/2026-11-24.md` via `governance_tools.memory_record` (`805c226`) | `memory/2026-11-24.md` via `governance_tools.memory_record` (`a2a13db`) | **PASS (both records preserved)** |

- **Explicit Open Product Scope (P2-2)**: Conflict resolution / reset API (`offlineQueue.mjs`) was intentionally **not** implemented in Slice 1 and remains **OPEN** for a subsequent `DB-04` slice alongside IndexedDB wiring and UI integration. Session B's `0 P2` delta review does not close P2-2.

---

## 2. Measurement Record (A + B Combined Accounting)

| Metric | Session A | Session B | Sample 002 Total (A + B) |
|---|---:|---:|---:|
| Wall-clock duration | `17m 02s` (`02:13:08Z`–`02:30:10Z`) | `36m 29s` (`03:03:03Z`–`03:39:33Z`) | **`53m 31s`** |
| Total tokens | `2,011,597` | `3,437,383` | **`5,448,980`** |
| Input tokens (cached) | `1,991,620` (`1,892,096` / 95.0%) | `3,420,862` (`3,308,544` / 96.7%) | **`5,412,482` (`5,200,640` / 95.4%)** |
| Uncached input / output tokens | `99,524` / `19,977` (reasoning `5,938`) | `112,318` / `16,521` (reasoning `3,986`) | **`211,842` / `36,498`** |
| One-time setup cost (separate) | Standalone clone + manual `SessionStart` hook addition + `/hooks` trust | None | **1x initial setup** |
| Human interventions | `/hooks` trust + sandbox approvals | Sandbox approvals | Multiple approvals; no mid-task rescue |
| True catches / gate blocks | Independent review caught P2-1 (`undefined` storage) & P2-2; `strict` gate correctly blocked missing `latest.json` | Independent verification confirmed 84/84 XML-to-JSON integrity | Governance enforcement worked as designed |

- **Cost Assessment**: Governance reliability (strict gate block, A->B ownership handoff, non-destructive history preservation, independent review) is demonstrated locally, **but cost efficiency is NOT yet demonstrated**. Session B's 38-line follow-up took longer and used 1.7x more tokens than Session A's 475-line implementation; no ungoverned baseline exists for direct comparison, and the exact share of Session B time attributable to JUnit XML adaptation cannot be isolated precisely.

---

## 3. Observed Framework / Tooling Findings (Evidence-Driven)

1. **P1 Candidate — `test_result_ingestor.py` JUnit XML incompatibility with Node 22** (`governance_tools/test_result_ingestor.py:151-191`):
   - `node --test --test-reporter=junit` (Node `v22.16.0`) emits top-level `<testsuites><testcase .../></testsuites>` without a `<testsuite>` wrapper when no `describe` suites are present.
   - `ingest_junit_xml` falls back to `suites = list(root)`, treating each `<testcase>` as a `<testsuite>`, yielding `passed=0` and `test_names=[]`.
   - Session B preserved raw `node-test.xml` and wrapped the exact 84 `<testcase>` nodes into a single `<testsuite>` (`node-test-ingestor.xml`) to publish `latest.json`. Independent review verified 100% 1-to-1 fidelity across all 84 test cases.
2. **One-Time Setup Friction**: `manage_agent_closeout install --agent codex` installs only the `Stop` hook and omits `SessionStart`; manual addition was required.
3. **R2 Semantic Note (Observation Only)**: `session_closeout_entry.py` releases R2 ownership (`state=RELEASED`, `exit_code=0`) even when `hook_outcome.gate_blocked=True`, while preserving `gate_blocked=True` inside the receipt. Validators and agents must check both `state=RELEASED` and `hook_outcome.gate_blocked=False` before claiming verified completion.

---

## 4. Traceable Artifact Digests (SHA-256)

| Artifact (relative to backup root) | SHA-256 |
|---|---|
| `artifacts/runtime/closeout-receipts/closeout_receipt_20261124T023008529373Z_r2_1563e6dbc6b04aff945b892ea771fcd7.json` (Session A, `gate_blocked=True`) | `d72f95434b81f6227d84319dc8cc2fb73a13d56ece0d110b4161e716b014231e` |
| `artifacts/runtime/closeout-receipts/closeout_receipt_20261124T033931194022Z_r2_594540cd281e451fadc0a78d2813c7b4.json` (Session B, `gate_blocked=False`) | `15d1a8977e479764c399d7221cf2eaaa3c12a5995a8b70afbade27e0b8fda794` |
| `artifacts/runtime/shared-closeout/owner.json` (`gen=2, RELEASED`) | `f5598348575ae9396e6ad15b6e1903d68085f7e1923f793d0c73b1d9d87160e9` |
| `artifacts/runtime/shared-closeout/releases/1.json` | `9c8700b54e992ec905a2cbd773a798d8ac1a5fc89374f846ec3fdd579cda94e8` |
| `artifacts/runtime/shared-closeout/releases/2.json` | `05ff94585c698d1e3a08b6010fde48936bd6274e079792d7a1bc0b06cbf5c835` |
| `artifacts/runtime/test-results/node-test.xml` (raw Node 22 JUnit) | `f73ea2dd925e33d6e39fe68023f7a0645e682b01f7c23abe95a8c5185e70f47b` |
| `artifacts/runtime/test-results/node-test-ingestor.xml` (adapted wrapper) | `100435579d7389345f8eb450ab1e451eadcf7844d7c9344da04c0a170917f428` |
| `artifacts/runtime/test-results/latest.json` (`84 passed, 0 failed`) | `3300939f0317c5a24ed8a177d1aa88fc5e4f95698d2252fd0e1dbd422b6ca65f` |
| `memory/2026-11-24.md` (Session A + B entries) | `4aec421629bb8472bff099c618926ceae9d7e840d802837187c5ea0e7b4e5a02` |

---

## 5. Claim Ceiling (`NOT_CLAIMED`)

- **Not Claimed**:
  - Full completion of `DB-04` (only Slice 1 pure JS queue is implemented; IndexedDB wiring, UI integration, and P2-2 conflict resolution/reset API remain open).
  - Remote product merge or production deployment of `DB-04` Slice 1.
  - Proof that AI Governance reduces total engineering time or token cost.
  - Completion of G4 or cross-consumer independent adoption.
