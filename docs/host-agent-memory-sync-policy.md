# Host-Agent Memory Sync Policy：repo memory 與 host-agent memory 的同步原則

> 狀態：draft  
> 更新日期：2026-04-01

## 目的

這份文件定義：當 repo memory 與 host-agent memory 可能脫節時，framework 應採取什麼同步姿態。

它要回答的是：
- 哪些情況需要 memory sync
- 哪些情況只要求 repo memory 完整即可
- sync 失敗時，應留下哪些 signal

## 名詞定義

### Repo Memory

指 repo 內可被 framework 直接觀測的記錄，例如：
- `memory/*.md`
- runtime verdict / trace artifacts
- reviewer handoff
- session summaries

### Host-Agent Memory

指 AI agent 在宿主產品中的記憶系統。  
目前 framework 對這一層通常沒有直接 API control，只能透過 adapter 或外部系統接入。

### 需要先分開的事

- repo memory ≠ host-agent memory
- artifact generation ≠ memory sync
- instruction guidance ≠ sync completion

## 目前的 sync posture

### `memory_sync_required`

適用於那些如果不同步，就會讓 reviewer / agent 對重要決策失去連續性的 session，例如：
- 重複發生的 failure 修復
- adoption / operator canonical workflow
- 已明確暴露 host-agent memory gap 的問題追蹤

### `memory_sync_optional`

適用於中低風險、即使只保留 repo memory 也仍能維持治理語境的情況，例如：
- wording / naming / framing-only 變更
- reviewer run 中單次、低風險的補充記錄
- 不涉及跨 session 依賴的輕量工作

### `repo_memory_only`

適用於只要求 repo 端留下紀錄，而不要求 host-agent 同步的情況，例如：
- terminal output
- 單次 artifact 驗證
- raw logs

## Host-Agent Memory 要保留什麼

如果 host-agent memory 存在，也不應直接同步整份 raw dump。  
較合理的最小內容是：
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

觸發條件：
- 某次 session 被標成 `memory_sync_required`
- repo artifact / repo memory 已存在
- 但沒有 host sync 的可見證據，且不屬於 `host_memory_not_applicable`

輸出位置：
- warning
- reviewer handoff / session summary

### `host_memory_not_applicable`

用來表示：
- 這個 agent / 平台沒有可接的 host memory layer
- 因此不能把 absence of sync 當成 failure

### `memory_sync_observed`

用來表示：
- 有足夠證據顯示 host-agent memory 已同步
- 但它仍然只是 sync state，不等於 memory quality 已被驗證

## 一句總結

這份 sync policy 的重點，不是強迫所有 session 都同步到 host-agent memory，而是把 repo memory、host-agent memory 與 sync state 三者明確分開，讓「沒有同步」變成可觀測，而不是默默消失。
