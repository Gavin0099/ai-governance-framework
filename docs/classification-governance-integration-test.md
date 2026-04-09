# Classification Governance 整合測試

> 更新日期：2026-04-08  
> 目的：驗證 classification governance 在 `session_end`、verdict artifact 與 session summary 之間，是否維持 bounded companion slice 的一致性

## 範圍

這份測試只覆蓋目前已落地的 bounded slice：
- `runtime_hooks/core/session_end.py`
- `governance_tools/classification_session_summary.py`
- `tests/test_runtime_session_end.py`
- `tests/test_classification_session_summary.py`
- `_classification_governance_smoke.py`

它不是 full matrix 測試，也不是 machine-authoritative classification system 測試。

## 測試目標

這份整合測試主要驗三件事：
1. `session_end` 能否正確記錄 classification transition
2. verdict artifact 能否正確帶出 governance escalation metadata
3. `classification_session_summary` 能否正確產出 policy flags

## Path 1：Session-End Transition Tracking

### 1. 無 classification change

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "no_governance_escalation_when_class_unchanged"
```

預期：
- `decision_context.initial_agent_class = instruction_capable`
- `decision_context.effective_agent_class = instruction_capable`
- `decision_context.classification_changed = False`
- `decision_context.reclassification_reason = None`

### 2. 合法 downgrade：`instruction_capable -> instruction_limited`

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "governance_escalation_on_classification_downgrade"
```

預期：
- `classification_changed = True`
- `reclassification_reason = context_degraded` 或 `conservative_downgrade`
- `override_or_escalation.governance_escalation_type = classification_downgrade`

### 3. 異常 upgrade：`wrapper_only -> instruction_capable`

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "governance_escalation_on_anomaly_upgrade"
```

預期：
- `classification_changed = True`
- `reclassification_reason = classification_anomaly_upgrade`
- `override_or_escalation.governance_escalation_type = classification_anomaly_upgrade`

## Path 2：Classification Session Summary

### 1. 執行 pytest

```powershell
python -m pytest tests/test_classification_session_summary.py -q
```

預期：
- empty summaries 時 `policy_ok = True`
- downgrade session 會累積 `downgrade_count`
- anomaly upgrade 會累積 `anomaly_count`
- unknown reason 會進 `unknown_reasons`

### 2. 執行 CLI

```powershell
python governance_tools/classification_session_summary.py --project-root .
```

輸出至少應包含：
```text
[classification_session_summary]
[policy_flags]
[reason_distribution]
[effective_class_distribution]
```

### 3. Policy Flags 解讀

| flag | 意義 |
|---|---|
| `anomaly_alert` | 出現 `classification_anomaly_upgrade`，代表有 anomaly 需額外審查 |
| `classifier_review` | `conservative_downgrade_rate` 高於門檻，代表 drift signal |
| `taxonomy_breach` | 出現未知 `reclassification_reason`，代表 taxonomy drift |

`policy_ok = False` 代表 policy flags 被觸發，但不等於 runtime verdict 自動失敗。

## Path 3：Isolated Smoke Test

這個 smoke 用來驗 companion slice 的基本連動，不污染真實 `artifacts/runtime/summaries/`。

```powershell
python _classification_governance_smoke.py --project-root .
```

預期：
```text
[classification_session_summary]
session_count=3
downgrade_count=1
anomaly_count=0
policy_ok=True
SMOKE TEST PASS
```

## 一句總結

這份 integration test 的目的，不是把 classification governance 升格成新的 authority，而是確認 companion slice 在 `session_end`、summary 與 smoke 之間保持一致。
