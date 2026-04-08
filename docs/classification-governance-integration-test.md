# Classification Governance Integration Test

> 更新日期：2026-04-08
> 目的：驗證 classification governance 在 `session_end`、verdict artifact 與 session summary 三個面向的最小整合行為。

## 範圍

這份文件只驗證目前已落地的 bounded slice：

- `runtime_hooks/core/session_end.py`
- `governance_tools/classification_session_summary.py`
- `tests/test_runtime_session_end.py`
- `tests/test_classification_session_summary.py`
- `_classification_governance_smoke.py`

這不是 full matrix 驗證，也不是 machine-authoritative classification system 驗證。

## 驗證目標

最小整合測試要回答 3 件事：

1. `session_end` 是否正確記錄 classification transition
2. verdict artifact 是否正確暴露 governance escalation 語義
3. `classification_session_summary` 是否正確聚合 policy flags

## Path 1：Session-End Transition Tracking

### 1. 正常情況：沒有 classification change

執行：

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "no_governance_escalation_when_class_unchanged"
```

預期：

- `decision_context.initial_agent_class = instruction_capable`
- `decision_context.effective_agent_class = instruction_capable`
- `decision_context.classification_changed = False`
- `decision_context.reclassification_reason = None`

### 2. 降級情況：instruction_capable -> instruction_limited

執行：

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "governance_escalation_on_classification_downgrade"
```

預期：

- `classification_changed = True`
- `reclassification_reason = context_degraded` 或 `conservative_downgrade`
- `override_or_escalation.governance_escalation_type = classification_downgrade`

### 3. 異常升級情況：wrapper_only -> instruction_capable

執行：

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "governance_escalation_on_anomaly_upgrade"
```

預期：

- `classification_changed = True`
- `reclassification_reason = classification_anomaly_upgrade`
- `override_or_escalation.governance_escalation_type = classification_anomaly_upgrade`

## Path 2：Classification Session Summary

### 1. 直接跑 pytest

執行：

```powershell
python -m pytest tests/test_classification_session_summary.py -q
```

預期：

- empty summaries 時 `policy_ok = True`
- downgrade session 會被算進 `downgrade_count`
- anomaly upgrade 會被算進 `anomaly_count`
- unknown reason 會進 `unknown_reasons`

### 2. 直接跑 CLI

執行：

```powershell
python governance_tools/classification_session_summary.py --project-root .
```

輸出至少應有：

```text
[classification_session_summary]
[policy_flags]
[reason_distribution]
[effective_class_distribution]
```

### 3. Policy Flags 解讀

目前的 policy flags 只做 bounded summary semantics：

| flag | 意義 |
| --- | --- |
| `anomaly_alert` | 出現 `classification_anomaly_upgrade`，需要人工調查 |
| `classifier_review` | `conservative_downgrade_rate` 高於目前門檻，屬 drift signal |
| `taxonomy_breach` | 出現未知 `reclassification_reason`，代表 taxonomy drift |

`policy_ok = False` 表示至少一個 flag 被觸發，不等於 runtime verdict 被改寫。

## Path 3：Isolated Smoke Test

這個 smoke 只驗最小 companion slice，不應污染真實 `artifacts/runtime/summaries/`。

執行：

```powershell
python _classification_governance_smoke.py --project-root .
```

目前 smoke 會在隔離 temp root 建 3 個 mock summary：

- 2 個正常 session
- 1 個 downgrade session

預期：

```text
[classification_session_summary]
session_count=3
downgrade_count=1
anomaly_count=0
policy_ok=True
SMOKE TEST PASS
```

## 建議驗證順序

1. `python -m pytest tests/test_classification_session_summary.py -q`
2. `python -m pytest tests/test_runtime_session_end.py -q -k "governance_escalation"`
3. `python _classification_governance_smoke.py --project-root .`

## 不在本文件範圍內

以下內容刻意不在這份整合測試範圍內：

- full signal × full surface coverage
- machine-facing advisory authority
- post-hoc taxonomy normalization
- cross-repo aggregation semantics
- multi-agent classification orchestration

## 判讀邊界

這份驗證通過，只代表：

- classification governance 的 bounded runtime slice 已可被測試與聚合
- transition tracking、verdict escalation 語義、summary policy flags 三者一致

這不代表：

- classification system 已完全完成
- downstream automation 可直接拿 summary flags 當裁決權
- anomaly / downgrade taxonomy 已經 completeness-first
