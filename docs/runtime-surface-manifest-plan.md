# Runtime Surface Manifest 計畫：把 runtime surface 顯性化

> 狀態：draft  
> 日期：2026-04-01

## 目的

這份計畫的目的，是替 repo 建立一份 execution / evidence / authority surface 的 inventory-first 視圖。

它不是新的 governance model，也不是 agent harness，而是：

- 先把有哪些 runtime surface 寫清楚
- 讓 reviewer / agent / adopter 知道 framework 實際在跑哪些面向
- 為後續 consistency smoke 與 coverage model 打底

## 為什麼需要 manifest

目前 repo 已經有：

- runtime hooks
- evidence normalization
- verdict / trace artifacts
- reviewer handoff
- authority / policy files

但如果沒有一份 manifest，外部很難快速回答：

- 目前有哪些 adapter family
- 哪些 runtime entrypoint 真正在 decision path 中
- 哪些 tool / smoke / audit surface 屬於治理系統
- 哪些輸出算 first-class evidence surface
- authority boundary 的正式來源有哪些

## First Slice 要列哪些東西

### 1. Adapter Inventory

記錄：

- `adapter_family`
- `supported_events`
- `normalizer_path`
- `runner_path`
- `contract_dependency`

### 2. Runtime Entrypoint Inventory

記錄：

- `entrypoint_name`
- `path`
- `category`
- `input_mode`
- `primary_output`
- `artifact_effect`

### 3. Governance Tool Entry Inventory

記錄：

- `tool_name`
- `category`
- `canonical_use`
- `human_track`
- `agent_track`
- `produces_artifact`

### 4. Evidence Surface Inventory

記錄：

- `surface_name`
- `producer`
- `artifact_type`
- `machine_readable`
- `human_auditable`
- `used_by`

### 5. Authority Boundary Inventory

記錄：

- `authority_surface`
- `declared_source`
- `scope`
- `can_change_verdict`
- `notes`

## 輸出形式

### Machine-readable

- `docs/status/generated/runtime-surface-manifest.json`

### Human-readable

- `docs/status/runtime-surface-manifest.md`

## 建議推進順序

1. 先定義 first-slice scope
2. 建立 extraction table
3. 產出 JSON
4. 產出 human summary
5. 補 consistency smoke

## Manifest Consistency Signals

first slice 之後，應逐步支援最小 consistency signal：

- `unknown_surface`
- `orphan_surface`
- `evidence_surface_mismatch`

這些 signal 的定位應是：

- soft enforcement
- non-invasive
- 不直接改 verdict

## 非目標

這份計畫目前不做：

- semantic policy engine
- maturity score / risk score
- execution harness
- runtime hard gate

## 一句話結論

manifest 的價值不在於多一份 JSON，而在於讓這個 repo 的 runtime reality 可以被 inventory-first 地看見與檢查。
