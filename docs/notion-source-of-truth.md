# PLAN.md ↔ Notion 同步策略：Source of Truth 定義

> 適用範圍：使用 `governance_tools/notion_integrator.py` 進行 Notion 整合的專案
> 最後更新：2026-03-06

---

## 核心原則：PLAN.md 為主、Notion 為從

```text
PLAN.md  ──(同步到)──▶  Notion Database Pages
   │                              │
   │◀──(狀態回寫，人工觸發)────────┘
   │
   └── Git commit 觸發 freshness check
```

`PLAN.md` 是 repo 內 single source of truth，`Notion` 是外部協作與展示層。

---

## 為什麼以 PLAN.md 為主

| 考量 | `PLAN.md` | Notion |
|---|---|---|
| 版本控制 | Git 歷史可查 | 無原生 diff |
| 離線可讀 | 本地檔案可直接讀 | 需要網路 |
| AI 可消費性 | Markdown 可直接讀取 | 需 API / UI |
| 與 repo 資料對齊 | 可直接連 code / artifact / docs | 關聯較鬆散 |
| 可審核性 | 變更隨 commit 留痕 | 多依賴外部紀錄 |

因此：

- `PLAN.md` 適合當 canonical governance source
- Notion 適合當可瀏覽、可協作的 mirror

---

## 同步原則

### 主同步方向

主要方向是：

- `PLAN.md` → Notion

也就是先在 repo 內更新 `PLAN.md`，再同步到 Notion。

### 狀態回寫

若要把 Notion 狀態回寫到 `PLAN.md`，應採：

- 人工觸發
- 可審查的同步步驟
- 不自動覆寫 repo 內容

這樣才能避免外部頁面成為第二個不受控的真相來源。

---

## 允許同步的資訊

適合同步到 Notion 的資訊：

- 任務標題
- 狀態
- owner / assignee
- milestone
- 高層摘要
- 指向 repo 內 `PLAN.md`、artifact、PR 的連結

不適合在 Notion 變成 primary truth 的資訊：

- 詳細治理判斷
- raw session note
- 需依賴 repo 結構才能重建的 evidence chain
- runtime artifact 內容本體

---

## Freshness 與衝突處理

`PLAN.md` 更新後，應由：

- Git commit
- freshness check
- drift / sync check

提醒是否需要同步到 Notion。

若發生狀態不一致，處理順序是：

1. 先確認 `PLAN.md` 的內容
2. 對照 Notion 是否只是延遲同步或舊狀態
3. 必要時重跑同步，不做雙向自動 merge

---

## Non-goals

這份策略不主張：

- 用 Notion 取代 `PLAN.md`
- 建立雙向自動同步的平行真相來源
- 讓 Notion 頁面直接決定 repo 內 canonical governance state

---

## 一句話結論

在 Notion 整合情境下，`PLAN.md` 仍是 repo-native single source of truth；Notion 只是協作、瀏覽與彙整層，不應反過來主導 repo 內治理真相。
