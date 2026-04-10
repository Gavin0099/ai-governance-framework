# Decision Boundary First Slice

> 更新日期：2026-03-31
> 相關文件：`docs/decision-boundary-layer.md`, `docs/dbl-first-slice-validation-plan.md`

---

## 目的

這份文件定義 `Decision Boundary Layer` 的第一個可執行切片。

第一刀不追求完整 DBL，而是先證明一件事：

> pre-decision boundary 可以在 runtime surface 上形成一個 bounded、可觀測、可 reviewer 重建的 decision layer。

---

## First Slice 的範圍

`Slice 1` 只處理 **precondition handling**。

也就是：

- implementation proposal 是否缺少必要前提
- 缺失狀態是否被顯式表達
- 缺失時是否能依 task level 走出一致的 degradation path

這一刀先不做：

- 完整 identity constraint
- 完整 invariant library
- 廣泛 capability policy engine
- 多層 DBL schema rollout

---

## 為什麼先做 precondition

precondition 最適合 first slice，因為它同時滿足幾個條件：

- failure mode 清楚
- reviewer 容易重建
- 缺失狀態可直接表達
- verdict 容易對應到 `warning / escalate / stop`

典型例子：

- parser 沒有 sample data
- protocol implementation 沒有 spec
- migration 沒有 rollback plan

---

## Slice 1 的 runtime 行為

### `L0`

- 允許 exploration / analysis-only
- 需要明確 warning
- 不應假裝已滿足 precondition

### `L1`

- 不應直接當作完整可實作狀態
- 應進入 `escalate`
- reviewer 應能看到缺少什麼

### `L2`

- 若 correctness 依賴該前提，應進 `stop`
- 不應用 narrative 把缺失合理化

---

## First Slice 要證明什麼

這個 slice 不只是 demo，它要證明：

1. precondition 可以在 runtime verdict 中被顯式看見
2. 缺失狀態可以進 trace / artifact
3. reviewer 能從 artifact 重建缺失原因
4. runtime 不會把缺失誤說成 capability proof

---

## 不做什麼

first slice 刻意不做：

- full DBL schema
- complete identity routing
- full invariant coverage
- multi-layer authority engine

這些都留到後續切片，不在這一刀一起追。

---

## 一句話

`Decision Boundary First Slice` 的目標不是完成整個 DBL，而是先把「missing precondition 會改變 decision posture」這件事做成可運作、可 reviewer 重建的 runtime surface。
