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
if governance_escalation_present:
    escalation_present = True
```

**表面**：`artifacts/runtime/verdicts/{session_id}.json` 中的：
```json
{
  "override_or_escalation": {
    "escalation_present": true,
    "governance_escalation_present": true
  }
}
```

**語義**：
- `governance_escalation_present = True` 明確標示「governance 層偵測到 classification 變化」
- `escalation_present = True` 讓所有 verdict 消費者（reviewer 工具、CI pipeline）知道本 session 需要關注
- 這是獨立於 contract `oversight` 設定的 governance-layer 訊號

**為什麼兩種 change 都觸發**：
- Downgrade → governance strategy 收緊，reviewer 需確認收緊後的行為仍符合預期
- Upgrade anomaly → proxy 訊號不一致，reviewer 需調查訊號來源
- 兩者都屬於「classification 的實際行為與預期不一致」的情況，都值得 reviewer 注意

---

### 3. Classification session summary tool（本文件定義，已實作）

**用途**：讓 reviewer 和系統管理員看到跨 session 的 classification 分布統計。

**工具**：`governance_tools/classification_session_summary.py`

**輸入**：掃描 `artifacts/runtime/summaries/*.json`，讀取每個 session 的 `decision_context`

**輸出**：
```
[classification_session_summary]
summary=ok=True | sessions=5 | downgrades=2 | anomalies=0 | conservative_rate=0.2
session_count=5
downgrade_count=2
anomaly_count=0
conservative_downgrade_rate=0.2
[reason_distribution]
  context_degraded=1
  conservative_downgrade=1
[effective_class_distribution]
  instruction_capable=3
  instruction_limited=2
```

**主要用途**：

| 問題 | 對應指標 |
|------|---------|
| `conservative_downgrade` 是否異常高頻？ | `conservative_downgrade_rate` |
| `classification_anomaly_upgrade` 有無出現？ | `anomaly_count` |
| 哪個 effective class 最常見？ | `effective_class_distribution` |
| 有無未知 reason value 出現（schema drift）？ | `unknown_reasons` |

**預期的正常範圍**：
- `conservative_downgrade_rate` 應接近 0（如果高頻 > 10%，代表分類邏輯有漏洞）
- `anomaly_count` 應永遠為 0（任何非零值都需要調查）

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
