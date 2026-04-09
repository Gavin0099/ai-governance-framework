# Decision Boundary Layer

> 狀態：提案中的設計方向
> 建立日期：2026-03-31
> 目的：在 AI-assisted implementation 與 machine-interpretable governance runtime 之間建立可執行的 pre-decision constraint surface

---

## 為什麼需要這一層

目前 framework 已經有多個 runtime / reviewer-facing surface，例如：

- `session_start`
- `pre_task_check`
- `post_task_check`
- drift checks
- artifacts / reviewer handoff

但這些 surface 多半處理 discipline、evidence、replay、review 與 escalation。  
它們還沒有正式回答這個問題：

> 在實作開始之前，系統能不能用可重建、可追溯、可審核的方式，對 implementation proposal 施加真正會改變 verdict 的限制？

`Decision Boundary Layer` 就是用來承接這件事的最小執行層。

---

## 核心想法

repo-specific context 不應只停在「補充說明」。

它應該能回答：

> 哪些 implementation proposal 即使表面合理，只要碰到 repo identity、local invariant、precondition 或 capability boundary，就應該被限制、降級、升級或停止。

也就是說，這一層不是再多一份 repo note，而是要把下列內容轉成 governance-relevant decision input：

- repo / domain identity
- local invariant
- precondition requirement
- change capability boundary
- degradation / stop path

---

## 四層約束模型

### Layer 0：Identity Constraint

回答：
- 這個 repo 本質上是什麼
- 哪些 solution framing 從一開始就不適合

例子：
- 韌體工具，不是 GUI app
- CLI-first tool，不是 web service

範例：

```yaml
repo_identity:
  repo_type: firmware_tool
  repo_purpose: usb_hub_firmware_update
  forbidden_misclassification:
    - gui_application
    - web_service
```

這層目前較適合當：

- routing input
- reviewer trace
- 後續 bounded enforcement 候選

第一階段不應讓 identity 單獨把 verdict 改成 `stop`。

### Layer 1：Invariant Constraint

回答：
- 這個 repo / domain 有哪些不可破壞的行為邊界

例子：
- matching 必須 automatic
- 不允許 manual selector UI
- flashing path 不可 silent fallback

範例：

```yaml
local_invariants:
  forbidden_patterns:
    - manual_matching_selector
    - silent_fallback_write_path
  required_behavior:
    - automatic_matching_only
```

這層的作用不是寫成散文警告，而是把 invariant violation 導入可追溯的 decision path。

### Layer 2：Precondition Constraint

回答：
- 某類 implementation 開始前，是否已具備最低前提

例子：
- parser 沒有 sample files
- protocol implementation 沒有 spec
- migration 沒有 rollback plan

範例：

```yaml
preconditions:
  sample_data:
    required_for:
      - pdf_parser
    degradation:
      L0: allow_exploration_with_warning
      L1: escalate
      L2: stop
  spec_validation:
    required_sections:
      - protocol_definition
      - error_handling
      - boundary_conditions
    degradation:
      L0: analysis_only
      L1: escalate
      L2: stop
```

這一層最適合做 first slice，因為：

- failure mode 明確
- reviewer 容易重建
- verdict 可直接變化
- 可先從 explicit missing-state 做起

### Layer 3：Capability Constraint

回答：
- 這次 task 被允許動到哪種層級的變更

例子：
- 允許 local module patch
- 不允許 public API break
- 不允許 new framework introduction

範例：

```yaml
capability_constraints:
  allowed_change_scope:
    - local_module_only
  forbidden_change_classes:
    - public_api_break
    - new_framework_introduction
    - cross_module_refactor
```

這層通常要與既有 scope / evidence / diff surface 對齊，而不是另外長出一套新 authority。

---

## 和 repo note / `CLAUDE.md` 的關係

repo-local context file 很有價值，但它不應該獨自承擔治理權限。

較合理的分工是：

- `CLAUDE.md` / repo note
  - vocabulary
  - orientation
  - 主要路徑與 entrypoint
  - canonical source links

- Decision Boundary Layer
  - hard-stop / degrade logic
  - task gate
  - precondition check
  - capability restriction
  - runtime-consumable constraint

也就是：

- `CLAUDE.md` 負責 framing
- DBL 負責 bounded enforcement candidate

---

## 和 runtime decision model 的整合

這一層不是平行系統，而是應該掛進現有 runtime path：

- `session_start`
  - 顯示 identity / framing preview
- `pre_task_check`
  - 驗 preconditions
  - 檢查 capability overreach
- decision model / runtime verdict path
  - 套用 degradation / escalation

trace output 至少應能回答：

- 哪些 constraint 被載入
- 哪些 constraint 被觸發
- 哪條 constraint 改變了 verdict
- 結果是 `pass` / `warn` / `restrict` / `escalate` / `stop`

---

## Policy precedence

這一層如果要進 runtime，就必須有可預期的 precedence。

目前較穩的順序是：

1. Precondition
2. Invariant
3. Capability
4. Identity

原因：

- precondition 對 correctness 的即時影響最大
- invariant 比 capability 更接近 repo 不可破壞邊界
- identity 在 early slice 應先當 routing / trace，而不是直接 hard gate

---

## Degradation path

不是所有 boundary failure 都應直接 hard-stop。

較健康的做法是把缺陷轉成可重建的 degradation：

```yaml
missing_sample:
  L0: allow_exploration_with_warning
  L1: escalate
  L2: stop

spec_incomplete:
  L0: analysis_only
  L1: restrict_code_generation_and_escalate
  L2: stop
```

這樣 reviewer 才能從 artifact 看出：

- 不是單純 pass / fail
- 而是系統在風險與前提不足下，採取了哪種限制

---

## Non-goals

這一層現在不應該承擔：

- catch-all repo diary
- 另一套 local preference schema
- 無邊界 repo taxonomy growth
- 一口氣做到 semantic sufficiency inference
- 平行於既有 runtime 的第二套 authority

---

## 和 entry-layer 的關係

`entry-layer` 處理的是「是否有正當理由擴充 runtime surface」。

Decision Boundary Layer 處理的是：

> 在已被接受的 runtime surface 裡，哪些 constraints 可以在 pre-decision 階段改變真實 verdict。

所以兩者不是重複，而是前後關係：

- entry-layer 決定某個 runtime surface 是否值得存在
- DBL 決定某個 constraint 是否能進 decision path

---

## 最小實作路徑

如果只做 first slice，順序應該是：

1. 先有 machine-readable precondition input
2. 讓 `pre_task_check` 真正消費它
3. 讓缺失前提改變真實 verdict
4. 讓 trace / artifact 可重建這個 verdict 變化
5. 再回頭做 reviewer 驗證

---

## 第一個 runtime slice 建議

最穩的 first slice 應只做：

- `missing_sample`
- `missing_spec`
- `missing_fixture`

允許的結果：

- `analysis_only`
- `restrict_code_generation_and_escalate`
- `stop`

明確不做：

- full identity enforcement
- full invariant authoring expansion
- semantic insufficiency inference
- broad repo taxonomy growth

換句話說，第一刀不是要證明整個 DBL 已完成，而是要證明：

> pre-decision boundary 已能透過真實 runtime verdict 被看見、被重建、被審核。

---

## 成功條件

這一層第一階段成立，至少要滿足：

1. 缺少必要前提時，runtime verdict 真的會改變
2. verdict 變化能從 trace / artifact 重建
3. reviewer 不需要靠作者口頭補充才能理解原因
4. 不會引入 duplicate truth source
5. 功能增加的複雜度，小於它阻止的 failure mode

如果這些還沒成立，就不該急著擴到 identity 或更廣的 semantic sufficiency。
