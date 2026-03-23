# Payload Audit

此目錄存放 governance payload 的 token 基線報告。

## 目的

量測每種任務類型在 session_start 實際載入的 token 數，
作為 Step 3-5 優化的量測依據。

## 如何產出 baseline 報告

### 1. 開啟 audit 記錄

```bash
export GOVERNANCE_PAYLOAD_AUDIT=1   # Linux / macOS
set GOVERNANCE_PAYLOAD_AUDIT=1      # Windows CMD
$env:GOVERNANCE_PAYLOAD_AUDIT="1"   # Windows PowerShell
```

### 2. 跑三種任務

| 任務類型 | CLI 範例 | 目標 baseline |
|---------|---------|--------------|
| L0 — UI | `python runtime_hooks/core/session_start.py --risk low --task-level L0 --task-type ui --task-text "Update button label"` | `L0-baseline.md` |
| L1 — Schema | `python runtime_hooks/core/session_start.py --risk medium --task-level L1 --task-type schema --task-text "Modify API schema"` | `L1-baseline.md` |
| Onboarding | `python governance_tools/adopt_governance.py --target /path/to/repo` 後接 session_start | `onboarding-baseline.md` |

### 3. 產出報告

```bash
python governance_tools/payload_audit_logger.py baseline --task-level L0 --output docs/payload-audit/L0-baseline.md
python governance_tools/payload_audit_logger.py baseline --task-level L1 --output docs/payload-audit/L1-baseline.md
python governance_tools/payload_audit_logger.py baseline --task-level onboarding --output docs/payload-audit/onboarding-baseline.md
```

### 4. 關閉 audit 記錄

```bash
unset GOVERNANCE_PAYLOAD_AUDIT       # Linux / macOS
$env:GOVERNANCE_PAYLOAD_AUDIT="0"   # Windows PowerShell
```

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `audit_log.jsonl` | 所有 session 的原始記錄（JSONL，不 commit） |
| `L0-baseline.md` | L0 任務 token 分布報告 |
| `L1-baseline.md` | L1 任務 token 分布報告 |
| `onboarding-baseline.md` | Onboarding 任務 token 分布報告 |
| `step7-rebaseline-checklist.md` | Step 7 完成後的重測清單與記錄模板 |
| `README.md` | 本文件 |

## 解讀報告

- **Top 3 Token 黑洞**：優先砍除或摘要化的目標
- **Domain Contract 占比 > Governance**：優先建立 adapter summary（Step 4）
- **Memory 占比 > Governance × 0.5**：優先推進 incremental memory（Step 3）

> ⚠️ `audit_log.jsonl` 不應 commit 進版本控制（已加入 .gitignore）
> baseline 報告（*.md）可以 commit
