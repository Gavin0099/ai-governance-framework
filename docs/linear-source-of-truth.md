# Linear ↔ PLAN.md 同步策略：Source of Truth 定義

> 適用範圍：使用 `governance_tools/linear_integrator.py` 進行 Linear 整合的專案
> 最後更新：2026-03-05

---

## 核心原則：PLAN.md 為主、Linear 為從

```text
PLAN.md  ──(同步到)──▶  Linear Issues
   │                         │
   │◀──(狀態回寫，人工觸發)───┘
   │
   └── Git commit 觸發 freshness check
```

`PLAN.md` 是 single source of truth，`Linear` 是協作與追蹤介面，不是主要真相來源。

---

## 為什麼以 PLAN.md 為主

| 考量 | `PLAN.md` | Linear |
|---|---|---|
| 版本控制 | Git 歷史可查 | 無完整 diff 追溯 |
| 離線可讀 | 本地檔案可直接讀 | 需要網路 |
| AI 可消費性 | Markdown 可直接讀取 | 需 API 或 UI |
| Repo 結構關聯 | 可直接連到 code / artifact / docs | 關聯較鬆散 |
| 導入成本 | 內建於 repo workflow | 依賴外部服務 |

簡單說：

- `PLAN.md` 適合當 repo-native governance source
- Linear 適合當協作面與進度鏡像

---

## 同步策略

### 單向主路徑

主要同步方向是：

- `PLAN.md` → Linear

也就是先在 repo 內更新 `PLAN.md`，再用 integrator 將必要欄位同步到 Linear。

### 狀態回寫

若要把 Linear 狀態回寫到 `PLAN.md`，應採：

- 明確人工觸發
- 可審查的同步動作
- 不自動覆蓋 repo 內容

原因：

- repo 內的治理資料必須可重建
- 外部系統狀態不應偷偷改寫本地 canonical source

---

## 允許同步的內容

適合同步到 Linear 的內容：

- 任務標題
- 任務狀態
- owner / assignee
- 里程碑
- 簡短摘要
- 指向 `PLAN.md` / artifact / PR 的連結

不適合同步成 primary truth 的內容：

- 詳細治理判斷
- session-level raw notes
- runtime artifact 內容本體
- 只能在 repo 中重建的 evidence chain

---

## Freshness 與衝突處理

`PLAN.md` 更新後，應由：

- Git commit
- freshness check
- drift / sync 檢查

來提醒是否需要同步到 Linear。

若發生衝突，處理原則是：

1. 先以 `PLAN.md` 為準
2. 確認 Linear 是否只是舊狀態殘留
3. 必要時重新同步，不做雙向自動 merge

---

## Non-goals

這份策略不主張：

- Linear 取代 `PLAN.md`
- 雙向自動同步成平行真相來源
- 讓外部工具直接改 repo 內 canonical governance file

---

## 一句話結論

在採用 Linear 整合時，`PLAN.md` 仍是 repo-native single source of truth；Linear 是方便協作與追蹤的投影層，而不是主要治理真相來源。
