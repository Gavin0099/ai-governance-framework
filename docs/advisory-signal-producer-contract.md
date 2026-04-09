# Advisory Signal Producer Contract：advisory signal producer 最小責任

## 目的

這份文件定義 advisory signal producer 的最小責任邊界。

它只處理 `advisory-only` signal，不處理一般 signal universe，也不把 advisory infrastructure 長成 verdict substrate。

核心目標：

- 定義誰可以產生 advisory signal
- 定義 producer 至少要帶哪些 metadata
- 防止 advisory signal 被 downstream 誤當成 proof 或 verdict input

## 範圍

目前 contract 只涵蓋 runtime / docs 已經實際使用的三個 signal：

- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Producer Responsibilities

每個 advisory signal producer 至少要明示以下欄位：

1. `producer_identity`
   - 誰產生這個 signal
   - 不只 module name，還要有角色描述

2. `signal_class`
   - 明確聲明這個 signal 屬於哪一類：
     - `degradation_advisory`
     - `behavioral_advisory`
     - `evidence_advisory`

3. `decision_distance`
   - 說清楚這個 signal 離真正 decision authority 有多近：
     - `far`
     - `near`
     - `adjacent`
     - `enforced_elsewhere`

4. `non_proof_declaration`
   - 明確標示：
     - `not_proof_of_compliance`
     - `not_proof_of_violation`
     - `not_verdict_bearing`

5. `observation_basis`
   - 說清楚 signal 是根據什麼觀測基礎產生：
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
| `signal_name` | yes | 標識 signal |
| `producer_identity.module` | yes | 指出來源模組 |
| `producer_identity.role` | yes | 定義 producer 的責任角色 |
| `signal_class` | yes | 避免 signal 被壓成 generic warning |
| `decision_distance` | yes | 限制 downstream 的解讀範圍 |
| `non_proof_declaration` | yes | 防止 advisory 越權 |
| `observation_basis.type` | yes | 說明證據基礎 |
| `signal_specific_caveat` | recommended | 保留 signal-specific caveat |

## Current Signals

| Signal | Producer identity | Signal class | Decision distance | Observation basis | Notes |
|---|---|---|---|---|---|
| `context_degraded` | `runtime_hooks.core.pre_task_check` / `snapshot_derived_runtime_checker` | `degradation_advisory` | `enforced_elsewhere` | `environment_state` | 由 runtime injection trigger 帶出，會進 escalation effect |
| `required_evidence_missing` | `runtime_hooks.core.pre_task_check` / `decision_boundary_and_evidence_checker` | `evidence_advisory` | `enforced_elsewhere` | `evidence_presence_check` | 雖屬 advisory family，但已與 escalation / stop 相鄰 |
| `require_full_read_for_large_files` | `governance_tools.runtime_injection_observation` / `observation_proxy_evaluator` | `degradation_advisory` | `far` | `file_read_coverage_proxy` | 只代表 visibility / truncation risk，不代表 relevant section coverage |

## Contract Rules

- advisory producer 不得把 signal 表述成 compliance proof
- advisory producer 不得把 signal 表述成 violation proof
- advisory producer 不得直接產出 verdict-bearing result
- producer metadata 不得自行升格成 final verdict authority
- `signal_specific_caveat` 不得被 downstream 忽略

## Non-Goals

這份 contract 目前不是：

- general signal schema
- enforcement signal schema
- producer registration system
- runtime hard gate
- signal precedence model

## Current Posture

目前的 producer contract 是：

- advisory-only
- minimal
- 以 producer responsibility 為主
- 預設為 non-proof-bearing

這樣做的目的，是先把 advisory signal 的責任邊界固定下來，再決定 reviewer / trace surface 是否真的需要更多 metadata。
