# Entry Layer Boundary：entry layer 的權限邊界

> 狀態：**enforced**  
> 更新日期：2026-03-30  
> 定位：說明 codebase 中 entry layer 能做什麼、不能做什麼，以及 drift 如何被辨識

---

## 這份文件在說什麼

這份文件不是 feature list，而是一份 constraint document。
它要固定的不是「entry layer 有哪些功能」，而是「entry layer 不能越界成什麼」。

如果 `docs/entry-layer-justification.md` 說明的是為什麼需要 entry layer，這份文件則負責把它和 runtime 其他層之間的責任邊界寫死。

---

## 核心邊界

### 1. Entry layer 不是 authority source

entry layer 不能取代 task classification、domain gate、risk tier 或 authority resolution。  
這些應由 `pre_task_check`、contract loader 與其他既有 runtime 決策面處理。

### 2. Entry layer 不是 escalation source

entry layer 本身不決定 task level、risk tier 或 oversight requirement。  
就算 `tech_spec` artifact 缺失，也不應單靠 entry layer 直接升成 `L2`。

### 3. Entry layer 不產生 stop / continue / escalate verdict

即使 entry-layer artifact 如 `tech_spec`、`validation_evidence`、`pr_handoff` 缺失，
也不應繞過：
- `session_start ok`
- `pre_task_check ok`
- `post_task_check ok`
- 既有 governance gate / exit code

### 4. Entry layer 只附著在 `session_start`

目前這份 justification 對應的整合點，是把 `workflow_entry_observer` 接進 `session_start.py`。  
這是刻意收斂 runtime surface area 的選擇，不代表 entry layer 可以擴張到所有 hook。

### 5. Entry-layer observation state 是 policy input，不是 policy owner

`recognized`、`missing`、`incomplete`、`stale`、`unverifiable` 這些狀態只能作為：
- risk signal
- task level detection 的輔助訊號
- domain gate decision 的輔助訊號
- authority validation 的輔助訊號

它們不是新的 policy owner。

---

## Drift Detection

若 code review 中出現以下情況，應視為 boundary violation：
- `workflow_entry_observer` 被接進 `pre_task_check.py`、`post_task_check.py` 等非既定位置
- entry-layer state 被直接寫成 `ok`、`task_level` 或 `risk`
- entry-layer observation 被直接當成 authority validation payload
- entry-layer artifact 缺失被直接升格成 gate failure

---

## 與 justification 的分工

可以把 `docs/entry-layer-justification.md` 理解成「為什麼這個東西值得存在」，而這份文件回答的是：
1. 就算它值得存在，也不能長成 framework 的新 authority surface
2. 它為什麼只能先接在 `session_start`
3. 未來如果要擴張，需要先回答哪些越界風險

## 一句總結

entry layer 的價值在於補齊 workflow artifact 的可見性；它的邊界則在於：永遠不應繞過既有 runtime authority。
