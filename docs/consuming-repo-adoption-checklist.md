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
python ai-governance-framework/runtime_hooks/core/pre_task_check.py --contract ./contract.yaml --risk L1 --task-text "Implement parser without sample file"
```

目標：

- 有 `decision_boundary`
- 有 `boundary_effect`
- hook 有真的進到 governance decision path

## Step 8：gate policy 配置

consuming repo 應在 `governance/gate_policy.yaml` 放置自己的 gate policy，而不是依賴 framework default。

不放的後果：

- session_end_hook 每次都會發出 `repo_local_policy_missing` warning
- gate 行為由 framework default 決定（strict）
- reviewer 無法（從 diff）看出 consuming repo 的預期 risk posture

### 最小配置

```yaml
version: "1"

fail_mode: strict   # strict / permissive / audit

blocking_actions:
  - production_fix_required

unknown_treatment:
  mode: block_if_count_exceeds
  threshold: 3

artifact_stale_seconds: 86400
```

### 結構性無 test artifact 的 repo（C++、韌體、純文件）

如果 consuming repo 在結構上無法產出 test-result artifact（例如：C++ 專案、純文件 repo、沒有 Python 測試套件的 tooling repo），應使用 `skip_test_result_check: true` 明確宣告，而**不是**調高 `signal_threshold_ratio` 來壓制 false positive。

```yaml
version: "1"

fail_mode: warn

skip_test_result_check: true   # 結構性宣告：此 repo 不產出 test-result artifact

blocking_actions:
  - production_fix_required

unknown_treatment:
  mode: never_block

artifact_stale_seconds: 0
```

`skip_test_result_check: true` 的效果：

- `test_result_artifact_absent` advisory signal 不再被發出
- gate.blocked **完全不受影響**
- E8a audit log 仍然寫入（`signals=[]`），結構宣告可被觀測
- `format_human_result` 改顯示 `[skipped] test_result_check: structural absence declared`

這是一個明確的結構性宣告，不是 threshold 調整。它讓 reviewer 可以從 policy diff 看出「這個 repo 有意識地選擇不跑測試」，而不是靠提高 ratio 隱蔽本質。

### canonical_audit_trend 配置（可選）

如果 session 頻率高，建議調整：

```yaml
canonical_audit_trend:
  window_size: 50          # 預設 20；頻率高的 repo 應加大視窗
  signal_threshold_ratio: 0.3   # 預設 0.5；較嚴格的 repo 可降低
```



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

### 類型 D：gate policy 配置語義不正確

例如：

- 沒有 `governance/gate_policy.yaml`，每次 session_end_hook 都發出 `repo_local_policy_missing` warning
- C++ / 韌體 repo 用 `signal_threshold_ratio: 0.95` 壓制 `test_result_artifact_absent`，
  而不是用 `skip_test_result_check: true` 做結構宣告
- `fail_mode: permissive` 但 consuming repo 其實想 gate on `production_fix_required`



導入成功，不是指「檔案有了」，而是 repo 已經進入一條可被檢查、可被 reviewer 理解、也可逐步進入 bounded governance runtime 的 adoption path。
