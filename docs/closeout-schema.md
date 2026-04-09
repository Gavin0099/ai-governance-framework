# Closeout Schema：Candidate 與 Canonical

> Authority: `runtime_hooks/core/_canonical_closeout.py`
> Status: Stable (v1)
> Date: 2026-04-08

---

## 概覽

每個 session 都只會產生一份 **canonical closeout artifact**。  
這份 canonical artifact 永遠由 system 寫出，不能由 AI 直接產生。

AI 可以透過 `/wrap-up` 產生 **candidate closeout**。  
`/wrap-up` 的定位是 *candidate closeout drafting surface*，也就是提升輸入品質的輔助面，而不是 canonical 輸出的 producer。

candidate 屬於不可信輸入，會在 session end 時由 `build_canonical_closeout()` 驗證、整理並轉成 canonical artifact。  
即使完全移除 `/wrap-up`，也不應阻斷 canonical closeout 的產出；系統只是退化成 `closeout_status = "missing"`，但 canonical artifact 仍然必須被寫出。

```text
AI 寫入:      closeout_candidates/{session_id}/{timestamp}.json  -> candidate (untrusted)
System 寫入:  closeouts/{session_id}.json                        -> canonical (authoritative)
```

---

## Trust Boundary

| Writer | Artifact | Trust level |
|--------|----------|-------------|
| AI (`/wrap-up`) | candidate | Untrusted，使用前必須驗證 |
| `session_end_hook` | canonical | System，具 authoritative 地位 |
| `_append_session_index` | `session-index.ndjson` | 只作 cache，不是 source of truth |

**不可被破壞的 invariants：**
- AI 不得直接寫入 `artifacts/runtime/closeouts/`
- `session-index.ndjson` 不得被 `session_start`、audit 或任何 downstream consumer 當成 source of truth
- `build_canonical_closeout()` 是唯一合法的 canonicalization function，其他路徑不得自行產生 canonical closeout dict

---

## Candidate Schema（AI 撰寫，不可信）

Path: `artifacts/runtime/closeout_candidates/{session_id}/{YYYYmmddTHHMMSSffffffZ}.json`

```json
{
  "task_intent": "string - 一句話描述本次 session 想完成什麼",
  "work_summary": "string - 具體描述做了什麼，需點名檔案 / 函式 / 工具",
  "tools_used": ["string"],
  "artifacts_referenced": ["string"],
  "open_risks": ["string"]
}
```

**不在 candidate 中的欄位：**
- `session_id`
- `closed_at`
- `closeout_status`

這些欄位都由 system 補入。  
`/wrap-up` 若在同一個 session 被呼叫多次，會產生多份 candidate；`pick_latest_candidate()` 只取字典序最新的一份，也就是最近寫出的那份，不代表它一定最完整。

---

## Canonical Schema（system 撰寫，具 authoritative 地位）

Path: `artifacts/runtime/closeouts/{session_id}.json`

```json
{
  "session_id": "string",
  "closed_at": "ISO-8601 datetime with timezone",
  "closeout_status": "valid | missing | schema_invalid | content_insufficient | inconsistent",
  "task_intent": "string | null",
  "work_summary": "string | null",
  "evidence_summary": {
    "tools_used": ["string"],
    "artifacts_referenced": ["string"]
  },
  "open_risks": ["string"]
}
```

只有在 `closeout_status` 為 `valid`、`content_insufficient` 或 `inconsistent` 時，
`task_intent`、`work_summary`、`evidence_summary.*`、`open_risks` 才會從 candidate 帶入。  
對 `missing` 與 `schema_invalid` 來說，這些欄位會回落到 `null` / `[]`。

---

## `closeout_status`：五種合法值

判定規則採 **first-match**，依下表順序檢查；一旦命中就停止，不再往下判。

| # | 條件 | closeout_status | 欄位是否填入 |
|---|------|-----------------|--------------|
| 1 | 找不到 candidate 檔案 | `missing` | 否 |
| 2 | candidate 無法讀取、不是 dict、缺欄位或欄位型別錯誤 | `schema_invalid` | 否 |
| 3 | schema 合法，但 `work_summary` 為空，或 `tools_used` 與 `artifacts_referenced` 同時為空 | `content_insufficient` | 部分 |
| 4 | schema 合法，但引用的 artifact 不存在；或宣稱執行了可驗工具卻沒有 runtime signal | `inconsistent` | 是 |
| 5 | 全部檢查通過 | `valid` | 是 |

同一份 candidate 只會落到一個 `closeout_status`。  
因為採 first-match，所以不會同時有多個 competing 狀態。

---

## `build_canonical_closeout()` 的保證

這個函式有兩個硬保證：

1. **永不 raise。**  
   不管輸入是 `None`、壞掉的 dict、垃圾字串，函式都必須回傳結果，而不是拋例外。

2. **永遠回傳合法 canonical dict。**  
   回傳值一定符合 canonical schema：所有必要 key 都在、型別也正確。  
   最差情況只是 `closeout_status = "missing"` 或 `"schema_invalid"`，而欄位內容退化為空值。

這兩個保證是 load-bearing 的。  
`run_session_end()` 會在 artifact 寫盤之前先呼叫 `build_canonical_closeout()`，所以就算後續磁碟寫入失敗，canonical dict 也已經存在。

呼叫端不應用 try/except 去吞掉 `build_canonical_closeout()` 的回傳；這個函式本來就保證任何輸入都能產生可用結果。

---

## Signal Strength

不是所有 signal 都具有同樣強度。  
downstream consumer（例如 `session_start`、`closeout_audit`）必須知道每個檢查能證明什麼、不能證明什麼。

### `existing_artifacts`：弱存在性 signal

`_existing_artifacts` 來自 `artifacts_referenced` 中那些在 session close 時實際存在於磁碟上的路徑。

**它能證明：**
- 該路徑在 session end 當下存在於專案中

**它不能證明：**
- 該檔案一定是在這次 session 內建立或修改
- `work_summary` 對這個檔案的描述一定正確
- 某個 tool 一定處理過這個檔案
- 檔案內容一定符合 candidate 的敘述

> artifact existence 只是 consistency hint，不是 provenance。  
> 它只能說明「路徑存在」，不能說明「誰做的」或「是否符合主張」。

### `tools_executed`：可驗工具 signal

`runtime_signals["tools_executed"]` 來自 `event_log` 中帶有 `"tool"` 欄位的事件。

**它能證明：**
- session 中記錄到某個 tool invocation

**它不能證明：**
- invocation 一定成功
- 這次 invocation 與當前 candidate 一定相關
- tool 的執行上下文一定和 `work_summary` 相符

### 可驗工具 taxonomy（凍結）

目前 `_VERIFIABLE_TOOLS` 為：

```python
_VERIFIABLE_TOOLS = frozenset({"pytest", "build", "lint", "test", "make"})
```

比對採 **case-insensitive**，但**不做 normalization**。  
因此 `"python -m pytest"` 不會自動等同於 `"pytest"`。如果 caller 需要模糊匹配，應在將 `event_log` 傳入前先自行正規化工具名稱。

**這是刻意的設計取捨：**
- 低 recall
- 高穩定性
- 高可審計性

如果要擴充這份 taxonomy，必須同時更新：
- `_canonical_closeout._VERIFIABLE_TOOLS`
- 本文件

兩者不可漂移。

---

## Session Index Cache

Path: `artifacts/session-index.ndjson`

每行是一筆 NDJSON：

```json
{
  "session_id": "string",
  "closed_at": "ISO-8601 datetime",
  "closeout_status": "string",
  "task_intent": "string | null",
  "has_open_risks": true
}
```

**這個檔案不是 source of truth。**  
它存在的目的只是為了快速掃描，不必逐一打開每份 closeout。  
它採 append-only，且寫入失敗不應視為 fatal。  
只要 index 與 canonical closeout artifact 不一致，就必須以 canonical artifact 為準。

---

## Downstream Consumer Rules

**通用規則：**任何新 consumer 都只能讀 `artifacts/runtime/closeouts/` 裡的 canonical artifact。  
直接讀 candidate 或把 `session-index.ndjson` 當 authoritative，都是禁止行為。

### session_start（Slice 5）

- 只能讀 `artifacts/runtime/closeouts/`
- 不讀 `session-index.ndjson`
- 依 `closeout_status` 套用 injection 規則：

| closeout_status | Inject 行為 |
|-----------------|-------------|
| `valid` | 注入 `task_intent`、`work_summary`、`open_risks` |
| `content_insufficient` | 只給 diagnostic warning，不注入摘要 |
| `missing` / `schema_invalid` / `inconsistent` | 只給最小狀態 warning |

### closeout_audit（Slice 6）

- 只能讀 `artifacts/runtime/closeouts/`
- 可把 `session-index.ndjson` 當 scan cache，但不能當 authoritative source
- 不得自創新的 `closeout_status`
- 不得延伸 taxonomy
- 輸出只限 aggregation、counts、trends、reviewer summary

---

## 相關檔案

| File | 角色 |
|------|------|
| `runtime_hooks/core/_canonical_closeout.py` | canonicalization logic，權威實作 |
| `runtime_hooks/core/_canonical_closeout_context.py` | `session_start` closeout context loader |
| `runtime_hooks/core/session_end.py` | 收集輸入並呼叫 `build_canonical_closeout()` |
| `runtime_hooks/core/session_start.py` | 在 session start payload 中注入 `closeout_context` |
| `governance_tools/closeout_audit.py` | 對 canonical closeout 做 aggregate health audit |
| `governance_tools/expansion_boundary_checker.py` | `closeout_context` 的 admission record |
| `tests/test_canonical_closeout.py` | `_canonical_closeout` 單元測試 |
| `tests/test_canonical_closeout_context.py` | `_canonical_closeout_context` 單元測試 |
| `tests/test_closeout_audit.py` | `closeout_audit` 單元測試 |
| `tests/test_session_end_closeout_integration.py` | full pipeline 整合測試 |
| `docs/session-workflow-enhancement-plan.md` | 設計理由與實作計畫 |
