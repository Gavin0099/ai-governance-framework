# PLAN.md ↔ Notion 同步策略：Source of Truth 定義

> **適用範圍**: 使用 `governance_tools/notion_integrator.py` 進行 Notion 整合的專案
> **最後更新**: 2026-03-06

---

## 核心原則：PLAN.md 為主、Notion 為從

```
PLAN.md  ──(同步到)──▶  Notion Database Pages
   │                              │
   │◀──(狀態回寫，人工觸發）────────┘
   │
   └── Git commit 觸發 freshness check
```

**PLAN.md 是 Single Source of Truth**，原因：

| 考量點 | PLAN.md | Notion |
|--------|---------|--------|
| 版本控制 | ✅ Git 歷史可查 | ❌ 無 diff 追溯 |
| 離線存取 | ✅ 本地檔案 | ❌ 需要網路 |
| AI 可讀 | ✅ Markdown 直讀 | ❌ 需要 API 呼叫 |
| 視覺化管理 | ❌ 純文字 | ✅ Gallery/Table/Kanban |
| 團隊協作 | ❌ 較弱 | ✅ 評論、指派、Relation |
| 免費額度 | ✅ 無限制 | ✅ 個人版免費 |

**結論**：PLAN.md 定義「要做什麼」，Notion 負責「可見性與協作」。

---

## 前置設定（3 步驟）

### 步驟 1：建立 Notion Integration

1. 前往 https://www.notion.so/my-integrations
2. 點擊「+ New integration」
3. 填寫名稱（如 `ai-governance`），選擇 Workspace
4. 複製 **Internal Integration Token**（`secret_xxxx`）
5. 設定環境變數：`export NOTION_API_KEY='secret_xxxx'`

### 步驟 2：建立目標 Database

推薦 Database 欄位設計：

| 欄位名稱 | 類型 | 說明 |
|---------|------|------|
| Name | Title | 任務名稱（必要） |
| Status | Select | Todo / In Progress / Done |
| Source | Rich Text | 固定填入 "PLAN.md" |
| Notes | Rich Text | 任務描述 |

> 💡 若 Database 無 Status 或 Notes 欄位，同步仍可運作，Notion 會忽略未知欄位。
> 若 API 回傳欄位錯誤，請確認欄位名稱與型別正確。

### 步驟 3：授權 Integration 存取 Database

1. 開啟目標 Database 頁面
2. 點擊右上角「...」→「Add connections」
3. 搜尋並加入步驟 1 建立的 Integration
4. 執行 `--list-databases` 確認可看到該 Database：
   ```bash
   python governance_tools/notion_integrator.py --list-databases
   ```

---

## 操作規則

### 規則 1：新任務先寫 PLAN.md

```
❌ 不要做：直接在 Notion 建頁面 → 再嘗試反寫 PLAN.md
✅ 正確做法：在 PLAN.md 加任務 → 執行 --sync 推送到 Notion
```

### 規則 2：狀態更新以 PLAN.md 為準

- 任務完成 → 在 PLAN.md 標記 `[x]` → commit → （可選）手動在 Notion 更新 Status
- **不要**只在 Notion 更改狀態，而不更新 PLAN.md

### 規則 3：Notion ID 寫回本地

`--sync` 執行後，`notion_integrator` 會在任務後面加 `[NOTION:XXXXXXXX]` 標記（8 字元短 ID）。
這個標記：
- 防止重複建立相同 Page
- 是定位 Notion Page 的本地橋梁

### 規則 4：衝突解法

| 情境 | 解法 |
|------|------|
| PLAN.md 有任務，Notion 沒有 | 執行 `--sync` |
| Notion 有 Page，PLAN.md 沒有 | 手動在 PLAN.md 補記，再標記 NOTION ID |
| 兩邊狀態不一致 | 以 PLAN.md 為準，手動更新 Notion |
| Notion Page 被刪除 | 移除 PLAN.md 中的 `[NOTION:XXXXXXXX]` 標記，下次 `--sync` 會重建 |

---

## 不支援的功能（明確邊界）

- ❌ Notion → PLAN.md 自動反寫（避免雙向同步競爭）
- ❌ Notion 上的評論/附件同步到本地
- ❌ 子 Page / Relation 階層對應（PLAN.md 是平面清單）
- ❌ 多 Database 批次同步（每次指定單一 `--database-id`）
- ❌ Notion 內容編輯（只建立 Page，不修改已存在的 Page）

---

## 工具使用流程

```bash
# 1. 確認環境變數已設定
export NOTION_API_KEY='secret_xxxx'

# 2. 列出可存取的 Database（取得 Database ID）
python governance_tools/notion_integrator.py --list-databases

# 3. 同步未完成任務到 Notion（--database-id 可用環境變數代替）
python governance_tools/notion_integrator.py --sync --database-id <DB_ID>

# 4. CI/dashboard 用 JSON 輸出
python governance_tools/notion_integrator.py --sync --database-id <DB_ID> --format json

# 5. 也可用環境變數指定 Database ID
export NOTION_DATABASE_ID='<DB_ID>'
python governance_tools/notion_integrator.py --sync
```

---

## 安全性

`notion_integrator` 在送出前會掃描 title 與 description，若偵測到以下類型會**拒絕送出**：

| 類型 | 範例 |
|------|------|
| `API_KEY` | `secret_*`, `lin_api_*`, `sk-*` |
| `CREDENTIAL` | `password=xxx`, `token: yyy` |
| `PRIVATE_KEY` | `-----BEGIN PRIVATE KEY-----` |
| `POSSIBLE_SECRET` | 40+ 字元 base64 blob |

若誤觸（例如正常的 base64 ID），使用 `--format json` 查看具體錯誤後，
清理任務描述中的可疑字串即可。

---

## 與 Linear 的比較

| 面向 | Notion | Linear |
|------|--------|--------|
| 適用對象 | 個人 / 小團隊 / 知識型工作 | 軟體開發團隊 |
| 免費額度 | ✅ 個人版免費 | ✅ 免費版可用 |
| API 類型 | REST | GraphQL |
| 視覺化 | Gallery / Table / Kanban / List | Issue Board / Roadmap |
| 關聯資料 | ✅ Relation（連結其他 DB） | ✅ Epic / Sub-issue |
| 整合複雜度 | ⭐⭐ | ⭐⭐ |

---

## 相關文件

- [PLAN.md](../PLAN.md) — 主計畫文件
- [governance_tools/notion_integrator.py](../governance_tools/notion_integrator.py) — 工具原始碼
- [docs/linear-source-of-truth.md](./linear-source-of-truth.md) — Linear 整合策略（對照參考）
- [governance/02_workflow.md](../governance/02_workflow.md) — 整體工作流程
