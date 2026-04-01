# Execution Surface Coverage Plan

## 目的

這份文件定義 `runtime surface manifest` 之後的下一個最小步驟：

> 不是直接做 execution harness，
> 而是先定義 execution surface coverage model。

目前 framework 已經有：

- execution / evidence / authority surface inventory
- manifest-first observability
- consistency smoke

但還沒有回答：

- 哪些 surface 是 decision 必要條件
- 哪些 surface 缺失會導致 false allow / false deny
- 哪些 surface 雖存在，但目前沒有被 coverage model 接住

## 為什麼現在不先做 harness

如果現在直接做 harness layer，風險是：

- 會在 coverage 未定義前先抽象 execution
- 可能做出 orchestration 看起來完整、但 decision completeness 不可驗證的 runtime
- 會把 execution runtime 和 governance runtime 再次混在一起

所以正確順序是：

1. runtime surface manifest
2. execution surface coverage model
3. execution harness layer

目前只完成了第 1 步。

## Step 2 的核心問題

這一步要讓 framework 能回答：

1. 哪些 execution surface 對某類 decision 是必需的
2. 哪些 evidence surface 對某類 evaluator 是必需的
3. 哪些 authority surface 對某類 escalation / approval path 是必需的
4. 缺失某個 surface 時，會導致什麼 failure mode

也就是從：

- `有哪些 surface 存在`

進一步走到：

- `哪些 surface 應該存在且必須被觀測`

## First Slice 範圍

第一版不要做整套 coverage engine。

只做最小分類與 smoke：

### 1. Surface Classification

對每個 surface 補一個最小分類：

- `required_for_decision`
- `required_for_evidence`
- `optional`
- `unknown`

第一版先只標最核心的 surfaces，不追求全覆蓋。

### 2. Coverage Mapping

先定義少量 mapping，至少涵蓋：

- `pre_task_check`
- `post_task_check`
- `session_start`
- `runtime-verdict`
- `runtime-trace`
- authority / escalation related surfaces

每個 mapping 回答：

- 這個 decision / evaluator 依賴哪些 execution surface
- 這個 decision / evaluator 依賴哪些 evidence surface
- 這個 decision / evaluator 依賴哪些 authority surface

### 3. Coverage Smoke

新增一個輕量 smoke，不跑 execution，只驗 coverage completeness。

第一版先檢查：

- required surface 是否缺失
- evidence-required surface 是否缺失
- authority-required surface 是否缺失
- 是否存在 dead surface

## 建議輸出

### Machine-readable

- `docs/status/generated/execution-surface-coverage.json`

### Human-readable

- `docs/status/execution-surface-coverage.md`

### Smoke

- `governance_tools/execution_surface_coverage_smoke.py`

## 最小分類模型

第一版建議的 schema 只要這麼小：

```json
{
  "surface_name": "pre_task_check",
  "surface_type": "runtime_entrypoint",
  "coverage_role": "required_for_decision",
  "used_by": ["pre_task_governance"],
  "failure_modes_if_missing": [
    "false_allow",
    "pseudo_allow"
  ]
}
```

對 evidence / authority surface 也採同樣思路。

## Failure Mode 對應

coverage model 第一版至少要對到這些 failure language：

- `false_allow`
- `false_deny`
- `pseudo_allow`
- `pseudo_deny`
- `blind_spot`

重點不是一次做完整 taxonomy，而是先讓 coverage 缺失和 failure mode 能對得起來。

## 驗收條件

第一版完成時，至少要滿足：

1. coverage model 不重寫現有 governance semantics
2. coverage model 能指出 required surface 缺失
3. coverage smoke 可對 dead/missing surface 發 signal
4. output 能讓 reviewer 看出：
   - 哪些 decision surface 已被 coverage 接住
   - 哪些 surface 仍屬 unknown / uncovered

## 非目標

第一版不做：

- execution harness
- multi-agent orchestration
- runtime introspection
- dynamic path coverage
- hard enforcement
- verdict precedence 重寫

## 風險控制

### 1. 不要變成新 rule engine

coverage model 只描述 completeness，不重新定義 policy。

### 2. 不要把 inventory 和 coverage 混在一起

manifest 回答：

- 有哪些 surface

coverage model 回答：

- 哪些 surface 對 decision completeness 是必要的

### 3. 不要太早接主 gate

第一版 coverage smoke 先做獨立 signal，不直接掛進主 drift critical path。

## 一句話總結

> 下一步不是做 harness，而是先定義：
> execution 跑得夠不夠、哪些 surface 缺失會讓 decision 失真。
