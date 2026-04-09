# Entry-Layer Contract：workflow artifact 的最小契約

## 目的

這份文件定義 workflow skills 產生的 artifact，要如何進入 runtime 可辨識的範圍。
它不是在宣告新的 workflow engine，而是在定義一組最小 contract，讓下列路徑能互相對接：

`tech-spec -> precommit -> create-pr`

## 為什麼需要這份 contract

目前 repo 同時存在：
- runtime governance hooks
- reviewer handoff 與 trust surfaces
- workflow skills
- CI 與 repo boundary validation

如果 workflow artifact 沒有最小 contract，很容易出現：
- workflow skill 只產生文字，但 runtime 無法辨識
- runtime 只能看到檔案存在，卻不知道它屬於哪個 workflow step
- downstream consumer 無法判斷缺失的 consequence class

## 這份 spec 做什麼

這份 spec 定義：
- entry layer 可接受的 object model
- closed loop 的 edge semantics
- workflow artifact 如何被 runtime recognition 使用
- 缺失時 downstream 應如何對待 consequence class

這份 spec **不做**：
- generic DAG engine
- multi-agent orchestration
- AI 自動推論下一步 workflow
- 為所有 task 建立完整 workflow
- 用 workflow evidence 取代 domain/runtime evidence

## 設計位置

這個 repo 已有：
- runtime governance system
- evidence / reviewer-surface system

entry layer 的角色是補上一條「workflow artifact 如何進 runtime 可觀測面」的橋，而不是再多長一個 authority system。

## 核心 artifact

### `tech_spec`

用途：
- 補足非 trivial 工作在實作前的範圍與設計描述

### `validation_evidence`

用途：
- 把 reviewer handoff 前需要的驗證結果留下來

### `pr_handoff`

用途：
- 把接近完成的變更交給 reviewer 時，保留最小 handoff 結構

這三類 artifact 不代表完整 workflow path，只是目前先定義的最小可辨識 path。

## Workflow Object Model

runtime 目前只需要辨識：
- workflow artifact 本身
- workflow artifact 被識別後的 recognition result
- recognition result 對 downstream 的 consequence class

### Object Types

1. **Workflow Artifact**  
   某個 workflow step 產出的、可被辨識的結構化檔案或文字輸出。

2. **Workflow Recognition Result**  
   runtime 對 artifact 的辨識結果，包括是否識別成功、是否完整，以及其 scope。

3. **Workflow Consequence Class**  
   當 recognition 缺失或不完整時，下游應如何解讀該缺口的影響等級。

## Artifact Envelope

entry-layer artifact 的最小 envelope：

- `artifact_type`
- `skill`
- `scope`
- `timestamp`
- `status`
- `provenance`

## 一句總結

entry-layer contract 的目標，不是把 workflow 變成新的 authority，而是讓 workflow artifact 至少能被 runtime 看見、辨識、並被 reviewer 正確解讀。
