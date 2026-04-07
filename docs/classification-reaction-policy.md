# Classification Reaction Policy

## 目的

這份文件定義當 governance classification 發生變化時，系統的**具體反應**。

它只做兩件事：
1. 每種 classification change 觸發哪些 downstream surface 反應
2. 哪些反應已實作，哪些是未來工作

這是 `docs/classification-transition-semantics.md` 的延伸。
那份文件說清楚「哪些 transition 合法，以及 session_end 的 runtime reaction（warning 發出）」；
這份文件說清楚「那個 warning 之後，還有哪些 downstream surface 受到影響」。

---

## 已實作的 Reaction

### 1. Session-end warnings（classification-transition-semantics.md 定義）

**觸發條件**：`classification_changed == True`

**動作**：
- Downgrade：`warnings[]` 中加入 `"governance: classification_downgrade — ..."` advisory
- Upgrade anomaly：`warnings[]` 中加入 `"governance: classification_anomaly — ..."` advisory

**表面**：session_end return dict 的 `warnings[]` 欄位

---

### 2. Verdict artifact escalation（本文件定義，已實作）

**觸發條件**：`classification_changed == True`（downgrade 或 upgrade anomaly 均觸發）

**動作**：
```python
# _build_verdict_artifact() 中
governance_escalation_present = decision_context.get("classification_changed") is True
governance_escalation_type = None
if governance_escalation_present:
    escalation_present = True
    if reclassification_reason == "classification_anomaly_upgrade":
        governance_escalation_type = "classification_anomaly_upgrade"
    else:
        governance_escalation_type = "classification_downgrade"
```

**表面**：`artifacts/runtime/verdicts/{session_id}.json` 中的：
```json
{
  "override_or_escalation": {
    "escalation_present": true,
    "governance_escalation_present": true,
    "governance_escalation_type": "classification_downgrade"
  }
}
```

**`governance_escalation_type` 語義**：

| 值 | 事件本質 | Consumer 應如何解讀 |
|----|---------|-------------------|
| `"classification_downgrade"` | Agent 能力退化；governance strategy 收緊 | 確認收緊後行為是否仍符合預期；檢查 reclassification_reason |
| `"classification_anomaly_upgrade"` | Proxy 訊號前後不一致；分類器可疑 | 調查 proxy signal 來源；不代表 agent 能力真的回升 |
| `null` | 無 classification change | 不需要特別注意 |

**為什麼區分兩種 escalation type**：
- Downgrade 和 anomaly upgrade 本質不同：前者是 agent 路徑變化，後者是分類器自身的一致性問題
- Consumer 不應把 `"governance_escalation_present": true` 當成單一信號——它代表兩種截然不同的問題來源
- `governance_escalation_type` 讓 CI pipeline 和 reviewer 能做出不同的 triage 決定，而不是一律走同一條審查路徑

---

### 3. Classification session summary tool（本文件定義，已實作）

**用途**：讓 reviewer 和系統管理員看到跨 session 的 classification 分布統計。

**工具**：`governance_tools/classification_session_summary.py`

**輸入**：掃描 `artifacts/runtime/summaries/*.json`，讀取每個 session 的 `decision_context`

**輸出**：
```
[classification_session_summary]
summary=ok=True | policy_ok=True | sessions=5 | downgrades=2 | anomalies=0 | conservative_rate=0.2
session_count=5
downgrade_count=2
anomaly_count=0
conservative_downgrade_rate=0.2
[policy_flags]
  anomaly_alert=False  # hard invariant: any anomaly_count > 0 needs investigation
  classifier_review=False  # drift signal: conservative_downgrade_rate > 0.1
  taxonomy_breach=False  # schema drift: unknown reason values detected
[reason_distribution]
  context_degraded=1
  conservative_downgrade=1
[effective_class_distribution]
  instruction_capable=3
  instruction_limited=2
```

**`policy_flags` 語義**：

| 旗標 | 性質 | 觸發條件 | 應對方向 |
|------|------|---------|---------|
| `anomaly_alert` | Hard invariant | `anomaly_count > 0` | 調查 proxy 訊號不一致來源；這不應出現在正常運作中 |
| `classifier_review` | Drift signal | `conservative_downgrade_rate > 10%` | 審查分類決策邏輯；尋找未處理的 edge case |
| `taxonomy_breach` | Schema contract | `unknown_reasons` 非空 | 檢查 session_end 版本；reason 值是否與 taxonomy 不符 |

**關於 `conservative_downgrade_rate` 的判讀**：

這個指標不應追求「接近 0」的絕對標準。
在某些環境（context 不穩定、instruction surface 不完整）下，適度的 conservative_downgrade 是正常的。

更有意義的問題是：

- 這個比率是否相對穩定（沒有突然暴增）？
- 它是否在某個 adapter 版本或環境變更後驟升？
- 它是否成為 downgrade 的「主導原因」而非少數例外？

10% 閾值是 drift indicator，不是 zero-tolerance invariant。

---

## 未來工作（超出目前範圍）

| Reaction | 說明 | 阻礙 |
|---------|------|------|
| Mid-session class lock | Session 內一旦 downgrade，有效 class 即使後期 proxy 回升也不改變 | 需要 mid-session checkpoint（目前只有 session start/end 兩點） |
| Downstream governance threshold adaptation | Downgrade 後，enforcement threshold 自動收緊 | 需要 enforcement layer 讀取 classification 狀態 |
| Subsequent session conservative default | 前一 session 如果 downgrade，下一 session 的初始 class 偏保守 | 需要 cross-session state（目前每 session 各自獨立分類） |
| Reviewer surface annotation | Trust signal 或 reviewer handoff summary 顯示 classification downgrade flag | reviewer 工具目前不讀 session runtime artifacts |

---

## 與現有文件的對應

| 文件 | 覆蓋範圍 |
|------|---------|
| `docs/classification-evidence-semantics.md` | 每個 evidence 欄位代表什麼（不能代表什麼） |
| `docs/classification-transition-semantics.md` | 哪些 transition 合法 + reclassification_reason 允許值 + session_end warnings |
| `docs/classification-reaction-policy.md`（本文件） | Warning 之後，哪些 downstream surface 受影響，以及統計工具 |
| `docs/governance-strategy-runtime.md` | Classification 決策規則與 governance_strategy 映射 |
