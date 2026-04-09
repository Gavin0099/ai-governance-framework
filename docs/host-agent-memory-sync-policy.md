# Host-Agent Memory Sync Policy：repo memory 與 host-agent memory 的同步政策

> 狀態：draft  
> 日期：2026-04-01

## 目的

這份政策不是在宣稱 repo memory 已經自動同步到 host-agent memory，而是在定義：

- 哪些情況值得考慮 memory sync
- 哪些情況只需要寫 repo memory
- 哪些情況應該留下 signal，而不是假裝同步已完成

## 核心區分

### Repo Memory

repo 內可見、可追蹤、可被 framework 讀寫的記憶：

- `memory/*.md`
- runtime verdict / trace artifacts
- reviewer handoff
- session summaries

### Host-Agent Memory

AI agent 宿主平台自己的 memory，例如某些 adapter / 平台提供的長期記憶能力。

### 重要區分

- repo memory ≠ host-agent memory
- artifact generation ≠ memory sync
- instruction guidance ≠ sync completion

## 三種 sync posture

### `memory_sync_required`

適用於高價值、跨 session、且對未來 reviewer / agent 有明顯可復用價值的內容，例如：

- 重大決策結論
- adoption / operator canonical workflow
- host-agent memory gap 這類結構性缺口

### `memory_sync_optional`

適用於有保存價值，但只寫 repo memory 也能接受的內容，例如：

- wording / naming / framing-only 調整
- reviewer run 的觀測摘要
- 短期整理、沒有長期策略意義的修補

### `repo_memory_only`

適用於只需要 repo 內留下紀錄，不需要 host-agent 同步的內容，例如：

- 純 terminal output
- 一次性 artifact 路徑
- raw logs

## 可允許的同步內容

若 host-agent memory 可用，允許同步的內容應是**整理後的 decision / boundary / open gap**，而不是 raw dump。

優先類型：

1. Decision Summary
2. Boundary Rule
3. Strategic Direction
4. Open Gap

不建議同步：

- full trace
- raw artifact JSON
- prompt-by-prompt transcript

## Signals

### `memory_sync_missing`

條件：

- 當前項目屬於 `memory_sync_required`
- repo artifact / repo memory 已存在
- 但沒有 host sync 成功紀錄，也不是 `host_memory_not_applicable`

輸出：

- warning
- 進 reviewer handoff / session summary

### `host_memory_not_applicable`

條件：

- 當前平台沒有可用 memory API / adapter
- 或本次 run 明確不支援 host sync

輸出：

- informational

### `repo_memory_written_only`

條件：

- 只有 repo memory 被寫入
- policy 並未要求 host sync

輸出：

- informational

## Enforcement 邊界

目前這份政策**不做**：

- 自動寫入 host memory API
- 強制每次 repo memory 都同步到 adapter 記憶
- hard fail / hard stop
- cross-platform durability guarantee

## 一句話結論

這份政策的目的，不是宣稱 host-agent memory 已整合，而是把「何時需要同步、何時只要留下 signal」先定義清楚。
