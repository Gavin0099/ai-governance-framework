# Payload 審計
這個目錄保存與 payload 審計相關的基線、摘要與操作指南。
這個目錄保存與 payload 審計相關的基線、摘要與操作指南。

用途包括：
- 比較 `session_start`、onboarding 與 baseline re-run 的 token 組成
- 觀察不同 slice 的 payload 變化趨勢
- 保留 rebaseline 與延後處理工作的審計痕跡

這裡的內容主要用來支撐 reviewer / maintainer 的觀察，不是新的 authority layer。

## 內容總覽

目前主要包含：
1. 既定 baseline
2. 重新建立 baseline 的操作方式
3. 與 payload 審計有關的 deferred work

## 基線文件

| 類型 | 命令示例 | 對應文件 |
|---|---|---|
| `L0` UI / presentation | `python runtime_hooks/core/session_start.py --risk low --task-level L0 --task-type ui --task-text "Update button label"` | `L0-baseline.md` |
| `L1` schema / logic | `python runtime_hooks/core/session_start.py --risk medium --task-level L1 --task-type schema --task-text "Modify API schema"` | `L1-baseline.md` |
| `Onboarding` / adoption | `python governance_tools/adopt_governance.py --target <repo>` 與對應 onboarding shaped run | `onboarding-baseline.md` |

## 重新建立 baseline 的方式

### 1. 開啟 audit

```bash
export GOVERNANCE_PAYLOAD_AUDIT=1   # Linux / macOS
set GOVERNANCE_PAYLOAD_AUDIT=1      # Windows CMD
$env:GOVERNANCE_PAYLOAD_AUDIT="1"   # Windows PowerShell
```

### 2. 固定 task shape

至少要明確區分 `L0`、`L1` 與 `Onboarding`，不要把不同場景混成同一份 baseline。

### 3. 寫出 baseline 文件

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

## 主要檔案說明

| 檔案 | 說明 |
|---|---|
| `audit_log.jsonl` | 原始 payload 審計紀錄；通常不直接提交 |
| `L0-baseline.md` | `L0` task shape 的 token 基線 |
| `L1-baseline.md` | `L1` task shape 的 token 基線 |
| `onboarding-baseline.md` | onboarding / adoption shaped run 的基線 |
| `step7-rebaseline-checklist.md` | Step 7 rebaseline 操作檢查表 |
| `step1-step7-token-summary.md` | Step 1 到 Step 7 的 token 變化摘要 |
| `README.md` | 本目錄導覽 |

## 觀察重點

建議優先關注：
- top token contributors 是否穩定
- domain contract 變化是否帶來合理的 payload 漲幅
- memory / governance payload 是否出現不必要膨脹

## 使用原則

- `audit_log.jsonl` 屬於原始審計資料，通常應列入 `.gitignore`
- baseline `.md` 屬於可提交的摘要基線，可放回 repo
- rebaseline 應以「更新既有 baseline」為原則，而不是每次都額外產生新基線
