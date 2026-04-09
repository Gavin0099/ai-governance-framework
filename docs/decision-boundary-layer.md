# Decision Boundary Layer

> Status: proposed design direction
> Created: 2026-03-31
> Purpose: 在 AI-assisted implementation 開始前，定義可被 machine 消費的 constraint surface

---

## 為什麼需要這一層

framework 已經在 session / task 邊界上有不少治理能力：

- `session_start`
- `pre_task_check`
- `post_task_check`
- drift checks
- artifacts / reviewer handoff

這讓它在 discipline、evidence、replay 上很強。

但它仍弱在另一個點：

> 在系統決定「允許哪一類解法」、「可不可以開始實作」、「這次任務最多能改多少」之前，
> 其實還缺一個正式的 pre-decision constraint layer。

這份文件的目的，就是把這個缺口顯性化。

---

## Core Idea

真正缺的不是單純的「repo-specific context」。

真正缺的是：

> 在 implementation 開始前就很重要、但常常只存在於人腦、前一輪對話或 repo note 裡的 constraint。

若它們只寫在註記裡，就仍然可能被忽略。  
要成為 governance-relevant，至少要滿足：

- 結構化到可被消費
- 綁到實際 decision point
- 進入 trace output
- 服從 precedence
- 能 degradation，不只有 hard-stop

這整個 surface，就叫 **Decision Boundary Layer**。

---

## 範圍

這一層試圖在 implementation 之前先回答四個問題：

1. 這是什麼類型的 repo / problem？
2. 哪些 solution class 即使技術上可行，也是不合法的？
3. implementation 開始前，哪些條件一定要先存在？
4. 這個 task 最多允許改到什麼程度？

這四個問題不同，不能被壓成一個模糊的「context file」。

---

## 四層 Constraint Layers

### Layer 0：Identity Constraint

作用：
- 限制 repo routing 與 solution framing
- 在更深推理開始前就擋掉類別誤判

例如：
- 這是 firmware tool，不是 GUI app
- 這是 CLI-first tool，不是 web service

建議形狀：

```yaml
repo_identity:
  repo_type: firmware_tool
  repo_purpose: usb_hub_firmware_update
  forbidden_misclassification:
    - gui_application
    - web_service
```

若 identity 只停在 metadata，就沒有治理價值。  
它必須能進 decision routing。

最低 runtime effect：
- 若 proposal solution class 與 `repo_identity` 衝突，至少要 `escalate`
- 高風險 mismatch 可以直接 `reject`

### Layer 1：Invariant Constraint

作用：
- 限制這個 repo / domain 內允許的 solution space

例如：
- matching 必須 automatic
- manual selector UI 禁止
- public flashing path 必須保持 single-owner

這些不是單純 context note，而是 local policy。  
它們不應只住在 `CLAUDE.md` 或任意 repo note。

建議形狀：

```yaml
local_invariants:
  forbidden_patterns:
    - manual_matching_selector
    - silent_fallback_write_path
  required_behavior:
    - automatic_matching_only
```

最低 runtime effect：
- invariant violation 必須進同一條 contract-driven decision path
- 它應被當成 constraint-based rejection，而不是 prose guidance

### Layer 2：Precondition Constraint

作用：
- 決定 implementation 是否允許開始

例如：
- parser 工作需要 sample files
- protocol implementation 需要 spec
- migration 需要 rollback plan

這一層最有 immediate value。  
但不能只做 existence check，因為真實世界還有：

1. explicit absence
2. pseudo-presence
3. semantic insufficiency

建議形狀：

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

最低 runtime effect：
- `pre_task_check` 應檢查 preconditions
- 缺失或不足時，要有 deterministic verdict
- verdict 必須支援 degradation，不只能 pass/stop

### Layer 3：Capability Constraint

作用：
- 限制這次 task 允許改動的範圍與類型

例如：
- 不得引入新 framework
- 不得 public API break
- 不得 cross-module refactor

這些與 identity、invariant 都不同。  
它們屬於 task-bounded mutation constraints。

建議形狀：

```yaml
capability_constraints:
  allowed_change_scope:
    - local_module_only
  forbidden_change_classes:
    - public_api_break
    - new_framework_introduction
    - cross_module_refactor
```

最低 runtime effect：
- capability violation 應觸發 scope-based escalation 或 rejection
- 而且應在 implementation 開始前被處理，不是等 diff review 才補抓

---

## 為什麼這不是 `CLAUDE.md`

repo-local context file 當然可以存在，但它的角色應很窄：

適合放：
- vocabulary
- repo orientation
- major folders / entrypoints
- canonical source links

不適合當 primary home 的內容：
- hard-stop rules
- task gate logic
- policy precedence
- capability constraints
- enforcement logic

一句話：

- `CLAUDE.md` 可以幫忙 framing
- 但 `CLAUDE.md` 不是 policy source
- 更不是 gate source

---

## Decision Model Integration

這一層只有在 runtime 真的吃進去時才有意義。

最低 consumer 應包括：

- `session_start`
  - 可載入 identity / framing preview
- `pre_task_check`
  - 必須檢查 preconditions
  - 應檢查 identity mismatch 與 capability overreach
- decision model / runtime verdict path
  - 必須處理 precedence 與 degradation

最低 trace output 應可回答：
- 載入了哪些 constraints
- 評估了哪些 constraints
- 哪些 constraint 改變了 verdict
- 結果是 `pass` / `warn` / `restrict` / `escalate` / `stop`

若這些資訊不進 artifact，這一層就還不算 governance-relevant。

---

## Policy Precedence

Identity、Invariant、Precondition、Capability 一旦同時存在，precedence 就必須明寫。

否則不同 reviewer / session 會各自 improvisation。

一個起始順序可以是：

1. Precondition
2. Invariant
3. Capability
4. Identity

這只是提議，不是既定真理。  
重要的不是「順序一定長這樣」，而是：

> precedence 必須被定義，而不是臨場猜

---

## Degradation Paths

純 hard-gate 系統很快就會變得太僵。

由於 framework 已有 replay、artifact、review 能力，某些 failure 更適合 degradation，而不是一律 stop。

例如：

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

這能避免系統滑向「AI 什麼都不能做」，同時又讓 grounding 不足的狀態保持可見、可追蹤、可 review。

但 degradation 一定要綁 task level。  
否則它很容易變成自我開脫的 bypass。

---

## Non-Goals

這一層不應變成：

- 第二份治理憲法
- domain contract 的替代品
- catch-all repo diary
- 收納所有 local preference 的新 schema

若它沒有真正 decision consumer，就只會變成 context inflation。  
若它重複既有規則，就會變成 governance duplication。

---

## 與現有 Entry-Layer 文件的關係

現有 `entry-layer` 文件原本的任務，是防止 unjustified runtime expansion。

那個邊界仍然有效。  
這份文件不是要把舊 entry layer 重新拉回來，而是想把真正需要的 successor shape 講清楚：

- 不是再加更多 observation
- 不是默默長更多 runtime surface
- 而是更小、更明確、能綁到 real verdict 的 pre-decision model

---

## Minimal Implementation Path

若真的要落地，最小路徑應該是：

1. 先加 machine-readable `repo_identity`
2. 只加一兩個高價值 precondition validator
3. 透過 `pre_task_check` 跑它們
4. 在 trace 中清楚標出是哪個 boundary constraint 改變 verdict
5. 做不到第 4 步就停

如果沒辦法在 trace 中說清楚 constraint 如何改變 verdict，那就代表只是多長一層結構，沒有多出可驗證價值。

---

## First Runtime Slice Recommendation

第一個 runtime slice 不應一次實作完整四層。

建議順序：

1. minimal precondition gate
2. minimal capability hook
3. identity 當 input / trace surface
4. identity 真正進 enforcement

理由：
- preconditions 最容易對應真實錯誤
- capability 已和現有 scope / evidence tooling 比較接得上
- identity 雖重要，但太早做 enforcement 容易 overfit

建議 first slice：

```yaml
first_slice:
  includes:
    - missing_sample
    - missing_spec
    - missing_fixture
  degradation_actions:
    - analysis_only
    - restrict_code_generation_and_escalate
    - stop
  excludes:
    - full identity enforcement
    - full invariant expansion
    - repo taxonomy growth
```

成功條件：
- boundary 真的改變過至少一個 real verdict
- 原因能在 trace 中看見
- reviewer 能只靠 artifact 重建決策
- 不製造 duplicate truth source
- false stop / false escalate 是可觀測、可解釋的

---

## Alignment With Existing Framework Surfaces

這一層若要成立，應盡量重用 framework 已有 surface，而不是重造一個 parallel system。

對應關係大致是：

- precondition constraint
  - `pre_task_check`
  - runtime contract
  - escalation path

- capability constraint
  - public API diff checks
  - refactor evidence
  - scope control

- invariant constraint
  - domain contracts
  - 正式 rule pack

- identity constraint
  - 先當 trace / routing input，之後再考慮 enforcement

如果某個實作無法明確對應現有 surface，很可能不是在延伸 framework，而是在偷偷長第二套系統。

---

## Success Criteria

這一層只有在以下條件都能成立時，才算成功：

- 錯的 proposal class 能被 identity routing 擋下
- missing / insufficient prerequisite 能 deterministically 改變 verdict
- reviewer 可只靠 artifact 重建 decision
- 不需要 repo note 與 contract 各寫一份真相
- token / complexity 成長保持有界

若做不到，這份文件就應維持 design memo，而不是 runtime 行為。
