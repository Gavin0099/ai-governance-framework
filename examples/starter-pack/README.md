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

**Adoption model 對齊**：starter-pack 是手動複製模式。依 [`docs/ADOPTION_MODEL.md`](../../docs/ADOPTION_MODEL.md)，複製 starter-pack 檔案**不會**讓 repo 成為 governed consumer——它仍在 framework adoption 之前。要取得 managed updates 與完整治理閉環，升級路徑是 submodule adoption（`adopt_governance`），不是繼續累積複製檔案。

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

---

# Starter Pack (English)

Status: a copyable set of governance starter files — not a runnable application.

The purpose of `starter-pack` is to give a new repo a minimal usable
governance skeleton before full framework adoption:

- `SYSTEM_PROMPT.md`
- `PLAN.md`
- `memory/01_active_task.md`
- AI adapter surfaces (Claude / Gemini / Copilot)
- `memory_janitor.py`

Once the project grows and needs runtime governance, drift checks, or
adopt / readiness / audit capabilities, upgrade to the full framework —
do not stay on starter-pack permanently.

## What this starter-pack solves

- Makes the AI read `PLAN.md` at the start of every session
- Gives work focus, memory pressure, and architecture boundaries a minimal dependable entry point
- Gives a new repo a clear governance starting point before full adoption

## What this starter-pack does not claim

- No full runtime governance
- No formal closeout / audit / readiness / drift loop
- Not equivalent to having adopted `ai-governance-framework`

**Adoption model alignment**: starter-pack is a manual-copy pattern. Per
[`docs/ADOPTION_MODEL.md`](../../docs/ADOPTION_MODEL.md), copying
starter-pack files does **not** make the repo a governed consumer — it is
still pre-adoption. The upgrade path to managed updates and the full
governance loop is submodule adoption (`adopt_governance`), not
accumulating more copied files.

## Files

| File | Purpose |
|---|---|
| `SYSTEM_PROMPT.md` | Minimal governance prompt; fixed entry point for every AI session |
| `PLAN.md` | Single text source for project focus and the current sprint |
| `memory/01_active_task.md` | Current task record |
| `CLAUDE.md` | Claude Code adapter |
| `GEMINI.md` | Gemini adapter |
| `.github/copilot-instructions.md` | GitHub Copilot adapter |
| `demo.md` | Walkthrough example |

Also bring from the framework repo:

| File | Source |
|---|---|
| `memory_janitor.py` | `governance_tools/memory_janitor.py` |

## Initialization

### Option A: manual copy

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

### Option B: automated refresh tool

For repos already on starter-pack:

```bash
python -m governance_tools.upgrade_starter_pack --repo /your/project --dry-run
python -m governance_tools.upgrade_starter_pack --repo /your/project
```

What this path is:

- Fills in missing starter-pack files
- Refreshes adapter / prompt surfaces when needed
- Does **not** auto-upgrade the repo to the full framework

> `upgrade_starter_pack` is an instruction / scaffold refresh, not a governance quality certification.

## Usage rules

### 1. Maintain `PLAN.md` first

`PLAN.md` is the core of the starter-pack. The AI should read it before
every session. Maintain at minimum: project goal, current phase,
`## Current Sprint`, `## Backlog`, architecture boundaries and anti-goals.

### 2. Control memory pressure

If `memory/01_active_task.md` grows too large:

```bash
python memory_janitor.py --plan      # review the cleanup plan
python memory_janitor.py --execute   # then execute it
```

### 3. Upgrade when the project grows

Consider upgrading to the full framework when the repo needs: runtime
governance, closeout / audit / readiness, an external repo adoption
baseline, or rule packs / drift check / source audit.

## Common misreadings

1. **Having starter-pack ≠ having adopted the framework.** Starter-pack is
   a minimal starting point, not full adoption.
2. **Running `upgrade_starter_pack` ≠ governance maturity.** It only means
   starter-pack managed files are filled in or refreshed.
3. **`PLAN.md` cannot go stale.** The starter-pack's governance effect
   depends entirely on `PLAN.md` remaining a trustworthy source of truth.

## Next step

For the full governance framework rather than a minimal prompt skeleton,
return to the framework root:

- `README.md`
- `docs/INTEGRATION_GUIDE.md`
- `governance_tools/adopt_governance.py`
