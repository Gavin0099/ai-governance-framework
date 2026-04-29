# PLAN.md — Todo App Demo

> **專案類型**: Web 應用（示範用）
> **技術棧**: Python / FastAPI / SQLite
> **複雜度**: L1
> **預計工期**: 2026/03 ~ 2026/04
> **最後更新**: 2026-03-05
> **Owner**: YourName
> **Freshness**: Sprint (7d)

---

## 📋 專案目標

建立一個簡單的 Todo List API，作為 AI Governance Framework 的示範專案。

**Bounded Context**:
- REST API 的建立（CRUD）
- SQLite 資料儲存
- 基本錯誤處理

**不負責**:
- 前端介面（Phase C 才做）
- 使用者認證（Phase C 才做）
- 效能優化（Phase C 才做）

---

## 🏗️ 當前階段

```
階段進度:
├─ [🔄] Phase A: 核心 CRUD API    (進行中，預計 2026/03/20)
├─ [⏳] Phase B: 測試與文件       (待開始，預計 2026/04/05)
└─ [⏳] Phase C: 進階功能         (待開始，預計 2026/04/30)
```

**當前 Phase**: **Phase A — 核心 CRUD API**

---

## 🔥 本週聚焦 (Sprint 1)

**Sprint 1** (2026/03/05 - 2026/03/12)

**目標**: 建立可運行的基本 CRUD API

- [ ] 建立 FastAPI 專案架構（2h）
- [ ] 實作 POST /todos（建立任務）（2h）
- [ ] 實作 GET /todos（列表查詢）（1h）
- [ ] 實作 PATCH /todos/{id}（完成/取消）（2h）
- [ ] 實作 DELETE /todos/{id}（刪除）（1h）

**下一步**:
完成基本 CRUD 後進入 Phase B（測試撰寫）

**當前阻礙**: 無

---

## 📊 待辦清單 (Backlog)

### 高優先 (P0)
- [ ] 基本 CRUD API 完整實作
- [ ] SQLite 連線與 migration

### 中優先 (P1)
- [ ] 單元測試（pytest）
- [ ] API 文件（OpenAPI）
- [ ] 輸入驗證與錯誤訊息

### 低優先 (P2)
- [ ] 使用者認證（JWT）
- [ ] 搜尋與篩選功能
- [ ] 效能優化

---

## 🚫 不要做 (Anti-Goals)

❌ **Phase A 禁止**:
- 不要做前端（Phase C 才做）
- 不要做使用者認證（Phase C 才做）
- 不要提前優化效能
- 不要加 cache layer

---

## 🤖 AI 協作規則

**AI 在實作任何功能前，必須確認**:

1. ✅ 這項任務在「本週聚焦」或「下一步」中嗎?
2. ✅ 是否符合當前 Phase A 的範圍（CRUD API）?
3. ✅ 是否在「不要做」清單中?

**如果不符合上述條件**:
- 先詢問是否調整 PLAN
- 不要自行決定優先級
- 提供明確的選項 (A/B/C)
