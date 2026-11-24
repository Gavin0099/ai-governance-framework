# G4 Consumer Sample 003 — `chinese-writing-practice` `DB-04` Slice 2 (`PASS — Recovered via Session A -> B under codex exec`)

- **Record Class**: Real Consumer Natural Work-Item Observation (**G4 Consumer Sample 003**, single work item spanning Session A + Session B)
- **Prior Samples Preserved**: `docs/status/g4-consumer-sample-001-english-vocab-trainer-issue375-2026-11-23.md` (`FAIL / NOT PERSISTED`) and `docs/status/g4-consumer-sample-002-chinese-writing-practice-db04-2026-11-24.md` (`PASS — Recovered via Session A -> B`) remain unchanged.
- **Counting Discipline**: Session A and Session B belong to **one** natural work item (Sample 003). Session A's `FAIL_CLOSED_CLOSEOUT_CONTENT_INSUFFICIENT` daily memory audit entry is preserved verbatim alongside Session B's `AUTO_PROMOTE` recovery; this sample is **not** counted as a single-session first-pass `AUTO_PROMOTE`.
- **Date**: 2026-11-24
- **Archived Against Framework Main**: `7b2cd5d20ac29e4bf8d7f3a348f275da210e6fe7`
- **Consumer Repository / Base**: `chinese-writing-practice` `origin/main@abffba0df5e4a628456f0663a449db0d8bc23ce0`
- **Experimental Execution Submodule**: Local test branch bumped `ai-governance-framework` from `1a30faed` to `7b2cd5d2` (`eade01a09d6f45bea502e4be621ffb7aa183cca8`, separately accounted) to validate PR `#358` (Node 22 JUnit XML parser fix). Clean product PR branch cherry-picked only product commits onto `origin/main@abffba0d` without the experimental submodule bump.
- **Execution Environment**: Standalone git clone (`C:\Users\reiko\AppData\Local\Temp\cwp-g4-s1-db04-s2\chinese-writing-practice`) + non-interactive `codex exec` (`codex-cli 0.171.0-alpha.13`, `--trust --dangerously-bypass-hook-trust --approve-for-me` under isolated `CODEX_HOME` `E:\BackUp\Git_EE\_codex_home_isolated\cwp-db04-s2`) + independent read-only subagent review. Raw evidence backed up outside Temp to `E:\BackUp\Git_EE\_evidence_backup\g4-sample-003-cwp-db04-s2-2026-11-24`.
- **Work Item**: `DB-04` Slice 2 — Controlled conflict resolution (`resolveConflict` in `offlineQueue.mjs`, addressing P2-2 deferred from PR `#21`) + transactional IndexedDB queue storage adapter (`indexedDbQueueStorage.mjs`) and unit tests (`tests/offline-queue.test.mjs`, `tests/indexeddb-queue-storage.test.mjs`).

---

## 1. Outcome Summary (Session A Preserved + Session B Recovery)

| Verification Dimension | Session A (`01a20c46-...`) | Session B (`01a20c53-...`) | Sample 003 Status |
|---|---|---|---|
| Product commits (local run) | `21dbc28c68c33c5ce4b004f86281a72d0985a6ee` (4 files, `+314/-1`) | `58a217f20468b0ac8f567f39dcbe14d8dacd57fd` (`onblocked`/`close()`/reconnect fixes, `+108/-13`) | **PASS (clean PR commits: `339fda3`, `e18d848`)** |
| Automated unit tests | `node --test tests/*.test.mjs` -> **92/92 PASS** (`710.1ms`) | `node --test tests/*.test.mjs` -> **95/95 PASS** (`768.5ms`; clean PR branch `660.5ms`) | **PASS** |
| Node 22 JUnit XML ingestion (`#358`) | Direct raw `node-test.xml` -> `latest.json` (`92/92`, `ok=True`, `warnings=[]`, **0 manual XML conversion**) | Direct raw `node-test.xml` -> `latest.json` (`95/95`, `ok=True`, `warnings=[]`, **0 manual XML conversion**) | **PASS (`#358` verified in consumer)** |
| Independent code review | Read-only subagent `e9dbd4fb`: **0 P0 / 0 P1 / 2 P2 / 2 P3** | Read-only subagent `727fde5f`: **0 P0 / 0 P1 / 0 P2 / 0 P3 (`APPROVED`)** | **PASS** |
| Native `SessionStart` / `Stop` hooks | Auto-triggered; session identity matched | Auto-triggered; new session identity matched | **PASS** |
| R2 Ownership & Strict Gate | `generation=1`, `state=RELEASED`, `hook_outcome.ok=True`, `gate_blocked=False` | `generation=2`, `state=RELEASED`, `hook_outcome.ok=True`, `gate_blocked=False` | **PASS (both generations `gate_blocked=False`)** |
| Canonical daily memory | **`FAIL_CLOSED_CLOSEOUT_CONTENT_INSUFFICIENT`** (`CHECKS_RUN` listed internal `functions.exec` without observable file/tool anchor; `promoted=False`) | **`AUTO_PROMOTE`** (`closeout_status=valid`, `snapshot_created=True`, `promoted=True` after listing concrete test/tool anchors) | **Recovered PASS (A's fail-closed record preserved)** |

---

## 2. Measurement Record (A + B Combined Accounting)

| Metric | Session A | Session B | Sample 003 Total (A + B) |
|---|---:|---:|---:|
| Wall-clock duration | `5m 44s` (`06:38:24Z`–`06:44:08Z`) | `3m 36s` (`06:51:45Z`–`06:55:21Z`) | **`9m 20s`** |
| Idle/long gaps (`>= 30s`) | `52.6s` (1 gap, model generation; 0 human waits) | `0.0s` (0 gaps; 0 human waits) | **`52.6s`** |
| LLM turns / tool calls | `22` turns / `21` tool calls | `15` turns / `14` tool calls | **`37` turns / `35` tool calls** |
| Total tokens | `1,197,829` | `821,776` | **`2,019,605`** |
| Input tokens (cached % of input) | `1,188,027` (`1,127,680` / 94.9%) | `815,709` (`761,472` / 93.4%) | **`2,003,736` (`1,889,152` / 94.3%)** |
| Uncached input / output tokens | `60,347` / `9,802` (reasoning `681`) | `54,237` / `6,067` (reasoning `292`) | **`114,584` / `15,869`** |
| Separate setup / upgrade overhead | Local submodule bump `2m 25s` + 10s hook probe (`22,051` tokens) | None | **Tracked separately from task runtime** |
| Mid-task human approvals / rescues | `0` (`--approve-for-me` in `workspace-write`) | `0` (`--approve-for-me` in `workspace-write`) | **`0` mid-task interventions** |

- **Attribution Boundary vs Sample 002 (`53m 31s` / `5.45M` tokens -> `9m 20s` / `2.02M` tokens)**: Because execution mode (`codex exec --approve-for-me`), framework commit (`7b2cd5d2` with `#358`), and slice content (`DB-04` Slice 2 vs Slice 1) all changed simultaneously, this comparison is an operational directional signal rather than a single-variable controlled experiment.

---

## 3. Traceable Artifact Digests (SHA-256)

| Artifact (relative to backup root) | SHA-256 |
|---|---|
| `artifacts/runtime/closeout-receipts/closeout_receipt_20261124T064406782495Z_r2_d4d33223a25f4038a78e0de7c8d233b1.json` (Session A) | `b4af2cd3e5b8f7c2649335d68463e277aa9a478ac60ae949c3687bce13e57a5a` |
| `artifacts/runtime/closeout-receipts/closeout_receipt_20261124T065519830737Z_r2_af7d8c34dd3f401c8a60f290bd92dc97.json` (Session B) | `a61724a41683d6ea74079b2ce2da780ff4d97c3fb3205e669ce814ae7590f9cb` |
| `artifacts/runtime/closeout-completions/01a20c46-e6bb-77e0-b923-a13fa9965aa9.json` | `231bc0bcfbbcf6e61fa72c253ee5b8fc7755326206ece3dacb292381618033ac` |
| `artifacts/runtime/closeout-completions/01a20c53-1e4c-7430-8e64-4a2ed7306a09.json` | `da0b8fd485165790581303e223a635fd516638a85ec319f5018a6b4919809c0a` |
| `artifacts/runtime/shared-closeout/owner.json` (`gen=2, RELEASED`) | `068984b1c6ec8284944e3a22053c65d2726e860e74362b2149fafaef96d03f68` |
| `artifacts/runtime/shared-closeout/releases/1.json` | `48813e956cfcbdc4322ed82ebe0586f24f4f2993366bc5f124653f53e8108575` |
| `artifacts/runtime/shared-closeout/releases/2.json` | `1b9e41488d2625c0c625a6d48d8c7a09b8720d53825cd395feb16256e5fcb226` |
| `artifacts/runtime/test-results/node-test.xml` (`95/95` raw Node 22 JUnit) | `b5de06e0ad0f1ca887aaca6161100a9cd44158cc97a434025e1f7d2de45f73c8` |
| `artifacts/runtime/test-results/latest.json` (`95 passed, 0 failed`) | `bc85b052f4beb6a0003af52e09da67fed8788c564cf40d7905f3a07cdc1783ab` |
| `memory/2026-11-24.md` (Session A fail-closed + Session B `AUTO_PROMOTE`) | `e936885befd9bb359b47faeb4cd0397d3b19d87f37b0a3e7ba0530a0b511cbcd` |

---

## 4. Claim Ceiling (`NOT_CLAIMED`)

- **Not Claimed**:
  - Single-session first-pass `AUTO_PROMOTE` (Session A hit `content_insufficient` before Session B recovered).
  - Real browser IndexedDB verification (multi-tab blocking, `versionchange` timing, and browser persistence were exercised via deterministic Node mocks only; live browser QA remains open).
  - Production suitability of `--dangerously-bypass-hook-trust` outside an isolated test `CODEX_HOME`; routine consumer runs must rely on explicit persisted hook trust.
  - Formal governance upgrade of `chinese-writing-practice` `main` (which remains pinned at `1a30faed` until upgraded separately) or remote merge of `DB-04` Slice 2.
  - Quantitative proof of how much subsequent sessions save by reading promoted `memory/` records, or completion of G4 across diverse consumers.
  - External independent retrieval or reproduction of raw receipts/XML without access to the local backup (`E:\BackUp\Git_EE\_evidence_backup\g4-sample-003-cwp-db04-s2-2026-11-24`); GitHub stores only the summary and SHA-256 digests.
