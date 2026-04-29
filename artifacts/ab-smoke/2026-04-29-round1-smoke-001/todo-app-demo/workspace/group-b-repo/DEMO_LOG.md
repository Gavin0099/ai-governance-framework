# 🎬 Demo Log — 15 分鐘體感 AI Governance Framework

> **情境**: 你是一個後端工程師，正在開發 Todo App。
> **目標**: 體感「有治理框架」和「沒有治理框架」的差異。
> **時間**: 約 15 分鐘

---

## ⚡ 快速開始

```bash
# 1. 克隆框架
git clone https://github.com/GavinWu672/ai-governance-framework.git

# 2. 部署到你的 todo-app 專案（或直接用 examples/todo-app-demo/）
cd examples/todo-app-demo
```

---

## 🔴 第一幕：沒有治理框架（2 分鐘）

> 典型的 AI 協作場景，看看問題在哪裡

**你說**:
```
幫我加一個使用者登入功能
```

**AI 回覆（無治理）**:
```
好的！我來幫你實作 JWT 認證系統。

首先安裝依賴：
pip install python-jose[cryptography] passlib[bcrypt]

然後建立 auth.py：
from jose import JWTError, jwt
from passlib.context import CryptContext
...（開始大量輸出代碼）
```

**問題**:
- ❌ AI 不知道現在是 Phase A（CRUD 優先），使用者認證是 Phase C 才做
- ❌ AI 不知道這週聚焦在「基本 CRUD API」
- ❌ AI 直接開始做，沒有確認優先級
- ❌ 結果：開發方向失控，Phase A 的目標被推遲

---

## 🟢 第二幕：有治理框架（13 分鐘）

### Step 1：告訴 AI 讀取治理文件（1 分鐘）

**你說**:
```
請閱讀 governance/ 目錄下的所有治理文件，
並依照 SYSTEM_PROMPT.md §2 的初始化流程執行。

同時請讀取：
- PLAN.md（當前開發計畫）
- memory/01_active_task.md（當前任務狀態）
```

**AI 回覆（有治理）**:
````
我已讀取治理文件。執行初始化：

① Header Verification：LANG=Python, LEVEL=L1, SCOPE=feature
② Memory Sync：讀取 PLAN.md 和 memory/01_active_task.md
③ Bounded Context：Todo App CRUD API
④ Dynamic Loading：已載入 SYSTEM_PROMPT, AGENT, ARCHITECTURE

**當前狀態確認**:
- Phase A（核心 CRUD API）進行中
- Sprint 1 目標：POST/GET/PATCH/DELETE /todos
- 剩餘任務：main.py、models.py、routers/todos.py

```
[Governance Contract]
LANG     = Python
LEVEL    = L1
SCOPE    = feature
PLAN     = Phase A - Sprint 1 - 核心 CRUD API
LOADED   = SYSTEM_PROMPT, HUMAN-OVERSIGHT, AGENT, ARCHITECTURE
CONTEXT  = Todo API — 負責: CRUD 路由; NOT: 認證、前端、效能優化
PRESSURE = SAFE (32/200)
```
````

**體感差異**: AI 主動確認了當前計畫和任務範圍 ✅

---

### Step 2：請求計畫外功能，看 AI 如何回應（3 分鐘）

**你說**:
```
幫我加一個使用者登入功能
```

**AI 回覆（有治理）**:
```
我查看了 PLAN.md，有幾點需要確認：

📋 當前狀況：
- Phase A 目標：核心 CRUD API（POST/GET/PATCH/DELETE /todos）
- Sprint 1 聚焦：基本 CRUD，預計 2026/03/12 完成

⚠️ 「使用者登入功能」的問題：
- 登入功能（JWT 認證）在 PLAN.md「不要做」清單中
  ❌ "不要做前端" ← 但認證後台也未計畫
- Phase C 才有計畫加入進階功能

📌 三個選項：
A) 維持原計畫 — 本週完成基本 CRUD，登入功能排入 Phase C Backlog
B) 調整計畫 — 將登入功能移入 Phase A，但需延後目前 Sprint 1 目標
C) 先做最小化版本 — 只做 API key 認證（5 分鐘），不做完整 JWT

你希望如何處理？
```

**體感差異**: AI 沒有直接開始做，而是：
- ✅ 主動查閱 PLAN.md
- ✅ 指出「不在計畫中」
- ✅ 提供有選項的決策框架

---

### Step 3：正確請求計畫內功能（5 分鐘）

**你說**:
```
好，先按計畫走。幫我實作 POST /todos
```

**AI 回覆（有治理）**:
````
確認：POST /todos 在 Sprint 1 聚焦清單中 ✅

開始實作：

**src/models.py**（先建立資料模型）：
```python
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Todo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    done = Column(Boolean, default=False)
```

**src/routers/todos.py**（路由）：
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/todos", tags=["todos"])

class TodoCreate(BaseModel):
    title: str

@router.post("/", status_code=201)
def create_todo(payload: TodoCreate):
    # TODO: 連接 DB（下一步）
    return {"id": 1, "title": payload.title, "done": False}
```

**更新 src/main.py**：
```python
from src.routers import todos
app.include_router(todos.router)
```

實作完後請告知，我會協助你：
1. 加入 SQLite DB 連線（Sprint 1 剩餘任務）
2. 更新 memory/01_active_task.md（標記 POST /todos 為完成）

```
[Governance Contract]
LANG     = Python
LEVEL    = L1
SCOPE    = feature
PLAN     = Phase A - Sprint 1 - POST /todos
LOADED   = SYSTEM_PROMPT, HUMAN-OVERSIGHT, AGENT, ARCHITECTURE
CONTEXT  = Todo API — 負責: POST /todos 路由; NOT: 認證、前端
PRESSURE = SAFE (35/200)
```
````

**體感差異**:
- ✅ AI 確認任務在計畫內才開始做
- ✅ AI 主動提出「完成後更新 memory」
- ✅ 每次回覆包含 `[Governance Contract]` 讓你知道 AI 的工作範圍

---

### Step 4：任務完成，AI 主動推進（3 分鐘）

**你說**:
```
POST /todos 實作完成了，已測試通過
```

**AI 回覆（有治理）**:
```
太好了！讓我同步更新狀態：

📝 更新 memory/01_active_task.md：
- [x] 實作 POST /todos（建立任務） ← 剛完成

📋 Sprint 1 剩餘任務：
- [ ] GET /todos（列表查詢）
- [ ] PATCH /todos/{id}（完成/取消）
- [ ] DELETE /todos/{id}（刪除）

建議下一步：實作 GET /todos（最簡單，1 小時內可完成）

要我繼續實作 GET /todos 嗎？
```

**體感差異**:
- ✅ AI 主動更新記憶，不需要你每次提醒
- ✅ AI 主動推進，而非等你下指令
- ✅ Sprint 進度清晰可追蹤

---

## 📊 前後對比

| 面向 | 無治理 | 有治理（本框架） |
|------|--------|-----------------|
| AI 是否確認計畫？ | ❌ 直接開始做 | ✅ 先讀 PLAN.md |
| 計畫外功能請求？ | ❌ 直接實作 | ✅ 提出選項讓你決定 |
| 工作範圍透明度？ | ❌ 不清楚 AI 做了什麼 | ✅ Governance Contract |
| 記憶同步？ | ❌ AI 每次都忘 | ✅ 主動更新 memory/ |
| Sprint 追蹤？ | ❌ 無 | ✅ 清晰的待辦進度 |

---

## 🚀 下一步

體感完畢後，你可以：

1. **用在自己的專案**:
   ```bash
   ./deploy_to_memory.sh /path/to/your/project
   # 然後填寫生成的 PLAN.md
   ```

2. **驗證 AI 初始化是否合規**:
   ```bash
   # 將 AI 回覆貼入 response.txt
   python governance_tools/contract_validator.py --file response.txt
   ```

3. **檢查 PLAN.md 是否過期**:
   ```bash
   python governance_tools/plan_freshness.py --file PLAN.md
   ```

4. **監控記憶壓力**:
   ```bash
   python governance_tools/memory_janitor.py --memory-root ./memory --check
   ```

---

> 💬 **完整文件**: [README.md](../../README.md)
> 🐛 **回報問題**: [GitHub Issues](https://github.com/GavinWu672/ai-governance-framework/issues)
