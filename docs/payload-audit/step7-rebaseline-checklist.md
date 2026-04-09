# Step 7 Rebaseline Checklist

> 目的：讓 Step 7 `output tier separation` 上線後，重新建立對應 baseline task shape  
> 這份清單只處理 token 結構與 payload 變化，不處理 deferred work 的最終設計

## 範圍

重新建立基線時，至少要覆蓋：
1. `L0` UI / presentation
2. `L1` schema / logic
3. `Onboarding` / adoption

目前 baseline 參考：
- [L0-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L0-baseline.md)
- [L1-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L1-baseline.md)
- [onboarding-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/onboarding-baseline.md)

## 前置檢查

- pull 最新 `main`
- 確認 Step 7 對應 commit 已存在，例如 `e35f60c`
- 確認 payload audit 所需 Python/runtime 路徑可執行
- 確認這次 run 的目標是重建 baseline，而不是混入其他優化實驗

## 命令範例

### L0

```bash
python runtime_hooks/core/session_start.py ^
  --project-root . ^
  --rules common ^
  --risk low ^
  --oversight auto ^
  --memory-mode candidate ^
  --task-level L0 ^
  --task-type ui ^
  --task-text "Update button label in UI" ^
  --format json
```

### L1

```bash
python runtime_hooks/core/session_start.py ^
  --project-root . ^
  --rules common ^
  --risk medium ^
  --oversight auto ^
  --memory-mode candidate ^
  --task-level L1 ^
  --task-type schema ^
  --task-text "Refactor state generator module" ^
  --format json
```

### Onboarding

```bash
python runtime_hooks/core/session_start.py ^
  --project-root . ^
  --rules common ^
  --risk medium ^
  --oversight auto ^
  --memory-mode candidate ^
  --task-level L1 ^
  --task-type onboarding ^
  --task-text "Adopt governance baseline for external repo" ^
  --format json
```

## 每次 run 至少要記的欄位

- task shape（`L0` / `L1` / `Onboarding`）
- commit SHA
- 日期
- output 是否 `ok`
- `task_level`
- `repo_type`
- `output_tier`
- token estimate 總量
- top token contributors
- `domain_contract` 是否載入
- Tier 3 artifact path 是否存在
- notable warnings / blocker

## 解讀原則

重建 baseline 的目的是看 Step 7 是否真的改變 payload 結構，而不是只看總 token 有沒有下降。
重點包括：
1. `L1` 與 `Onboarding` 是否與 `L0` 明顯分層
2. `domain_contract` 與 rendered output 的相對佔比是否改變
3. 是否需要把 `Step 3b` 的 full memory refactor 納入後續檢查
4. `Onboarding` 是否仍屬於 `summary-first` 之外的 deferred optimization

## 建議記錄格式

```markdown
## Step 7 Rebaseline <task-shape>

- Date: <YYYY-MM-DD>
- Commit: <sha>
- Command: `<exact command>`
- ok: <true|false>
- task_level: <L0|L1|L2>
- repo_type: <value>
- output_tier: <1|2|3>
- estimated_tokens: <number>
- domain_contract_loaded: <true|false>
- tier3_artifact_ref: <path or none>
- top_token_sources:
  - <source 1>
  - <source 2>
  - <source 3>
- notable_warnings:
  - <warning or none>
- delta_vs_current_baseline:
  - <L0/L1/onboarding delta>
- interpretation:
  - <what changed after Step 7>
- next_decision:
  - <stop / defer / continue specific optimization>
```

## 一句總結

Step 7 rebaseline 的重點，是確認 `output tier separation` 之後 payload 結構是否真的改變，而不是只把舊 baseline 換成新數字。
