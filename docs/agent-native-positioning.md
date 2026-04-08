# Agent-Native 定位

> 狀態：positioning note
> 建立：2026-03-31
> 更新：2026-04-08
> 目的：說清楚這個 repo 為什麼對 AI 來說容易讀、容易採用，但又不把 AI 誤寫成 authority layer

---

## 觀察

近期多個 consuming repo 的 adopt / validation 行為顯示，這個 framework 對 AI 來說確實比一般只靠長篇 prose 的治理 repo 更容易理解與操作。

AI assistant 通常可以：

- 正確辨識 framework root
- 用 submodule 或 nested checkout 方式拉入 repo
- 找到 canonical adopt path
- 跑對 smoke / readiness / validation tooling
- 把 governance files 放進正確位置

這是有意義的結果，但它證明的是比較窄的一件事：

> 這個 repo 對機器來說高度可解讀、可載入、可導航。

這不等於它已經是 fully `agent-ready` system。

---

## 這不代表什麼

AI setup 很順，不代表 durable agent adoption 已經成立。

目前證據**還不能**證明：

- 跨 session 的 decision consistency 已穩定
- constraint adherence 已經長期可控
- drift 下的 failure-mode classification 已可靠
- policy enforcement 已不依賴 prompt interpretation
- 各工具、各作者之間的 agent adoption 已低維護

所以現在比較合理的區分是：

- setup success
- deployment success

而不是：

- decision-level integration
- full agent readiness

---

## 重要的不對稱

目前 repo 其實呈現兩種成熟度輪廓。

### Human self-serve maturity

這一側仍然受限於：

- onboarding 偏重
- governance surface 較多
- 概念密度高
- 某些地方仍依賴作者導讀

### Machine-consumption maturity

這一側已相對更強，因為：

- contract 明確
- boundary 文件成形
- runtime entrypoint 穩定
- artifact 可被讀取與追溯
- status / readiness / closeout surfaces 開始具有可機器消費的形狀

這是事實，但要小心解讀。

它不自動代表：

> repo 已經天生為 agent 設計完成。

另一個同樣合理的解讀是：

> AI 目前正在補償 human-facing interface layer 仍不夠薄的問題。

這兩種解讀差很多。

---

## 更準的系統表述

最準的說法不是 `Agent-Driven Governance`。

這個 repo 現在比較像：

> 一個 machine-interpretable governance runtime，
> 具備 AI-augmented 的 adoption 與 operation path。

也就是：

- runtime 和 policy 仍是 authority
- AI 可以加速載入、導航、執行與 reviewer-facing 消費
- AI 不能變成隱性的治理真相來源

一句話：

> AI 是 interface / acceleration layer，
> 不是 authority layer。

---

## 為什麼 AI 在這裡效果不錯

原因不是 AI 很神，而是這個 repo 越來越像一個小型治理 DSL：

- `contract` 像 schema
- decision model 像 execution semantics
- `pre_task_check` 像 interpreter
- artifact 像 trace log
- Decision Boundary Layer 像 constraint surface

LLM 天生比較擅長讀這種結構化、可推理的系統。

這是優勢，但也帶來設計義務：

> framework 必須盡量站在 deterministic、machine-checkable 的 runtime path 上，
> 而不是偷偷把 prompt interpretation 當成真正的 execution layer。

---

## 可行的對外定位

目前可以誠實主張的有：

- 它高度 machine-interpretable
- 它對 AI-assisted adoption 友善
- 它提供 AI 可操作的結構化 governance entrypoint
- 它比多數 prose-heavy framework 更 AI-comprehensible

目前**不應該**主張的有：

- fully agent-ready
- AI-led deployment 等於 governance adoption
- agent behavior 已 tool-independent 且 deterministic
- human onboarding 已經不再重要

所以比較穩的公開用詞仍然是：

- `AI-augmented governance runtime`
- `machine-interpretable governance runtime`

它們都比 `agent-ready` 更準、更能防止過度承諾。

---

## 如果被誤讀，會有什麼風險

### 風險 1：把 AI-native 當成忽略 interface gap 的理由

如果 AI 能跨過 repo，但人仍然覺得難，正確結論不是「問題解決了」。

更可能的結論是：

> human-facing interface layer 仍然不夠清楚。

### 風險 2：prompt flow 長成 shadow policy source

如果系統實際靠 prompt convention 在運作，而不是靠 runtime-enforced boundary，policy 就會越來越難驗證，也越容易 drift。

### 風險 3：deployment success 被誤當成 governance success

clone、pin、放對檔案都只是 deployment success。

真正的 governance adoption 還需要：

- verdict consistency
- 正確 escalation
- 可存活的升級路徑
- bounded duplicate truth source

---

## 這個解讀暗示的產品方向

下一步不是把所有文件都寫短，而是把 deterministic interface 更清楚地露出來，同時保留 AI 作為加速層。

比較有價值的後續方向是：

1. 定義最小 AI-facing interface
2. 保持 human onboarding 誠實
3. 把 authority 留在 runtime-enforced path

具體來說：

- AI quickstart 是合理的
- canonical prompt 可以有幫助
- 但 prompt 不能變成 policy
- CLI / runtime surface 仍比 prompt cleverness 更重要

---

## 與 Decision Boundary Layer 的關係

這個定位和 Decision Boundary Layer 是一致的。

repo 越能從 prose expectation 轉成 machine-consumable decision boundary，`AI-augmented` 這個說法就越可信。

但同一個警告仍成立：

> 如果只是增加結構，卻沒有改變可觀測 decision，
> 那增加的是文件，不是能力。

---

## 目前的成熟度判讀

從這個角度看，repo 現在比較準的描述是：

- human self-serve maturity：仍有限
- framework core maturity：已明顯更強
- machine-consumption maturity：足以支撐真實 AI-assisted adoption experiment

一個比較穩的工作標籤可以是：

> `beta-core, adoption-pre-beta, agent-loadable`

如果需要更強但仍保守的字眼，優先用：

- `machine-interpretable`
- `AI-comprehensible`
- `AI-augmented`

不要太快用：

- `agent-ready`
- `agent-driven`
