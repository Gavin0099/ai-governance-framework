# Advisory Signal Producer Contract

## 目的

這份文件定義 advisory signal producer 的最小責任邊界。

它只處理 advisory-only signal，不處理 general signal universe，也不把 advisory infrastructure 包裝成 verdict substrate。

它的作用是：
- 定義誰可以產生 advisory signal
- 定義 producer 至少要明示哪些 metadata
- 防止 advisory signal 被 downstream 誤當成 proof 或 verdict input

## 範圍

這份 contract 目前只涵蓋已在 runtime 或 docs 中出現的三個 signal：
- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Producer Responsibilities

每個 advisory signal producer 至少要明示以下欄位：

1. `producer_identity`
- 誰產生這個 signal
- 不只 module name，也要有語義角色

2. `signal_class`
- 這個 signal 屬於哪一類：
  - `degradation_advisory`
  - `behavioral_advisory`
  - `evidence_advisory`

3. `decision_distance`
- 這個 signal 距 decision 的距離：
  - `far`
  - `near`
  - `adjacent`
  - `enforced_elsewhere`

4. `non_proof_declaration`
- 至少要明示：
  - `not_proof_of_compliance`
  - `not_proof_of_violation`
  - `not_verdict_bearing`

5. `observation_basis`
- signal 是根據什麼觀測基礎產生：
  - `environment_state`
  - `file_read_coverage_proxy`
  - `evidence_presence_check`
  - `execution_trace_fragment`

## 最小 contract 形狀

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

## 必填欄位

| Field | Required | Purpose |
|---|---|---|
| `signal_name` | yes | 識別 signal |
| `producer_identity.module` | yes | 模組來源 |
| `producer_identity.role` | yes | producer 的語義角色 |
| `signal_class` | yes | 避免 generic warning 混淆 |
| `decision_distance` | yes | 限制 downstream 濫用 |
| `non_proof_declaration` | yes | 避免 advisory 被誤升格 |
| `observation_basis.type` | yes | 說清觀測依據 |
| `signal_specific_caveat` | recommended | 保留 signal-specific caveat |

## 當前 signal producers

| Signal | Producer identity | Signal class | Decision distance | Observation basis | Notes |
|---|---|---|---|---|---|
| `context_degraded` | `runtime_hooks.core.pre_task_check` / `snapshot_derived_runtime_checker` | `degradation_advisory` | `enforced_elsewhere` | `environment_state` | 來自 runtime injection trigger，已有 escalation effect |
| `required_evidence_missing` | `runtime_hooks.core.pre_task_check` / `decision_boundary_and_evidence_checker` | `evidence_advisory` | `enforced_elsewhere` | `evidence_presence_check` | 屬 advisory family，但與 escalation / stop 相鄰 |
| `require_full_read_for_large_files` | `governance_tools.runtime_injection_observation` / `observation_proxy_evaluator` | `degradation_advisory` | `far` | `file_read_coverage_proxy` | 表示 visibility / truncation risk，不代表 relevant section coverage |

## Contract Rules

- advisory producer 不得把 signal 表述成 compliance proof
- advisory producer 不得把 signal 表述成 violation proof
- advisory producer 不得輸出 verdict-bearing result
- producer metadata 不得自動升格成 final verdict authority
- signal-specific caveat 不得省略到讓 downstream 誤讀

## 這份 contract 不做什麼

- general signal schema
- enforcement signal schema
- producer registration system
- runtime hard gate
- signal precedence model

## 當前 posture

目前這份 contract 的定位是：
- advisory-only
- minimal
- producer responsibility first
- non-proof-bearing by default

它的目的不是讓 advisory signal 看起來更正式，而是限制其權力外溢。

## 下一步

若要往前走，下一步應該是：
- 把這份 producer contract 接到 reviewer / trace surface
- 驗證這些 metadata 是否真的被 consumer 理解

而不是先擴成 general signal contract。
