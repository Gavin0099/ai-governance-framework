# Host-Agent Memory Sync Policy

> 狀態：draft
> 日期：2026-04-01
> 目的：為 repo memory 與 host-agent memory 之間的同步建立最小政策面，
> 先回答「何時需要 sync、允許 sync 什麼、誰負責、沒做怎麼辦」，再談
> adapter 或自動化。

---

## 這份文件處理什麼

這份文件只定義 **policy**，不直接定義平台 API 或 adapter 實作。

它回答四個問題：

1. 哪些事件需要 memory sync？
2. 哪些內容允許寫入 host-agent memory？
3. 哪些角色負責 sync？
4. sync 缺失時應該產生什麼 signal？

---

## 先講清楚邊界

### Repo memory

指 repo 內可版本化或可稽核的內容，例如：

- `memory/*.md`
- runtime verdict / trace artifacts
- reviewer handoff
- session summaries

### Host-agent memory

指宿主 AI 平台自己的記憶層，例如 Copilot / Claude / ChatGPT / Codex
內建或附屬的 memory 工具 / API。

### 核心原則

- repo memory ≠ host-agent memory
- artifact generation ≠ memory sync
- instruction guidance ≠ sync completion
- host-agent memory 只應承載高價值、跨 session 仍有意義的壓縮資訊

---

## 同步目標

host-agent memory sync 的目標不是複製 repo。

它只應該保存：

- 高價值決策
- 高價值邊界
- 長期穩定的工作規則
- 下次 session 重啟時仍然重要的 context

它不應該保存：

- 全量 trace
- 臨時命令輸出
- 一次性 debug 過程
- 可由 repo artifact 穩定重建的低價值內容

---

## 事件分級

### Level A：必須同步 (`memory_sync_required`)

以下事件發生後，應視為 host-agent memory sync 的正式 checkpoint：

1. **治理邊界變更**
   - 例如：
     - DBL first slice 建立
     - human / agent gate semantics split
     - authority boundary 重新定義

2. **正式路線切換**
   - 例如：
     - human self-serve 不再是主成功標準
     - agent-assisted adoption 成為主要路線

3. **新的長期設計缺口確認**
   - 例如：
     - host-agent memory gap 被正式定義
     - runtime surface manifest 成為新主線

4. **新的 canonical workflow / operator path 確立**
   - 例如：
     - 新的正式 adoption path
     - 新的 smoke / reviewer / handoff 標準入口

### Level B：可選同步 (`memory_sync_optional`)

以下事件可以只寫 repo memory，不一定需要 host-agent sync：

1. 一般文件修正
2. wording / naming / framing-only 調整
3. 單次 reviewer run 的局部 observation
4. 一般測試補強，若未改變長期心智模型

### Level C：只寫 repo (`repo_memory_only`)

以下內容預設不應進 host-agent memory：

1. 全量 terminal output
2. 一次性 artifact 路徑
3. 可由 repo 直接重建的 raw logs
4. 中間態失敗嘗試，除非它改變了長期 policy 或邊界理解

---

## 允許同步的內容單位

host-agent memory 應使用壓縮單位，而不是 raw dump。

允許的同步單位：

### 1. Decision Summary

例如：

- 「human self-serve 與 agent-assisted adoption 已正式分軌」
- 「DBL first slice 現在只處理 explicit missingness，不處理 semantic sufficiency」

### 2. Boundary Rule

例如：

- 「human fail 不自動否定 agent path」
- 「manifest consistency 目前只做 soft enforcement」

### 3. Strategic Direction

例如：

- 「下一步優先做 agent-assisted adoption baseline，而不是繼續擴 DBL runtime」

### 4. Open Gap

例如：

- 「host-agent memory integration gap 仍未關閉」
- 「memory sync policy 已定義，但尚未接 enforceable signal」

不允許的同步單位：

- full trace
- raw artifact JSON
- 未壓縮的測試輸出
- prompt-by-prompt transcript

---

## 角色責任

### Agent

負責：

- 在 `memory_sync_required` 事件後，產生 repo memory 記錄
- 若 host-agent memory 可用，執行對應 sync
- 若 host-agent memory 不可用，明確記錄 `host_memory_not_applicable`

不得：

- 在沒有 policy basis 的情況下，把大量 repo artifact 直接灌進 host memory
- 自行提升 `optional` 內容為 `required`，除非有新政策或明確人工方向

### Framework Runtime

目前負責：

- 產生 repo-level artifacts 與 memory evidence
- 提供可被 sync 的候選內容

目前不負責：

- 直接寫入 host-agent memory
- 驗證 host platform memory API 是否成功持久化

### Human Reviewer / Operator

負責：

- 在需要審查時確認：
  - 事件是否真的屬於 `memory_sync_required`
  - sync 是否有留下可審計證據

---

## 最小 signal policy

第一版先定義 signal，不直接定義 hard stop。

### `memory_sync_missing`

條件：

- 發生 `memory_sync_required` 事件
- 有 repo artifact / repo memory 更新
- 但沒有任何 host sync 完成證據，也沒有 `host_memory_not_applicable`

預設處理：

- warning
- 進 reviewer handoff 或 session summary

### `host_memory_not_applicable`

條件：

- 宿主平台沒有可用 memory API / tool
- 或本次 run 的執行條件不允許 host sync

預設處理：

- informational
- 不視為失敗，但必須明確記錄

### `repo_memory_written_only`

條件：

- 已完成 repo memory 寫入
- 但 policy 判斷本次只需要 repo memory，不需要 host sync

預設處理：

- informational

---

## 證據要求

sync 是否完成，不應只靠代理自述。

最小可接受證據：

1. repo memory 記錄存在
2. 明確標記本次事件是：
   - `memory_sync_required`
   - `memory_sync_optional`
   - `repo_memory_only`
3. 若屬於 required，還需至少其一：
   - host sync success note
   - `host_memory_not_applicable`
   - reviewer-confirmed defer reason

---

## 第一版不做的事

這份 policy 目前不處理：

- 各平台 host memory API 差異
- 自動寫入 host memory 的 adapter 細節
- sync 內容的自動摘要品質
- hard fail / hard stop 條件
- cross-platform durability guarantee

---

## 建議的最小落地順序

1. 先接受這份 policy 作為正式邊界。
2. 在 `memory/` 或 reviewer/session close 路徑中標記事件級別：
   - required / optional / repo-only
3. 補最小 signal：
   - `memory_sync_missing`
   - `host_memory_not_applicable`
   - `repo_memory_written_only`
4. 最後才討論 host-agent adapter。

---

## 一句總結

host-agent memory sync 不應再被視為「代理最好記得做」的附帶動作。

它應被視為：

> 一個有事件分級、有內容限制、有角色責任、也有缺失 signal 的治理政策面。
