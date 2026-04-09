# Entry Layer Justification：entry layer 是否值得進 runtime

> 狀態：**incomplete，entry layer 尚未被證成**  
> 建立日期：2026-03-30  
> 對應約束文件：`docs/entry-layer-boundary.md`

---

## 這份文件的角色

這不是 feature proposal，而是一份**反方論證文件**。

它要回答的是：entry layer 是否真的有不可替代的角色，值得被納入 framework runtime；還是它其實只是可見性輔助層，應留在 runtime 外面。

如果這份文件無法完成，結論就是：

**entry layer 還沒有達到 runtime integration 的門檻，不應繼續。**

---

## A. 既有系統已經能做什麼

### `session_start` 已經提供

- task level detection（`L0 / L1 / L2`）
- domain contract loading 與 domain gate
- rule pack loading 與 context-aware suggestions
- authority table validation
- risk signal override
- change proposal 與 oversight requirement
- domain validator preflight

### `pre_task_check` 已經提供

- `PLAN.md` freshness gate
- runtime contract（rules、risk、oversight、memory mode）
- architecture impact preview
- suggested skills / agent

### 既有 artifact 已經提供

- `change_control_summary`
- `reviewer_handoff_summary`
- `session_end` artifacts
- `governance_drift_checker`

---

## B. Entry layer 自稱要補的缺口

> **本段仍未完成。真正的 gap 尚未被明確定義。**

目前只知道一些候選 gap：

- `session_start` 執行前，是否存在 `tech-spec` artifact 的可見性
- 從 PR 回溯到原始 task spec 的 traceability
- implementation 開始前，是否已完成 scope planning 的前置證據

但這些候選 gap 都還沒有回答同一個關鍵問題：

**如果缺少這些可見性，runtime 哪裡會因此做錯 decision？**

---

## C. 尚未被排除的較小替代方案

在接受 runtime integration 之前，至少應先排除以下替代方案：

| 替代方案 | 為什麼可能已足夠 |
|---|---|
| 文件約定 | 團隊照樣寫 `tech-spec`，不必機器辨識 |
| 離線 observer（CLI only） | `workflow_entry_observer.py` 當獨立 audit 工具，不進 runtime |
| 事後報告 | 將資訊放進 `reviewer_handoff_summary` 即可 |
| `pre_task_check` 可選證據 | 擴充 `--spec-file` 類選項，而不是新 entry layer |

---

## D. 為什麼較小替代方案不夠

> **本段仍未完成。現在還沒有足夠論證。**

---

## E. Irreplaceability Test

> **這兩題目前都還沒被回答。**

### Q1：如果 entry layer 永遠不存在，framework 會不可逆地失去什麼能力？

答案：`unknown`

### Q2：為什麼這個能力不能在 `pre_task_check` 中解決？

答案：`unknown`

---

## 目前結論

entry layer 目前尚未達到 runtime integration 的門檻。

因此：

- `docs/entry-layer-boundary.md` 中的所有約束仍完全有效
- 在 justification 完成前，不應：
  - 重新把 `workflow_entry_observer` 接回 `session_start`
  - 把 entry-layer observation state 當作 policy input
  - 重新啟動先前暫停的 E1–E4 類整合工作

---

## 什麼情況下才應重開

只有在以下問題能被明確回答時，才值得重新打開這條線：

1. 缺少 entry layer，runtime 會在哪個 decision 上反覆失真？
2. 這個失真為什麼無法靠 `pre_task_check`、reviewer handoff、或離線 observer 解決？
3. 最小整合版本能否只提供該能力，而不長出第二套 authority？
