# 💥 Chaos Demo — AI 架構破壞 vs 治理攔截

> **情境**: 你有一個三層架構的 Python 服務（API → Service → Repository）。
> **目標**: 展示 AI 在沒有治理文件時如何破壞架構，以及框架如何介入。
> **時間**: 約 10 分鐘閱讀

---

## 架構規則（先看這個）

```
┌─────────────────────────────────────────────────┐
│              Architecture Rule                  │
│                                                 │
│  Repository 層                                  │
│    ✅ DB 讀寫、SQL 查詢、連線管理                 │
│    ❌ HTTP 呼叫、業務邏輯、快取策略               │
│                                                 │
│  Service 層                                     │
│    ✅ 業務邏輯、呼叫外部服務、協調 repository    │
│    ❌ 直接操作 HTTP request/response 物件        │
│                                                 │
│  違反此規則 = 架構邊界破壞                        │
└─────────────────────────────────────────────────┘
```

---

## 📂 起始狀態（乾淨的分層）

```python
# repository.py — 只做 DB 操作
class UserRepository:
    def get_user(self, user_id: str):
        return self.db.query("SELECT * FROM users WHERE id = ?", user_id)
```

這是架構紅線保護的區域。

---

## 🔴 第一幕：沒有治理

**你說**：
```
repository.py 查詢太慢，幫我加個快取，找不到就從外部 API 抓
```

**AI 直接修改**（無治理）：

```diff
--- a/src/repository.py
+++ b/src/repository.py
@@ -1,7 +1,21 @@
+import httpx                                    # ← HTTP 進入 Repository 層

 class UserRepository:
     def get_user(self, user_id: str):
+        if cached := self.cache.get(f"user:{user_id}"):
+            return cached
+
         user = self.db.query("SELECT * FROM users WHERE id = ?", user_id)

+        if not user:
+            response = httpx.get(                # ← 架構紅線被穿越
+                f"https://legacy-api.internal/users/{user_id}"
+            )
+            user = response.json()
+            self.db.insert("users", user)        # ← Repository 現在做業務決策
+
+        self.cache.set(f"user:{user_id}", user)
         return user
```

**架構邊界被破壞**：

```
❌ Repository 層現在包含：
   import httpx                 ← HTTP client
   httpx.get(api_url)          ← 網路 IO
   if not user: fetch + insert  ← 業務邏輯

問題不是「功能壞了」。CI 會通過，tests 也過。
問題是：
  • 測試 repository 現在需要 mock 外部 API
  • 當 API 掛掉，DB 查詢也超時
  • Service 層不知道 repository 可能觸發網路請求
  • 架構圖與實際代碼不再一致
```

這次破壞沒有任何警告，悄悄進入 main branch。

---

## 🟢 第二幕：有治理（context rehydration）

同樣的請求，但 AI 在開始前讀了 `ARCHITECTURE.md`。

**AI 回覆（有治理）**：

```
[Governance Contract]
LANG     = Python
LEVEL    = L2
SCOPE    = refactor
LOADED   = SYSTEM_PROMPT, HUMAN-OVERSIGHT, ARCHITECTURE
CONTEXT  = chaos-demo — query optimization; NOT: HTTP layer changes
PRESSURE = SAFE (23/200)

---

讀到 ARCHITECTURE.md：Repository 層不能包含 HTTP 呼叫。

需求「加快取 + 外部 API fallback」需要拆成兩部分：
• 快取 → Repository 層可以做（DB 存取優化，合法）
• 外部 API fallback → 業務邏輯，必須在 Service 層
```

**正確的 diff**：

```diff
--- a/src/repository.py          (+快取，無 HTTP)
+++ b/src/repository.py
@@ -1,5 +1,9 @@
 class UserRepository:
     def get_user(self, user_id: str):
+        if cached := self.cache.get(f"user:{user_id}"):
+            return cached
         user = self.db.query("SELECT * FROM users WHERE id = ?", user_id)
+        if user:
+            self.cache.set(f"user:{user_id}", user)
         return user                # ← 找不到回傳 None，不做業務決策
```

```diff
--- a/src/service.py             (fallback 在 Service 層)
+++ b/src/service.py
@@ -3,4 +3,9 @@
 class UserService:
     def get_user(self, user_id: str):
         user = self.user_repo.get_user(user_id)
+        if not user:
+            user = self.legacy_client.fetch_user(user_id)  # ← HTTP 在對的地方
+            if user:
+                self.user_repo.save_user(user)
         return user
```

```
✅ Repository：DB + 快取（架構合法）
✅ Service：fallback 業務邏輯（架構合法）
✅ 架構邊界完整保留
✅ AI 主動說明為何這樣拆
```

---

## 🔵 第三幕：CI 防線

即使 AI 沒有讀到 `ARCHITECTURE.md`，CI 有一道備援。

**contract_validator — 檢查 AI 是否完成初始化**：

```bash
$ echo "<AI 直接修改的回覆，無 Governance Contract>" | \
  python governance_tools/contract_validator.py

🚨 [Governance Contract] 區塊不存在
   AI 回覆不合規 — 請要求 AI 重新初始化

exit code: 2  ← 未初始化的 AI 回覆被擋
```

**verify_phase_gates — 推送前驗證**：

```bash
$ bash scripts/verify_phase_gates.sh

── Gate 2 / PLAN.md 新鮮度 ────────────────────
  ❌ PLAN.md CRITICAL (15d) — 架構修改沒有反映在計畫中

結果: 1/4 Gates 通過
🚨 push 擋截
```

---

## 📊 總結

| 面向 | 沒有治理 | 有治理 |
|------|---------|-------|
| AI 行為 | 直接修改，穿越架構邊界 | 讀規則 → 主動提合規方案 |
| 架構邊界 | 悄悄破壞，CI 照過 | 保持清晰 |
| 問題發現 | Code review 或 production | 對話階段攔截 |
| 技術債 | 每次 AI 協作都在累積 | 有文件化的邊界限制速度 |

---

## ⚠️ 誠實說明

**AI 遵守 ARCHITECTURE.md 是指導性的，不是技術強制**。

長對話中的 attention decay 可能讓 AI「遺忘」架構規則（不是故意違反——是近距離 context 權重遠高於遠距離規則的結構性問題）。`contract_validator` 驗證初始化，但不掃描每一行代碼的架構合規性。

詳見 [LIMITATIONS.md](../../docs/LIMITATIONS.md)。

---

## 🚀 自己跑一遍

```bash
# 部署框架到你的專案
bash deploy_to_memory.sh --target /path/to/your/project

# 對 AI 說：「請讀取 ARCHITECTURE.md 後再開始工作」
# 嘗試讓 AI 做一個會越過架構邊界的修改
# 觀察它是否主動提出合規的分層方案

# 驗證 CI
bash scripts/verify_phase_gates.sh
```
