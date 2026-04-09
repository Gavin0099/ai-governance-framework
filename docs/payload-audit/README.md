# Payload Audit

這個資料夾用來記錄治理 payload 的量測結果，目的是回答：

- `session_start`、onboarding、baseline re-run 目前各自消耗多少 token
- 哪些 slice 是主要成本來源
- 某次優化之後，成本是真的下降，還是只是輸出形狀改變

這裡存放的是量測基準與比較結果，不是新的 authority layer。

## 用途

主要用在三種情境：

1. 建立 baseline
2. 重新量測 rebaseline
3. 用實測資料重新排序 deferred work

## 常見 baseline 類型

| 任務形狀 | 範例命令 | 對應基準文件 |
|---|---|---|
| `L0` UI / presentation | `python runtime_hooks/core/session_start.py --risk low --task-level L0 --task-type ui --task-text "Update button label"` | `L0-baseline.md` |
| `L1` 一般實作 / schema | `python runtime_hooks/core/session_start.py --risk medium --task-level L1 --task-type schema --task-text "Modify API schema"` | `L1-baseline.md` |
| `Onboarding` / adoption | `python governance_tools/adopt_governance.py --target <repo>` 或對應 onboarding shaped run | `onboarding-baseline.md` |

## 建立 baseline 的基本流程

### 1. 開啟 audit

```bash
export GOVERNANCE_PAYLOAD_AUDIT=1   # Linux / macOS
set GOVERNANCE_PAYLOAD_AUDIT=1      # Windows CMD
$env:GOVERNANCE_PAYLOAD_AUDIT="1"   # Windows PowerShell
```

### 2. 執行目標 task shape

用固定命令重跑 `L0` / `L1` / `Onboarding`，避免量測混進臨時變數。

### 3. 產生 baseline 文件

```bash
python governance_tools/payload_audit_logger.py baseline --task-level L0 --output docs/payload-audit/L0-baseline.md
python governance_tools/payload_audit_logger.py baseline --task-level L1 --output docs/payload-audit/L1-baseline.md
python governance_tools/payload_audit_logger.py baseline --task-level onboarding --output docs/payload-audit/onboarding-baseline.md
```

### 4. 關閉 audit

```bash
unset GOVERNANCE_PAYLOAD_AUDIT       # Linux / macOS
$env:GOVERNANCE_PAYLOAD_AUDIT="0"    # Windows PowerShell
```

## 目錄說明

| 檔案 | 說明 |
|---|---|
| `audit_log.jsonl` | 每次量測留下的原始 JSONL 記錄；不要直接 commit |
| `L0-baseline.md` | `L0` task shape 的 token 基準 |
| `L1-baseline.md` | `L1` task shape 的 token 基準 |
| `onboarding-baseline.md` | onboarding / adoption shaped run 的基準 |
| `step7-rebaseline-checklist.md` | Step 7 後重新量測的操作清單 |
| `step1-step7-token-summary.md` | Step 1 到 Step 7 的比較摘要 |
| `README.md` | 本資料夾入口說明 |

## 解讀原則

- **先看 top token contributors，再看總量**
- **domain contract 變薄，不等於治理成本整體已健康**
- **memory / governance payload 的變化要分開看**

## 注意事項

- `audit_log.jsonl` 屬於本地量測資料，應維持在 `.gitignore`
- baseline `.md` 屬於可追蹤的比較基準，應提交進 repo
- rebaseline 時要和**目前已提交的 baseline**比較，不要只和印象比較
