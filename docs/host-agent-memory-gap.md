# Host-Agent Memory Gap

> 狀態：draft
> 日期：2026-04-01
> 目的：釐清 `ai-governance-framework` 目前的 memory pipeline 能治理什麼、
> 不能治理什麼，以及為什麼 repo memory 與 host-agent memory 之間仍會出現
> 同步落差。

---

## 問題定義

目前的問題不是「沒有 memory 設計」，而是：

- 有 instruction
- 有 repo artifact
- 有 memory pipeline
- 但沒有 **可驗證的 host-agent memory 同步閉環**

因此會出現這種情況：

- repo 內已經留下 artifact / handoff / memory file
- 但宿主 AI 平台自己的 memory 沒有同步
- 最後只能靠代理事後補記

---

## 先拆 4 層，不然會一直混

### 1. Instruction Layer

例子：

- `AGENTS.md`
- `copilot-instructions.md`
- `governance/SYSTEM_PROMPT.md`

這一層的作用是：

- 提醒
- 引導
- 描述流程
- 定義優先順序

這一層做不到：

- 強制執行
- 驗證是否真的完成
- 自動寫入 host-agent memory

所以：

> instruction 不等於 integration

---

### 2. Artifact Layer

例子：

- `memory/*.md`
- runtime verdict / trace artifacts
- reviewer handoff
- session summaries

這一層的作用是：

- 留痕
- 交接
- 稽核
- repo 內可追蹤

這一層不等於：

- 宿主 AI 平台自己的 memory

所以：

> repo memory 不等於 host-agent memory

---

### 3. Host Memory Layer

這是 Copilot / Claude / ChatGPT / Codex 等宿主平台自己的記憶系統。

典型特性：

- 平台私有
- 只有代理或平台 API 能寫
- 外部 repo script 無法直接操作
- 是否寫入，取決於代理是否真的呼叫對應 memory tool / API

所以：

> host memory 是平台狀態，不是 repo 狀態

---

### 4. Enforcement / Integration Layer

真正缺的其實是這層。

這層要回答的不是：

- 有沒有 instruction？
- 有沒有 artifact？

而是：

- memory sync 何時是 required？
- 哪些事件需要 sync？
- 誰負責 sync？
- sync 完成要留下什麼證據？
- 沒 sync 時誰發 signal？
- signal 是否影響後續 session / reviewer / gate？

目前這一層還沒被正式定義。

---

## 目前真正的根因

### 第一層根因：概念混疊

目前很容易把下面幾個東西太早視為同一體：

- instruction
- repo memory
- runtime artifact
- host memory
- enforcement

這是最上游的誤差來源。

### 第二層根因：缺少可驗證閉環

目前比較像：

- 應該做
- 希望做
- 有文件寫

而不是：

- 必須做
- 做了可驗證
- 沒做會出 signal
- signal 會影響後續流程

### 第三層根因：命名與邊界不夠誠實

如果使用：

- `memory pipeline`
- `session memory`
- `handoff memory`

這類名稱，但沒有明確寫出：

- repo memory only
- not host-agent memory
- no automatic sync
- no platform adapter

那 expectation mismatch 就不是使用者單方面誤讀，而是產品邊界沒有切乾淨。

---

## 這是 framework 的問題，還是 agent 的問題？

### 從架構責任看：偏 framework

因為 framework 已經定義了 `memory pipeline` 這個概念，但目前沒有明確做到：

- repo memory / host memory 邊界聲明
- host-agent memory adapter
- enforced sync checkpoint
- missing-sync signal

這屬於 framework 的產品邊界設計缺口。

### 從執行責任看：偏 agent

如果代理已知：

- 目前沒有自動化
- memory sync 是重要 checkpoint

但仍然沒補，那是 workflow execution 的缺口。

但這是次要責任，因為好的系統本來就不該把關鍵同步只交給「記得」。

### 更精準的分類

這不是單純工具 bug，而是：

- **host-agent memory integration gap**
- **memory sync policy gap**

也就是說，缺的不是只有 adapter，還缺同步規則本身。

---

## 不該只靠 adapter 解決

即使今天真的做了一個 host-agent memory adapter，問題也不會自動解決。

還必須先定義：

- 什麼值得寫進 host memory？
- 什麼只該留在 repo artifact？
- 哪個 milestone 才需要 sync？
- sync 單位是 summary、decision、constraint，還是 full trace？
- sync 失敗時是 warning 還是 hard stop？
- human self-serve 與 agent-assisted path 是否使用相同 sync policy？

所以：

> adapter 只是水管，policy 才決定水流是否合法

---

## 建議拆成 3 條正式缺口

### 1. Boundary Clarification

至少要明寫：

- repo memory ≠ host-agent memory
- instruction ≠ integration
- artifact generation ≠ memory sync

### 2. Sync Policy Definition

至少要定義：

- 哪些事件需要 sync
- 哪些內容允許 sync
- 哪些角色負責 sync
- 哪些情況只 warning
- 哪些情況必須 fail 或 block reviewer claim

### 3. Enforceable Evidence Loop

至少要定義：

- sync 完成要留下什麼證據
- 沒證據時出什麼 signal
- signal 是否影響：
  - `session_end`
  - reviewer handoff
  - adoption gate

---

## 建議的最小修補方向

### Phase 1：先補邊界聲明

先在文件中明確寫死：

- 目前 memory pipeline 只治理 repo memory / artifacts
- 不自動同步到 host-agent platform memory
- `copilot-instructions.md` / `AGENTS.md` 只能作為 guidance，不構成 sync 保證

### Phase 2：定義最小 sync policy

先不要接平台 API，先定義：

- 哪些事件需要 `memory_sync_required`
- 哪些事件只需要 `repo_memory_only`
- 哪些同步內容是禁止的

### Phase 3：補最小 signal

先做 non-invasive signal：

- `memory_sync_missing`
- `host_memory_not_applicable`
- `repo_memory_written_only`

這些 signal 一開始不需要改 verdict，但至少要能進 reviewer 或 session close 的觀測面。

---

## 一句正式判斷

這次 memory 沒同步，不是單一工具故障，而是 repo-level memory artifact、
host-agent memory、instruction guidance、artifact generation 與 enforcement
checkpoint 之間，缺少明確且可驗證的同步閉環。

更短的說法：

> 問題不在「有沒有 memory 設計」，而在「memory 設計目前停在指示與留痕，還沒升級成可驗證同步」。
