# Starter Pack

狀態：這是一組可複製的治理起始檔，不是可直接執行的應用程式。

`starter-pack` 的目的，是讓新 repo 在還沒導入完整 framework 前，就能先有一個最小可用的治理骨架：

- `SYSTEM_PROMPT.md`
- `PLAN.md`
- `memory/01_active_task.md`
- AI adapter surfaces（Claude / Gemini / Copilot）
- `memory_janitor.py`

當專案已經長大、開始需要 runtime governance、drift check、adopt / readiness / audit 等能力時，應升級到完整 framework，而不是永遠停在 starter-pack。

## 這份 starter-pack 解決什麼

- 讓 AI 每次 session 都先讀 `PLAN.md`
- 讓工作焦點、記憶壓力、架構邊界有一個最小可依賴的入口
- 讓新 repo 在沒有完整 adopt 前，也有一個明確的治理起點

## 這份 starter-pack 不主張什麼

- 不提供完整 runtime governance
- 不提供 closeout / audit / readiness / drift 的正式閉環
- 不等於已導入完整 `ai-governance-framework`

---

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `SYSTEM_PROMPT.md` | starter-pack 的最小治理提示，作為 AI 每次 session 的固定入口 |
| `PLAN.md` | 專案工作焦點與當前 sprint 的唯一文字來源 |
| `memory/01_active_task.md` | 當前任務記錄 |
| `CLAUDE.md` | Claude Code adapter |
| `GEMINI.md` | Gemini adapter |
| `.github/copilot-instructions.md` | GitHub Copilot adapter |
| `demo.md` | 範例說明 |

另外還需要從 framework repo 帶出：

| 檔案 | 來源 |
|---|---|
| `memory_janitor.py` | `governance_tools/memory_janitor.py` |

---

## 初始化方式

### 方式 A：手動複製

```bash
cp examples/starter-pack/SYSTEM_PROMPT.md        /your/project/
cp examples/starter-pack/PLAN.md                 /your/project/
cp governance_tools/memory_janitor.py            /your/project/
cp -r examples/starter-pack/memory/              /your/project/

cp examples/starter-pack/CLAUDE.md               /your/project/          # Claude Code
cp examples/starter-pack/GEMINI.md               /your/project/          # Gemini
mkdir -p /your/project/.github
cp examples/starter-pack/.github/copilot-instructions.md \
   /your/project/.github/
```

### 方式 B：使用自動升級 / 補齊工具

對已經採用 starter-pack 的 repo，可以用：

```bash
python -m governance_tools.upgrade_starter_pack --repo /your/project --dry-run
python -m governance_tools.upgrade_starter_pack --repo /your/project
```

這條路徑的定位是：

- 補齊缺失的 starter-pack 檔案
- 視需要 refresh adapter / prompt surfaces
- 不把 repo 自動升級成完整 framework

> `upgrade_starter_pack` 是 instruction / scaffold refresh，不是治理品質認證。

---

## 使用規則

### 1. 先維護 `PLAN.md`

`PLAN.md` 是 starter-pack 的核心。每次 session 前，AI 都應先讀這份檔案。

至少要維護：

- 專案目標
- 目前 phase
- `## Current Sprint`
- `## Backlog`
- 架構邊界與 anti-goals

### 2. 控制記憶壓力

若 `memory/01_active_task.md` 逐漸膨脹，應使用：

```bash
python memory_janitor.py --plan
```

確認整理方案後再執行：

```bash
python memory_janitor.py --execute
```

### 3. 專案長大後應升級

當 repo 進入以下狀態時，應考慮升級到完整 framework：

- 需要 runtime governance
- 需要 closeout / audit / readiness
- 需要 external repo adoption baseline
- 需要規則 pack、drift check、source audit

---

## 常見誤解

### 誤解 1：有 starter-pack 就等於已導入 framework

不是。starter-pack 只是最小治理起點，不是完整 adopt。

### 誤解 2：跑過 upgrade_starter_pack 就等於治理成熟

不是。這只代表 starter-pack managed files 已補齊或 refresh。

### 誤解 3：`PLAN.md` 可以長期不更新

不行。starter-pack 的治理效果高度依賴 `PLAN.md` 是否還是可信的 source of truth。

---

## 下一步

如果你要的是完整治理框架，而不是最小提示骨架，請回到 framework root 參考：

- `README.md`
- `docs/INTEGRATION_GUIDE.md`
- `governance_tools/adopt_governance.py`
