# Governance Runtime v2.6

<!-- anchors: Governance Constraint Layer | Violation Handling Matrix | Determinism Contract -->

> 更新日期：2026-03-20

這份文件記錄 current runtime spine 之後的下一個架構方向：

> 從「混合式 enforcement，夾帶少量 hard stop」，
> 走向「以 runtime 為中心、能明確處理 constraint 的 decision system」。

對應的 machine-readable artifact 是：

- `governance/governance_decision_model.v2.6.json`

---

## 為什麼需要 v2.6

目前 repo 已經有：

- 真實 runtime path
- external domain contracts
- validator execution
- evidence ingestion
- 部分 `hard_stop_rules`

這證明接縫已經是真的，但整體仍屬 transitional enforcement model。

真正缺的是一層能穩定回答下列問題的 constraint layer：

1. 這個 task 在什麼前提下可以開始？
2. 缺少哪些 evidence 時應降級、升級或停止？
3. 哪些 change class 超出目前允許邊界？
4. 哪些 decision 應能被 reviewer 從 artifact 重建？

---

## v2.6 的目標

v2.6 不是要把 framework 變成更大的 orchestration platform。  
它要做的是把 runtime decision system 的幾個核心面收斂清楚：

- constraint handling
- degradation path
- evidence-aware decision
- reviewer-reconstructable artifact

換句話說，v2.6 追求的是：

> decision system 的一致性與可重建性，
> 不是功能面積的擴張。

---

## 核心轉變

從舊形態：

- 規則分散在多個 surface
- 某些 hard stop 是局部 patch
- reviewer 需要用大量人工理解把訊號拼回來

轉到較清楚的形態：

- constraint 有可辨識位置
- degradation path 可追溯
- verdict 不是單純 pass / stop，而是 bounded decision outcome
- artifact 能說明為什麼這次被限制、升級或停止

---

## 核心組件

### 1. Contract

`contract.yaml` 仍是 repo-local governance runtime 的主要入口之一。  
它應負責提供：

- repo / domain identity
- rule pack roots
- task-level boundary
- precondition / closeout / evidence 相關設定

### 2. Runtime hooks

`session_start`、`pre_task_check`、`post_task_check`、`session_end` 是 decision runtime 的骨架。

它們不應各自長出獨立 authority，而應共享一致的 decision model。

### 3. Evidence ingestion

runtime 需要的不只是規則，也包括：

- validator outputs
- public API diff
- test / typecheck 結果
- closeout / session summary

沒有 evidence，decision 只能是假裝嚴格。

### 4. Degradation / escalation path

v2.6 特別強調：

- 缺前提時不一定直接 stop
- 但也不能裝作沒事 pass

所以系統必須支援：

- `analysis_only`
- `restrict_code_generation_and_escalate`
- `review_required`
- `stop`

這類 bounded outcome。

---

## 和 DBL / advisory / closeout 的關係

這份文件是較高層的 runtime direction，不取代後續 slice 文件。

它和其他線的關係是：

- DBL：補強 pre-decision constraint
- advisory：補齊 reviewer-visible semantics，但不偷渡 authority
- closeout：讓 session 結束時的 decision surface 可被 canonical 化與審核

它們都屬 v2.6 之後 runtime-centered decision system 的不同側面。

---

## Non-goals

v2.6 不主張：

- full execution harness
- generic multi-agent orchestration
- 把所有 reviewer signal 都變成 machine-authoritative verdict input
- 以更大 surface 取代邏輯清楚的 bounded runtime

---

## 一句話結論

`Governance Runtime v2.6` 的重點，不是再新增更多 runtime feature，而是把既有 contract、evidence、constraint、degradation 與 artifact 收斂成一個更一致、可重建的 decision system。
