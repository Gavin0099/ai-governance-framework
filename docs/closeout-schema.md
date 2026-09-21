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

目前 implementation 從 `event_log` 中帶有 `"tool"` 欄位的事件建立
`runtime_signals["tools_executed"]`。這是資料擷取行為，不代表任意帶有
`tool` 的事件都具備下列證據資格。

#### Q1：最低 invocation evidence（owner 已採納，2026-09-21）

**已觀察到的觸發問題與來源：** 2026-09-21 的 Codex
`0.154.0-alpha.6.2` disposable probe 中，被 PreToolUse 拒絕的命令仍有
Pre 事件但沒有 Post；main 事件缺少 `agent_id`，而 subagent 與 main
共用 session ID；成功與非零退出命令都有 Post，且沒有獨立 exit-code 欄位。
因此把任意 tool event 當成已執行工具，會混淆被拒絕的 attempt、actor
歸屬與成功結果。這是已觀察到的證據授權歧義，不是已部署 collector 的事故。
原始觀察保留於本地 `memory/evidence/native-tool-probe-20260921/report.md`、
`event-inventory.json` 及 `events/`（本 PR 不發布這些原始 evidence）。
可公開核對的接點是 [runtime producer](../runtime_hooks/core/session_end.py)
對 `event_log` 的 `tool` 擷取，以及
[canonical tests](../tests/test_canonical_closeout.py) 的名稱清單驗證；
兩者都沒有建立事件生命週期／actor 配對資格。
未來只有新增明確的平台 actor／lifecycle 證據及另行 owner 決策，才重審
此最低門檻；coverage 不足本身不構成放寬理由。

對 PreToolUse / PostToolUse 平台事件，只有兩者的 session、actor、turn、
tool-call identity 及 platform tool name 全部一致，才符合最低 invocation
evidence。它只建立「該平台工具呼叫已到達 PostToolUse」這一項主張。

Actor identity 必須在 Pre 與 Post 各自由明確的平台證據建立，且指向同一
actor。身分缺失、衝突或只能推測時，一律為 `UNPROVEN`（證據不足）：

- 兩邊都沒有 `agent_id` 不構成 actor 相等。
- `agent_type` 相同不足以識別同一 actor。
- 不得因缺少 `agent_id` 而推定為 main agent。

只有 PreToolUse 表示 attempt observed，不得據此填入 `tools_executed`。
任一配對身分缺失、衝突或無法確認，也不得據此填入；candidate 自述或
結果 artifact 不能替代平台配對證據。`UNPROVEN` 不表示工具沒有執行。

此規則只規定最低證據資格，不授權 collector 或 canonical mapping，
也不改變可驗工具 taxonomy。既有 implementation 尚未執行這套配對驗證；
文件採納不代表 runtime enforcement 已完成，也不追溯重寫既有紀錄。

**它能證明：**
- 在符合 Q1 的平台事件證據下，該 session / actor 的工具呼叫到達 PostToolUse

**它不能證明：**
- invocation 一定成功
- 這次 invocation 與當前 candidate 一定相關
- tool 的執行上下文一定和 `work_summary` 相符
- subprocess 已啟動或 executable 已解析
- exit code 為零、測試實際執行或結果有效

#### Q2：Bash → pytest 證據轉換（owner 已採納 NO，2026-09-21）

即使 actor 明確、Pre/Post 符合 Q1、shell 已確認且命令符合窄 grammar，
`tool_name = Bash` 搭配指向 pytest 的命令文字，仍只支持「Bash 平台呼叫
到達 PostToolUse」及「command syntax 指向 pytest」。它不足以建立
pytest 本身 `actually invoked during the session` 的主張。

因此不得僅憑這組證據宣稱 `tools_used = ["pytest"]`，也不得據此產生
`tools_executed = ["pytest"]`。把 syntactic target 當成 actual invocation
會改變既有 trust semantics，不是單純名稱正規化。是否可映射平台工具
本身，仍須符合欄位適用的工具類型並另行授權。

本研究線到此結束：不為這條轉換開發 collector，不追求 process
instrumentation，不放寬 canonical，也不改寫既有 finalized evidence。
Q2 = NO 是現有證據在現行語義下不足的決策，不表示 pytest 沒有執行，
也不是所有未來平台或其他 evidence source 都不可能建立其 invocation。

Q1 的 actor 規則不變：main-agent actor identity 無法明確建立時仍為
`UNPROVEN`；command identity 契約另外要求明確的 shell identity，不能
將 shell 不明的命令套用窄 grammar。Memory write / snapshot / promotion 的既有
成果與工具證據資格分開；本決策不宣告 native pytest evidence 或整體
Memory qualification 通過。Parser、collector、canonical mapping、schema
及 runtime 均不因本次文件決策而變更。

### 可驗工具 taxonomy（凍結）

目前 `_VERIFIABLE_TOOLS` 為：

```python
_VERIFIABLE_TOOLS = frozenset({"pytest", "build", "lint", "test", "make"})
```

比對採 **case-insensitive**，但**不做 normalization**。  
因此 `"python -m pytest"` 不會自動等同於 `"pytest"`。名稱正規化若有需要，
屬於 caller 的另行契約；這個責任歸屬不授權提升證據強度，也不授權
Q2 的 `Bash` 命令內容轉換成 `pytest` 身分。

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
