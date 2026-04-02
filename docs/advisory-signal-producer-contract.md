# Advisory Signal Producer Contract

## Purpose

這份文件定義 advisory signal producer 的最小責任邊界。

第一版只處理 advisory-only signal，不處理 general signal universe，也不把 advisory infrastructure 升格成 verdict substrate。

它的目的是：
- 定義誰可以產生 advisory signal
- 定義產生時最少要帶哪些欄位
- 限制 advisory signal 不能暗示或偷渡的語義

這份 contract 不等於 general runtime signal schema，也不代表 advisory signal 已準備好進入 final verdict。

## Scope

這份 contract 目前只適用於已存在、且已被 runtime 或 docs 觸碰到的三個 signal：
- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Producer Responsibilities

每個 advisory signal producer 在第一版至少要明示五件事：

1. `producer_identity`
- 誰產生這個 signal
- 不只 module name，也要說出語義角色

2. `signal_class`
- 必須明講自己屬於哪一類：
  - `degradation_advisory`
  - `behavioral_advisory`
  - `evidence_advisory`

3. `decision_distance`
- 必須明講與 decision 的距離：
  - `far`
  - `near`
  - `adjacent`
  - `enforced_elsewhere`

4. `non_proof_declaration`
- 必須明講：
  - `not_proof_of_compliance`
  - `not_proof_of_violation`
  - `not_verdict_bearing`

5. `observation_basis`
- 必須說清楚 signal 是依據什麼觀測基礎產生：
  - `environment_state`
  - `file_read_coverage_proxy`
  - `evidence_presence_check`
  - `execution_trace_fragment`

## Minimal Contract Shape

第一版 advisory producer contract 的最小骨架：

```yaml
signal_name: require_full_read_for_large_files
producer_identity:
  module: governance_tools.runtime_injection_observation
  role: observation_proxy_evaluator
signal_class: degradation_advisory
decision_distance: far
non_proof_declaration:
  not_proof_of_compliance: true
  not_proof_of_violation: true
  not_verdict_bearing: true
observation_basis:
  type: file_read_coverage_proxy
  note: large-file visibility proxy only
signal_specific_caveat: does not imply relevant section coverage
```

## Required Fields

第一版 producer 至少要能對應出以下欄位：

| Field | Required | Purpose |
|---|---|---|
| `signal_name` | yes | 穩定識別 signal |
| `producer_identity.module` | yes | 指出哪個模組產生 |
| `producer_identity.role` | yes | 指出 producer 的語義角色 |
| `signal_class` | yes | 避免 warning 類型模糊 |
| `decision_distance` | yes | 避免 downstream 自行腦補位階 |
| `non_proof_declaration` | yes | 防止 advisory 被偷渡成 proof |
| `observation_basis.type` | yes | 表明 signal 的觀測基礎 |
| `signal_specific_caveat` | recommended | 保留 signal-specific 細節，不要被通用骨架壓平 |

## Current Signal Producers

| Signal | Producer identity | Signal class | Decision distance | Observation basis | Notes |
|---|---|---|---|---|---|
| `context_degraded` | `runtime_hooks.core.pre_task_check` / `snapshot_derived_runtime_checker` | `degradation_advisory` | `enforced_elsewhere` | `environment_state` | 目前透過 runtime injection trigger 產生，已有 escalation effect |
| `required_evidence_missing` | `runtime_hooks.core.pre_task_check` / `decision_boundary_and_evidence_checker` | `evidence_advisory` | `enforced_elsewhere` | `evidence_presence_check` | 雖在 advisory family 中，但已有 escalation / stop adjacency |
| `require_full_read_for_large_files` | `governance_tools.runtime_injection_observation` / `observation_proxy_evaluator` | `degradation_advisory` | `far` | `file_read_coverage_proxy` | 目前只表示 visibility / truncation risk，不代表 relevant section coverage |

## Contract Rules

第一版 producer contract 先寫死以下規則：

- advisory producer 不得暗示 signal 自動構成 compliance proof
- advisory producer 不得暗示 signal 自動構成 violation proof
- advisory producer 不得把 advisory signal 包裝成 verdict-bearing result
- producer metadata 完整，不等於 signal 已可安全進入 final verdict
- signal-specific caveat 不得被通用骨架消掉

## What This Contract Does Not Do

這份 contract 第一版不做：
- general signal schema
- enforcement signal schema
- producer registration system
- runtime hard gate
- signal precedence model

## Current Posture

目前這份 contract 的定位是：
- advisory-only
- minimal
- producer responsibility first
- non-proof-bearing by default

它的作用是把 advisory signal 的 metadata 與責任先釘住，避免後續因為欄位愈來愈完整，就被誤讀成可以更正式地進 verdict。

## Next Move

下一步如果繼續，應優先考慮：
- 將這份 producer contract 對應回既有 reviewer / trace surface
- 或驗證目前欄位中哪些真的被 consumer 使用

而不是直接升級成 general signal contract。
