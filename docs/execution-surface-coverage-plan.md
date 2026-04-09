# Execution Surface Coverage 計畫：從 surface inventory 走向 decision-aware coverage

## 目的

`runtime surface manifest` 解決的是「有哪些 surface 存在」。  
這份 plan 則要進一步回答：

> 哪些 surface 對 decision completeness 是必要的？
> 缺少哪些 surface 會導致 false allow、pseudo allow 或 blind spot？

這份計畫不是要直接做 execution harness，而是先建立 decision-aware execution coverage model。

## 為什麼現在不先做 harness

如果 coverage model 還沒定義就先做 harness，很容易出現：
- coverage 還不知道要涵蓋什麼，就先設計 orchestration
- runtime 看起來完整，但 decision completeness 沒有被驗證
- execution substrate 與 governance runtime 再次糾纏

因此順序應是：
1. runtime surface manifest
2. execution surface coverage model
3. execution harness layer

## 這份 plan 要回答的問題

framework 需要回答：
- 哪些 execution surface 對 decision 是 required
- 哪些 evidence surface 缺失會讓 decision quality 下降
- 哪些 authority surface 缺失會導致 escalation / approval path 失真
- 哪些 surface 是 dead surface

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

不是只讓 surface 說自己被誰使用，而是讓 decision 明確說自己需要哪些 surface。

範例：

```json
{
  "decision": "post_task_governance",
  "required_surfaces": ["pre_task_check", "post_task_check"],
  "evidence_surfaces": ["runtime-verdict", "runtime-trace"],
  "authority_surfaces": ["human_approval"]
}
```

### 3. Coverage Smoke

coverage smoke 檢查的是 completeness，不是 execution 成功與否。

目前 first slice 先看：
- `missing_hard_required`
- `missing_soft_required`
- `dead_never_observed`
- `dead_never_required`

## Failure Mode Mapping

coverage model 需要能映射到 failure language，例如：
- `false_allow`
- `false_deny`
- `pseudo_allow`
- `pseudo_deny`
- `blind_spot`

這樣 coverage 才不只是 inventory，而是 decision-aware signal。

## 一句總結

這份計畫的重點不是把 execution 跑起來，而是定義：某個 decision 是否在可接受的 execution coverage 條件下做出。
