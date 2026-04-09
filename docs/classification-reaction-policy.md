# Classification Reaction Policy：classification change 對下游 surface 的影響

## 目的

這份文件定義 governance classification 變動後，哪些 downstream surface 應該收到 reaction，以及 reaction 的位階是什麼。

它和 `docs/classification-transition-semantics.md` 的分工是：

- transition semantics：哪些變動合法、reason 是什麼
- reaction policy：這些變動怎麼被投影到 warnings、artifacts、summary tools

---

## 目前的 reaction surfaces

### 1. `session_end` warnings

觸發條件：

- `classification_changed == True`

行為：

- downgrade 時，`warnings[]` 增加 `classification_downgrade` advisory
- anomaly upgrade 時，`warnings[]` 增加 `classification_anomaly` advisory

來源：

- `session_end` return dict 的 `warnings[]`

### 2. Verdict artifact escalation

觸發條件：

- `classification_changed == True`

行為：

- `override_or_escalation.governance_escalation_present = true`
- `governance_escalation_type` 依 reason 區分：
  - `classification_downgrade`
  - `classification_anomaly_upgrade`

這個 escalation type 的作用，是讓下游 consumer 不只知道「有 escalation」，也知道 escalation 的性質是保守 downgrade，還是 anomaly。

### 3. Classification session summary tool

用途：

- 讓 reviewer / maintainer 看到某段期間內 classification 漂移的分布

主要輸出：

- `downgrade_count`
- `anomaly_count`
- `conservative_downgrade_rate`
- `policy_flags`
- `reason_distribution`
- `effective_class_distribution`

## `policy_flags` 語義

| Flag | 類型 | 觸發條件 | 代表什麼 |
|---|---|---|---|
| `anomaly_alert` | hard invariant | `anomaly_count > 0` | proxy inconsistency 需要立即調查 |
| `classifier_review` | drift signal | `conservative_downgrade_rate > threshold` | downgrade 分布偏高，需要回看 classifier / adapter |
| `taxonomy_breach` | schema contract | unknown reason values 出現 | `reclassification_reason` 脫離 taxonomy |

## `policy_ok` 的解讀

`policy_ok = False` 不代表某個單一 hard failure。  
它只是壓縮後的總覽布林值。

真正需要拿來 triage 的，應該是 `policy_flags`：

- 哪個是 hard invariant
- 哪個是 drift signal
- 哪個是 schema breach

consumer 不應只看 `policy_ok`。

## Conservative Downgrade Threshold

`conservative_downgrade_rate` 的 threshold 應被視為 drift indicator，不是 zero-tolerance invariant。

它主要在回答：

- adapter / observation baseline 是否過於保守
- 某種 agent class 是否一直被 proxy 拉低
- 是否需要回頭看 classification evidence 的設計

這個 rate 不應被誤讀成：

- 只要大於 0 就是系統壞掉
- 只要偏高就代表 agent 一定不可用

## 目前不做的 reaction

以下 reaction 目前都**不做**：

- mid-session class lock
- 因 downgrade 直接調整 enforcement threshold
- 跨 session 持續保守預設
- 把 classification 直接寫進 hard gate

## 相關文件

- `docs/classification-evidence-semantics.md`
- `docs/classification-transition-semantics.md`
- `docs/governance-strategy-runtime.md`

## 一句話結論

classification reaction policy 目前只負責把變動安全地投影到 reviewer-visible 與 artifact-visible surface；它不是新的 authority source，也不是新的 enforcement engine。
