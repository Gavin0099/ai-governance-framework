# Hearth Memory Schema 驗證清單

## 目的

驗證最新版 `ai-governance-framework` 是否能正確處理 Hearth 這種
「部分導入、只有 `memory/02_tech_stack.md` 可用」的 consuming repo。

這份清單要回答兩個問題：

1. 在 **未重新 adopt** 的舊狀態下，framework 是否會把 partial schema
   明確標成 `partial`，而不是靜默當成完整導入。
2. 在 **重新 adopt** 之後，framework 是否會補齊最小 memory scaffold，
   並讓 drift / intake / readiness 反映新的完整狀態。

## 測試前提

- 不要直接在 Hearth 的主工作樹上做第一次驗證。
- 先用 scratch clone 或暫時副本。
- 明確指定 `--framework-root` 指向目前這份 framework checkout。

假設：

- framework repo: `e:\BackUp\Git_EE\ai-governance-framework`
- scratch repo: `e:\BackUp\Git_EE\hearth-memory-check`

## Step 0：建立 scratch clone

```powershell
git clone <HEARTH_REPO_URL> hearth-memory-check
Set-Location hearth-memory-check
```

如果 Hearth 已經在本機，直接複製工作樹也可以，但不要先用主 repo。

## Step 1：先看舊狀態

在**尚未重新 adopt** 的 scratch repo 中執行：

```powershell
python ..\ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root ..\ai-governance-framework

python ..\ai-governance-framework\governance_tools\external_project_facts_intake.py --repo . --project-root ..\ai-governance-framework --format human

python ..\ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root ..\ai-governance-framework --format human
```

### 預期結果

- `governance_drift_checker.py`
  - 應該出現 `memory_schema_complete` warning
  - warning 應指出缺少的 logical files

- `external_project_facts_intake.py`
  - 若只有 `02_tech_stack.md` 或 `02_project_facts.md`
  - 應顯示：
    - `memory_schema_status=partial`
    - `missing_logical_names=...`

- `external_repo_readiness.py`
  - `project_facts` 可為 `available`
  - 但應伴隨 partial schema 訊號
  - 不應再讓單一 `02_*` 看起來像完整 memory schema

## Step 2：重新 adopt

在同一份 scratch repo 中執行：

```powershell
python ..\ai-governance-framework\governance_tools\adopt_governance.py --target . --framework-root ..\ai-governance-framework
```

### 預期結果

`memory/` 應至少出現：

- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`

如果原本已有 alias 檔名，例如 `02_project_facts.md`，要記錄 adopt 是否保留既有檔，
以及是否新增 canonical scaffold。

## Step 3：再看 adopt 後狀態

重新執行：

```powershell
python ..\ai-governance-framework\governance_tools\governance_drift_checker.py --repo . --framework-root ..\ai-governance-framework

python ..\ai-governance-framework\governance_tools\external_project_facts_intake.py --repo . --project-root ..\ai-governance-framework --format human

python ..\ai-governance-framework\governance_tools\external_repo_readiness.py --repo . --framework-root ..\ai-governance-framework --format human
```

### 預期結果

- `governance_drift_checker.py`
  - `memory_schema_complete` 應轉為 `PASS`

- `external_project_facts_intake.py`
  - `memory_schema_status` 應轉為 `complete`
  - `missing_logical_names` 應為空

- `external_repo_readiness.py`
  - 不再只依賴單一 `02_*`
  - `project_facts_schema_complete` 應為 `True`

## 要特別記錄的觀察點

### 1. 既有 alias 行為

如果 Hearth 原本只有：

- `02_tech_stack.md`
  或
- `02_project_facts.md`

請記錄：

- adopt 後是否保留原檔
- intake 最後選的是哪個檔名
- 是否有重複或衝突

### 2. root schema 是否仍是舊 workflow

請另外記錄 Hearth root 是否仍以這些為主：

- `PLAN.md`
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`

如果是，則要區分：

- `framework memory scaffold 已建立`
- 與
- `repo 實際工作流是否已切換`

這兩件事不是同一件事。

### 3. 是否需要 migration 決策

如果 adopt 後只補了 scaffold，但 Hearth 仍主要依賴：

- `PLAN.md`
- `MEMORY.md`
- daily logs

那後續要決定的是：

- 正式切到 `01/02/03/04`
  或
- 承認 Hearth 的舊 schema，改 framework alias / onboarding 規則

## 驗證輸出建議

把結果記成一份簡短 run record，例如：

- `docs/hearth-memory-schema-run-YYYY-MM-DD.md`

至少記：

- scratch repo commit / branch
- adopt 前輸出摘要
- adopt 後輸出摘要
- `memory/` 實際檔案列表
- 最終判斷：
  - partial correctly detected
  - scaffold correctly created
  - alias behavior acceptable or not

## 一句成功標準

成功不只是「補出 01/03/04」。

真正成功標準是：

> adopt 前會被明確標成 partial，adopt 後會補齊 scaffold，且整個過程不再讓單一 `02_*` 冒充完整 memory schema。
