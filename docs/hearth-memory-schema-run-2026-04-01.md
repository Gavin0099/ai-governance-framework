# Hearth Memory Schema Run — 2026-04-01

## 範圍

驗證當前 `ai-governance-framework` 是否能正確處理 Hearth 這種 consuming repo 的兩種狀態：

1. pre-adoption partial memory schema
2. post-adoption scaffolded memory schema

## 環境

- Framework root: `E:\BackUp\Git_EE\ai-governance-framework`
- Scratch repo: `E:\BackUp\Git_EE\hearth-memory-check`
- Scratch baseline commit before local full adoption: `03dca60` (`Extract transaction import batch helper`)
- Scratch state after pre-check cleanup: detached HEAD at `03dca60`, 並用 `git clean -fd` 清掉較新的 untracked scaffold 檔

## Step 0

建立 scratch clone：

```powershell
git clone https://github.com/Gavin0099/Hearth.git e:\BackUp\Git_EE\hearth-memory-check
```

## Step 1：Pre-Adoption 狀態

### Adopt 前的 memory 目錄

```text
02_tech_stack.md
2026-03-21.md
2026-03-22.md
2026-03-23.md
2026-03-26.md
2026-03-27.md
2026-03-28.md
2026-03-29.md
2026-03-30.md
2026-03-31.md
2026-04-01.md
```

### 執行命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python ..\ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root ..\ai-governance-framework

$env:PYTHONPATH='..\ai-governance-framework'
python ..\ai-governance-framework\governance_tools\external_project_facts_intake.py --repo . --project-root ..\ai-governance-framework --format human

python ..\ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root ..\ai-governance-framework --format human
```

### Pre-Adoption 結果摘要

- `governance_drift_checker.py`
  - `memory_schema_complete = FAIL`
  - warning 明確指出：
    - `memory/ schema is partial`
    - 缺少 `active_task`、`knowledge_base`、`review_log`

- `external_project_facts_intake.py`
  - `source_filename = 02_tech_stack.md`
  - `memory_schema_status = partial`
  - `missing_logical_names = knowledge_base,review_log,active_task`

- `external_repo_readiness.py`
  - `project_facts.status = available`
  - `project_facts.source_filename = 02_tech_stack.md`
  - `project_facts.schema_status = partial`
  - `project_facts_schema_complete = False`

### Pre-Adoption 判定

`partial correctly detected = YES`

---

## Step 2：Adopt

### 執行命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python ..\ai-governance-framework\governance_tools\adopt_governance.py --target . --framework-root ..\ai-governance-framework
```

### Adopt 結果摘要

- 保留既有：
  - `PLAN.md`
  - `AGENTS.md`
  - `contract.yaml`
  - `memory/02_tech_stack.md`

- 新增：
  - `.governance/baseline.yaml`
  - `memory/01_active_task.md`
  - `memory/03_knowledge_base.md`
  - `memory/04_review_log.md`

值得注意的是：

- adopt 沒有建立 `02_project_facts.md`
- adopt 沒有建立 `03_decisions.md`
- adopt 採用 canonical scaffold naming，但仍保留既有 `02_tech_stack.md` 來滿足 tech/project-facts logical slot

---

## Step 3：Post-Adoption 狀態

### Adopt 後的 memory 目錄

```text
01_active_task.md
02_tech_stack.md
03_knowledge_base.md
04_review_log.md
2026-03-21.md
2026-03-22.md
2026-03-23.md
2026-03-26.md
2026-03-27.md
2026-03-28.md
2026-03-29.md
2026-03-30.md
2026-03-31.md
2026-04-01.md
```

### 執行命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python ..\ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root ..\ai-governance-framework

$env:PYTHONPATH='..\ai-governance-framework'
python ..\ai-governance-framework\governance_tools\external_project_facts_intake.py --repo . --project-root ..\ai-governance-framework --format human

python ..\ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root ..\ai-governance-framework --format human
```

### Post-Adoption 結果摘要

- `governance_drift_checker.py`
  - `memory_schema_complete = PASS`

- `external_project_facts_intake.py`
  - 仍選擇 `02_tech_stack.md` 作為 project-facts source
  - 也能解析新增的：
    - `03_knowledge_base.md`
    - `04_review_log.md`
    - `01_active_task.md`
  - `memory_schema_status = complete`

- `external_repo_readiness.py`
  - `project_facts.source_filename = 02_tech_stack.md`
  - `project_facts.schema_status = complete`
  - `project_facts_schema_complete = True`

### Post-Adoption 判定

- `scaffold correctly created = YES`
- `post-adopt schema complete = YES`

---

## Alias 行為觀察

在 Hearth 這種前提下：

- pre-adopt 只有 `02_tech_stack.md`
- post-adopt 後：
  - 原本的 `02_tech_stack.md` 被保留
  - intake 繼續使用 `02_tech_stack.md`
  - framework 補齊缺少的 canonical scaffold files
  - 沒有多生成一份 `02_project_facts.md`

### 評估

`alias behavior acceptable = YES`

原因：

- framework 沒有覆寫或複製既有 facts file
- 它是補齊 schema，而不是重造一份重複 truth source
- readiness / intake 只有在缺少的 logical slots 補齊後，才從 `partial` 轉成 `complete`

---

## Root Workflow 觀察

就算 scaffold 已建立，Hearth 這種 repo 的日常工作模式仍明顯保留：

- `PLAN.md`
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`

也就是說，這次驗證同時證明了兩件不同的事：

1. framework memory scaffold 已建立
2. repo 日常 workflow 仍可能主要依賴舊的 `PLAN + MEMORY + daily-log` 模式

這兩件事不能混成一件事。

---

## 額外觀察

- 在 Windows 上，`governance_drift_checker.py` 與 `adopt_governance.py` 需要 `PYTHONIOENCODING=utf-8`，否則可能出現 `cp950` `UnicodeEncodeError`
- `external_project_facts_intake.py` 以這種方式直接呼叫時，需要 `PYTHONPATH=..\ai-governance-framework`
- 還有一個非 memory 類 warning 在 adopt 前後都存在：
  - `expansion_boundary: new_return_key: unrecognized key(s) in return dict: ['boundary_effect', 'preconditions_checked']`
  - 這不影響 memory schema completion 的判定

---

## 最終判定

- `partial correctly detected`: **PASS**
- `scaffold correctly created`: **PASS**
- `single 02_* no longer impersonates complete schema after tooling check`: **PASS**

## 一句話結論

framework 現在已能正確處理 Hearth 這種 partial repo：  
在 adopt 前，它會明確標成 `partial`；在 adopt 後，它會補齊缺少的 logical files，讓 readiness / intake 正式轉成 `complete`，不再讓單一 `02_tech_stack.md` 偽裝成完整 memory schema。
