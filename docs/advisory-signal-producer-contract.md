# Advisory Signal Producer Contract：producer 責任與最小 metadata 契約

## 目的

這份文件定義 advisory signal producer 的最小責任邊界。
它只處理 `advisory-only` signal，不試圖涵蓋整個 signal universe，也不把 advisory infrastructure 誤升格成 verdict substrate。

這份 contract 的目標是：
- 定義哪些模組可以產生 advisory signal
- 定義 producer 至少要提供哪些 metadata
- 防止 advisory signal 被 downstream 誤用成 proof 或 verdict input

## 範圍

這份 contract 目前只覆蓋已在 runtime / docs 中被正式引用的 signal：
- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Producer Responsibilities

每個 advisory signal producer 至少要明示以下欄位：

1. `producer_identity`
   - 說明是誰產生這個 signal
   - 不只提供 module name，還要提供語義角色

2. `signal_class`
   - 明示 signal 所屬類別：
     - `degradation_advisory`
     - `behavioral_advisory`
     - `evidence_advisory`

3. `decision_distance`
   - 說明這個 signal 與 decision authority 的距離：
     - `far`
     - `near`
     - `adjacent`
     - `enforced_elsewhere`

4. `non_proof_declaration`
   - 明示這個 signal：
     - `not_proof_of_compliance`
     - `not_proof_of_violation`
     - `not_verdict_bearing`

5. `observation_basis`
   - 說明 signal 依據哪種觀測基礎產生：
     - `environment_state`
     - `file_read_coverage_proxy`
     - `evidence_presence_check`
     - `execution_trace_fragment`

## 最小 contract 範例

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

## 欄位要求

| Field | Required | Purpose |
|---|---|---|
| `signal_name` | yes | 辨識 signal |
| `producer_identity.module` | yes | 對應程式模組 |
| `producer_identity.role` | yes | 說明 producer 的語義角色 |
| `signal_class` | yes | 防止 signal 被壓扁成 generic warning |
| `decision_distance` | yes | 防止 downstream 自行腦補權限 |
| `non_proof_declaration` | yes | 明示 advisory 的邊界 |
| `observation_basis.type` | yes | 說明觀測基礎 |
| `signal_specific_caveat` | recommended | 保留 signal-specific caveat |

## Current Signals

| Signal | Producer identity | Signal class | Decision distance | Observation basis | Notes |
|---|---|---|---|---|---|
| `context_degraded` | `runtime_hooks.core.pre_task_check` / `snapshot_derived_runtime_checker` | `degradation_advisory` | `enforced_elsewhere` | `environment_state` | 由 runtime injection trigger 帶出，具有既有 escalation effect |
| `required_evidence_missing` | `runtime_hooks.core.pre_task_check` / `decision_boundary_and_evidence_checker` | `evidence_advisory` | `enforced_elsewhere` | `evidence_presence_check` | 屬於 advisory family，但已與 escalation / stop 路徑相鄰 |
| `require_full_read_for_large_files` | `governance_tools.runtime_injection_observation` / `observation_proxy_evaluator` | `degradation_advisory` | `far` | `file_read_coverage_proxy` | 只表示 visibility / truncation risk，不代表 relevant section coverage |

## Contract Rules

- advisory producer 不得把 signal 宣稱為 compliance proof
- advisory producer 不得把 signal 宣稱為 violation proof
- advisory producer 不得產出 verdict-bearing result
- producer metadata 不得被包裝成 final verdict authority
- `signal_specific_caveat` 不得被 downstream 移除

## Non-Goals

這份 contract 目前**不做**：

- general signal schema
- enforcement signal schema
- producer registration system
- runtime hard gate
- signal precedence model

## Current Posture

目前 producer contract 的姿態是：

- advisory-only
- minimal
- 強調 producer responsibility
- 明確 `non-proof-bearing`

後續如果要擴張 advisory producer contract，應先證明 metadata 已被 reviewer / trace surface 正確消費，而不是只增加欄位數量。
