# Entry Layer Justification：為什麼需要 entry layer runtime integration

> 狀態：**incomplete，但 entry layer 邊界已固定**  
> 更新日期：2026-03-30  
> 邊界文件：`docs/entry-layer-boundary.md`

---

## 這份文件要回答什麼

這不是單純的 feature proposal，而是在回答一個更底層的問題：

**entry layer 是否值得進入 runtime integration？**

換句話說，workflow artifact 的存在，是否真的能補上 framework runtime 目前缺少的治理可見性？

如果不能，這條線就不該繼續擴張。

---

## A. 既有流程中缺了什麼

### `session_start` 已處理的事

- task level detection（`L0 / L1 / L2`）
- domain contract loading 與 domain gate
- rule pack loading 與 context-aware suggestions
- authority table validation
- risk signal override
- change proposal 的 oversight requirement
- domain validator preflight

### `pre_task_check` 已處理的事

- `PLAN.md` freshness gate
- runtime contract（rules、risk、oversight、memory mode）
- architecture impact preview
- suggested skills / agent

### 已存在的 artifact 面

- `change_control_summary`
- `reviewer_handoff_summary`
- `session_end` artifacts
- `governance_drift_checker`

---

## B. Entry layer 想補的是哪個 gap

目前最明顯的 gap 是：
- `session_start` 之前，沒有一個可被 runtime 看見的 `tech_spec` artifact
- PR 前雖然有 reviewer handoff，但缺少 task spec 的 traceability
- implementation 前的 planning / validation / handoff 之間沒有最小閉環

這些 gap 不會立刻讓 runtime 壞掉，但會讓：
- reviewer reconstruction 變難
- scope planning 不可見
- workflow evidence 容易在 session 中消失

**因此，entry layer 的真正目的不是增加 runtime 權力，而是補 visibility。**

---

## C. 為什麼不是直接做成新 authority

如果把 entry layer 直接做成新的 authority，會立刻出現幾個問題：

| 問題 | 原因 |
|---|---|
| 規則會變得太重 | `tech_spec` 缺失不應直接等於 task 非法 |
| observer 變成 gate | `workflow_entry_observer.py` 若直接改 verdict，就越過現有 runtime |
| 缺失被過度處罰 | 目前 `reviewer_handoff_summary` 也不是 authority source |
| `pre_task_check` 膨脹 | 會把 workflow artifact 誤當成必要治理前置條件 |

所以這條線要先被限制在：
- `session_start` 的 observation
- reviewer-visible consequence
- 不直接寫進 authority owner

---

## D. Irreplaceability Test

如果 entry layer 值得存在，至少要能回答：

1. 沒有 entry layer 時，framework 是否真的少了一個重要可見面？
2. 這個可見面是否不能由 `pre_task_check`、`reviewer_handoff_summary` 或既有 artifact 直接替代？
3. 如果未來不做 entry layer，會不會持續重複相同的 workflow visibility gap？

目前答案偏向：**值得做，但只值得做成受限的 observation slice**。

---

## E. 目前結論

entry layer 目前的 justification 是成立的，但只成立到這個範圍：
- 補 runtime 對 workflow artifact 的 visibility gap
- 幫 reviewer reconstruction 建立更穩定的入口
- 不擴成新的 authority source
- 不擴成完整 workflow engine

## 一句總結

entry layer 值得存在，不是因為 workflow 本身很重要，而是因為現在 framework 缺少一個能把 planning / validation / handoff 這條鏈接成可見 surface 的最小 observation layer。
