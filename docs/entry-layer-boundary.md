# Entry Layer Boundary：entry layer 的禁止邊界

> 狀態：**enforced**  
> 建立日期：2026-03-30  
> 原因：codebase 中已有 entry layer 雛形，但尚未證明其必要性

---

## 這份文件是什麼

這份文件定義的是：在 justification 完成之前，entry layer **不能變成什麼**。

它不是 feature list，而是 constraint document。

如果 `docs/entry-layer-justification.md` 未來能證明 entry layer 的必要性，這些約束才可能被局部放寬；在那之前，以下限制一律有效。

---

## 目前有效的約束

### 1. Entry layer 不是 authority source

entry layer 不決定某個 task 應套用哪些規則。  
這仍是 `pre_task_check` 與 contract loader 的責任。

### 2. Entry layer 不是 escalation source

entry layer 不得抬升 task level、risk tier、或 oversight requirement。  
即使某個 `tech_spec` artifact 缺失，也不能因此自動觸發 `L2` escalation。

### 3. Entry layer 不影響 stop / continue / escalate verdict

任何 entry-layer artifact（如 `tech_spec`、`validation_evidence`、`pr_handoff`）的有無，都不得直接改變以下結果：

- `session_start ok`
- `pre_task_check ok`
- `post_task_check ok`
- 任一 governance gate 的 exit code

### 4. Entry layer 尚未連到 `session_start`

在 justification 完成之前，`workflow_entry_observer` 不得被 `session_start.py` import 或呼叫。

**記錄：** 2026-03-30 曾經接上又回退。  
回退原因：runtime surface area 增加了，但必要性尚未被證明。

### 5. Entry-layer observation state 不是 policy input

`recognized`、`missing`、`incomplete`、`stale`、`unverifiable` 目前都只是診斷標籤，不能被用作：

- risk signal 計算輸入
- task level detection 輸入
- domain gate decision 輸入
- authority validation 輸入

---

## Drift Detection

如果 code review 中出現以下情況，應視為 boundary violation：

- `workflow_entry_observer` 被 import 到 `session_start.py`、`pre_task_check.py`、或 `post_task_check.py`
- entry-layer state 被拿來影響 `ok`、`task_level`、或 `risk`
- entry-layer observation 被放進 authority validation payload
- entry-layer artifact 缺失被當成 gate failure

---

## 如何解除約束

必須先完成 `docs/entry-layer-justification.md`，並回答：

1. 如果 entry layer 永遠不存在，framework 會不可逆地失去什麼能力？
2. 為什麼這個能力不能在 `pre_task_check` 內處理？
3. 最小、且只提供該能力的實作是什麼？

如果這三題答不出來，約束就維持不變。
