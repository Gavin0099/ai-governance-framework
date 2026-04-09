# Consuming Repo 導入驗證清單

## 目的

這份清單用來驗證：

> 使用者在一個尚未導入的專案裡，把 `ai-governance-framework` 以 submodule 或等價方式拉進來後，是否真的完成導入。

關鍵不是「framework clone 進 repo」而已，而是要確認：

- framework 檔案真的接進 consuming repo
- adopt 已執行
- drift / smoke 可跑
- runtime hook 已經能產生治理輸出

## Step 1：確認 submodule / scaffold 是否存在

至少應看到：

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

如果只有 submodule，卻沒有上面這些檔案，表示只是 clone 了 framework，還沒真的 adopt。

## Step 2：執行 adopt

```powershell
python ai-governance-framework/governance_tools/adopt_governance.py --target . --framework-root ./ai-governance-framework
```

### 預期結果

- 無 critical adopt failure
- 會寫出 baseline / scaffold
- 既有檔案若可保留，應保留而不是粗暴覆蓋

## Step 3：跑 drift

```powershell
python ai-governance-framework/governance_tools/governance_drift_checker.py --repo . --framework-root ./ai-governance-framework
```

### 預期結果

- 無 `critical`
- 若有 `warning`，必須可解釋

特別要看：

- `baseline_yaml_present`
- `protected_files_present`
- `protected_files_unmodified`
- `contract_required_fields_present`
- `memory_schema_complete`

## Step 4：跑 quickstart smoke

```powershell
python ai-governance-framework/governance_tools/quickstart_smoke.py
```

### 預期結果

- `ok=True`
- `pre_task_ok=True`
- `session_start_ok=True`

## Step 5：跑 runtime surface consistency smoke

```powershell
python ai-governance-framework/governance_tools/runtime_surface_manifest_smoke.py --format human
```

### 預期結果

- `unknown_surfaces=0`
- `orphan_surfaces=0`
- `evidence_surface_mismatch=0`

## Step 6：跑 project facts intake / readiness

```powershell
python ai-governance-framework/governance_tools/external_project_facts_intake.py --repo . --project-root ./ai-governance-framework --format human
python ai-governance-framework/governance_tools/external_repo_readiness.py --repo . --framework-root ./ai-governance-framework --format human
```

### 預期結果

- `memory_schema_status=complete` 或明確顯示 `partial`
- readiness 不會把 partial schema 假裝成 complete

## Step 7：驗 runtime hook 是否真的進 decision path

至少跑一次 `pre_task_check`：

```powershell
python ai-governance-framework/runtime_hooks/core/pre_task_check.py --contract ./contract.yaml --task-level L1 --task-text "Implement parser without sample file"
```

### 預期結果

- 有 `decision_boundary`
- 有 `boundary_effect`
- hook 不是只回文字，而是真的進入 governance decision path

## 最小成功標準

下列條件都成立，才算「正確導入」：

1. submodule / framework checkout 存在
2. `adopt_governance.py` 已跑過
3. `governance_drift_checker.py` 無 critical
4. memory scaffold 存在
5. `quickstart_smoke.py` 回傳 `ok=True`
6. `runtime_surface_manifest_smoke.py` 無 consistency signal
7. 至少一個 runtime hook 有產生治理輸出

## 常見失敗類型

### 類型 A：只有 submodule，沒有 adopt

現象：

- 沒有 `.governance/baseline.yaml`
- 沒有 `AGENTS.base.md`
- 沒有 memory scaffold

### 類型 B：adopt 完成，但 memory schema 仍 partial

現象：

- `memory_schema_status=partial`
- `memory_schema_complete` warning

### 類型 C：靜態導入成功，但 runtime 沒接上

現象：

- 檔案都在
- drift / smoke 可能也能跑
- 但 runtime hook 沒有治理輸出

## 一句話結論

正確導入 `ai-governance-framework`，不是「submodule 在」而已，而是：adopt 已完成、drift 可檢、smoke 可跑、memory schema 狀態可見、且 runtime hook 已真的進 decision path。
