# Execution Surface Coverage Plan

## 目的

這份文件定義 `runtime surface manifest` 之後的下一個最小步驟：

> 不是直接做 execution harness，
> 而是先定義 decision-aware execution coverage model。

目前 framework 已經有：

- execution / evidence / authority surface inventory
- manifest-first observability
- consistency smoke

但還沒有回答：

- 哪些 surface 是 decision 必要條件
- 哪些 surface 缺失會導致 false allow / false deny
- 哪些 surface 雖存在，但目前沒有被 coverage model 接住
- 哪些 coverage 缺失只該 warning，哪些應該 downgrade decision confidence

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
5. coverage 缺失時，decision 應該如何被標示或降級

也就是從：

- `有哪些 surface 存在`

進一步走到：

- `哪些 surface 應該存在且必須被觀測`
- `當這些 surface 不完整時，decision 是否仍可接受`

## First Slice 範圍

第一版不要做整套 coverage engine。

只做最小分類與 smoke：

### 1. Surface Classification

對每個 surface 補兩個最小維度：

- `coverage_role`
  - `decision`
  - `evidence`
  - `authority`
- `requirement_level`
  - `hard`
  - `soft`
  - `optional`
  - `unknown`

第一版先只標最核心的 surfaces，不追求全覆蓋。

### 2. Coverage Mapping

先定義少量 mapping，至少涵蓋：

- `pre_task_governance`
- `post_task_governance`
- `session_start_governance`
- `runtime_verdict_reviewability`
- `runtime_trace_reviewability`
- authority / escalation related surfaces

每個 mapping 改成 decision-level 定義，而不是只由 surface 自述。

每個 decision definition 回答：

- 這個 decision / evaluator 依賴哪些 execution surface
- 這個 decision / evaluator 依賴哪些 evidence surface
- 這個 decision / evaluator 依賴哪些 authority surface
- 哪些是 hard required，哪些只是 soft required
- 缺失後建議的最小 action hint 是什麼

### 3. Coverage Smoke

新增一個輕量 smoke，不跑 execution，只驗 coverage completeness。

第一版先檢查：

- hard required surface 是否缺失
- soft required surface 是否缺失
- evidence-required surface 是否缺失
- authority-required surface 是否缺失
- 是否存在 dead surface
- 是否存在未被任何 decision 使用的 unknown/optional surface

## 建議輸出

### Machine-readable

- `docs/status/generated/execution-surface-coverage.json`

### Human-readable

- `docs/status/execution-surface-coverage.md`

### Smoke

- `governance_tools/execution_surface_coverage_smoke.py`

## 最小分類模型

第一版建議的 surface schema 只要這麼小：

```json
{
  "surface_name": "pre_task_check",
  "surface_type": "runtime_entrypoint",
  "coverage_role": "decision",
  "requirement_level": "hard",
  "used_by": ["pre_task_governance"],
  "failure_modes_if_missing": [
    {
      "mode": "false_allow",
      "suggested_action": "require_review"
    },
    {
      "mode": "pseudo_allow",
      "suggested_action": "degrade_confidence"
    }
  ]
}
```

對 evidence / authority surface 也採同樣思路。

## Decision-Level Coverage Definition

第一版還需要補一個很小的 decision-level schema：

```json
{
  "decision": "post_task_governance",
  "required_surfaces": [
    "pre_task_check",
    "post_task_check"
  ],
  "evidence_surfaces": [
    "runtime-verdict",
    "runtime-trace"
  ],
  "authority_surfaces": [
    "human_approval"
  ],
  "requirement_level": {
    "pre_task_check": "soft",
    "post_task_check": "hard",
    "runtime-verdict": "hard",
    "runtime-trace": "hard",
    "human_approval": "soft"
  }
}
```

重點不是追求完整，而是讓 framework 能回答：

- 這個 decision 最小需要哪些 coverage
- 缺哪些時只能 warning
- 缺哪些時應該要求 reviewer 明確注意

## Failure Mode 對應

coverage model 第一版至少要對到這些 failure language：

- `false_allow`
- `false_deny`
- `pseudo_allow`
- `pseudo_deny`
- `blind_spot`

重點不是一次做完整 taxonomy，而是先讓 coverage 缺失和 failure mode 能對得起來，
並且至少能給出最小 action hint：

- `require_review`
- `degrade_confidence`
- `warn_only`

## Dead Surface 定義

第一版不要把所有 dead surface 混成同一類。

至少區分：

- `never_observed`
  - surface 存在，但沒有任何觀測或對應 signal
- `never_required`
  - surface 存在，但沒有被任何 decision coverage 使用

這樣 reviewer 才能分辨：

- 是 instrumentation 問題
- 還是設計冗餘 / 抽象過度

## 第一個 Consumer

第一版 coverage output 先只服務一個 consumer：

- `reviewer`

也就是：

- 讓 reviewer 看得出哪些 decision coverage 不完整
- 讓 reviewer 看得出哪些 surface 是 hard/soft requirement
- 讓 reviewer 看得出某個 warning 是 observability noise，還是 decision completeness 問題

第一版先不要直接接 runtime gate。

## 驗收條件

第一版完成時，至少要滿足：

1. coverage model 不重寫現有 governance semantics
2. coverage model 能指出 hard / soft required surface 缺失
3. coverage smoke 可對 dead/missing surface 發 signal
4. output 能讓 reviewer 看出：
   - 哪些 decision surface 已被 coverage 接住
   - 哪些 surface 仍屬 unknown / uncovered
5. output 能讓 reviewer 看出：
   - 缺失會造成什麼 failure mode
   - 建議 action hint 是什麼

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
- 缺失時 decision 會怎麼失真
- 這種缺失應被如何標示

### 3. 不要太早接主 gate

第一版 coverage smoke 先做獨立 signal，不直接掛進主 drift critical path。

## 一句話總結

> 下一步不是做 harness，而是先定義：
> 某個 decision 是否在可接受的 execution coverage 下做出，
> 以及 coverage 不完整時應該怎麼被標示。
