# Host-Agent Memory Gap：目前 memory pipeline 與 host memory 之間的缺口

> 狀態：draft  
> 日期：2026-04-01

## 問題定義

目前 `ai-governance-framework` 已有：

- instruction
- repo artifact
- memory pipeline

但**沒有**完整的 host-agent memory integration。

所以真正的現況是：

- repo 內的 memory / artifact / handoff 可以被 framework 管理
- 宿主 AI 平台自己的 memory 不一定可見、可寫、可驗證
- 兩者之間沒有自動同步閉環

## 四層結構

### 1. Instruction Layer

例如：

- `AGENTS.md`
- `copilot-instructions.md`
- `governance/SYSTEM_PROMPT.md`

這一層提供 guidance，但不等於 memory sync。

### 2. Artifact / Repo Memory Layer

例如：

- `memory/*.md`
- runtime verdict / trace artifacts
- reviewer handoff
- session summaries

這一層屬於 repo memory，不等於 host-agent memory。

### 3. Host Memory Layer

這一層屬於各 AI 平台自己的 memory 機制：

- 可能有 memory UI
- 可能有 memory API
- 也可能完全沒有可靠寫入點

framework 目前無法直接保證這一層。

### 4. Enforcement / Integration Layer

真正缺的不是 instruction 或 artifact，而是：

- 什麼情況需要 sync
- 什麼情況不需要 sync
- sync 成功與否如何留下可觀測 signal
- signal 如何回到 session / reviewer / adoption gate

## 目前缺口

### 缺口 1：沒有可驗的 host memory integration

repo memory 可以被 framework 管理，但 host-agent memory 沒有相應 adapter / API contract。

### 缺口 2：沒有 enforceable sync policy

目前沒有把以下事情正式寫死：

- 哪些情況必須 sync
- 哪些情況可以只寫 repo memory
- sync 失敗要怎麼被表達

### 缺口 3：沒有 closeout 級 signal loop

也就是：

- closeout 結束後，framework 目前只能較可靠地處理 repo memory
- 但 host-agent sync 成功與否，還沒有成熟的 evidence loop

## 這個缺口不該被誤解成什麼

不要把下面幾件事混在一起：

- instruction 存在
- repo memory 有寫
- runtime artifact 有產出
- host-agent memory 已同步

目前這四者不是同一件事。

## 比較準確的現況

現在比較準的說法是：

- framework 有 repo-level memory artifacts
- framework 有 instruction guidance
- framework 尚未對 host-agent memory 提供完整 integration / enforcement

所以真正的缺口名稱應該是：

- `host-agent memory integration gap`
- `memory sync policy gap`

## 後續方向

較合理的路線分三步：

1. 先把 boundary 講清楚
2. 再定義 sync policy
3. 最後才補 enforceable evidence loop

## 一句話結論

目前 framework 並不是「沒有 memory」，而是**只有 repo memory / artifact memory，還沒有完整 host-agent memory integration**。
