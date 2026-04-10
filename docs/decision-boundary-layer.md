# Decision Boundary Layer

> 版本：草案
> 日期：2026-03-31
> 目的：在 AI-assisted implementation 與 machine-interpretable governance runtime 之間建立 pre-decision constraint surface

---

## 目的

repo 目前已經有多個 runtime / reviewer-facing surface，例如：

- `session_start`
- `pre_task_check`
- `post_task_check`
- drift checks
- artifacts / reviewer handoff

這些 surface 已能處理測試 discipline、evidence、review、escalation 等問題。
但在很多情況下，系統仍然缺少一層更早的約束：

> 在 implementation proposal 進入 execution / verdict 之前，就先把 repo identity、local invariant、precondition 與 capability boundary 明確放進 decision path。

`Decision Boundary Layer` 就是為了補上這層 pre-decision constraint。

---

## 要解決的問題

repo-specific context 常常不是一般 repo note，而是會直接影響決策的 governance input。

這些資訊包括：

- repo / domain identity
- local invariant
- precondition requirement
- change capability boundary
- degradation / stop path

如果這些條件沒有在 decision 前被明確讀進來，系統就容易出現：

- 錯誤的 solution framing
- 把 repo 類型判錯
- 沒有前置條件仍直接進 implementation
- 超出允許變更範圍

---

## 分層模型

### Layer 0：Identity Constraint

這一層處理：

- 這個 repo 是什麼
- 不應該被誤分類成什麼

例子：

- 實際上是 firmware / tooling repo
- 但模型把它當 GUI app 或 web service

示意：

```yaml
repo_identity:
  repo_type: firmware_tool
  repo_purpose: usb_hub_firmware_update
  forbidden_misclassification:
    - gui_application
    - web_service
```

如果 identity 被判錯，後面很多 implementation proposal 一開始就會歪掉。
因此 identity constraint 在高風險情況下可以直接導向 `stop` 或 escalate。

### Layer 1：Invariant Constraint

這一層處理 repo / domain 的不可破壞行為邊界。

例子：

- matching 應維持 automatic
- 不允許引入 manual selector UI
- flashing path 不應 silent fallback

示意：

```yaml
local_invariants:
  forbidden_patterns:
    - manual_matching_selector
    - silent_fallback_write_path
  required_behavior:
    - automatic_matching_only
```

如果 proposal 直接違反 invariant，就不能只當作普通 implementation choice。

### Layer 2：Precondition Constraint

這一層處理在實作前必須先具備的條件。

例子：

- parser 沒有 sample files
- protocol implementation 沒有 spec
- migration 沒有 rollback plan

示意：

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

這一層特別適合 first slice，因為：

- failure mode 清楚
- reviewer 易於重建
- verdict 可顯式呈現 missing-state

### Layer 3：Capability Constraint

這一層處理目前任務被允許做到哪裡。

例子：

- 可做 local module patch
- 不可做 public API break
- 不可引入全新 framework

示意：

```yaml
capability_constraints:
  allowed_change_scope:
    - local_module_only
  forbidden_change_classes:
    - public_api_break
    - new_framework_introduction
    - cross_module_refactor
```

這一層的價值在於：即使 proposal 看起來合理，也不能因為合理就越過 authority / scope boundary。

---

## 與 repo note / `CLAUDE.md` 的差別

repo note 常常只是背景資訊。
`Decision Boundary Layer` 要處理的不是背景，而是：

> 會直接改變 implementation allow / escalate / stop 的條件。

因此這一層不該只是文件存在，而應能進入 runtime-readable decision surface。

---

## first slice 建議

最適合先做的是 `Precondition Constraint`。

原因：

- failure mode 最具體
- reviewer reconstruction 成本低
- 最容易轉成 explicit missing-state verdict

例如：

- `sample_data missing`
- `spec_validation incomplete`
- `rollback plan absent`

這些都比抽象的 architecture doctrine 更容易先落到可操作的 bounded surface。

---

## 不是什麼

`Decision Boundary Layer` 不是：

- 把所有 repo note 都塞進 runtime
- 在 execution 後再補理由
- 用更多文字替代更清楚的 constraint

它真正要做的是：

> 把會左右 implementation 合法性與可信度的前置條件，提早變成 decision surface，而不是事後才被 reviewer 發現。
