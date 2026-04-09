# Step 7 Rebaseline Checklist

> 目的：在 Step 7 `output tier separation` 之後，重新量測三種 baseline task shape，  
> 用最新資料確認 token 節省幅度，以及 deferred work 是否該重新排序。

## 範圍

重新量測以下三條 flow：

1. `L0` UI / presentation 任務
2. `L1` 一般實作任務
3. `Onboarding` / adoption 任務

不要只拿新結果和 Step 7 之前的印象比較。  
一定要和目前已提交的 baseline 比：

- [L0-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L0-baseline.md)
- [L1-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L1-baseline.md)
- [onboarding-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/onboarding-baseline.md)

## 前置檢查

- pull 最新 `main`
- 確認 Step 7 commit 已存在：`e35f60c`
- 使用和前一次 payload audit 相同的 Python/runtime 路徑
- 先校正期待值：
  - `L0` 應明顯低於舊的 `L1` baseline
  - `L1` 的改善應主要來自 output 壓縮，而不是 domain 被移除
  - `Onboarding` 應先反映 `summary-first` 的效果，再談新的 deferred optimization

## 命令

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

## 要記錄的欄位

每次 run 至少記下：

- task shape：`L0` / `L1` / `Onboarding`
- commit SHA
- 日期
- output 是否 `ok`
- `task_level`
- `repo_type`
- `output_tier`
- token estimate 總量
- top token contributors
- `domain_contract` 是否有載入
- 是否有輸出 Tier 3 artifact path
- 重要 warning / blocker

## 決策問題

三條 flow 都重跑完之後，再回答這四題，才決定是否做下一輪 payload 優化：

1. Step 7 是否實質降低了 `L1` 和 `Onboarding`，還是只壓到 `L0` presentation？
2. `kernel-driver-adapter-summary.md` 上線後，下一個瓶頸是否已經是 `pre_task_check` / rendered output，而不是 `domain_contract` 本身？
3. 新 baseline 出來後，`Step 3b` 的 full memory refactor 是否仍有必要？
4. `Onboarding` 還需要獨立 short-circuit，還是 `summary-first` 已經足夠？

## 記錄模板

把下面這段貼進對應 baseline 檔或某份 dated note：

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

## 完成條件

滿足以下條件，才算 Step 7 rebaseline 完成：

- 三種 task shape 都已重跑
- 每一種都有記下 token 數
- 每一種都有短版 interpretation
- 已有一份更新後的 comparison summary
- deferred items 已依據**實測資料**重新排序，而不是靠估計
