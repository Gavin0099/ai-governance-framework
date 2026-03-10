# Starter Pack — 5 分鐘開始使用 AI Governance

最小可用版本。3 個文件，解決一個核心問題：

> **AI 在長對話中會忘記你的計畫，然後做它自己覺得對的事。**

**先看效果**: [demo.md](demo.md) — 5 分鐘看懂治理在運作時長什麼樣子 ⭐

---

## 你需要的文件

**核心文件（所有 AI 工具共用）：**

| 文件 | 來源 | 作用 |
|------|------|------|
| `SYSTEM_PROMPT.md` | 本目錄 | 治理規則 master（所有工具讀這份） |
| `PLAN.md` | 本目錄（填入後使用） | 專案計畫，AI 每次對話決定任務範圍 |
| `memory/01_active_task.md` | 本目錄 | AI 跨 session 的狀態記憶 |
| `memory_janitor.py` | `../../governance_tools/` | 監控記憶體壓力 |

**AI 工具 Adapter（擇一或全部複製）：**

| 文件 | 工具 | 說明 |
|------|------|------|
| `CLAUDE.md` | Claude Code | 自動讀取，指向 SYSTEM_PROMPT.md |
| `GEMINI.md` | Gemini Code Assist | 自動讀取，指向 SYSTEM_PROMPT.md |
| `.github/copilot-instructions.md` | GitHub Copilot | 內嵌關鍵規則（Copilot 不讀其他文件） |

---

## 步驟一：複製文件到你的專案

```bash
# 核心文件
cp examples/starter-pack/SYSTEM_PROMPT.md        /your/project/
cp examples/starter-pack/PLAN.md                 /your/project/
cp governance_tools/memory_janitor.py            /your/project/
cp -r examples/starter-pack/memory/             /your/project/

# AI 工具 Adapter（依你使用的工具選擇）
cp examples/starter-pack/CLAUDE.md               /your/project/          # Claude Code
cp examples/starter-pack/GEMINI.md               /your/project/          # Gemini
mkdir -p /your/project/.github
cp examples/starter-pack/.github/copilot-instructions.md \
   /your/project/.github/                                                 # GitHub Copilot
```

---

## 步驟二：填寫 PLAN.md（2 分鐘）

打開 `PLAN.md`，填入：

1. 第 1 行：專案名稱
2. `最後更新` 日期
3. `當前階段`：你現在在做什麼
4. `本週聚焦`：這週要完成的 1-3 件事
5. `架構紅線`：AI 不能穿越的邊界（沒有的話刪掉這段也可以）

其他欄位保持範本格式，之後慢慢填。

---

## 步驟三：設定你的 AI 工具

**Claude Code**:

```bash
# 在你的專案根目錄建立 CLAUDE.md，加入：
echo "Read SYSTEM_PROMPT.md and PLAN.md at the start of every conversation." >> CLAUDE.md
```

**ChatGPT / 其他工具**:

將 `SYSTEM_PROMPT.md` 內容貼入 Custom Instructions 或 System Prompt 欄位。

---

## 步驟四：驗證有效（30 秒）

開啟新對話，輸入任何任務，確認 AI 回覆**開頭**出現：

```
[Governance Contract]
PLAN     = Phase 1 / 本週聚焦 / [你的任務]
PRESSURE = SAFE (0/200)
```

如果出現這個 block，代表 AI 已讀取 PLAN.md 並初始化治理。

如果沒有出現 → 確認 SYSTEM_PROMPT.md 有被 AI 讀取到。

---

## 步驟五：維持習慣（每次對話後）

1. **更新 `memory/01_active_task.md`**（AI 會提醒你，你也可以自己更新）
2. **每週更新 `PLAN.md` 的「本週聚焦」**（5 分鐘）
3. **定期監控記憶壓力**：

```bash
python memory_janitor.py --check
```

---

## 你會得到什麼

**沒有框架時**:
```
對話 1: AI 開始寫你沒要求的快取功能
對話 8: AI 忘記 3 天前的決策，重新解釋問題
```

**有這 3 個文件後**:
```
對話 1: AI 確認任務在本週範圍，詢問優先級後再動手
對話 8: AI 讀取 PLAN.md，知道目前狀態，延續上次決策
```

---

## 遇到問題？

| 問題 | 原因 | 解法 |
|------|------|------|
| AI 沒有輸出 Governance Contract | SYSTEM_PROMPT.md 未被讀取 | 確認 AI 工具的 system prompt 設定 |
| AI 無視 PLAN.md 的範圍限制 | Attention decay（正常現象） | 每次對話開頭手動提醒「請先讀 PLAN.md」 |
| memory_janitor 報錯 | `memory/` 資料夾不存在 | `mkdir -p memory && touch memory/01_active_task.md` |

---

## 準備升級？

當你需要以下功能時，切換到完整框架：

| 需求 | 對應文件 |
|------|----------|
| 架構邊界強制執行 | `governance/ARCHITECTURE.md` |
| 程式碼 Review 標準 | `governance/REVIEW_CRITERIA.md` |
| 多 Agent 協作 | `governance/AGENT.md` |
| CI 自動驗證 | `scripts/verify_phase_gates.sh` |
| Governance Contract 驗證 | `governance_tools/contract_validator.py` |

完整框架：[返回 repo 根目錄](../../README.md)
