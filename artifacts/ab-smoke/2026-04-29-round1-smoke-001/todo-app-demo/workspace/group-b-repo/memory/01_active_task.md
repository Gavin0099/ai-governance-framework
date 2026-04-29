# 01 Active Task

**當前任務**: 建立 FastAPI Todo App 基礎架構

## 進行中

### Sprint 1 - 核心 CRUD API

**目標**: 本週完成 Phase A Gate（基本 CRUD API 可運行）

**已完成**:
- [x] 初始化專案結構
- [x] 安裝 FastAPI + uvicorn + SQLAlchemy

**待辦**:
- [ ] 建立 FastAPI 主程式 (src/main.py)
- [ ] 建立資料模型 (src/models.py)
- [ ] 實作 CRUD 路由 (src/routers/todos.py)

## 技術決策紀錄

- **ORM**: 使用 SQLAlchemy（不用原生 SQL，減少錯誤）
- **DB**: SQLite（Phase A 快速開發優先，Phase C 再考慮 PostgreSQL）
- **驗證**: Pydantic v2（FastAPI 原生支援）

## Next Steps

完成基本 CRUD → 撰寫 pytest 測試 → 進入 Phase B
