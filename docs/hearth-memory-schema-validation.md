# Hearth Memory Schema 驗證清單

## 目的

這份清單用來驗證目前 `ai-governance-framework` 是否能正確處理 Hearth 這類舊形態 consuming repo：
它可能長期只保留 `memory/02_tech_stack.md`，卻沒有完整 memory scaffold。

這份驗證要確認兩件事：
1. 在 **未 adopt** 狀態下，framework 能否正確把它標成 `partial`
2. 在 **重新 adopt** 後，framework 能否補齊最小 scaffold，並讓 drift / intake / readiness 正確轉為 `complete`

## 測試前提

- 不要直接在 Hearth 主工作樹上測
- 先建立 scratch clone，避免污染真實 repo
- 所有命令都明確指定 `--framework-root`

建議路徑：
- framework repo：`e:\BackUp\Git_EE\ai-governance-framework`
- scratch repo：`e:\BackUp\Git_EE\hearth-memory-check`

## Step 0：建立 scratch clone

```powershell
git clone <HEARTH_REPO_URL> hearth-memory-check
Set-Location hearth-memory-check
```

## Step 1：在 adopt 之前先看 partial 狀態

```powershell
python ..\ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root ..\ai-governance-framework

python ..\ai-governance-framework\governance_tools\external_project_facts_intake.py --repo . --project-root ..\ai-governance-framework --format human

python ..\ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root ..\ai-governance-framework --format human
```

### 預期

- `governance_drift_checker.py`
  - 應出現 `memory_schema_complete` warning
  - warning 應明確指出缺少 logical files

- `external_project_facts_intake.py`
  - 若只存在 `02_tech_stack.md`，應顯示：
    - `memory_schema_status=partial`
    - `missing_logical_names=...`

- `external_repo_readiness.py`
  - `project_facts` 可以是 `available`
  - 但不能把單一 `02_*` 誤判成完整 memory schema

## Step 2：重新 adopt

```powershell
python ..\ai-governance-framework\governance_tools\adopt_governance.py --target . --framework-root ..\ai-governance-framework
```

### 預期

`memory/` 至少應出現：
- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`

若 repo 原本已有 `02_tech_stack.md`，應保留既有檔案，而不是重複建立 `02_project_facts.md`。

## Step 3：adopt 後重新檢查

```powershell
python ..\ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root ..\ai-governance-framework

python ..\ai-governance-framework\governance_tools\external_project_facts_intake.py --repo . --project-root ..\ai-governance-framework --format human

python ..\ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root ..\ai-governance-framework --format human
```

### 預期

- `governance_drift_checker.py`
  - `memory_schema_complete` 應變成 `PASS`

- `external_project_facts_intake.py`
  - `memory_schema_status` 應變成 `complete`
  - `missing_logical_names` 應消失

- `external_repo_readiness.py`
  - `project_facts_schema_complete` 應變成 `True`

## 觀察重點

### 1. alias 行為

如果原本只有 `02_tech_stack.md`：
- framework 應保留它
- 應補 canonical scaffold 到其他缺的 logical slot
- 不應為了「統一名字」而重複建立不必要的 `02_*` 檔案

### 2. workflow 與 schema 是兩回事

Hearth 可能仍保留：
- `PLAN.md`
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`

這不表示 framework memory scaffold 沒導入；而是表示 repo workflow 與 scaffold 可以並存。

## 一句總結

這份驗證的關鍵不是「有沒有 memory 檔案」，而是：舊 partial repo 是否會先被正確辨識為 `partial`，並在 adopt 後被補成可觀測、可檢查的完整 schema。
