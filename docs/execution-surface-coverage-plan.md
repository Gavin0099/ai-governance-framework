# Execution Surface Coverage Plan：從 surface inventory 走到 decision-aware coverage

## 目的

`runtime surface manifest` 已經回答了「有哪些 surface 存在」。  
這份 plan 要回答的是：

> 哪些 surface 對 decision completeness 是必要的？  
> 缺了哪些 surface 會導致 false allow / pseudo allow / blind spot？

這一步不是做 execution harness，而是建立 decision-aware execution coverage model。

## 為什麼現在不是先做 harness

如果在 coverage model 之前就先做 harness，會出現三個問題：

- coverage 尚未定義，就先抽象 execution
- orchestration 看起來很完整，但沒有 completeness 保證
- execution runtime 與 governance runtime 的邊界會再度混掉

所以正確順序是：

1. runtime surface manifest
2. execution surface coverage model
3. execution harness layer

## 這一步要解的問題

這份 plan 要讓 framework 能回答：

- 哪些 execution surface 對某個 decision 是 required
- 哪些 evidence surface 缺失會導致 decision quality 下降
- 哪些 authority surface 缺失會造成 escalation / approval path 不完整
- 哪些 surface 已存在但其實是 dead surface

## First Slice

### 1. Surface Classification

每個 surface 先標兩個維度：

- `coverage_role`
  - `decision`
  - `evidence`
  - `authority`
- `requirement_level`
  - `hard`
  - `soft`
  - `optional`
  - `unknown`

### 2. Decision-Level Coverage Definition

不要只讓 surface 自己說自己被誰使用，而是要讓每個 decision 說自己需要什麼。

例如：

```json
{
  "decision": "post_task_governance",
  "required_surfaces": ["pre_task_check", "post_task_check"],
  "evidence_surfaces": ["runtime-verdict", "runtime-trace"],
  "authority_surfaces": ["human_approval"]
}
```

### 3. Coverage Smoke

coverage smoke 檢查的是 completeness，不是 execution 本身。

它應至少能指出：

- `missing_hard_required`
- `missing_soft_required`
- `dead_never_observed`
- `dead_never_required`

## Failure Mode Mapping

coverage model 要能對應 failure language，例如：

- `false_allow`
- `false_deny`
- `pseudo_allow`
- `pseudo_deny`
- `blind_spot`

並提供最小 action hint，例如：

- `require_review`
- `degrade_confidence`
- `warn_only`

## Consumers

第一個 consumer 應該是 reviewer，而不是 runtime gate。

目前較合理的輸出面：

- `docs/status/generated/execution-surface-coverage.json`
- `docs/status/execution-surface-coverage.md`
- `governance_tools/execution_surface_coverage_smoke.py`

## 非目標

這份 plan 目前不做：

- execution harness
- multi-agent orchestration
- dynamic runtime introspection
- hard enforcement
- verdict precedence 改寫

## 一句話結論

這份 plan 的目的，不是讓 execution 跑得更花，而是定義：decision 若要被視為可接受，至少需要哪些 execution / evidence / authority coverage。
