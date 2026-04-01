# Consuming Repo 導入驗證清單

## 目的

這份清單用來驗證一個原本**未導入**的專案，在執行：

> clone `https://github.com/Gavin0099/ai-governance-framework` 做成 submodule，然後導入進去

之後，是否已經**正確導入** `ai-governance-framework`。

這裡的「正確導入」不是只看 submodule 在不在，而是要確認：

- framework 檔案已接入 repo
- adopt 流程已完成
- drift / smoke 可運作
- runtime hook 已經能對 consuming repo 產生治理輸出

## 假設路徑

假設 consuming repo 結構如下：

```text
<target-repo>/
  ai-governance-framework/   # git submodule
```

以下命令都在 `<target-repo>` 根目錄執行。

## Step 1：確認 submodule 與基礎檔案是否存在

先確認至少有這些東西：

- `ai-governance-framework/`
- `.governance/baseline.yaml`
- `AGENTS.base.md`
- `contract.yaml`
- `PLAN.md`
- `.github/workflows/governance-drift.yml`

以及最小 memory scaffold：

- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`

### PowerShell 快速檢查

```powershell
Get-ChildItem ai-governance-framework
Test-Path .governance/baseline.yaml
Test-Path AGENTS.base.md
Test-Path contract.yaml
Test-Path PLAN.md
Test-Path .github/workflows/governance-drift.yml
Test-Path memory/01_active_task.md
Test-Path memory/02_tech_stack.md
Test-Path memory/03_knowledge_base.md
Test-Path memory/04_review_log.md
```

### 判讀

- 如果只有 submodule 存在，但其他檔案都沒有：
  - 代表只是把 framework clone 進 repo
  - **還沒完成 adopt**

## Step 2：執行 adopt

```powershell
python ai-governance-framework/governance_tools/adopt_governance.py --target . --framework-root ./ai-governance-framework
```

### 預期結果

- 不應出現 critical adopt failure
- 會寫入：
  - `.governance/baseline.yaml`
  - `AGENTS.base.md`
  - 缺少時補 `AGENTS.md`
  - 缺少時補 `contract.yaml`
  - 缺少時補 `PLAN.md`
  - 缺少時補 `.github/workflows/governance-drift.yml`
  - 最小 memory scaffold

### 補充

如果只想先看會做什麼，可先跑：

```powershell
python ai-governance-framework/governance_tools/adopt_governance.py --target . --framework-root ./ai-governance-framework --dry-run
```

## Step 3：驗證 drift

```powershell
python ai-governance-framework/governance_tools/governance_drift_checker.py --repo . --framework-root ./ai-governance-framework
```

### 最低成功標準

- 不應有 `critical`
- `warning` 可以存在，但要可解釋

### 特別要看

- `baseline_yaml_present`
- `protected_files_present`
- `protected_files_unmodified`
- `contract_required_fields_present`
- `memory_schema_complete`

### 判讀

- 如果 `memory_schema_complete` 是 `FAIL`
  - 代表 memory schema 仍是 partial
  - 不是完整導入

## Step 4：驗證 quickstart smoke

```powershell
python ai-governance-framework/governance_tools/quickstart_smoke.py
```

### 最低成功標準

- `ok=True`

### 補充

如果看到：

- `contract_mode=repo-default`
- `contract_note=no explicit --contract provided; using repo-local governance defaults`

這是目前預期行為，不是模糊錯誤。

## Step 5：驗證 runtime surface consistency smoke

```powershell
python ai-governance-framework/governance_tools/runtime_surface_manifest_smoke.py --format human
```

### 預期結果

- `unknown_surfaces=0`
- `orphan_surfaces=0`
- `evidence_surface_mismatch=0`

### 判讀

如果這裡出現非 0，代表：

- repo 內的 execution/evidence surface 與 framework manifest 不一致
- 導入可能不完整，或已經 drift

## Step 6：驗證 project facts intake / readiness

```powershell
python ai-governance-framework/governance_tools/external_project_facts_intake.py --repo . --project-root ./ai-governance-framework --format human

python ai-governance-framework/governance_tools/external_repo_readiness.py --repo . --framework-root ./ai-governance-framework --format human
```

### 預期結果

- intake 不應靜默把單一 `02_*` 當成完整 schema
- 應明示：
  - `memory_schema_status=complete`
  - 或 `memory_schema_status=partial`

### 判讀

- 如果是 `partial`
  - 代表 framework 有接上
  - 但 consuming repo 的 memory schema 還不完整
- 如果是 `complete`
  - 代表 memory 導入至少在 schema 面是完整的

## Step 7：驗證 runtime hook 是否真的進入 decision path

最少跑一次 `pre_task_check`。

範例：

```powershell
python ai-governance-framework/runtime_hooks/core/pre_task_check.py --contract ./contract.yaml --task-level L1 --task-text "Implement parser without sample file"
```

### 你要看的是

- 有沒有出現 `decision_boundary`
- 有沒有出現 `boundary_effect`
- 有沒有出現 task-level 對應的結果，例如：
  - `analysis_only`
  - `restrict_code_generation_and_escalate`
  - `stop`

### 判讀

如果這一步完全沒有治理輸出，通常代表：

- contract 沒接對
- runtime hook 沒進 decision path
- 或 consuming repo 其實只完成了靜態 adopt，沒完成 runtime 驗證

## 最小成功標準

要判定為「正確導入」，至少要同時滿足：

1. submodule 存在
2. `adopt_governance.py` 成功執行
3. `governance_drift_checker.py` 沒有 critical
4. 最小 memory scaffold 存在
5. `quickstart_smoke.py` 回傳 `ok=True`
6. `runtime_surface_manifest_smoke.py` 沒有 consistency signal
7. 至少一個 runtime hook 產生可讀治理輸出

## 失敗分類

### 類型 A：只有 submodule，沒有 adopt

現象：

- 沒有 `.governance/baseline.yaml`
- 沒有 `AGENTS.base.md`
- 沒有 memory scaffold

判斷：

- framework 只是被 clone 進來
- 還沒有導入

### 類型 B：adopt 完成，但 schema 仍 partial

現象：

- `external_project_facts_intake.py` 顯示 `memory_schema_status=partial`
- drift 顯示 `memory_schema_complete` warning

判斷：

- 有導入，但不完整

### 類型 C：靜態導入成功，但 runtime 未接上

現象：

- 檔案都在
- drift / smoke 看起來正常
- 但 runtime hook 沒有產生治理輸出

判斷：

- adopt 成功
- runtime integration 還沒驗證完成

## 一句話總結

> 正確導入 `ai-governance-framework`，不是「submodule 在」而已，而是「adopt 完、drift 可檢、smoke 可跑、memory schema 不再是 partial、runtime hook 已經能輸出治理結果」。
