# Consuming Repo 導入檢查清單

## 目的

這份清單用來確認 consuming repo 是真的把 `ai-governance-framework` 導進來，而不是只有把 framework clone 進 repo 或加了一個 submodule。

它的重點是：

- framework source 正確
- adopt 流程有跑
- scaffold / governance pack / rules pack 有落地
- drift / smoke / runtime path 能工作

## Step 1：確認 framework source

至少要先確認：

- framework checkout 來自 canonical source
- consuming repo 的 submodule / clone 版本是預期的 pinned version

建議 source：

```text
https://github.com/Gavin0099/ai-governance-framework.git
```

## Step 2：選擇導入路徑

### 路徑 A：完整 adopt

適用於：

- 希望直接接上 drift / readiness / runtime governance
- 需要 `governance/`、`memory/01~04`、`contract.yaml`

### 路徑 B：starter-pack

適用於：

- repo 還很小
- 目前只需要最小治理骨架
- 還不想導入完整 baseline

starter-pack 目前可搭配：

- [examples/starter-pack/README.md](../examples/starter-pack/README.md)
- [governance_tools/upgrade_starter_pack.py](../governance_tools/upgrade_starter_pack.py)

但要注意：starter-pack 不等於完整 adopt。

## Step 3：完整 adopt 檢查

執行：

```powershell
python ai-governance-framework/governance_tools/adopt_governance.py --target . --framework-root ./ai-governance-framework
```

至少應看到：

- `.governance/baseline.yaml`
- `AGENTS.base.md`
- `contract.yaml`
- `PLAN.md`
- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `governance/*.md`
- `governance/rules/**`

## Step 4：starter-pack 檢查

如果走的是 starter-pack 路徑，至少應確認：

- `SYSTEM_PROMPT.md`
- `PLAN.md`
- `memory/01_active_task.md`
- adapter files（如 `CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md`）
- `memory_janitor.py`

可用以下方式補齊 / refresh：

```powershell
python ai-governance-framework/governance_tools/upgrade_starter_pack.py --repo . --dry-run
python ai-governance-framework/governance_tools/upgrade_starter_pack.py --repo .
```

重點邊界：

- 它會補齊 starter-pack managed files
- 它不會自動把 repo 升級成完整 framework
- 它不會自動覆寫 repo 專屬 `PLAN.md`

## Step 5：drift / readiness

完整 adopt 路徑應至少跑：

```powershell
python ai-governance-framework/governance_tools/governance_drift_checker.py --repo . --framework-root ./ai-governance-framework
python ai-governance-framework/governance_tools/external_repo_readiness.py --repo . --framework-root ./ai-governance-framework --format human
```

目標：

- 沒有 critical drift
- `memory_schema_status` 不是 partial
- framework source 是 canonical

## Step 6：runtime smoke

```powershell
python ai-governance-framework/governance_tools/quickstart_smoke.py
python ai-governance-framework/governance_tools/runtime_surface_manifest_smoke.py --format human
```

## Step 7：runtime hook 路徑

至少驗一次 `pre_task_check`：

```powershell
python ai-governance-framework/runtime_hooks/core/pre_task_check.py --contract ./contract.yaml --task-level L1 --task-text "Implement parser without sample file"
```

目標：

- 有 `decision_boundary`
- 有 `boundary_effect`
- hook 有真的進到 governance decision path

## 失敗類型

### 類型 A：只有 framework checkout，沒有 adopt

通常缺：

- `.governance/baseline.yaml`
- `AGENTS.base.md`
- memory scaffold

### 類型 B：adopt 有跑，但 schema / docs / rules 不完整

例如：

- `memory_schema_status=partial`
- 缺 `governance/rules/`
- `contract.yaml` 沒有帶 `TESTING.md` / `ARCHITECTURE.md`

### 類型 C：只有 starter-pack，卻誤以為已完整導入 framework

這是常見誤讀。

starter-pack 只代表：

- 已有最小治理骨架

不代表：

- 已有 drift checker
- 已有 readiness surface
- 已有 closeout / audit / review runtime

## 一句話

導入成功，不是指「檔案有了」，而是 repo 已經進入一條可被檢查、可被 reviewer 理解、也可逐步進入 bounded governance runtime 的 adoption path。
